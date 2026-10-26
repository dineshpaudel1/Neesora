from django.conf import settings
from django.db import models
from django.utils import timezone

from orders.models import Order


class Payment(models.Model):
    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    order = models.OneToOneField(
        Order,
        on_delete=models.PROTECT,
        related_name="payment_record",
    )
    payment_method = models.CharField(
        max_length=30,
        choices=Order.PAYMENT_CHOICES,
        default=Order.PAYMENT_CASH_ON_DELIVERY,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    collected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collected_cod_payments",
    )
    collected_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_collected(self, actor):
        self.status = self.STATUS_PAID
        self.collected_by = actor
        self.collected_at = timezone.now()
        self.save(update_fields=["status", "collected_by", "collected_at", "updated_at"])
