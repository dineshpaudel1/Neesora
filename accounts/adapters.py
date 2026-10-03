from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from .models import CustomerProfile


class NeesoraSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        extra_data = sociallogin.account.extra_data
        full_name = (
            extra_data.get("name")
            or " ".join(
                part
                for part in (
                    extra_data.get("given_name"),
                    extra_data.get("family_name"),
                )
                if part
            )
        )
        CustomerProfile.objects.get_or_create(
            user=user,
            defaults={"full_name": full_name[:120]},
        )
        return user
