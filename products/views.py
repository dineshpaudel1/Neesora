from decimal import Decimal, InvalidOperation

from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from .models import Category, Product


def _apply_product_filters(request, queryset):
    query = request.GET.get('q', '').strip()
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(short_description__icontains=query)
            | Q(sku__icontains=query)
            | Q(category__name__icontains=query)
        )

    category_id = request.GET.get('category')
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    price_min = request.GET.get('price_min', '').strip()
    price_max = request.GET.get('price_max', '').strip()

    try:
        if price_min:
            queryset = queryset.filter(price__gte=Decimal(price_min))
    except InvalidOperation:
        pass

    try:
        if price_max:
            queryset = queryset.filter(price__lte=Decimal(price_max))
    except InvalidOperation:
        pass

    availability = request.GET.get('availability')
    if availability == 'in_stock':
        queryset = queryset.filter(stock_quantity__gt=0)
    elif availability == 'out_of_stock':
        queryset = queryset.filter(stock_quantity=0)

    sort = request.GET.get('sort', 'latest')
    if sort == 'price_low_high':
        queryset = queryset.order_by('discount_price', 'price')
    elif sort == 'price_high_low':
        queryset = queryset.order_by('-discount_price', '-price')
    elif sort == 'popularity':
        queryset = queryset.order_by('-is_best_seller', '-featured', '-stock_quantity', '-created_at')
    else:
        queryset = queryset.order_by('-created_at')

    return queryset


def shop(request):
    categories = Category.objects.filter(is_active=True)
    products = _apply_product_filters(request, Product.objects.filter(product_status=Product.STATUS_PUBLISHED).select_related('category'))
    context = {
        'page_title': 'Shop',
        'products': products,
        'categories': categories,
        'site_page_type': 'shop',
        'selected_category': request.GET.get('category', ''),
        'search_term': request.GET.get('q', '').strip(),
        'price_min': request.GET.get('price_min', ''),
        'price_max': request.GET.get('price_max', ''),
        'availability': request.GET.get('availability', ''),
        'sort': request.GET.get('sort', 'latest'),
    }
    return render(request, 'products/shop.html', context)


def search_products(request):
    return shop(request)


def category_products(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug, is_active=True)
    products = _apply_product_filters(
        request,
        Product.objects.filter(
            category=category,
            product_status=Product.STATUS_PUBLISHED,
        ).select_related('category'),
    )
    categories = Category.objects.filter(is_active=True)
    context = {
        'page_title': category.name,
        'category': category,
        'products': products,
        'categories': categories,
        'site_page_type': 'category',
        'selected_category': str(category.id),
        'search_term': request.GET.get('q', '').strip(),
        'price_min': request.GET.get('price_min', ''),
        'price_max': request.GET.get('price_max', ''),
        'availability': request.GET.get('availability', ''),
        'sort': request.GET.get('sort', 'latest'),
    }
    return render(request, 'products/category.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product,
        slug=slug,
        product_status=Product.STATUS_PUBLISHED,
    )
    related_products = Product.objects.filter(
        category=product.category,
        product_status=Product.STATUS_PUBLISHED,
    ).exclude(pk=product.pk).select_related('category')[:4]
    context = {
        'page_title': product.name,
        'product': product,
        'related_products': related_products,
        'site_page_type': 'product',
    }
    return render(request, 'products/product_detail.html', context)
