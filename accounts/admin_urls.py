from django.urls import path

from . import admin_views
from . import customer_admin_views
from orders import admin_views as order_admin_views
from products import management_views

app_name = "myadmin"

urlpatterns = [
    path("", admin_views.AdminLoginView.as_view(), name="login"),
    path("dashboard/", admin_views.dashboard, name="dashboard"),
    path("products/", management_views.product_list, name="products"),
    path("products/add/", management_views.product_create, name="product_add"),
    path("products/<int:product_id>/", management_views.product_detail, name="product_detail"),
    path("products/<int:product_id>/edit/", management_views.product_edit, name="product_edit"),
    path("products/<int:product_id>/delete/", management_views.product_delete, name="product_delete"),
    path("categories/", management_views.category_list, name="categories"),
    path("categories/add/", management_views.category_create, name="category_add"),
    path("categories/<int:category_id>/edit/", management_views.category_edit, name="category_edit"),
    path("categories/<int:category_id>/delete/", management_views.category_delete, name="category_delete"),
    path("orders/", order_admin_views.order_list, name="orders"),
    path("orders/<int:order_id>/", order_admin_views.order_detail, name="order_detail"),
    path("orders/<int:order_id>/status/", order_admin_views.update_order_status, name="order_status"),
    path("orders/<int:order_id>/payment/confirm/", order_admin_views.confirm_payment_collection, name="confirm_payment"),
    path("customers/", customer_admin_views.customer_list, name="customers"),
    path("customers/<int:user_id>/", customer_admin_views.customer_detail, name="customer_detail"),
    path(
        "password/",
        admin_views.password_change,
        name="password_change",
    ),
    path(
        "logout/",
        admin_views.admin_logout,
        name="logout",
    ),
]
