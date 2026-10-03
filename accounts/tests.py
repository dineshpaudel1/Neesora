from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import CustomerProfile


class RegistrationTests(TestCase):
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

    @override_settings(GOOGLE_LOGIN_ENABLED=True)
    def test_registration_shows_google_login_when_configured(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertContains(response, "Continue with Google")
        self.assertContains(response, "/accounts/google/login/")


class CategoryHomepageTests(TestCase):
    def test_homepage_links_to_active_categories(self):
        from products.models import Category

        category = Category.objects.create(name="Handbags", is_active=True)
        response = self.client.get(reverse("core:home"))

        self.assertContains(response, category.name)
        self.assertContains(response, reverse("products:category", args=[category.slug]))
        self.assertContains(response, "https://wa.me/9779765003814")
