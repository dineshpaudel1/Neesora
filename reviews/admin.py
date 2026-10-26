from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'title', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'rating', 'created_at')
    search_fields = ('product__name', 'user__username', 'title', 'body')
    list_editable = ('is_approved',)
    raw_id_fields = ('product', 'user')
    readonly_fields = ('created_at', 'updated_at')
