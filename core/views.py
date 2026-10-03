from django.shortcuts import render

from products.models import Category, Product


def home(request):
    published_products = Product.objects.filter(
        product_status=Product.STATUS_PUBLISHED
    ).select_related("category")
    featured_products = published_products.filter(featured=True)[:4]
    if not featured_products:
        featured_products = published_products.order_by("-created_at")[:4]
    categories = Category.objects.filter(is_active=True)[:8]
    return render(
        request,
        "core/home.html",
        {"featured_products": featured_products, "home_categories": categories},
    )


def coming_soon(request, page_title):
    return render(request, "core/coming_soon.html", {"page_title": page_title})
