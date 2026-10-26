from django.contrib.admin import AdminSite
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse

from accounts.admin_access import is_designated_admin


class NeesoraAdminSite(AdminSite):
    def has_permission(self, request):
        return (
            is_designated_admin(request.user)
            and request.user.is_staff
        )

    def login(self, request, extra_context=None):
        next_url = request.GET.get("next")
        login_url = reverse("myadmin:login")
        if next_url:
            return redirect_to_login(next_url, login_url)
        return redirect(login_url)
