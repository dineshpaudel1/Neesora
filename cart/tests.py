from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product

from .models import CartItem


class ShoppingCartTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Cart bags")
        self.product = Product.objects.create(
            name="Cart Tote",
            sku="CART-TOTE-1",
            description="A bag for cart tests.",
            category=category,
            price=Decimal("1500.00"),
            stock_quantity=5,
            product_status=Product.STATUS_PUBLISHED,
        )

    def test_guest_can_add_update_review_and_remove_cart_items(self):
        added = self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {"quantity": "2"},
        )
        self.assertEqual(added.status_code, 302)
        item = CartItem.objects.get(product=self.product)
        self.assertEqual(item.quantity, 2)

        updated = self.client.post(
            reverse("cart:update_cart", args=[self.product.pk]),
            {"quantity": "3"},
        )
        self.assertRedirects(updated, reverse("cart:cart"))
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)

        cart = self.client.get(reverse("cart:cart"))
        self.assertContains(cart, "Cart Tote")
        self.assertContains(cart, "4500")

        removed = self.client.post(
            reverse("cart:remove_from_cart", args=[self.product.pk]),
        )
        self.assertRedirects(removed, reverse("cart:cart"))
        self.assertFalse(CartItem.objects.filter(product=self.product).exists())

    def test_cart_rejects_invalid_quantity_and_respects_stock(self):
        self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {"quantity": "invalid"},
        )
        self.assertFalse(CartItem.objects.exists())

        self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {"quantity": "9"},
        )
        item = CartItem.objects.get(product=self.product)
        self.assertEqual(item.quantity, self.product.stock_quantity)

        Product.objects.filter(pk=self.product.pk).update(stock_quantity=0)
        self.client.post(
            reverse("cart:update_cart", args=[self.product.pk]),
            {"quantity": "1"},
        )
        item.refresh_from_db()
        self.assertEqual(item.quantity, self.product.stock_quantity)
        self.assertContains(self.client.get(reverse("cart:cart")), "currently unavailable")

    def test_header_cart_count_reflects_guest_quantity(self):
        self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {"quantity": "2"},
        )

        response = self.client.get(reverse("core:home"))

        self.assertContains(response, 'aria-label="Shopping bag, 2 items"')
        self.assertContains(response, 'class="cart-count" aria-hidden="true">2')

    def test_buy_now_keeps_existing_cart_items_and_opens_real_checkout(self):
        existing_product = Product.objects.create(
            name="Existing bag",
            sku="CART-EXISTING-1",
            description="Already in the bag.",
            category=self.product.category,
            price=Decimal("1200.00"),
            stock_quantity=3,
            product_status=Product.STATUS_PUBLISHED,
        )
        self.client.post(
            reverse("cart:add_to_cart", args=[existing_product.pk]),
            {"quantity": "2"},
        )

        response = self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {
                "quantity": "1",
                "next": reverse("orders:checkout"),
            },
        )

        self.assertRedirects(response, reverse("orders:checkout"))
        self.assertEqual(CartItem.objects.get(product=existing_product).quantity, 2)
        self.assertEqual(CartItem.objects.get(product=self.product).quantity, 1)
        checkout = self.client.get(reverse("orders:checkout"))
        self.assertEqual(checkout.status_code, 200)
        self.assertContains(checkout, "Existing bag")
        self.assertContains(checkout, "Cart Tote")
