from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect
from django.urls import reverse


def is_designated_admin(user):
    username = getattr(settings, "NEESORA_ADMIN_USERNAME", "").strip()
    return bool(
        username
        and user.is_authenticated
        and user.is_active
        and user.get_username() == username
    )


def designated_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(
                request.get_full_path(),
                reverse("myadmin:login"),
            )
        if not is_designated_admin(request.user):
            messages.error(request, "You are not authorized to access that page.")
            return redirect("core:home")
        return view_func(request, *args, **kwargs)

    return _wrapped_view
