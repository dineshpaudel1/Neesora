from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.db.models.deletion import ProtectedError
from django.utils.text import slugify

from .models import Category, Product, ProductImage

MAX_IMAGE_SIZE = 8 * 1024 * 1024


class AdminFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "admin-input")


class ProductManagementForm(AdminFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            "name",
            "sku",
            "category",
            "brand",
            "short_description",
            "description",
            "price",
            "discount_price",
            "stock_quantity",
            "product_status",
            "featured",
            "is_new_arrival",
            "is_best_seller",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.Textarea(attrs={"rows": 2}),
            "price": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "discount_price": forms.NumberInput(attrs={"min": "0.01", "step": "0.01"}),
            "stock_quantity": forms.NumberInput(attrs={"min": "0", "step": "1"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = Category.objects.order_by("name")

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price <= Decimal("0"):
            raise ValidationError("Regular price must be greater than zero.")
        return price

    def clean_discount_price(self):
        discount_price = self.cleaned_data.get("discount_price")
        if discount_price is not None and discount_price <= Decimal("0"):
            raise ValidationError("Discount price must be greater than zero.")
        return discount_price

    def save(self, commit=True):
        product = super().save(commit=False)
        if not product.slug:
            product.slug = self._unique_slug(Product, product.name, product.pk)
        if commit:
            product.save()
            self.save_m2m()
        return product

    @staticmethod
    def _unique_slug(model, name, instance_pk):
        base_slug = slugify(name) or "item"
        slug = base_slug[: model._meta.get_field("slug").max_length]
        suffix = 2
        while model.objects.filter(slug=slug).exclude(pk=instance_pk).exists():
            suffix_text = f"-{suffix}"
            max_base_length = model._meta.get_field("slug").max_length - len(suffix_text)
            slug = f"{base_slug[:max_base_length]}{suffix_text}"
            suffix += 1
        return slug


class ProductImageManagementForm(AdminFormMixin, forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ("image", "alt_text", "is_primary")

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_IMAGE_SIZE:
            raise ValidationError("Image files must be 8 MB or smaller.")
        return image


class ProductImageManagementFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        primary_images = 0
        for form in self.forms:
            data = getattr(form, "cleaned_data", {})
            if data.get("DELETE"):
                continue
            if data.get("is_primary"):
                primary_images += 1
                if not data.get("image"):
                    form.add_error("image", "Upload an image before setting it as the main image.")
        if primary_images > 1:
            raise ValidationError("Choose only one main product image.")


ProductImageManagementFormSetFactory = inlineformset_factory(
    Product,
    ProductImage,
    form=ProductImageManagementForm,
    formset=ProductImageManagementFormSet,
    fields=("image", "alt_text", "is_primary"),
    extra=1,
    can_delete=True,
)


class CategoryManagementForm(AdminFormMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ("name", "description", "image", "is_active")
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > MAX_IMAGE_SIZE:
            raise ValidationError("Image files must be 8 MB or smaller.")
        return image

    @transaction.atomic
    def save(self, commit=True):
        previous_image_name = (
            self.instance.image.name
            if self.instance.pk and self.instance.image
            else None
        )
        category = super().save(commit=False)
        if not category.slug:
            category.slug = ProductManagementForm._unique_slug(
                Category,
                category.name,
                category.pk,
            )
        if commit:
            category.save()
            self.save_m2m()
            if previous_image_name and category.image.name != previous_image_name:
                storage = category.image.storage
                transaction.on_commit(lambda: storage.delete(previous_image_name))
        return category


def delete_category_if_unused(category):
    if category.products.exists():
        raise ProtectedError(
            "This category still has products. Move or remove those products before deleting the category.",
            [category],
        )
    category.delete()
