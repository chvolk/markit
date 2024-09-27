from django.core.management.base import BaseCommand
from django.utils import timezone
from stocks.models import Portfolio, PortfolioStock

class Command(BaseCommand):
    help = 'Resets all user portfolios'

    def handle(self, *args, **kwargs):
        # Delete all PortfolioStock entries
        PortfolioStock.objects.all().delete()

        # Update all Portfolios to reset any calculated values
        Portfolio.objects.update(last_reset=timezone.now())

        self.stdout.write(self.style.SUCCESS('Successfully reset all portfolios'))