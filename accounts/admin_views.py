from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

from django.contrib.auth import get_user_model
from django.db.models import Count
from orders.models import Order
from products.models import Category, Product

from .admin_access import designated_admin_required, is_designated_admin


class DesignatedAdminAuthenticationForm(AuthenticationForm):
    error_messages = {
        "invalid_login": _(
            "Unable to sign in. Check your credentials or contact the administrator."
        ),
        "inactive": _(
            "Unable to sign in. Check your credentials or contact the administrator."
        ),
    }

    def confirm_login_allowed(self, user):
        if not is_designated_admin(user):
            raise self.get_invalid_login_error()
        super().confirm_login_allowed(user)


class AdminLoginView(LoginView):
    template_name = "admin/login.html"
    authentication_form = DesignatedAdminAuthenticationForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if is_designated_admin(request.user):
                return redirect("myadmin:dashboard")
            messages.error(request, "You are not authorized to access that page.")
            return redirect("core:home")
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_redirect_url() or reverse_lazy("myadmin:dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session.set_expiry(8 * 60 * 60)
        return response


@designated_admin_required
def dashboard(request):
    products = Product.objects.all()
    orders = Order.objects.all()
    customers = get_user_model().objects.filter(
        is_staff=False,
        is_superuser=False,
    )
    order_status_counts = dict(
        orders.order_by()
        .values("order_status")
        .annotate(count=Count("pk"))
        .values_list("order_status", "count")
    )
    order_status_summary = [
        (value, label, order_status_counts.get(value, 0))
        for value, label in Order.STATUS_CHOICES
    ]
    context = {
        "page_title": "Store dashboard",
        "active_section": "dashboard",
        "total_products": products.count(),
        "available_products": products.filter(
            product_status=Product.STATUS_PUBLISHED,
            stock_quantity__gt=0,
        ).count(),
        "out_of_stock_products": products.filter(stock_quantity=0).count(),
        "low_stock_products": products.filter(
            stock_quantity__gt=0,
            stock_quantity__lte=5,
        ).count(),
        "total_categories": Category.objects.count(),
        "total_customers": customers.count(),
        "total_orders": orders.count(),
        "pending_orders": orders.filter(order_status=Order.STATUS_PENDING).count(),
        "order_status_counts": order_status_counts,
        "order_status_summary": order_status_summary,
        "order_status_choices": Order.STATUS_CHOICES,
        "pending_payments": orders.filter(payment_status="pending").count(),
        "recent_orders": orders.order_by("-created_at")[:5],
    }
    return render(request, "products/management/dashboard.html", context)


@designated_admin_required
def password_change(request):
    return PasswordChangeView.as_view(
        template_name="admin/password_change.html",
        success_url=reverse_lazy("myadmin:dashboard"),
        extra_context={
            "page_title": "Change password",
            "active_section": "security",
        },
    )(request)


@designated_admin_required
def admin_logout(request):
    return LogoutView.as_view(next_page="myadmin:login")(request)
