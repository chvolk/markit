import yfinance as yf
from django.core.management.base import BaseCommand
from stocks.models import Stock
import os

class Command(BaseCommand):
    help = 'Populate the database with a comprehensive list of stocks'

    def handle(self, *args, **options):
        # Read symbols from the text file
        file_path = os.path.join(os.path.dirname(__file__), 'stock_symbols.txt')
        with open(file_path, 'r') as file:
            symbols = [line.strip() for line in file if line.strip()]
        self.stdout.write(str(symbols))
        created_count = 0
        updated_count = 0
        failed_count = 0

        # Process symbols in batches to avoid overwhelming the API
        batch_size = 100
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            tickers = yf.Tickers(' '.join(batch))

            for symbol in batch:
                try:
                    info = tickers.tickers[symbol].info
                    self.stdout.write(str(info))
                    current_price = info.get('currentPrice', 0)
                    if current_price == 0:
                        continue
                    stock, created = Stock.objects.update_or_create(
                        symbol=symbol,
                        defaults={
                            'name': info.get('longName', symbol),
                            'current_price': info.get('currentPrice'),
                            'industry': info.get('industry')
                        }
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                    
                    self.stdout.write(f'Processed {symbol}')
                    
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(self.style.WARNING(f'Failed to fetch data for {symbol}: {str(e)}'))

            self.stdout.write(f'Processed batch {i//batch_size + 1} of {len(symbols)//batch_size + 1}')

        self.stdout.write(self.style.SUCCESS(
            f'Successfully created {created_count} stocks, '
            f'updated {updated_count} stocks, and '
            f'failed to process {failed_count} stocks.'
        ))