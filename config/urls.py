"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.conf.urls.static import static
from django.urls import include, path

from accounts.admin_views import dashboard as admin_dashboard
from core.sitemaps import CategorySitemap, ProductSitemap, StorefrontSitemap

sitemaps = {
    "storefront": StorefrontSitemap,
    "categories": CategorySitemap,
    "products": ProductSitemap,
}

urlpatterns = [
    path('admin/', admin_dashboard, name='admin_dashboard'),
    path('django-admin/', admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path('myadmin/', include('accounts.admin_urls')),
    path('', include('core.urls')),
    path('', include('products.urls')),
    path('', include('accounts.urls')),
    path('', include('cart.urls')),
    path('', include('orders.urls')),
    path('', include('reviews.urls')),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
