import re
from django import forms

from .models import Order


NEPAL_PROVINCES = (
    ("", "Select province"),
    ("Koshi", "Koshi"),
    ("Madhesh", "Madhesh"),
    ("Bagmati", "Bagmati"),
    ("Gandaki", "Gandaki"),
    ("Lumbini", "Lumbini"),
    ("Karnali", "Karnali"),
    ("Sudurpashchim", "Sudurpashchim"),
)


class CheckoutForm(forms.Form):
    customer_name = forms.CharField(
        max_length=120,
        label="Full name",
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        required=False,
        label="Email (optional)",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
    )
    phone_number = forms.CharField(
        max_length=30,
        label="Mobile number",
        widget=forms.TextInput(
            attrs={"type": "tel", "autocomplete": "tel", "inputmode": "tel"}
        ),
    )
    province = forms.ChoiceField(choices=NEPAL_PROVINCES)
    district = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={"autocomplete": "address-level2"}),
    )
    city = forms.CharField(
        max_length=100,
        label="Municipality / rural municipality",
        widget=forms.TextInput(attrs={"autocomplete": "address-level3"}),
    )
    ward_number = forms.CharField(max_length=10, label="Ward number")
    address = forms.CharField(
        max_length=255,
        label="Street, tole, or locality",
        widget=forms.TextInput(attrs={"autocomplete": "street-address"}),
    )
    postal_code = forms.CharField(max_length=20, required=False, label="Postal code (optional)")
    order_notes = forms.CharField(
        required=False,
        max_length=1000,
        label="Delivery instructions (optional)",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    payment_method = forms.ChoiceField(
        choices=Order.PAYMENT_CHOICES,
        initial=Order.PAYMENT_CASH_ON_DELIVERY,
        widget=forms.RadioSelect,
    )
    checkout_reference = forms.UUIDField(widget=forms.HiddenInput)
    terms_accepted = forms.BooleanField(
        label="I have reviewed my delivery details and order total.",
    )

    def __init__(self, *args, checkout_reference=None, initial=None, **kwargs):
        initial = dict(initial or {})
        if checkout_reference is not None:
            initial["checkout_reference"] = checkout_reference
        super().__init__(*args, initial=initial, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "checkout-input")
        if self.is_bound:
            for name, field in self.fields.items():
                if self.errors.get(name):
                    field.widget.attrs["aria-invalid"] = "true"
                    field.widget.attrs["aria-describedby"] = f"id_{name}_errors"

    def clean_phone_number(self):
        phone = self.cleaned_data["phone_number"]
        compact = re.sub(r"[\s().-]", "", phone)
        if compact.startswith("00977"):
            compact = compact[2:]
        if compact.startswith("+977"):
            compact = compact[4:]
        elif compact.startswith("977") and len(compact) == 13:
            compact = compact[3:]
        if not re.fullmatch(r"9\d{9}", compact):
            raise forms.ValidationError(
                "Enter a valid 10-digit Nepal mobile number, optionally with +977."
            )
        return f"+977{compact}"

    def clean_ward_number(self):
        ward = self.cleaned_data["ward_number"].strip()
        if not ward.isdecimal() or not 1 <= int(ward) <= 35:
            raise forms.ValidationError("Enter a ward number from 1 to 35.")
        return str(int(ward))
