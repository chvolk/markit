from django.core.management.base import BaseCommand
from accounts.models import UserProfile
from stocks.models import StockHolding  # Adjust this import if needed

class Command(BaseCommand):
    help = 'Updates the leaderboard by recalculating user portfolios'

    def handle(self, *args, **options):
        # Fetch all user profiles
        user_profiles = UserProfile.objects.all()

        for profile in user_profiles:
            # Recalculate portfolio value
            total_value = sum(holding.stock.current_price * holding.quantity 
                              for holding in StockHolding.objects.filter(user=profile.user))
            
            # Update total gain/loss
            profile.total_gain_loss = total_value - profile.initial_balance
            profile.save()

        self.stdout.write(self.style.SUCCESS('Successfully updated leaderboard'))