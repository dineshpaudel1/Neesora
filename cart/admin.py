from django.contrib import admin

from .models import CartItem, WishlistItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'session_key', 'quantity', 'updated_at')
    list_filter = ('user',)
    search_fields = ('product__name', 'session_key', 'user__username')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'session_key', 'created_at')
    list_filter = ('user',)
    search_fields = ('product__name', 'user__username', 'session_key')
