from django.contrib.admin.apps import AdminConfig


class NeesoraAdminConfig(AdminConfig):
    default_site = "config.admin.NeesoraAdminSite"
