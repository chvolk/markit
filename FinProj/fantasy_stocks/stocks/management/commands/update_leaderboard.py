from django.core.management.base import BaseCommand
from accounts.models import UserProfile  # Adjust import as needed
from django.db.models import F

class Command(BaseCommand):
    help = 'Updates the leaderboard by recalculating user portfolios'

    def handle(self, *args, **options):
        # Fetch all user profiles
        user_profiles = UserProfile.objects.all()

        for profile in user_profiles:
            # Recalculate portfolio value
            total_value = sum(holding.stock.current_price * holding.quantity 
                              for holding in profile.stockholding_set.all())
            
            # Update total gain/loss
            profile.total_gain_loss = total_value - profile.initial_balance
            profile.save()

        self.stdout.write(self.style.SUCCESS('Successfully updated leaderboard'))