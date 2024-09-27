from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from stocks.models import Portfolio

class Command(BaseCommand):
    help = 'Deletes all users except superusers'

    def handle(self, *args, **kwargs):
        # Delete all portfolios first
        Portfolio.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('All portfolios have been deleted.'))

        # Delete all non-superuser users
        users_deleted = User.objects.filter(is_superuser=False).delete()[0]
        self.stdout.write(self.style.SUCCESS(f'{users_deleted} users have been deleted.'))

        # Output the number of remaining superusers
        superusers_count = User.objects.filter(is_superuser=True).count()
        self.stdout.write(self.style.SUCCESS(f'{superusers_count} superusers remain.'))