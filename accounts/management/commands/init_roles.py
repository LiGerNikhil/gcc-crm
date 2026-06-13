from django.core.management.base import BaseCommand
from accounts.models import Role, User, UserProfile


ROLES_DATA = [
    ("SUPER_ADMIN", "Super Admin", "Full system access. Can manage users, roles, and all data."),
    ("MANAGER", "Manager", "Manages team leads and AROs. Can view team performance and reports."),
    ("TEAM_LEAD", "Team Leader", "Manages AROs, assigns leads, and tracks team performance."),
    ("ARO", "ARO (Agent)", "Handles lead processing, customer calls, and follow-ups."),
    ("CALLER", "Caller", "Can view and manage assigned leads. Can update lead status and add activities."),
    ("DATA_ENTRY", "Data Entry Operator", "Can upload files, create leads via import, and manage lead data."),
]


class Command(BaseCommand):
    help = "Initialize default roles and create missing user profiles"

    def handle(self, *args, **options):
        for code, name, desc in ROLES_DATA:
            role, created = Role.objects.get_or_create(
                role_code=code,
                defaults={"name": name, "description": desc},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created role: {name}"))
            else:
                self.stdout.write(f"Role already exists: {name}")

        super_admin = Role.objects.filter(role_code="SUPER_ADMIN").first()

        profiles_created = 0
        for user in User.objects.filter(profile__isnull=True):
            UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": super_admin,
                    "is_active": True,
                },
            )
            profiles_created += 1

        if profiles_created:
            self.stdout.write(
                self.style.SUCCESS(f"Created {profiles_created} missing user profile(s)")
            )
        else:
            self.stdout.write("All users already have profiles")
