from django.core.management.base import BaseCommand
from bazaar.models import PersistentPortfolio, PersistentPortfolioStock, BazaarUserProfile, InventoryStock
from django.db import transaction

class Command(BaseCommand):
    help = 'Resets all persistent portfolios, sets default MOQs for BazaarUserProfiles, and optionally resets user inventories'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print what would be done without actually doing it',
        )
        parser.add_argument(
            '--reset-inventories',
            action='store_true',
            help='Also reset user inventories',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        reset_inventories = options['reset_inventories']

        if not dry_run:
            confirm = input("Are you sure you want to reset all persistent portfolios" +
                            (" and user inventories" if reset_inventories else "") +
                            "? This action cannot be undone. (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.WARNING('Operation cancelled.'))
                return

        try:
            with transaction.atomic():
                # Count stocks that would be deleted
                stocks_count = PersistentPortfolioStock.objects.count()
                
                # Count portfolios that would be reset
                portfolios_count = PersistentPortfolio.objects.count()

                # Count BazaarUserProfiles that would be updated
                profiles_count = BazaarUserProfile.objects.count()

                # Count inventory items that would be deleted
                inventory_count = InventoryStock.objects.count() if reset_inventories else 0

                if not dry_run:
                    # Delete all PersistentPortfolioStock entries
                    PersistentPortfolioStock.objects.all().delete()
                    
                    # Update BazaarUserProfile to reset MOQs
                    BazaarUserProfile.objects.all().update(moqs=800)  # Set default MOQs
                    
                    if reset_inventories:
                        # Delete all Inventory entries
                        InventoryStock.objects.all().delete()
                    
                    success_message = (
                        f'Successfully reset persistent portfolios. '
                        f'Deleted {stocks_count} stocks, kept {portfolios_count} empty portfolios, '
                        f'and reset MOQs for {profiles_count} user profiles.'
                    )
                    if reset_inventories:
                        success_message += f' Also deleted {inventory_count} inventory items.'
                    
                    self.stdout.write(self.style.SUCCESS(success_message))
                else:
                    dry_run_message = (
                        f'Dry run: Would delete {stocks_count} stocks, '
                        f'keep {portfolios_count} empty portfolios, '
                        f'and reset MOQs for {profiles_count} user profiles.'
                    )
                    if reset_inventories:
                        dry_run_message += f' Would also delete {inventory_count} inventory items.'
                    
                    self.stdout.write(self.style.SUCCESS(dry_run_message))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {str(e)}'))