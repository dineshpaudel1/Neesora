from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .admin_access import designated_admin_required

User = get_user_model()


@designated_admin_required
@require_GET
def customer_list(request):
    customers = (
        User.objects.filter(is_staff=False, is_superuser=False)
        .select_related("customer_profile")
        .annotate(order_count=Count("orders", distinct=True))
    )
    query = request.GET.get("q", "").strip()
    if query:
        customers = customers.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(customer_profile__full_name__icontains=query)
            | Q(customer_profile__phone_number__icontains=query)
        )

    status = request.GET.get("status", "")
    if status == "active":
        customers = customers.filter(is_active=True)
    elif status == "inactive":
        customers = customers.filter(is_active=False)

    page_obj = Paginator(customers.order_by("-date_joined", "pk"), 25).get_page(
        request.GET.get("page")
    )
    return render(request, "admin/customers/list.html", {
        "page_title": "Customers",
        "active_section": "customers",
        "customers": page_obj,
        "page_obj": page_obj,
        "search_query": query,
        "selected_status": status,
    })


@designated_admin_required
@require_GET
def customer_detail(request, user_id):
    customer = get_object_or_404(
        User.objects.filter(is_staff=False, is_superuser=False)
        .select_related("customer_profile"),
        pk=user_id,
    )
    orders = customer.orders.order_by("-created_at")
    return render(request, "admin/customers/detail.html", {
        "page_title": customer.customer_profile.display_name
        if hasattr(customer, "customer_profile")
        else customer.get_full_name() or customer.username,
        "active_section": "customers",
        "customer": customer,
        "orders": orders[:25],
        "order_count": orders.count(),
    })
