from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from payments.models import Payment
from products.models import Product

from .models import Order, OrderItem, OrderStatusHistory


STATUS_TRANSITIONS = {
    Order.STATUS_PENDING: {Order.STATUS_CONFIRMED, Order.STATUS_CANCELLED},
    Order.STATUS_CONFIRMED: {Order.STATUS_PROCESSING, Order.STATUS_CANCELLED},
    Order.STATUS_PROCESSING: {Order.STATUS_SHIPPED, Order.STATUS_CANCELLED},
    Order.STATUS_SHIPPED: {Order.STATUS_DELIVERED},
    Order.STATUS_DELIVERED: set(),
    Order.STATUS_CANCELLED: set(),
}


@transaction.atomic
def transition_order(*, order_id, new_status, actor, note=""):
    order = Order.objects.select_for_update().get(pk=order_id)
    allowed = STATUS_TRANSITIONS.get(order.order_status, set())
    if new_status not in allowed:
        raise ValidationError("This order status change is not allowed.")

    if new_status == Order.STATUS_CANCELLED and order.stock_deducted:
        items = list(
            OrderItem.objects.filter(order=order)
            .values("product_id", "quantity")
            .order_by("product_id")
        )
        quantities = {}
        for item in items:
            quantities[item["product_id"]] = (
                quantities.get(item["product_id"], 0) + item["quantity"]
            )
        list(
            Product.objects.select_for_update()
            .filter(pk__in=quantities)
            .order_by("pk")
        )
        for product_id, quantity in quantities.items():
            Product.objects.filter(pk=product_id).update(
                stock_quantity=F("stock_quantity") + quantity,
                updated_at=timezone.now(),
            )
        order.stock_deducted = False

    previous_status = order.order_status
    order.order_status = new_status
    order.save(update_fields=["order_status", "stock_deducted", "updated_at"])
    OrderStatusHistory.objects.create(
        order=order,
        previous_status=previous_status,
        new_status=new_status,
        actor=actor,
        note=note,
    )
    return order


@transaction.atomic
def confirm_cod_collection(*, order_id, actor):
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .get(order_id=order_id)
    )
    if payment.payment_method != Order.PAYMENT_CASH_ON_DELIVERY:
        raise ValidationError("Only cash-on-delivery collection can be confirmed here.")
    if payment.status == Payment.STATUS_PAID:
        return payment
    if payment.status != Payment.STATUS_PENDING:
        raise ValidationError("This payment is not awaiting collection.")
    if payment.order.order_status not in {
        Order.STATUS_SHIPPED,
        Order.STATUS_DELIVERED,
    }:
        raise ValidationError("COD collection can be confirmed after the order ships.")

    payment.mark_collected(actor)
    Order.objects.filter(pk=order_id).update(
        payment_status=Payment.STATUS_PAID,
        updated_at=timezone.now(),
    )
    return payment
