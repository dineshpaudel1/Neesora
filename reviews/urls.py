from django.urls import path

from . import views

app_name = 'reviews'

urlpatterns = [
    path('reviews/submit/<int:product_pk>/', views.submit_review, name='submit'),
    path('reviews/delete/<int:pk>/', views.delete_review, name='delete'),
]
