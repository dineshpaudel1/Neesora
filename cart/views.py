from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .models import CartItem, WishlistItem


def _get_session_key(request):
    if request.session.session_key is None:
        request.session.create()
    return request.session.session_key


def _get_cart_items(request):
    if request.user.is_authenticated:
        return CartItem.objects.filter(user=request.user).select_related('product__category')
    return CartItem.objects.filter(session_key=_get_session_key(request)).select_related('product__category')


def _get_wishlist_items(request):
    if request.user.is_authenticated:
        return WishlistItem.objects.filter(user=request.user).select_related('product__category')
    return WishlistItem.objects.filter(session_key=_get_session_key(request)).select_related('product__category')


def _safe_redirect(request, fallback_name, **kwargs):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and not next_url.startswith('http'):
        return redirect(next_url)
    return redirect(fallback_name, **kwargs)


@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id, product_status=Product.STATUS_PUBLISHED)
    if product.stock_quantity <= 0:
        messages.error(request, 'This product is currently out of stock.')
        return _safe_redirect(request, 'products:product_detail', slug=product.slug)

    quantity = int(request.POST.get('quantity', 1) or 1)
    if quantity <= 0:
        messages.warning(request, 'Please choose a valid quantity.')
        return _safe_redirect(request, 'products:product_detail', slug=product.slug)

    if quantity > product.stock_quantity:
        quantity = product.stock_quantity

    if request.user.is_authenticated:
        item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'quantity': quantity},
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock_quantity)
            item.save(update_fields=['quantity'])
    else:
        item, created = CartItem.objects.get_or_create(
            session_key=_get_session_key(request),
            product=product,
            defaults={'quantity': quantity},
        )
        if not created:
            item.quantity = min(item.quantity + quantity, product.stock_quantity)
            item.save(update_fields=['quantity'])

    messages.success(request, f'{product.name} was added to your bag.')
    return _safe_redirect(request, 'products:product_detail', slug=product.slug)


@require_POST
def update_cart_quantity(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    quantity = int(request.POST.get('quantity', 1) or 1)
    if quantity <= 0:
        return remove_from_cart(request, product_id)

    if request.user.is_authenticated:
        item = get_object_or_404(CartItem, user=request.user, product=product)
    else:
        item = get_object_or_404(CartItem, session_key=_get_session_key(request), product=product)

    if product.stock_quantity and quantity > product.stock_quantity:
        quantity = product.stock_quantity
        messages.warning(request, 'Only available stock has been added.')
    item.quantity = quantity
    item.save(update_fields=['quantity'])
    messages.success(request, 'Your bag was updated.')
    return redirect('cart:cart')


@require_POST
def remove_from_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.user.is_authenticated:
        CartItem.objects.filter(user=request.user, product=product).delete()
    else:
        CartItem.objects.filter(session_key=_get_session_key(request), product=product).delete()
    messages.info(request, 'Item removed from your bag.')
    return redirect('cart:cart')


@require_POST
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id, product_status=Product.STATUS_PUBLISHED)
    if request.user.is_authenticated:
        item, created = WishlistItem.objects.get_or_create(user=request.user, product=product)
    else:
        item, created = WishlistItem.objects.get_or_create(
            session_key=_get_session_key(request),
            product=product,
        )
    if created:
        messages.success(request, f'{product.name} was added to your wishlist.')
    else:
        messages.info(request, f'{product.name} is already in your wishlist.')
    return _safe_redirect(request, 'products:product_detail', slug=product.slug)


@require_POST
def remove_from_wishlist(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.user.is_authenticated:
        WishlistItem.objects.filter(user=request.user, product=product).delete()
    else:
        WishlistItem.objects.filter(session_key=_get_session_key(request), product=product).delete()
    messages.info(request, 'Item removed from your wishlist.')
    return redirect('cart:wishlist')


def cart_detail(request):
    items = _get_cart_items(request)
    subtotal = sum(item.line_total for item in items)
    shipping_fee = Decimal(str(getattr(settings, 'FLAT_SHIPPING_FEE', 0) or 0))
    total = subtotal + shipping_fee
    context = {
        'cart_items': items,
        'cart_total': total,
        'subtotal': subtotal,
        'shipping_fee': shipping_fee,
        'item_count': sum(item.quantity for item in items),
    }
    return render(request, 'cart/cart.html', context)


def wishlist_view(request):
    items = _get_wishlist_items(request)
    context = {
        'wishlist_items': items,
        'wishlist_count': items.count(),
    }
    return render(request, 'cart/wishlist.html', context)
