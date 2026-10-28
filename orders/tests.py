import secrets
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.urls import reverse

from cart.models import CartItem
from payments.models import Payment
from products.models import Category, Product

from .models import Order, OrderItem, OrderStatusHistory


@override_settings(NEESORA_ADMIN_USERNAME="orders-admin")
class AdminOrderManagementTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="orders-admin",
            email="orders-admin@example.com",
            password="OrdersAdminPass!842",
        )
        self.customer = get_user_model().objects.create_user(
            username="orders-customer",
            email="orders-customer@example.com",
            password="OrdersCustomerPass!842",
        )
        self.client.force_login(self.admin)
        self.order = Order.objects.create(
            user=self.customer,
            order_number="NSR-ORDER-1",
            customer_name="Bag Customer",
            phone_number="9800000000",
            email="buyer@example.com",
            address="Mangalbazar",
            city="Lalitpur",
            province="Bagmati",
            postal_code="44700",
            subtotal=Decimal("1500.00"),
            total_amount=Decimal("1600.00"),
        )
        category = Category.objects.create(name="Order bags")
        self.product = Product.objects.create(
            name="Order tote",
            sku="ORDER-TOTE-1",
            description="An ordered tote.",
            category=category,
            price=Decimal("1500.00"),
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=Decimal("1500.00"),
        )
        self.payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("1600.00"),
        )

    def test_order_list_searches_and_filters_using_existing_status(self):
        response = self.client.get(
            reverse("myadmin:orders"),
            {"q": "Bag Customer", "status": Order.STATUS_PENDING},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NSR-ORDER-1")
        self.assertEqual(list(response.context["orders"]), [self.order])

    def test_order_list_filters_payment_method_status_and_date(self):
        response = self.client.get(
            reverse("myadmin:orders"),
            {
                "payment_method": Order.PAYMENT_CASH_ON_DELIVERY,
                "payment_status": Payment.STATUS_PENDING,
                "date_from": self.order.created_at.date().isoformat(),
                "date_to": self.order.created_at.date().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["orders"]), [self.order])
        self.assertContains(response, "Cash on Delivery")

    def test_dashboard_reports_order_status_and_pending_payment_counts(self):
        response = self.client.get(reverse("myadmin:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_orders"], 1)
        self.assertEqual(response.context["pending_orders"], 1)
        self.assertEqual(response.context["pending_payments"], 1)
        self.assertIn(
            (Order.STATUS_PENDING, "Pending", 1),
            response.context["order_status_summary"],
        )
        self.assertContains(response, "Pending payments")

    def test_order_detail_displays_recorded_items_and_available_workflow_actions(self):
        response = self.client.get(
            reverse("myadmin:order_detail", args=[self.order.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Order tote")
        self.assertContains(response, "Update status")
        self.assertContains(response, "Status history")
        self.assertContains(response, "1600.00")

    def test_order_detail_does_not_allow_state_changes_by_post(self):
        response = self.client.post(
            reverse("myadmin:order_detail", args=[self.order.pk]),
            {"order_status": Order.STATUS_CANCELLED},
        )

        self.assertEqual(response.status_code, 405)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_PENDING)

    def test_admin_status_transition_is_audited_and_does_not_mark_payment_paid(self):
        response = self.client.post(
            reverse("myadmin:order_status", args=[self.order.pk]),
            {"order_status": Order.STATUS_CONFIRMED, "note": "Stock checked."},
        )

        self.assertRedirects(
            response,
            reverse("myadmin:order_detail", args=[self.order.pk]),
        )
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_CONFIRMED)
        self.assertEqual(self.order.payment_status, Payment.STATUS_PENDING)
        self.assertEqual(self.payment.status, Payment.STATUS_PENDING)
        history = self.order.status_history.get(new_status=Order.STATUS_CONFIRMED)
        self.assertEqual(history.previous_status, Order.STATUS_PENDING)
        self.assertEqual(history.actor, self.admin)
        self.assertEqual(history.note, "Stock checked.")

    def test_invalid_order_status_transition_is_rejected(self):
        response = self.client.post(
            reverse("myadmin:order_status", args=[self.order.pk]),
            {"order_status": Order.STATUS_DELIVERED},
        )

        self.assertRedirects(
            response,
            reverse("myadmin:order_detail", args=[self.order.pk]),
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_PENDING)
        self.assertFalse(
            OrderStatusHistory.objects.filter(
                order=self.order,
                new_status=Order.STATUS_DELIVERED,
            ).exists()
        )

    def test_cancelling_order_restores_stock_once(self):
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=0)
        self.order.stock_deducted = True
        self.order.save(update_fields=["stock_deducted"])

        response = self.client.post(
            reverse("myadmin:order_status", args=[self.order.pk]),
            {"order_status": Order.STATUS_CANCELLED},
        )

        self.assertRedirects(
            response,
            reverse("myadmin:order_detail", args=[self.order.pk]),
        )
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)
        self.assertFalse(self.order.stock_deducted)
        self.client.post(
            reverse("myadmin:order_status", args=[self.order.pk]),
            {"order_status": Order.STATUS_CANCELLED},
        )
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

    def test_cod_collection_requires_shipment_and_is_audited(self):
        blocked = self.client.post(
            reverse("myadmin:confirm_payment", args=[self.order.pk]),
        )
        self.assertRedirects(
            blocked,
            reverse("myadmin:order_detail", args=[self.order.pk]),
        )
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PENDING)

        for status in (
            Order.STATUS_CONFIRMED,
            Order.STATUS_PROCESSING,
            Order.STATUS_SHIPPED,
        ):
            self.client.post(
                reverse("myadmin:order_status", args=[self.order.pk]),
                {"order_status": status},
            )
        collected = self.client.post(
            reverse("myadmin:confirm_payment", args=[self.order.pk]),
        )

        self.assertRedirects(
            collected,
            reverse("myadmin:order_detail", args=[self.order.pk]),
        )
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.STATUS_PAID)
        self.assertEqual(self.payment.amount, self.order.total_amount)
        self.assertEqual(self.payment.collected_by, self.admin)
        self.assertIsNotNone(self.payment.collected_at)
        self.assertEqual(self.order.payment_status, Payment.STATUS_PAID)

    def test_customer_list_and_profile_show_non_sensitive_customer_data(self):
        list_response = self.client.get(reverse("myadmin:customers"))
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "orders-customer@example.com")
        self.assertNotContains(list_response, "pbkdf2_sha256")

        detail_response = self.client.get(
            reverse("myadmin:customer_detail", args=[self.customer.pk])
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "NSR-ORDER-1")
        self.assertNotContains(detail_response, "pbkdf2_sha256")

    def test_anonymous_cannot_access_order_or_customer_management(self):
        self.client.logout()

        order_response = self.client.get(reverse("myadmin:orders"))
        customers_response = self.client.post(reverse("myadmin:customers"))

        self.assertRedirects(
            order_response,
            f"{reverse('myadmin:login')}?next={reverse('myadmin:orders')}",
        )
        self.assertRedirects(
            customers_response,
            f"{reverse('myadmin:login')}?next={reverse('myadmin:customers')}",
        )

    def test_ordinary_customer_cannot_change_order_or_payment(self):
        self.client.force_login(self.customer)
        status_response = self.client.post(
            reverse("myadmin:order_status", args=[self.order.pk]),
            {"order_status": Order.STATUS_CONFIRMED},
        )
        payment_response = self.client.post(
            reverse("myadmin:confirm_payment", args=[self.order.pk]),
        )

        self.assertRedirects(status_response, reverse("core:home"))
        self.assertRedirects(payment_response, reverse("core:home"))
        self.order.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_PENDING)
        self.assertEqual(self.payment.status, Payment.STATUS_PENDING)


@override_settings(FLAT_SHIPPING_FEE="100.00")
class CustomerCheckoutTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Checkout bags")
        self.product = Product.objects.create(
            name="Checkout Tote",
            sku="CHECKOUT-TOTE-1",
            description="A tote for checkout tests.",
            category=self.category,
            price=Decimal("1600.00"),
            discount_price=Decimal("1500.00"),
            stock_quantity=5,
            product_status=Product.STATUS_PUBLISHED,
        )
        self.customer = get_user_model().objects.create_user(
            username="checkout-test-customer",
            email="checkout-test@example.com",
            password="CheckoutPass!482",
        )
        self.client.force_login(self.customer)

    def add_to_cart(self, quantity=2):
        self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {"quantity": str(quantity)},
        )

    def checkout_payload(self, response, **overrides):
        payload = {
            "customer_name": "Asha Customer",
            "email": "",
            "phone_number": "9800000000",
            "province": "Bagmati",
            "district": "Lalitpur",
            "city": "Lalitpur Metropolitan City",
            "ward_number": "3",
            "address": "Mangalbazar, near the temple",
            "postal_code": "",
            "order_notes": "Please call on arrival.",
            "payment_method": Order.PAYMENT_CASH_ON_DELIVERY,
            "checkout_reference": response.context["form"]["checkout_reference"].value(),
            "terms_accepted": "on",
        }
        payload.update(overrides)
        return payload

    def test_checkout_redirects_unauthenticated_users_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={reverse('orders:checkout')}",
        )

    def test_checkout_page_requires_cart_and_shows_secure_checkout(self):
        empty = self.client.get(reverse("orders:checkout"))
        self.assertRedirects(empty, reverse("cart:cart"))

        self.add_to_cart()
        response = self.client.get(reverse("orders:checkout"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Secure checkout")
        self.assertContains(response, "Cash on Delivery")
        self.assertContains(response, "NPR 3100.00")
        self.assertContains(response, 'name="checkout_reference"')

    def test_authenticated_cod_checkout_creates_order_payment_and_clears_cart_once(self):
        self.add_to_cart(quantity=2)
        checkout_page = self.client.get(reverse("orders:checkout"))
        payload = self.checkout_payload(checkout_page)

        placed = self.client.post(reverse("orders:checkout"), payload)

        self.assertEqual(placed.status_code, 302)
        order = Order.objects.get()
        self.assertEqual(order.user, self.customer)
        self.assertEqual(order.customer_name, "Asha Customer")
        self.assertEqual(order.phone_number, "+9779800000000")
        self.assertEqual(order.email, "")
        self.assertEqual(order.district, "Lalitpur")
        self.assertEqual(order.ward_number, "3")
        self.assertEqual(order.subtotal, Decimal("3000.00"))
        self.assertEqual(order.shipping_fee, Decimal("100.00"))
        self.assertEqual(order.total_amount, Decimal("3100.00"))
        self.assertEqual(order.payment_status, Payment.STATUS_PENDING)
        self.assertEqual(order.order_status, Order.STATUS_PENDING)
        self.assertTrue(order.stock_deducted)
        item = order.items.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal("1500.00"))
        self.assertEqual(item.line_total, Decimal("3000.00"))
        payment = order.payment_record
        self.assertEqual(payment.amount, order.total_amount)
        self.assertEqual(payment.status, Payment.STATUS_PENDING)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)
        self.assertFalse(CartItem.objects.filter(user=self.customer).exists())
        self.assertTrue(order.status_history.filter(new_status=Order.STATUS_PENDING).exists())

        confirmation_url = placed["Location"]
        confirmation = self.client.get(confirmation_url)
        self.assertEqual(confirmation.status_code, 200)
        self.assertContains(confirmation, order.order_number)
        self.assertContains(confirmation, "NPR 3100.00")

        duplicate = self.client.post(reverse("orders:checkout"), payload)
        self.assertEqual(duplicate.status_code, 302)
        self.assertEqual(duplicate["Location"], confirmation_url)
        self.assertEqual(Order.objects.count(), 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

    def test_checkout_recalculates_price_and_preserves_historical_item_price(self):
        self.add_to_cart()
        checkout_page = self.client.get(reverse("orders:checkout"))
        payload = self.checkout_payload(checkout_page)
        self.product.price = Decimal("1700.00")
        self.product.discount_price = None
        self.product.save()

        self.client.post(reverse("orders:checkout"), payload)

        order = Order.objects.get()
        self.assertEqual(order.subtotal, Decimal("3400.00"))
        self.assertEqual(order.total_amount, Decimal("3500.00"))
        self.assertEqual(order.items.get().unit_price, Decimal("1700.00"))

    def test_invalid_phone_and_missing_address_do_not_create_orders(self):
        self.add_to_cart()
        checkout_page = self.client.get(reverse("orders:checkout"))
        bad_phone = self.client.post(
            reverse("orders:checkout"),
            self.checkout_payload(checkout_page, phone_number="123456"),
        )

        self.assertEqual(bad_phone.status_code, 200)
        self.assertContains(bad_phone, "valid 10-digit Nepal mobile number")
        self.assertEqual(Order.objects.count(), 0)

        bad_address = self.client.post(
            reverse("orders:checkout"),
            self.checkout_payload(checkout_page, ward_number="0", district=""),
        )
        self.assertEqual(bad_address.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(CartItem.objects.filter(user=self.customer).exists())

    def test_stock_is_revalidated_and_insufficient_stock_keeps_cart(self):
        self.add_to_cart(quantity=2)
        checkout_page = self.client.get(reverse("orders:checkout"))
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=1)

        response = self.client.post(
            reverse("orders:checkout"),
            self.checkout_payload(checkout_page),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Only 1 of Checkout Tote")
        self.assertEqual(Order.objects.count(), 0)
        self.assertTrue(CartItem.objects.filter(user=self.customer).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

    @patch("orders.services.Payment.objects.create", side_effect=DatabaseError("payment write failed"))
    def test_database_failure_rolls_back_order_items_stock_and_cart(self, _payment_create):
        self.add_to_cart(quantity=2)
        checkout_page = self.client.get(reverse("orders:checkout"))
        payload = self.checkout_payload(checkout_page)

        with self.assertRaises(DatabaseError):
            self.client.post(reverse("orders:checkout"), payload)

        self.assertFalse(Order.objects.exists())
        self.assertFalse(OrderItem.objects.exists())
        self.assertTrue(CartItem.objects.filter(user=self.customer).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_unsupported_payment_method_and_missing_terms_are_rejected(self):
        self.add_to_cart()
        checkout_page = self.client.get(reverse("orders:checkout"))

        response = self.client.post(
            reverse("orders:checkout"),
            self.checkout_payload(
                checkout_page,
                payment_method="online",
                terms_accepted="",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Order.objects.count(), 0)

    def test_confirmation_page_enforces_ownership_for_authenticated_orders(self):
        self.add_to_cart()
        checkout_page = self.client.get(reverse("orders:checkout"))
        self.client.post(reverse("orders:checkout"), self.checkout_payload(checkout_page))
        order = Order.objects.get()

        ok = self.client.get(
            reverse("orders:confirmation", args=[order.order_number, order.guest_access_token])
        )
        self.assertEqual(ok.status_code, 200)

        other = get_user_model().objects.create_user(
            username="other-confirm-customer",
            email="other-confirm@example.com",
            password="OtherPass!482",
        )
        self.client.force_login(other)
        denied = self.client.get(
            reverse("orders:confirmation", args=[order.order_number, order.guest_access_token])
        )
        self.assertEqual(denied.status_code, 403)

    def test_legacy_guest_order_confirmation_requires_secret_token(self):
        """Backward compat: existing guest orders in the database still use the token."""
        token = secrets.token_urlsafe(32)
        order = Order.objects.create(
            user=None,
            order_number="NSR-GUEST-LEGACY-1",
            customer_name="Legacy Guest",
            phone_number="+9779800000000",
            address="Old address",
            city="Lalitpur",
            province="Bagmati",
            subtotal=Decimal("1500.00"),
            total_amount=Decimal("1500.00"),
            guest_access_token=token,
        )
        self.client.logout()

        denied = self.client.get(
            reverse("orders:confirmation", args=[order.order_number, "wrong-token"])
        )
        self.assertEqual(denied.status_code, 403)

        ok = self.client.get(
            reverse("orders:confirmation", args=[order.order_number, order.guest_access_token])
        )
        self.assertEqual(ok.status_code, 200)

    def test_authenticated_checkout_is_added_to_only_owners_order_history(self):
        CartItem.objects.create(user=self.customer, product=self.product, quantity=1)
        checkout_page = self.client.get(reverse("orders:checkout"))

        self.client.post(
            reverse("orders:checkout"),
            self.checkout_payload(checkout_page),
        )

        order = Order.objects.get()
        self.assertEqual(order.user, self.customer)
        self.assertEqual(self.client.get(reverse("orders:orders")).status_code, 200)
        self.assertEqual(
            self.client.get(
                reverse("orders:order_detail", args=[order.order_number])
            ).status_code,
            200,
        )
        other_customer = get_user_model().objects.create_user(
            username="other-checkout-customer",
            email="other-checkout@example.com",
            password="StrongBagPass!482",
        )
        self.client.force_login(other_customer)
        self.assertEqual(
            self.client.get(
                reverse("orders:order_detail", args=[order.order_number])
            ).status_code,
            404,
        )


class CustomerCancelOrderTests(TestCase):
    """Tests for the customer-facing cancel order view."""

    def setUp(self):
        self.customer = get_user_model().objects.create_user(
            username="cancel-customer",
            email="cancel-customer@example.com",
            password="CancelPass!123",
        )
        category = Category.objects.create(name="Cancel bags")
        self.product = Product.objects.create(
            name="Cancellable Tote",
            sku="CANCEL-TOTE",
            description="A tote used in cancel tests.",
            category=category,
            price=Decimal("1200.00"),
            stock_quantity=5,
            product_status=Product.STATUS_PUBLISHED,
        )
        self.order = Order.objects.create(
            user=self.customer,
            order_number="NSR-CANCEL-1",
            customer_name="Cancel Customer",
            phone_number="+9779800000001",
            email="cancel-customer@example.com",
            address="Test address",
            city="Lalitpur",
            province="Bagmati",
            subtotal=Decimal("1200.00"),
            total_amount=Decimal("1200.00"),
            order_status=Order.STATUS_PENDING,
            stock_deducted=True,
        )
        OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=Decimal("1200.00"),
        )
        Product.objects.filter(pk=self.product.pk).update(stock_quantity=4)
        self.client.force_login(self.customer)

    def _cancel_url(self):
        return reverse("orders:cancel_order", args=[self.order.order_number])

    def test_customer_can_cancel_pending_order_and_stock_is_restored(self):
        response = self.client.post(self._cancel_url())

        self.assertRedirects(
            response,
            reverse("orders:order_detail", args=[self.order.order_number]),
        )
        self.order.refresh_from_db()
        self.product.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_CANCELLED)
        self.assertFalse(self.order.stock_deducted)
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertTrue(
            self.order.status_history.filter(new_status=Order.STATUS_CANCELLED).exists()
        )

    def test_customer_cannot_cancel_confirmed_order(self):
        self.order.order_status = Order.STATUS_CONFIRMED
        self.order.save(update_fields=["order_status"])

        response = self.client.post(self._cancel_url())

        self.assertRedirects(
            response,
            reverse("orders:order_detail", args=[self.order.order_number]),
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_CONFIRMED)

    def test_cancel_requires_post_not_get(self):
        response = self.client.get(self._cancel_url())
        self.assertEqual(response.status_code, 405)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_PENDING)

    def test_anonymous_cancel_redirects_to_login(self):
        self.client.logout()
        response = self.client.post(self._cancel_url())
        self.assertRedirects(
            response,
            f"{reverse('accounts:login')}?next={self._cancel_url()}",
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_PENDING)

    def test_other_customer_cannot_cancel_this_order(self):
        other = get_user_model().objects.create_user(
            username="other-cancel-customer",
            email="other-cancel@example.com",
            password="OtherPass!123",
        )
        self.client.force_login(other)
        response = self.client.post(self._cancel_url())
        self.assertEqual(response.status_code, 404)
        self.order.refresh_from_db()
        self.assertEqual(self.order.order_status, Order.STATUS_PENDING)

    def test_cancel_order_detail_shows_cancel_button_only_when_pending(self):
        # Pending — cancel button visible
        detail = self.client.get(
            reverse("orders:order_detail", args=[self.order.order_number])
        )
        self.assertContains(detail, "Cancel order")

        # Move to confirmed — cancel button gone
        self.order.order_status = Order.STATUS_CONFIRMED
        self.order.save(update_fields=["order_status"])
        detail_confirmed = self.client.get(
            reverse("orders:order_detail", args=[self.order.order_number])
        )
        self.assertNotContains(detail_confirmed, "Cancel order")
