from django.conf import settings


def site_information(request):
    """Make the store's shared business details available to every template."""
    return {
        "site_name": settings.SITE_NAME,
        "site_url": settings.SITE_URL,
        "site_description": settings.SITE_DESCRIPTION,
        "site_address": settings.SITE_ADDRESS,
        "site_phone": settings.SITE_PHONE,
        "site_email": settings.SITE_EMAIL,
        "site_currency": settings.CURRENCY_CODE,
        "site_shipping_fee": settings.FLAT_SHIPPING_FEE,
        "google_login_enabled": settings.GOOGLE_LOGIN_ENABLED,
    }
