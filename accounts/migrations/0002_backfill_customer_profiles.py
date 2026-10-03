from django.conf import settings
from django.db import migrations


def create_missing_customer_profiles(apps, schema_editor):
    CustomerProfile = apps.get_model("accounts", "CustomerProfile")
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))

    users_without_profiles = User.objects.filter(
        customer_profile__isnull=True,
        is_staff=False,
        is_superuser=False,
    )
    for user in users_without_profiles.iterator():
        full_name = " ".join(
            value for value in (user.first_name, user.last_name) if value
        ).strip()
        CustomerProfile.objects.create(
            user_id=user.pk,
            full_name=full_name or user.username,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(
            create_missing_customer_profiles,
            migrations.RunPython.noop,
        ),
    ]
