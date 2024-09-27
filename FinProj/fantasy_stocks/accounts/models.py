from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    initial_balance = models.DecimalField(max_digits=10, decimal_places=2, default=10000.00)
    total_gain_loss = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    def str(self):
        return self.user.username
