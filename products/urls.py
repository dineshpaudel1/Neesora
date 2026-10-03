from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('search/', views.search_products, name='search'),
    path('shop/', views.shop, name='shop'),
    path('category/<slug:category_slug>/', views.category_products, name='category'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
]
