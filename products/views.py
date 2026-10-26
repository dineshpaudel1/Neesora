from django.db.models import Avg, Q
from django.shortcuts import get_object_or_404, render

from reviews.forms import ReviewForm
from reviews.models import Review
from .models import Category, Product


def _search_products(queryset, query):
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(short_description__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
        )

    return queryset.order_by("-created_at", "pk")


def shop(request):
    search_term = request.GET.get("q", "").strip()
    products = list(
        _search_products(
            Product.objects.filter(product_status=Product.STATUS_PUBLISHED)
            .select_related("category")
            .prefetch_related("images"),
            search_term,
        )
    )
    context = {
        "page_title": "Shop",
        'products': products,
        "product_count": len(products),
        "site_page_type": "shop",
        "search_term": search_term,
    }
    return render(request, 'products/shop.html', context)


def search_products(request):
    return shop(request)


def category_products(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    search_term = request.GET.get("q", "").strip()
    products = list(
        _search_products(
            Product.objects.filter(
                category=category,
                product_status=Product.STATUS_PUBLISHED,
            )
            .select_related("category")
            .prefetch_related("images"),
            search_term,
        )
    )
    context = {
        'page_title': category.name,
        'category': category,
        'products': products,
        "product_count": len(products),
        "site_page_type": "category",
        "search_term": search_term,
    }
    return render(request, 'products/category.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.prefetch_related("images"),
        slug=slug,
        product_status=Product.STATUS_PUBLISHED,
    )
    reviews = (
        Review.objects.filter(product=product, is_approved=True)
        .select_related('user__customerprofile')
        .order_by('-created_at')
    )
    rating_data = reviews.aggregate(avg=Avg('rating'))
    avg_rating = rating_data['avg']
    review_count = reviews.count()

    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(user=request.user).first()

    related_products = Product.objects.filter(
        category=product.category,
        product_status=Product.STATUS_PUBLISHED,
    ).exclude(pk=product.pk).select_related("category").prefetch_related("images")[:4]

    context = {
        'page_title': product.name,
        'product': product,
        'related_products': related_products,
        'site_page_type': 'product',
        'reviews': reviews,
        'review_count': review_count,
        'avg_rating': avg_rating,
        'user_review': user_review,
        'review_form': ReviewForm(),
    }
    return render(request, 'products/product_detail.html', context)
