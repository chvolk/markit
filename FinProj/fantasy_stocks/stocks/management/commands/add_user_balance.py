from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from stocks.models import Portfolio
from django.db import transaction

class Command(BaseCommand):
    help = 'Adds 10,000 to the balance of a specified user'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str, help='The username of the user to add balance to')

    @transaction.atomic
    def handle(self, *args, **options):
        username = options['username']
        amount_to_add = 10000

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            raise CommandError(f'User "{username}" does not exist')

        try:
            portfolio = Portfolio.objects.get(user=user)
        except Portfolio.DoesNotExist:
            raise CommandError(f'Portfolio for user "{username}" does not exist')

        old_balance = portfolio.balance
        portfolio.balance += amount_to_add
        portfolio.save()

        self.stdout.write(self.style.SUCCESS(
            f'Successfully added ${amount_to_add} to {username}\'s balance. '
            f'Old balance: ${old_balance}. New balance: ${portfolio.balance}.'
        ))
