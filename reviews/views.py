from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from products.models import Product
from .forms import ReviewForm
from .models import Review


@login_required
def submit_review(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk, product_status=Product.STATUS_PUBLISHED)
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            Review.objects.update_or_create(
                product=product,
                user=request.user,
                defaults={
                    'rating': form.cleaned_data['rating'],
                    'title': form.cleaned_data['title'],
                    'body': form.cleaned_data['body'],
                },
            )
            messages.success(request, 'Your review has been submitted. Thank you!')
        else:
            for field_errors in form.errors.values():
                for error in field_errors:
                    messages.error(request, error)
    return redirect('products:product_detail', slug=product.slug)


@login_required
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, user=request.user)
    product_slug = review.product.slug
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Your review has been removed.')
    return redirect('products:product_detail', slug=product_slug)
