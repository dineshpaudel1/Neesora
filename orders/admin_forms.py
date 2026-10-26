from django import forms

from .models import Order
from .workflow import STATUS_TRANSITIONS


class OrderStatusForm(forms.Form):
    order_status = forms.ChoiceField(label="Move order to")
    note = forms.CharField(
        required=False,
        label="Internal note",
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    def __init__(self, *args, order, **kwargs):
        super().__init__(*args, **kwargs)
        allowed = STATUS_TRANSITIONS.get(order.order_status, set())
        self.fields["order_status"].choices = [
            (value, label)
            for value, label in Order.STATUS_CHOICES
            if value in allowed
        ]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "admin-input")
