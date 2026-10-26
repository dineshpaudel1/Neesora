from django.contrib import messages
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from accounts.admin_access import designated_admin_required
from accounts.admin_views import dashboard

from .management_forms import (
    CategoryManagementForm,
    ProductManagementForm,
    ProductImageManagementFormSetFactory,
    delete_category_if_unused,
)
from .models import Category, Product, ProductImage


def _save_product_images(formset):
    old_file_names = set()
    for form in formset.forms:
        if not form.instance.pk:
            continue
        old_image_name = form.instance.image.name
        cleaned_data = getattr(form, "cleaned_data", {})
        if cleaned_data.get("DELETE") or "image" in form.changed_data:
            old_file_names.add(old_image_name)

    formset.save()

    for old_file_name in old_file_names:
        def delete_if_unused(name=old_file_name):
            if name and not ProductImage.objects.filter(image=name).exists():
                default_storage.delete(name)

        transaction.on_commit(delete_if_unused)


@designated_admin_required
@require_GET
def product_list(request):
    products = Product.objects.select_related("category").prefetch_related("images")
    query = request.GET.get("q", "").strip()
    if query:
        products = products.filter(
            Q(name__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
            | Q(brand__icontains=query)
        )

    category_id = request.GET.get("category", "").strip()
    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    status = request.GET.get("status", "").strip()
    valid_statuses = {value for value, _label in Product.STATUS_CHOICES}
    if status in valid_statuses:
        products = products.filter(product_status=status)

    stock = request.GET.get("stock", "").strip()
    if stock == "in_stock":
        products = products.filter(stock_quantity__gt=0)
    elif stock == "out_of_stock":
        products = products.filter(stock_quantity=0)
    elif stock == "low_stock":
        products = products.filter(stock_quantity__gt=0, stock_quantity__lte=5)

    ordering = request.GET.get("sort", "-created_at")
    sort_fields = {
        "name": "name",
        "-name": "-name",
        "price": "price",
        "-price": "-price",
        "stock": "stock_quantity",
        "-stock": "-stock_quantity",
        "created": "created_at",
        "-created_at": "-created_at",
    }
    products = products.order_by(sort_fields.get(ordering, "-created_at"), "pk")
    page_obj = Paginator(products, 20).get_page(request.GET.get("page"))
    return render(request, "admin/products/list.html", {
        "page_title": "Products",
        "active_section": "products",
        "products": page_obj,
        "page_obj": page_obj,
        "categories": Category.objects.order_by("name"),
        "search_query": query,
        "selected_category": category_id,
        "selected_status": status,
        "selected_stock": stock,
        "selected_sort": ordering,
        "status_choices": Product.STATUS_CHOICES,
    })


@designated_admin_required
@require_GET
def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("images"),
        pk=product_id,
    )
    return render(request, "admin/products/detail.html", {
        "page_title": product.name,
        "active_section": "products",
        "product": product,
    })


@designated_admin_required
@require_http_methods(["GET", "POST"])
def product_create(request):
    form = ProductManagementForm(request.POST or None, request.FILES or None)
    image_formset = ProductImageManagementFormSetFactory(
        request.POST or None,
        request.FILES or None,
        instance=form.instance,
    )
    if request.method == "POST":
        form_valid = form.is_valid()
        images_valid = image_formset.is_valid()
    else:
        form_valid = images_valid = False
    if form_valid and images_valid:
        with transaction.atomic():
            product = form.save()
            image_formset.instance = product
            _save_product_images(image_formset)
        messages.success(request, f"{product.name} was added to the catalog.")
        return redirect("myadmin:product_detail", product_id=product.pk)
    return render(request, "admin/products/form.html", {
        "page_title": "Add product",
        "active_section": "products",
        "form": form,
        "image_formset": image_formset,
        "is_create": True,
    })


@designated_admin_required
@require_http_methods(["GET", "POST"])
def product_edit(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    form = ProductManagementForm(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    image_formset = ProductImageManagementFormSetFactory(
        request.POST or None,
        request.FILES or None,
        instance=product,
    )
    if request.method == "POST":
        form_valid = form.is_valid()
        images_valid = image_formset.is_valid()
    else:
        form_valid = images_valid = False
    if form_valid and images_valid:
        with transaction.atomic():
            product = form.save()
            _save_product_images(image_formset)
        messages.success(request, f"{product.name} was updated.")
        return redirect("myadmin:product_detail", product_id=product.pk)
    return render(request, "admin/products/form.html", {
        "page_title": f"Edit {product.name}",
        "active_section": "products",
        "form": form,
        "image_formset": image_formset,
        "product": product,
        "is_create": False,
    })


@designated_admin_required
@require_http_methods(["GET", "POST"])
def product_delete(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    if request.method == "POST":
        product_name = product.name
        if product.order_items.exists():
            messages.error(
                request,
                "This product is linked to an order and cannot be deleted. Archive it instead.",
            )
            return redirect("myadmin:product_detail", product_id=product.pk)
        if product.cart_items.exists() or product.wishlist_items.exists():
            messages.error(
                request,
                "This product is saved in a customer cart or wishlist. Archive it instead to preserve customer data.",
            )
            return redirect("myadmin:product_detail", product_id=product.pk)
        try:
            product.delete()
        except ProtectedError:
            messages.error(
                request,
                "This product is linked to an order and cannot be deleted. Archive it instead.",
            )
            return redirect("myadmin:product_detail", product_id=product.pk)
        messages.success(request, f"{product_name} was deleted.")
        return redirect("myadmin:products")
    return render(request, "admin/products/delete.html", {
        "page_title": "Delete product",
        "active_section": "products",
        "product": product,
    })


@designated_admin_required
@require_GET
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products"))
    query = request.GET.get("q", "").strip()
    if query:
        categories = categories.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
    page_obj = Paginator(categories.order_by("name"), 20).get_page(
        request.GET.get("page")
    )
    return render(request, "admin/categories/list.html", {
        "page_title": "Categories",
        "active_section": "categories",
        "categories": page_obj,
        "page_obj": page_obj,
        "search_query": query,
    })


@designated_admin_required
@require_http_methods(["GET", "POST"])
def category_create(request):
    form = CategoryManagementForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"{category.name} was added.")
        return redirect("myadmin:categories")
    return render(request, "admin/categories/form.html", {
        "page_title": "Add category",
        "active_section": "categories",
        "form": form,
        "is_create": True,
    })


@designated_admin_required
@require_http_methods(["GET", "POST"])
def category_edit(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    form = CategoryManagementForm(
        request.POST or None,
        request.FILES or None,
        instance=category,
    )
    if request.method == "POST" and form.is_valid():
        category = form.save()
        messages.success(request, f"{category.name} was updated.")
        return redirect("myadmin:categories")
    return render(request, "admin/categories/form.html", {
        "page_title": f"Edit {category.name}",
        "active_section": "categories",
        "form": form,
        "category": category,
        "is_create": False,
    })


@designated_admin_required
@require_http_methods(["GET", "POST"])
def category_delete(request, category_id):
    category = get_object_or_404(Category, pk=category_id)
    if request.method == "POST":
        try:
            delete_category_if_unused(category)
        except ProtectedError:
            messages.error(
                request,
                "This category still contains products. Move or remove those products before deleting it.",
            )
            return redirect("myadmin:categories")
        messages.success(request, "The category was deleted.")
        return redirect("myadmin:categories")
    return render(request, "admin/categories/delete.html", {
        "page_title": "Delete category",
        "active_section": "categories",
        "category": category,
    })
