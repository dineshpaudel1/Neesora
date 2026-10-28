from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path(
        'orders/confirmation/<str:order_number>/<str:access_token>/',
        views.order_confirmation,
        name='confirmation',
    ),
    path('orders/', views.order_list, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
    path('orders/<str:order_number>/cancel/', views.cancel_order, name='cancel_order'),
]
