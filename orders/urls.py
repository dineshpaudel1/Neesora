from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('orders/', views.order_list, name='orders'),
    path('orders/<str:order_number>/', views.order_detail, name='order_detail'),
]
