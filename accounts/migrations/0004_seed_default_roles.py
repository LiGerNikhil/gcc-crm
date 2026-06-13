from django.db import migrations


ROLES = [
    ("SUPER_ADMIN", "Super Admin", "Full system access with all permissions"),
    ("MANAGER", "Manager", "Manages team leads and oversees operations"),
    ("TEAM_LEAD", "Team Lead", "Leads a team of AROs and Callers"),
    ("ARO", "ARO (Agent)", "Handles document processing and data work"),
    ("CALLER", "Caller", "Handles outbound and inbound calls"),
    ("DATA_ENTRY", "Data Entry Operator", "Handles data entry tasks"),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    for code, name, desc in ROLES:
        Role.objects.get_or_create(
            role_code=code,
            defaults={"name": name, "description": desc},
        )


def assign_superuser_roles(apps, schema_editor):
    Role = apps.get_model("accounts", "Role")
    User = apps.get_model("accounts", "User")
    UserProfile = apps.get_model("accounts", "UserProfile")

    super_role = Role.objects.filter(role_code="SUPER_ADMIN").first()
    if not super_role:
        return

    for user in User.objects.filter(is_superuser=True):
        profile, created = UserProfile.objects.get_or_create(user=user)
        if created or profile.role is None:
            profile.role = super_role
            profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_nullable_userprofile_role"),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_code=migrations.RunPython.noop),
        migrations.RunPython(assign_superuser_roles, reverse_code=migrations.RunPython.noop),
    ]
