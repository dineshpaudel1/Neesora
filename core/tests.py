from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product


class StorefrontPageTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Everyday bags")

    def create_product(
        self,
        name,
        sku,
        *,
        is_new_arrival=False,
        featured=False,
        is_best_seller=False,
        stock_quantity=2,
        status=None,
    ):
        return Product.objects.create(
            name=name,
            sku=sku,
            description=f"{name} description.",
            category=self.category,
            price=Decimal("1800.00"),
            stock_quantity=stock_quantity,
            product_status=status or Product.STATUS_PUBLISHED,
            is_new_arrival=is_new_arrival,
            featured=featured,
            is_best_seller=is_best_seller,
        )

    def test_homepage_uses_published_new_arrivals_from_the_database(self):
        self.create_product("Older arrival", "OLDER-1", is_new_arrival=True)
        newest = self.create_product("Newest arrival", "NEWEST-1", is_new_arrival=True)
        self.create_product("Regular listing", "REGULAR-1")
        self.create_product(
            "Draft arrival",
            "DRAFT-1",
            is_new_arrival=True,
            status=Product.STATUS_DRAFT,
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["new_arrivals"]),
            [newest, Product.objects.get(sku="OLDER-1")],
        )
        self.assertContains(response, "New arrivals")
        self.assertContains(response, "Buy now")
        self.assertNotContains(response, "coming soon")

    def test_homepage_prioritizes_in_stock_bestsellers_and_avoids_duplicate_arrivals(self):
        bestseller = self.create_product(
            "Neesora favourite",
            "FAVOURITE-1",
            is_new_arrival=True,
            featured=True,
            is_best_seller=True,
        )
        self.create_product(
            "Featured bag",
            "FEATURED-1",
            featured=True,
        )
        arrival = self.create_product(
            "New arrival",
            "ARRIVAL-1",
            is_new_arrival=True,
        )
        self.create_product(
            "Out of stock bestseller",
            "SOLD-OUT-1",
            is_best_seller=True,
            stock_quantity=0,
        )
        self.create_product(
            "Draft bestseller",
            "DRAFT-FAVOURITE-1",
            is_best_seller=True,
            status=Product.STATUS_DRAFT,
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(list(response.context["popular_products"]), [bestseller])
        self.assertEqual(list(response.context["new_arrivals"]), [arrival])
        self.assertContains(response, bestseller.name)
        self.assertContains(
            response,
            reverse("products:product_detail", args=[bestseller.slug]),
        )
        self.assertContains(response, reverse("cart:add_to_cart", args=[bestseller.pk]))
        self.assertContains(response, "Product image not yet available")
        self.assertContains(response, "Popular bags")

    def test_homepage_uses_featured_products_when_no_bestseller_exists(self):
        featured = self.create_product("Featured bag", "FEATURED-1", featured=True)
        self.create_product("Ordinary bag", "ORDINARY-1")

        response = self.client.get(reverse("core:home"))

        self.assertEqual(list(response.context["popular_products"]), [featured])
        self.assertEqual(
            list(response.context["new_arrivals"]),
            [Product.objects.get(sku="ORDINARY-1")],
        )

    def test_homepage_falls_back_to_latest_published_products(self):
        newest = self.create_product("Latest published", "LATEST-1")
        self.create_product(
            "Unpublished bag",
            "UNPUBLISHED-1",
            status=Product.STATUS_DRAFT,
        )

        response = self.client.get(reverse("core:home"))

        self.assertEqual(list(response.context["new_arrivals"]), [newest])

    def test_about_page_is_available_from_store_navigation(self):
        response = self.client.get(reverse("core:about"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "About Neesora")
        self.assertContains(response, reverse("products:shop"))

    def test_sitemap_includes_public_storefront_and_published_products_only(self):
        published = self.create_product("Published bag", "SITEMAP-1")
        self.create_product(
            "Draft bag",
            "SITEMAP-DRAFT-1",
            status=Product.STATUS_DRAFT,
        )

        response = self.client.get(reverse("sitemap"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("core:about"))
        self.assertContains(
            response,
            reverse("products:product_detail", args=[published.slug]),
        )
        self.assertNotContains(response, "SITEMAP-DRAFT-1")
        self.assertNotContains(response, "draft-bag")
