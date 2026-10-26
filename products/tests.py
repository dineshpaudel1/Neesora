from decimal import Decimal
from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from cart.models import CartItem, WishlistItem
from orders.models import Order, OrderItem

from .models import Category, Product, ProductImage


User = get_user_model()


class ProductCardPurchaseTests(TestCase):
    def setUp(self):
        category = Category.objects.create(name="Featured bags")
        self.product = Product.objects.create(
            name="Shop-ready Backpack",
            sku="SHOP-BACKPACK-1",
            description="Available from the shop listing.",
            category=category,
            price=Decimal("2500.00"),
            stock_quantity=3,
            product_status=Product.STATUS_PUBLISHED,
        )

    def test_shop_card_displays_add_to_bag_and_posts_to_cart(self):
        shop_url = reverse("products:shop")
        response = self.client.get(shop_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add to bag")
        self.assertContains(response, "Buy now")
        self.assertContains(
            response,
            reverse("cart:add_to_cart", args=[self.product.pk]),
        )
        self.assertNotContains(response, "Filter products")

        added = self.client.post(
            reverse("cart:add_to_cart", args=[self.product.pk]),
            {"quantity": "1", "next": shop_url},
        )

        self.assertRedirects(added, shop_url)
        item = CartItem.objects.get(product=self.product)
        self.assertEqual(item.quantity, 1)
        self.assertContains(self.client.get(shop_url), "Add to bag")

    def test_product_card_does_not_offer_add_to_bag_when_out_of_stock(self):
        self.product.stock_quantity = 0
        self.product.save()

        response = self.client.get(reverse("products:shop"))

        self.assertContains(response, "Out of stock")
        self.assertNotContains(response, "Add to bag")
        self.assertNotContains(response, "Buy now")

    def test_product_detail_has_available_purchase_actions_and_real_product_schema(self):
        response = self.client.get(
            reverse("products:product_detail", args=[self.product.slug])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Add to bag")
        self.assertContains(response, "Buy now")
        self.assertContains(response, '"price": "2500.00"')
        self.assertContains(response, "https://schema.org/InStock")

    def test_product_detail_exposes_keyboard_accessible_image_gallery_thumbnails(self):
        ProductImage.objects.create(
            product=self.product,
            image="products/front-view.jpg",
            alt_text="Front view",
            is_primary=True,
        )
        ProductImage.objects.create(
            product=self.product,
            image="products/side-view.jpg",
            alt_text="Side view",
        )

        response = self.client.get(
            reverse("products:product_detail", args=[self.product.slug])
        )

        self.assertContains(response, 'aria-label="Show image 1 of 2: Front view"')
        self.assertContains(response, 'aria-label="Show image 2 of 2: Side view"')
        self.assertContains(response, 'data-product-gallery-main')


class ProductManagementDashboardTests(TestCase):
    def setUp(self):
        self.url = reverse('products:management_dashboard')

    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(self.url)

        self.assertRedirects(response, f'{reverse("myadmin:login")}?next={self.url}')

    def test_non_designated_user_is_redirected_home(self):
        user = User.objects.create_user(
            username='customer',
            email='customer@example.com',
            password='test-password-123',
        )
        self.client.force_login(user)

        response = self.client.get(self.url)

        self.assertRedirects(response, reverse('core:home'))

    @override_settings(NEESORA_ADMIN_USERNAME='store-admin')
    def test_staff_user_sees_catalog_summary(self):
        staff_user = User.objects.create_superuser(
            username='store-admin',
            email='admin@example.com',
            password='test-password-123',
        )
        category = Category.objects.create(name='Everyday bags')
        Category.objects.create(name='Hidden category', is_active=False)
        Product.objects.create(
            name='Published bag',
            sku='BAG-001',
            description='A published bag.',
            category=category,
            price='1200.00',
            stock_quantity=3,
            product_status=Product.STATUS_PUBLISHED,
        )
        Product.objects.create(
            name='Draft bag',
            sku='BAG-002',
            description='A draft bag.',
            category=category,
            price='900.00',
            stock_quantity=0,
            product_status=Product.STATUS_DRAFT,
        )
        order = Order.objects.create(
            customer_name='Store customer',
            phone_number='9800000000',
            email='buyer@example.com',
            address='Lalitpur',
            city='Lalitpur',
            province='Bagmati',
            postal_code='44700',
            subtotal=Decimal('1200.00'),
            order_status=Order.STATUS_PENDING,
        )
        self.client.force_login(staff_user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'products/management/dashboard.html')
        self.assertEqual(response.context['total_products'], 2)
        self.assertEqual(response.context['available_products'], 1)
        self.assertEqual(response.context['out_of_stock_products'], 1)
        self.assertEqual(response.context['total_categories'], 2)
        self.assertEqual(response.context['total_orders'], 1)
        self.assertEqual(response.context['pending_orders'], 1)
        self.assertEqual(list(response.context['recent_orders']), [order])
        self.assertContains(response, 'href="/myadmin/orders/')


@override_settings(NEESORA_ADMIN_USERNAME="catalog-admin")
class CustomCatalogManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="catalog-admin",
            email="catalog-admin@example.com",
            password="CatalogAdminPass!842",
        )
        self.client.force_login(self.user)
        self.category = Category.objects.create(name="Everyday bags")
        self.media_root = TemporaryDirectory()
        self.addCleanup(self.media_root.cleanup)
        self.override = self.settings(MEDIA_ROOT=self.media_root.name)
        self.override.enable()
        self.addCleanup(self.override.disable)

    @staticmethod
    def image_upload(name="bag.png"):
        buffer = BytesIO()
        Image.new("RGB", (12, 12), color="olive").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def product_payload(self, **overrides):
        payload = {
            "name": "Canvas Tote",
            "sku": "TOTE-100",
            "category": str(self.category.pk),
            "brand": "Neesora",
            "short_description": "A simple everyday bag.",
            "description": "A durable canvas tote for everyday use.",
            "price": "1800.00",
            "discount_price": "",
            "stock_quantity": "12",
            "product_status": Product.STATUS_PUBLISHED,
            "featured": "on",
            "is_new_arrival": "",
            "is_best_seller": "",
            "images-TOTAL_FORMS": "1",
            "images-INITIAL_FORMS": "0",
            "images-MIN_NUM_FORMS": "0",
            "images-MAX_NUM_FORMS": "1000",
        }
        payload.update(overrides)
        return payload

    def test_product_create_updates_store_and_uploads_primary_image(self):
        response = self.client.post(
            reverse("myadmin:product_add"),
            self.product_payload(
                **{
                    "images-0-image": self.image_upload(),
                    "images-0-alt_text": "Olive canvas tote",
                    "images-0-is_primary": "on",
                }
            ),
        )

        product = Product.objects.get(sku="TOTE-100")
        self.assertRedirects(
            response,
            reverse("myadmin:product_detail", args=[product.pk]),
        )
        primary_image = product.images.get(is_primary=True)
        self.assertEqual(primary_image.alt_text, "Olive canvas tote")
        self.assertTrue(primary_image.image.storage.exists(primary_image.image.name))
        storefront_response = self.client.get(reverse("products:shop"))
        self.assertContains(storefront_response, "Canvas Tote")

    def test_product_create_supports_multiple_storefront_images(self):
        response = self.client.post(
            reverse("myadmin:product_add"),
            self.product_payload(
                **{
                    "images-TOTAL_FORMS": "2",
                    "images-0-image": self.image_upload("main.png"),
                    "images-0-alt_text": "Main bag image",
                    "images-0-is_primary": "on",
                    "images-1-image": self.image_upload("detail.png"),
                    "images-1-alt_text": "Bag detail image",
                }
            ),
        )

        product = Product.objects.get(sku="TOTE-100")
        self.assertRedirects(
            response,
            reverse("myadmin:product_detail", args=[product.pk]),
        )
        self.assertEqual(product.images.count(), 2)
        self.assertEqual(product.images.get(is_primary=True).alt_text, "Main bag image")
        self.assertTrue(product.images.filter(alt_text="Bag detail image").exists())

    def test_product_edit_can_remove_an_existing_image(self):
        product = Product.objects.create(
            name="Canvas Tote",
            sku="TOTE-IMAGE-EDIT",
            description="A tote with a removable gallery image.",
            category=self.category,
            price=Decimal("1800.00"),
        )
        image = ProductImage.objects.create(
            product=product,
            image=self.image_upload(),
            is_primary=True,
        )

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("myadmin:product_edit", args=[product.pk]),
                self.product_payload(
                    sku=product.sku,
                    **{
                        "images-TOTAL_FORMS": "2",
                        "images-INITIAL_FORMS": "1",
                        "images-0-id": str(image.pk),
                        "images-0-DELETE": "on",
                    }
                ),
            )

        self.assertRedirects(
            response,
            reverse("myadmin:product_detail", args=[product.pk]),
        )
        self.assertFalse(ProductImage.objects.filter(pk=image.pk).exists())
        self.assertFalse(default_storage.exists(image.image.name))

    def test_product_update_changes_price_stock_and_publication_visibility(self):
        product = Product.objects.create(
            name="Canvas Tote",
            sku="TOTE-101",
            description="Old description",
            category=self.category,
            price=Decimal("1800.00"),
            stock_quantity=10,
            product_status=Product.STATUS_PUBLISHED,
        )

        response = self.client.post(
            reverse("myadmin:product_edit", args=[product.pk]),
            self.product_payload(
                name="Canvas Tote Updated",
                sku=product.sku,
                price="2100.00",
                stock_quantity="0",
                product_status=Product.STATUS_DRAFT,
            ),
        )

        product.refresh_from_db()
        self.assertRedirects(
            response,
            reverse("myadmin:product_detail", args=[product.pk]),
        )
        self.assertEqual(product.price, Decimal("2100.00"))
        self.assertEqual(product.stock_quantity, 0)
        self.assertEqual(product.product_status, Product.STATUS_DRAFT)
        self.assertNotContains(self.client.get(reverse("products:shop")), "Canvas Tote Updated")

    def test_invalid_discount_keeps_form_errors_and_does_not_create_product(self):
        response = self.client.post(
            reverse("myadmin:product_add"),
            self.product_payload(discount_price="1800.00"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Discount price must be lower")
        self.assertFalse(Product.objects.filter(sku="TOTE-100").exists())

    def test_product_delete_requires_confirmation_and_protects_order_history(self):
        product = Product.objects.create(
            name="Ordered Tote",
            sku="TOTE-102",
            description="Linked to an order",
            category=self.category,
            price=Decimal("1800.00"),
        )
        order = Order.objects.create(
            customer_name="Store customer",
            phone_number="9800000000",
            email="buyer@example.com",
            address="Lalitpur",
            city="Lalitpur",
            province="Bagmati",
            postal_code="44700",
            subtotal=Decimal("1800.00"),
        )
        delete_confirmation = self.client.get(
            reverse("myadmin:product_delete", args=[product.pk])
        )
        self.assertEqual(delete_confirmation.status_code, 200)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            quantity=1,
            unit_price=product.price,
        )
        response = self.client.post(reverse("myadmin:product_delete", args=[product.pk]))

        self.assertRedirects(
            response,
            reverse("myadmin:product_detail", args=[product.pk]),
        )
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

    def test_product_delete_preserves_customer_cart_and_wishlist(self):
        product = Product.objects.create(
            name="Saved Tote",
            sku="TOTE-SAVED",
            description="A saved product.",
            category=self.category,
            price=Decimal("1800.00"),
        )
        customer = User.objects.create_user(
            username="saved-product-customer",
            email="saved-product-customer@example.com",
            password="CustomerPass!842",
        )
        CartItem.objects.create(user=customer, product=product, quantity=1)
        WishlistItem.objects.create(user=customer, product=product)

        response = self.client.post(
            reverse("myadmin:product_delete", args=[product.pk]),
        )

        self.assertRedirects(
            response,
            reverse("myadmin:product_detail", args=[product.pk]),
        )
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())
        self.assertTrue(CartItem.objects.filter(product=product).exists())
        self.assertTrue(WishlistItem.objects.filter(product=product).exists())

    def test_unreferenced_product_can_be_deleted(self):
        product = Product.objects.create(
            name="Unused Tote",
            sku="TOTE-UNUSED",
            description="Not referenced by customer or order data.",
            category=self.category,
            price=Decimal("1800.00"),
        )

        response = self.client.post(
            reverse("myadmin:product_delete", args=[product.pk]),
        )

        self.assertRedirects(response, reverse("myadmin:products"))
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())

    def test_category_management_and_safe_delete(self):
        response = self.client.get(reverse("myadmin:categories"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Everyday bags")

        create_response = self.client.post(
            reverse("myadmin:category_add"),
            {"name": "Travel bags", "description": "For longer journeys.", "is_active": "on"},
        )
        self.assertRedirects(create_response, reverse("myadmin:categories"))
        travel_category = Category.objects.get(name="Travel bags")

        Product.objects.create(
            name="Category protected product",
            sku="CATEGORY-LOCK",
            description="Keeps its category in use.",
            category=self.category,
            price=Decimal("1500.00"),
        )
        delete_response = self.client.post(
            reverse("myadmin:category_delete", args=[self.category.pk]),
        )
        self.assertRedirects(delete_response, reverse("myadmin:categories"))
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

        travel_delete = self.client.post(
            reverse("myadmin:category_delete", args=[travel_category.pk]),
        )
        self.assertRedirects(travel_delete, reverse("myadmin:categories"))
        self.assertFalse(Category.objects.filter(pk=travel_category.pk).exists())

    def test_product_search_filters_status_and_stock(self):
        Product.objects.create(
            name="Published Stocked Bag",
            sku="STOCK-1",
            description="Available",
            category=self.category,
            price=Decimal("100.00"),
            stock_quantity=4,
            product_status=Product.STATUS_PUBLISHED,
        )
        Product.objects.create(
            name="Draft Bag",
            sku="DRAFT-1",
            description="Not published",
            category=self.category,
            price=Decimal("100.00"),
            product_status=Product.STATUS_DRAFT,
        )

        response = self.client.get(
            reverse("myadmin:products"),
            {"q": "Stocked", "status": Product.STATUS_PUBLISHED, "stock": "low_stock"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([p.name for p in response.context["products"]], ["Published Stocked Bag"])

    def test_customer_cannot_post_product_creation(self):
        customer = User.objects.create_user(
            username="catalog-customer",
            email="catalog-customer@example.com",
            password="CustomerPass!842",
        )
        self.client.force_login(customer)

        response = self.client.post(
            reverse("myadmin:product_add"),
            self.product_payload(),
        )

        self.assertRedirects(response, reverse("core:home"))
        self.assertFalse(Product.objects.filter(sku="TOTE-100").exists())

    def test_product_mutation_requires_csrf_token(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        response = csrf_client.post(
            reverse("myadmin:product_add"),
            self.product_payload(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Product.objects.filter(sku="TOTE-100").exists())
