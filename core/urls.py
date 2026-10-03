from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
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
