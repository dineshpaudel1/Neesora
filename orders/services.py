import secrets
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from cart.models import CartItem
from payments.models import Payment
from products.models import Product

from .models import Order, OrderItem, OrderStatusHistory


class CheckoutError(Exception):
    pass


def get_cart_items(user, session_key):
    items = CartItem.objects.select_related(
        "product__category",
    ).prefetch_related("product__images")
    if user.is_authenticated:
        return items.filter(user=user)
    return items.filter(session_key=session_key)


def get_shipping_fee():
    try:
        fee = Decimal(str(settings.FLAT_SHIPPING_FEE)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ImproperlyConfigured("FLAT_SHIPPING_FEE must be a valid decimal amount.") from error
    if fee < 0:
        raise ImproperlyConfigured("FLAT_SHIPPING_FEE cannot be negative.")
    return fee


@transaction.atomic
def create_order(*, user, session_key, checkout_reference, customer_data):
    cart_queryset = (
        CartItem.objects.select_for_update()
        .select_related("product")
        .order_by("product_id")
    )
    if user.is_authenticated:
        cart_queryset = cart_queryset.filter(user=user, session_key__isnull=True)
    else:
        cart_queryset = cart_queryset.filter(
            session_key=session_key,
            user__isnull=True,
        )
    cart_items = list(cart_queryset)
    if not cart_items:
        raise CheckoutError("Your shopping bag is empty.")

    product_ids = [item.product_id for item in cart_items]
    products = {
        product.pk: product
        for product in Product.objects.select_for_update()
        .filter(pk__in=product_ids)
        .order_by("pk")
    }
    subtotal = Decimal("0.00")
    for item in cart_items:
        product = products.get(item.product_id)
        if product is None or not product.is_available:
            raise CheckoutError(
                f"{item.product.name} is no longer available. Remove it from your bag to continue."
            )
        if item.quantity <= 0 or item.quantity > product.stock_quantity:
            raise CheckoutError(
                f"Only {product.stock_quantity} of {product.name} are currently available. "
                "Update your bag and try again."
            )
        subtotal += product.selling_price * item.quantity

    shipping_fee = get_shipping_fee()
    total = subtotal + shipping_fee
    order = Order.objects.create(
        user=user if user.is_authenticated else None,
        checkout_reference=checkout_reference,
        guest_access_token=secrets.token_urlsafe(32),
        customer_name=customer_data["customer_name"],
        phone_number=customer_data["phone_number"],
        email=customer_data.get("email", ""),
        address=customer_data["address"],
        city=customer_data["city"],
        district=customer_data["district"],
        ward_number=customer_data["ward_number"],
        province=customer_data["province"],
        postal_code=customer_data.get("postal_code", ""),
        order_notes=customer_data.get("order_notes", ""),
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        discount_amount=Decimal("0.00"),
        total_amount=total,
        payment_method=Order.PAYMENT_CASH_ON_DELIVERY,
        payment_status=Payment.STATUS_PENDING,
        order_status=Order.STATUS_PENDING,
        stock_deducted=True,
    )

    for item in cart_items:
        product = products[item.product_id]
        updated = Product.objects.filter(
            pk=product.pk,
            product_status=Product.STATUS_PUBLISHED,
            stock_quantity__gte=item.quantity,
        ).update(
            stock_quantity=F("stock_quantity") - item.quantity,
            updated_at=timezone.now(),
        )
        if updated != 1:
            raise CheckoutError(
                f"{product.name} stock changed while placing your order. Please review your bag."
            )
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            quantity=item.quantity,
            unit_price=product.selling_price,
        )

    Payment.objects.create(
        order=order,
        payment_method=Order.PAYMENT_CASH_ON_DELIVERY,
        amount=total,
        status=Payment.STATUS_PENDING,
    )
    OrderStatusHistory.objects.create(
        order=order,
        previous_status="",
        new_status=Order.STATUS_PENDING,
        actor=user if user.is_authenticated else None,
        note="Order placed.",
    )
    CartItem.objects.filter(pk__in=[item.pk for item in cart_items]).delete()
    return order
