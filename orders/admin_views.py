from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from accounts.admin_access import designated_admin_required
from payments.models import Payment

from .admin_forms import OrderStatusForm
from .models import Order
from .workflow import confirm_cod_collection, transition_order


class OrderFilterForm(forms.Form):
    q = forms.CharField(required=False)
    status = forms.ChoiceField(required=False)
    payment_status = forms.ChoiceField(required=False)
    payment_method = forms.ChoiceField(required=False)
    date_from = forms.DateField(required=False, input_formats=["%Y-%m-%d"])
    date_to = forms.DateField(required=False, input_formats=["%Y-%m-%d"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "All order statuses"), *Order.STATUS_CHOICES]
        self.fields["payment_status"].choices = [
            ("", "All payment statuses"),
            (Payment.STATUS_PENDING, "Pending"),
            (Payment.STATUS_PAID, "Paid"),
            (Payment.STATUS_FAILED, "Failed"),
            (Payment.STATUS_REFUNDED, "Refunded"),
        ]
        self.fields["payment_method"].choices = [
            ("", "All payment methods"),
            *Order.PAYMENT_CHOICES,
        ]


@designated_admin_required
@require_GET
def order_list(request):
    filter_form = OrderFilterForm(request.GET or None)
    orders = Order.objects.select_related("user", "payment_record")
    query = ""
    status = payment_status = payment_method = ""
    if filter_form.is_valid():
        query = filter_form.cleaned_data["q"].strip()
        status = filter_form.cleaned_data["status"]
        payment_status = filter_form.cleaned_data["payment_status"]
        payment_method = filter_form.cleaned_data["payment_method"]
        date_from = filter_form.cleaned_data["date_from"]
        date_to = filter_form.cleaned_data["date_to"]
    else:
        date_from = date_to = None
    if query:
        orders = orders.filter(
            Q(order_number__icontains=query)
            | Q(customer_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone_number__icontains=query)
        )

    if status:
        orders = orders.filter(order_status=status)

    if payment_status:
        orders = orders.filter(payment_status=payment_status)
    if payment_method:
        orders = orders.filter(payment_method=payment_method)
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    sort = request.GET.get("sort", "-created_at")
    sort_fields = {
        "-created_at": "-created_at",
        "created_at": "created_at",
        "total_amount": "total_amount",
        "-total_amount": "-total_amount",
    }
    page_obj = Paginator(
        orders.order_by(sort_fields.get(sort, "-created_at"), "pk"),
        25,
    ).get_page(request.GET.get("page"))
    return render(request, "admin/orders/list.html", {
        "page_title": "Orders",
        "active_section": "orders",
        "orders": page_obj,
        "page_obj": page_obj,
        "search_query": query,
        "selected_status": status,
        "selected_payment_status": payment_status,
        "selected_payment_method": payment_method,
        "selected_sort": sort,
        "status_choices": Order.STATUS_CHOICES,
        "filter_form": filter_form,
        "payment_status_choices": Payment.STATUS_CHOICES,
        "payment_method_choices": Order.PAYMENT_CHOICES,
    })


@designated_admin_required
@require_GET
def order_detail(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("user", "payment_record")
        .prefetch_related("items__product", "status_history__actor"),
        pk=order_id,
    )
    status_form = OrderStatusForm(order=order)
    return render(request, "admin/orders/detail.html", {
        "page_title": f"Order {order.order_number}",
        "active_section": "orders",
        "order": order,
        "status_form": status_form,
        "can_cancel": any(
            value == Order.STATUS_CANCELLED
            for value, _label in status_form.fields["order_status"].choices
        ),
    })


@designated_admin_required
@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, pk=order_id)
    form = OrderStatusForm(request.POST, order=order)
    if not form.is_valid():
        messages.error(request, "Choose a valid next order status.")
        return redirect("myadmin:order_detail", order_id=order_id)
    try:
        transition_order(
            order_id=order.pk,
            new_status=form.cleaned_data["order_status"],
            actor=request.user,
            note=form.cleaned_data["note"],
        )
    except ValidationError as error:
        messages.error(request, "; ".join(error.messages))
        return redirect("myadmin:order_detail", order_id=order_id)
    messages.success(request, "Order status updated.")
    return redirect("myadmin:order_detail", order_id=order_id)


@designated_admin_required
@require_POST
def confirm_payment_collection(request, order_id):
    get_object_or_404(Order, pk=order_id)
    try:
        confirm_cod_collection(order_id=order_id, actor=request.user)
    except (Payment.DoesNotExist, ValidationError) as error:
        message = (
            "; ".join(error.messages)
            if isinstance(error, ValidationError)
            else "No COD payment record exists for this order."
        )
        messages.error(request, message)
    else:
        messages.success(request, "Cash-on-delivery payment collection confirmed.")
    return redirect("myadmin:order_detail", order_id=order_id)
