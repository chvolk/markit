from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bazaar.models import BazaarUserProfile

class Command(BaseCommand):
    help = 'Creates BazaarUserProfiles for existing users'

    def handle(self, *args, **options):
        users_without_profile = User.objects.filter(bazaar_profile__isnull=True)
        for user in users_without_profile:
            BazaarUserProfile.objects.create(user=user, moqs=1000)
            self.stdout.write(self.style.SUCCESS(f'Created profile for user {user.username}'))