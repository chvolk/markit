from django.core.management.base import BaseCommand, CommandError
from stocks.models import Stock, Portfolio
import yfinance as yf
from decimal import Decimal

class Command(BaseCommand):
    help = 'Updates a specific stock with latest data from Yahoo Finance'

    def add_arguments(self, parser):
        parser.add_argument('symbol', type=str, help='The stock symbol to update')

    def handle(self, *args, **options):
        symbol = options['symbol'].upper()

        try:
            stock = Stock.objects.get(symbol=symbol)
        except Stock.DoesNotExist:
            raise CommandError(f'Stock with symbol "{symbol}" does not exist in the database')

        try:
            # Fetch the latest data from Yahoo Finance
            yf_stock = yf.Ticker(symbol)
            info = yf_stock.info
            self.stdout.write(str(info))
            # Update the stock data
            Stock.objects.update_or_create(
                        symbol=symbol,
                        defaults={
                            'name': info.get('longName', symbol),
                            'current_price': 1.11,
                    'industry': info.get('industry', 'Unknown')
                }
            )
            # Update portfolios containing this stock
            portfolios = Portfolio.objects.filter(stocks=stock)
            for portfolio in portfolios:
                portfolio.update_total_value_and_gain_loss()
                self.stdout.write(self.style.SUCCESS(f'Updated portfolio for user {portfolio.user.username}'))

        except Exception as e:
            raise CommandError(f'Error updating stock {symbol}: {str(e)}')