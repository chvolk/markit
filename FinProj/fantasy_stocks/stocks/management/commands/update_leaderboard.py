from django.core.management.base import BaseCommand
from stocks.models import UserProfile, PortfolioStock, Portfolio

class Command(BaseCommand):
    help = 'Updates the leaderboard by recalculating user portfolios'

    def handle(self, *args, **options):
        # Fetch all portfolios
        portfolios = Portfolio.objects.all()

        for portfolio in portfolios:
            # Recalculate portfolio value
            stock_value = sum(holding.stock.current_price * holding.quantity 
                              for holding in PortfolioStock.objects.filter(portfolio=portfolio))
            total_value = stock_value + portfolio.balance
            
            # Update total gain/loss
            portfolio.total_value = total_value
            portfolio.total_gain_loss = total_value - portfolio.initial_investment
            portfolio.save()

        self.stdout.write(self.style.SUCCESS('Successfully updated leaderboard'))