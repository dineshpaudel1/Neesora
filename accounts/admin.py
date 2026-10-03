from django.contrib import admin

from .models import CustomerProfile


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'user', 'phone_number', 'city', 'province')
    search_fields = ('full_name', 'phone_number', 'user__username', 'user__email')
    list_filter = ('province', 'city')
