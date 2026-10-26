from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from products.models import Category, Product


class StorefrontSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.8

    def items(self):
        return ("core:home", "products:shop", "core:about")

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.filter(is_active=True)

    def location(self, item):
        return reverse("products:category", kwargs={"category_slug": item.slug})

    def lastmod(self, item):
        return item.updated_at


class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        return Product.objects.filter(
            product_status=Product.STATUS_PUBLISHED,
        ).only("slug", "updated_at")

    def location(self, item):
        return reverse("products:product_detail", kwargs={"slug": item.slug})

    def lastmod(self, item):
        return item.updated_at
