from django.conf import settings
from django.db import models
from django.db.models import Q

from products.models import Product


class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_items',
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_cart_item',
                condition=Q(user__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['session_key', 'product'],
                name='unique_session_cart_item',
                condition=Q(session_key__isnull=False),
            ),
        ]

    def __str__(self):
        return f'{self.product.name} ({self.quantity})'

    @property
    def line_total(self):
        return self.product.selling_price * self.quantity


class WishlistItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wishlist_items',
        null=True,
        blank=True,
    )
    session_key = models.CharField(max_length=40, blank=True, null=True, db_index=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wishlist_items')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'product'],
                name='unique_user_wishlist_item',
                condition=Q(user__isnull=False),
            ),
            models.UniqueConstraint(
                fields=['session_key', 'product'],
                name='unique_session_wishlist_item',
                condition=Q(session_key__isnull=False),
            ),
        ]

    def __str__(self):
        return self.product.name
