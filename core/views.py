from django.shortcuts import render

from products.models import Category, Product


def home(request):
    published_products = (
        Product.objects.filter(product_status=Product.STATUS_PUBLISHED)
        .select_related("category")
        .prefetch_related("images")
        .order_by("-created_at", "pk")
    )
    popular_products = list(
        published_products.filter(is_best_seller=True, stock_quantity__gt=0)[:4]
    )
    if not popular_products:
        popular_products = list(
            published_products.filter(featured=True, stock_quantity__gt=0)[:4]
        )

    popular_product_ids = [product.pk for product in popular_products]
    new_arrivals = list(
        published_products.filter(is_new_arrival=True)
        .exclude(pk__in=popular_product_ids)[:4]
    )
    if not new_arrivals:
        new_arrivals = list(
            published_products.exclude(pk__in=popular_product_ids)[:4]
        )

    return render(
        request,
        "core/home.html",
        {
            "new_arrivals": new_arrivals,
            "popular_products": popular_products,
            "home_categories": Category.objects.filter(is_active=True)[:4],
            "site_page_type": "home",
        },
    )


def about(request):
    return render(request, "core/about.html", {"site_page_type": "about"})


def coming_soon(request, page_title):
    return render(request, "core/coming_soon.html", {"page_title": page_title})
