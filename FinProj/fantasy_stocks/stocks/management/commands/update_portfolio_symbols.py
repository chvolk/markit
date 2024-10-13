from django.core.management.base import BaseCommand
from stocks.models import Stock, Portfolio, PortfolioStock
from bazaar.models import PersistentPortfolioStock
import yfinance as yf
from decimal import Decimal

class Command(BaseCommand):
    help = 'Update stock prices for symbols in portfolios using yfinance'

    def handle(self, *args, **options):
        # Get unique symbols from weekly portfolios
        weekly_symbols = PortfolioStock.objects.values_list('stock__symbol', flat=True).distinct()
        
        # Get unique symbols from persistent portfolios
        persistent_symbols = PersistentPortfolioStock.objects.values_list('stock__symbol', flat=True).distinct()
        
        # Combine and deduplicate symbols
        all_symbols = set(list(weekly_symbols) + list(persistent_symbols))
        

        for symbol in all_symbols:
            try:
                # Fetch data from yfinance
                ticker = yf.Ticker(symbol)
                current_price = ticker.info['currentPrice']
                
                # Update the stock in the database
                stock = Stock.objects.get(symbol=symbol)
                stock.current_price = Decimal(str(current_price))
                stock.save()
                
                self.stdout.write(self.style.SUCCESS(f"Updated {symbol}: ${current_price}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error updating {symbol}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Stock price update complete!"))