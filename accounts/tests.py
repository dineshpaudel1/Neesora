from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from cart.models import CartItem
from products.models import Category, Product

from .models import CustomerProfile


class RegistrationTests(TestCase):
    def test_account_page_has_post_logout_form(self):
        user = get_user_model().objects.create_user(
            username="customer-logout-form",
            email="logout-form@example.com",
            password="StrongBagPass!482",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:account"))

        self.assertContains(response, 'action="/logout/" method="post"')
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, ">Logout</button>")

    def test_logout_requires_post_and_clears_authenticated_session(self):
        user = get_user_model().objects.create_user(
            username="customer-logout",
            email="logout@example.com",
            password="StrongBagPass!482",
        )
        self.client.force_login(user)

        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertEqual(self.client.get(reverse("accounts:account")).status_code, 200)

        post_response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(post_response, reverse("core:home"))
        self.assertEqual(self.client.get(reverse("accounts:account")).status_code, 302)

    def test_registration_creates_user_profile_and_logs_user_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "customer@example.com",
                "password1": "StrongBagPass!482",
                "password2": "StrongBagPass!482",
            },
        )

        self.assertRedirects(response, reverse("accounts:account"))
        user = get_user_model().objects.get(email="customer@example.com")
        self.assertEqual(user.email, "customer@example.com")
        self.assertTrue(user.username)
        self.assertTrue(CustomerProfile.objects.filter(user=user).exists())
        account_response = self.client.get(reverse("accounts:account"))
        self.assertEqual(account_response.status_code, 200)
        self.assertContains(account_response, 'aria-label="My account"')
        self.assertNotContains(account_response, "Account / Login")

    def test_registration_renders_password_validation_errors(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "email": "customer@example.com",
                "password1": "short",
                "password2": "short",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password")
        self.assertFalse(
            get_user_model().objects.filter(email="customer@example.com").exists()
        )

    def test_registration_only_asks_for_email_and_password(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertNotContains(response, 'name="username"')

    def test_login_uses_neesora_site_branding(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertContains(response, "<title>Login | Neesora</title>", html=False)
        self.assertNotContains(response, "example.com")

    def test_login_password_field_does_not_show_password_toggle(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertContains(response, 'type="password" name="password"')
        self.assertNotContains(response, 'aria-label="Show password"')
        self.assertNotContains(response, "data-password-toggle")

    def test_login_accepts_email_and_password(self):
        user = get_user_model().objects.create_user(
            username="customer-login",
            email="customer@example.com",
            password="StrongBagPass!482",
        )
        CustomerProfile.objects.create(user=user)

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "customer@example.com", "password": "StrongBagPass!482"},
        )

        self.assertRedirects(response, reverse("accounts:account"))
        self.assertEqual(self.client.get(reverse("accounts:account")).status_code, 200)

    def test_login_merges_guest_cart_into_customer_account(self):
        user = get_user_model().objects.create_user(
            username="cart-merge-customer",
            email="cart-merge@example.com",
            password="StrongBagPass!482",
        )
        category = Category.objects.create(name="Cart merge bags")
        product = Product.objects.create(
            name="Merge Tote",
            sku="MERGE-TOTE-1",
            description="A bag carried over from a guest session.",
            category=category,
            price="1200.00",
            stock_quantity=4,
            product_status=Product.STATUS_PUBLISHED,
        )
        self.client.post(
            reverse("cart:add_to_cart", args=[product.pk]),
            {"quantity": "2"},
        )
        guest_session_key = self.client.session.session_key

        response = self.client.post(
            reverse("accounts:login"),
            {"username": user.email, "password": "StrongBagPass!482"},
        )

        self.assertRedirects(response, reverse("accounts:account"))
        self.assertTrue(
            CartItem.objects.filter(user=user, product=product, quantity=2).exists()
        )
        self.assertFalse(
            CartItem.objects.filter(session_key=guest_session_key).exists()
        )

    def test_login_accepts_username_and_password_for_superuser(self):
        get_user_model().objects.create_superuser(
            username="store-admin",
            email="admin@example.com",
            password="StrongBagPass!482",
        )

        response = self.client.post(
            reverse("accounts:login"),
            {"username": "store-admin", "password": "StrongBagPass!482"},
        )

        self.assertRedirects(response, reverse("accounts:account"))
        self.assertTrue(self.client.session["_auth_user_id"])

    @override_settings(GOOGLE_LOGIN_ENABLED=True)
    def test_registration_shows_google_login_when_configured(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertContains(response, "Continue with Google")
        self.assertContains(response, "/accounts/google/login/")


@override_settings(NEESORA_ADMIN_USERNAME="store-admin")
class DesignatedAdminAuthenticationTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.admin = self.user_model.objects.create_superuser(
            username="store-admin",
            email="admin@example.com",
            password="SecureAdminPass!739",
        )
        self.login_url = reverse("myadmin:login")
        self.dashboard_url = reverse("myadmin:dashboard")

    def test_admin_root_displays_custom_login_page(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "admin/login.html")
        self.assertContains(response, "Neesora")
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'aria-label="Show password"')
        self.assertNotContains(response, "Create one")

    def test_designated_admin_login_redirects_to_dashboard(self):
        response = self.client.post(
            self.login_url,
            {"username": "store-admin", "password": "SecureAdminPass!739"},
        )

        self.assertRedirects(response, self.dashboard_url)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertEqual(
            self.client.session.get_expiry_age(),
            8 * 60 * 60,
        )
        self.assertEqual(self.client.get(self.dashboard_url).status_code, 200)

    def test_authenticated_designated_admin_visiting_login_goes_to_dashboard(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.login_url)

        self.assertRedirects(response, self.dashboard_url)

    def test_invalid_credentials_do_not_authenticate(self):
        response = self.client.post(
            self.login_url,
            {"username": "store-admin", "password": "incorrect-password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unable to sign in.")
        self.assertFalse(self.client.session.get("_auth_user_id"))
        dashboard_response = self.client.get(self.dashboard_url)
        self.assertRedirects(
            dashboard_response,
            f"{self.login_url}?next={self.dashboard_url}",
        )

    def test_other_superuser_cannot_login_to_custom_admin(self):
        self.user_model.objects.create_superuser(
            username="other-admin",
            email="other@example.com",
            password="OtherAdminPass!739",
        )

        response = self.client.post(
            self.login_url,
            {"username": "other-admin", "password": "OtherAdminPass!739"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Unable to sign in.")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_customer_and_other_staff_are_denied_direct_dashboard_access(self):
        users = [
            self.user_model.objects.create_user(
                username="customer-user",
                email="customer-admin-test@example.com",
                password="CustomerPass!739",
            ),
            self.user_model.objects.create_user(
                username="other-staff",
                email="staff-admin-test@example.com",
                password="StaffPass!739",
                is_staff=True,
            ),
            self.user_model.objects.create_superuser(
                username="another-superuser",
                email="superuser-admin-test@example.com",
                password="SuperuserPass!739",
            ),
        ]

        for user in users:
            with self.subTest(username=user.username):
                self.client.force_login(user)
                response = self.client.get(self.dashboard_url)
                self.assertRedirects(response, reverse("core:home"))
                self.client.logout()

    def test_legacy_management_and_builtin_admin_require_designated_identity(self):
        user = self.user_model.objects.create_superuser(
            username="unselected-admin",
            email="unselected@example.com",
            password="UnselectedPass!739",
        )
        self.client.force_login(user)

        legacy_response = self.client.get(reverse("products:management_dashboard"))
        self.assertRedirects(legacy_response, reverse("core:home"))

        builtin_response = self.client.get(reverse("admin:index"), follow=True)
        self.assertEqual(builtin_response.status_code, 200)
        self.assertTemplateUsed(builtin_response, "core/home.html")

    def test_admin_root_opens_neesora_dashboard_for_designated_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "products/management/dashboard.html")
        self.assertContains(response, "Store dashboard")
        self.assertContains(response, "Recent orders")

    def test_admin_root_redirects_anonymous_visitors_to_custom_login(self):
        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(
            response,
            f"{self.login_url}?next={reverse('admin_dashboard')}",
        )

    def test_admin_root_denies_an_authenticated_customer(self):
        customer = self.user_model.objects.create_user(
            username="admin-route-customer",
            email="admin-route-customer@example.com",
            password="CustomerPass!739",
        )
        self.client.force_login(customer)

        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(response, reverse("core:home"))

    def test_dashboard_redirects_anonymous_visitors_to_custom_login(self):
        response = self.client.get(self.dashboard_url)

        self.assertRedirects(
            response,
            f"{self.login_url}?next={self.dashboard_url}",
        )

    def test_missing_admin_configuration_fails_closed(self):
        self.client.force_login(self.admin)

        with override_settings(NEESORA_ADMIN_USERNAME=""):
            response = self.client.get(self.dashboard_url)

        self.assertRedirects(response, reverse("core:home"))

        with override_settings(NEESORA_ADMIN_USERNAME=""):
            self.client.logout()
            login_response = self.client.post(
                self.login_url,
                {"username": "store-admin", "password": "SecureAdminPass!739"},
            )

        self.assertEqual(login_response.status_code, 200)
        self.assertContains(login_response, "Unable to sign in.")
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_external_next_url_is_not_used_after_login(self):
        response = self.client.post(
            f"{self.login_url}?next=https://attacker.example/",
            {"username": "store-admin", "password": "SecureAdminPass!739"},
        )

        self.assertRedirects(response, self.dashboard_url)

    def test_safe_next_url_is_honored_after_login(self):
        password_url = reverse("myadmin:password_change")
        response = self.client.post(
            f"{self.login_url}?next={password_url}",
            {"username": "store-admin", "password": "SecureAdminPass!739"},
        )

        self.assertRedirects(response, password_url)

    def test_designated_admin_can_access_builtin_admin(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)

    def test_logout_requires_post_and_clears_session(self):
        self.client.force_login(self.admin)

        get_response = self.client.get(reverse("myadmin:logout"))
        self.assertEqual(get_response.status_code, 405)
        self.assertTrue(self.client.session.get("_auth_user_id"))

        post_response = self.client.post(reverse("myadmin:logout"))

        self.assertRedirects(post_response, self.login_url)
        self.assertFalse(self.client.session.get("_auth_user_id"))

    def test_password_change_updates_password_and_keeps_admin_session(self):
        self.client.force_login(self.admin)
        self.assertTrue(self.client.session.get("_auth_user_id"))
        self.assertEqual(
            self.client.get(reverse("myadmin:password_change")).status_code,
            200,
        )

        response = self.client.post(
            reverse("myadmin:password_change"),
            {
                "old_password": "SecureAdminPass!739",
                "new_password1": "ChangedAdminPass!842",
                "new_password2": "ChangedAdminPass!842",
            },
        )

        self.assertRedirects(response, self.dashboard_url)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("ChangedAdminPass!842"))
        self.assertFalse(self.admin.check_password("SecureAdminPass!739"))
        self.assertEqual(self.client.get(self.dashboard_url).status_code, 200)

    def test_login_attempts_are_rate_limited(self):
        for _ in range(5):
            self.client.post(
                self.login_url,
                {"username": "store-admin", "password": "incorrect-password"},
            )

        response = self.client.post(
            self.login_url,
            {"username": "store-admin", "password": "SecureAdminPass!739"},
        )

        self.assertIn(response.status_code, (403, 429))
        self.assertFalse(self.client.session.get("_auth_user_id"))


class CategoryHomepageTests(TestCase):
    def test_homepage_links_to_active_categories(self):
        from products.models import Category

        category = Category.objects.create(name="Handbags", is_active=True)
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, category.name)
        self.assertContains(response, reverse("products:category", args=[category.slug]))
        self.assertContains(response, "https://wa.me/9779765003814")
