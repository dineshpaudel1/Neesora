from django.db import migrations


def set_default_site_branding(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.filter(pk=1, domain="example.com").update(
        domain="neesora.com",
        name="Neesora",
    )


def restore_default_site_branding(apps, schema_editor):
    Site = apps.get_model("sites", "Site")
    Site.objects.filter(pk=1, domain="neesora.com").update(
        domain="example.com",
        name="example.com",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(
            set_default_site_branding,
            restore_default_site_branding,
        ),
    ]
