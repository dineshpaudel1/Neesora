from decimal import Decimal
import secrets
from uuid import UUID, uuid4

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from accounts.models import CustomerProfile

from .forms import CheckoutForm
from .models import Order
from .services import CheckoutError, create_order, get_cart_items, get_shipping_fee
from .workflow import transition_order


def _checkout_session_key(request):
    if request.session.session_key is None:
        request.session.create()
    return request.session.session_key


def _checkout_reference(request, has_items):
    reference = request.session.get("checkout_reference")
    try:
        reference_uuid = UUID(str(reference))
    except (TypeError, ValueError):
        reference_uuid = None
    if reference_uuid is None or (
        has_items
        and Order.objects.filter(checkout_reference=reference_uuid).exists()
    ):
        reference = str(uuid4())
        request.session["checkout_reference"] = reference
        reference_uuid = UUID(reference)
    return reference_uuid


def _checkout_initial(request):
    initial = {"email": request.user.email} if request.user.is_authenticated else {}
    if request.user.is_authenticated:
        profile = CustomerProfile.objects.filter(user=request.user).first()
        if profile:
            initial.update({
                "customer_name": profile.full_name or request.user.get_full_name(),
                "phone_number": profile.phone_number,
                "address": profile.address,
                "city": profile.city,
                "province": profile.province,
                "postal_code": profile.postal_code,
            })
    return {key: value for key, value in initial.items() if value}


def _can_access_checkout_order(request, order, reference):
    if order.user_id is not None:
        return request.user.is_authenticated and order.user_id == request.user.pk
    return request.session.get("checkout_reference") == str(reference)


def _confirmation_redirect(order):
    return redirect(
        "orders:confirmation",
        order_number=order.order_number,
        access_token=order.guest_access_token,
    )


@login_required
@require_http_methods(["GET", "POST"])
def checkout(request):
    session_key = _checkout_session_key(request)
    if request.method == "POST":
        try:
            posted_reference = UUID(request.POST.get("checkout_reference", ""))
        except (TypeError, ValueError):
            posted_reference = None
        if posted_reference is not None:
            completed_order = Order.objects.filter(
                checkout_reference=posted_reference,
            ).first()
            if completed_order and _can_access_checkout_order(
                request,
                completed_order,
                posted_reference,
            ):
                return _confirmation_redirect(completed_order)

    items = get_cart_items(request.user, session_key)
    if not items.exists():
        messages.info(request, "Add an available product to your bag before checkout.")
        return redirect("cart:cart")

    reference = _checkout_reference(request, has_items=True)
    initial = _checkout_initial(request)
    if request.method == "POST":
        form = CheckoutForm(request.POST, checkout_reference=reference, initial=initial)
        if form.is_valid():
            submitted_reference = form.cleaned_data["checkout_reference"]
            existing_order = Order.objects.filter(
                checkout_reference=submitted_reference,
            ).first()
            if existing_order:
                if _can_access_checkout_order(request, existing_order, submitted_reference):
                    return _confirmation_redirect(existing_order)
                form.add_error(None, "This checkout has expired. Please reload the checkout page.")
            elif str(submitted_reference) != request.session.get("checkout_reference"):
                form.add_error(None, "This checkout has expired. Please reload the checkout page.")
            else:
                try:
                    order = create_order(
                        user=request.user,
                        session_key=session_key,
                        checkout_reference=submitted_reference,
                        customer_data=form.cleaned_data,
                    )
                except CheckoutError as error:
                    order = Order.objects.filter(
                        checkout_reference=submitted_reference,
                    ).first()
                    if order and _can_access_checkout_order(
                        request,
                        order,
                        submitted_reference,
                    ):
                        return _confirmation_redirect(order)
                    form.add_error(None, str(error))
                except IntegrityError:
                    order = Order.objects.filter(
                        checkout_reference=submitted_reference,
                    ).first()
                    if order is None:
                        raise
                    if not _can_access_checkout_order(
                        request,
                        order,
                        submitted_reference,
                    ):
                        raise
                    return _confirmation_redirect(order)
                else:
                    messages.success(request, "Your order was placed successfully.")
                    return _confirmation_redirect(order)
    else:
        form = CheckoutForm(checkout_reference=reference, initial=initial)

    items = list(items)
    subtotal = sum(
        (item.product.selling_price * item.quantity for item in items),
        start=Decimal("0.00"),
    )
    shipping_fee = get_shipping_fee()
    return render(request, "orders/checkout.html", {
        "form": form,
        "cart_items": items,
        "subtotal": subtotal,
        "shipping_fee": shipping_fee,
        "estimated_total": subtotal + shipping_fee,
        "unavailable_items": [
            item
            for item in items
            if not item.product.is_available
            or item.quantity > item.product.stock_quantity
        ],
    })


@login_required
def order_list(request):
    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def order_detail(request, order_number):
    order = get_object_or_404(
        Order.objects.filter(user=request.user)
        .prefetch_related("items", "status_history")
        .select_related("payment_record"),
        order_number=order_number,
    )
    return render(request, 'orders/order_detail.html', {'order': order})


def order_confirmation(request, order_number, access_token):
    order = get_object_or_404(
        Order.objects.prefetch_related("items", "status_history")
        .select_related("payment_record"),
        order_number=order_number,
    )
    if order.user_id:
        if not request.user.is_authenticated or request.user.pk != order.user_id:
            raise PermissionDenied
    elif not secrets.compare_digest(order.guest_access_token, access_token):
        raise PermissionDenied
    return render(request, "orders/confirmation.html", {"order": order})


# Statuses that a customer is permitted to cancel.
_CUSTOMER_CANCELLABLE_STATUSES = {Order.STATUS_PENDING}


@login_required
@require_POST
def cancel_order(request, order_number):
    order = get_object_or_404(
        Order.objects.filter(user=request.user),
        order_number=order_number,
    )
    if order.order_status not in _CUSTOMER_CANCELLABLE_STATUSES:
        messages.error(
            request,
            "This order can no longer be cancelled. "
            "Please contact us if you need assistance.",
        )
        return redirect("orders:order_detail", order_number=order_number)
    try:
        transition_order(
            order_id=order.pk,
            new_status=Order.STATUS_CANCELLED,
            actor=request.user,
            note="Cancelled by customer.",
        )
    except ValidationError as exc:
        messages.error(request, "; ".join(exc.messages))
    else:
        messages.success(request, f"Order {order.order_number} has been cancelled.")
    return redirect("orders:order_detail", order_number=order_number)
