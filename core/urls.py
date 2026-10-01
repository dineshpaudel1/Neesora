from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.coming_soon, {"page_title": "Shop"}, name="shop"),
    path("search/", views.coming_soon, {"page_title": "Search"}, name="search"),
    path("wishlist/", views.coming_soon, {"page_title": "Wishlist"}, name="wishlist"),
    path("cart/", views.coming_soon, {"page_title": "Shopping bag"}, name="cart"),
    path("account/", views.coming_soon, {"page_title": "Your account"}, name="account"),
    path("login/", views.coming_soon, {"page_title": "Sign in"}, name="login"),
    path(
        "privacy-policy/",
        views.coming_soon,
        {"page_title": "Privacy policy"},
        name="privacy",
    ),
    path(
        "terms/",
        views.coming_soon,
        {"page_title": "Terms and conditions"},
        name="terms",
    ),
]
