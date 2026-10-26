from django.db import transaction

from .models import CartItem


@transaction.atomic
def merge_session_cart(user, session_key):
    if not session_key:
        return
    session_items = list(
        CartItem.objects.select_for_update()
        .filter(user__isnull=True, session_key=session_key)
        .select_related("product")
        .order_by("product_id")
    )
    for item in session_items:
        existing = CartItem.objects.select_for_update().filter(
            user=user,
            product_id=item.product_id,
        ).first()
        if existing:
            quantity = existing.quantity + item.quantity
            if item.product.stock_quantity > 0:
                quantity = min(quantity, item.product.stock_quantity)
            existing.quantity = quantity
            existing.save(update_fields=["quantity", "updated_at"])
            item.delete()
        else:
            item.user = user
            item.session_key = None
            item.save(update_fields=["user", "session_key"])
