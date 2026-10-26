from django.urls import path

from . import management_views, views

app_name = 'products'

urlpatterns = [
    path('manage/', management_views.dashboard, name='management_dashboard'),
    path('search/', views.search_products, name='search'),
    path('shop/', views.shop, name='shop'),
    path('category/<slug:category_slug>/', views.category_products, name='category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
]
