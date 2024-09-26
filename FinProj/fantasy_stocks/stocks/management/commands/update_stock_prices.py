import yfinance as yf
from django.core.management.base import BaseCommand
from stocks.models import Stock

class Command(BaseCommand):
    help = 'Update prices for existing stocks from Yahoo Finance'

    def handle(self, *args, **options):
        stocks = Stock.objects.all()
        updated_count = 0

        for stock in stocks:
            try:
                ticker = yf.Ticker(stock.symbol)
                info = ticker.info

                stock.name = info.get('longName', stock.name)
                stock.current_price = info.get('regularMarketPrice', stock.current_price)
                stock.save()

                updated_count += 1

                if updated_count % 100 == 0:
                    self.stdout.write(f'Updated {updated_count} stocks so far...')

            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to update {stock.symbol}: {str(e)}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} stocks'))