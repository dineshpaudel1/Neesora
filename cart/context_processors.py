from django.db.models import Sum

from .models import CartItem


def cart_information(request):
    if request.user.is_authenticated:
        cart_items = CartItem.objects.filter(user=request.user)
    elif request.session.session_key:
        cart_items = CartItem.objects.filter(session_key=request.session.session_key)
    else:
        return {"cart_item_count": 0}

    item_count = cart_items.aggregate(item_count=Sum("quantity"))["item_count"] or 0
    return {"cart_item_count": item_count}
