from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
import random
import string


def generate_user_id(role):
    prefix = {
        'admin': 'AD',
        'accounts': 'AC',
        'factory': 'FC'
    }.get(role, 'US')

    while True:
        number = ''.join(random.choices(string.digits, k=6))
        uid = f"{prefix}{number}"
        if not User.objects.filter(user_id=uid).exists():
            return uid


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('accounts', 'Accounts'),
        ('factory', 'Factory'),
    ]

    # username = None
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    user_id = models.CharField(max_length=10, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    active_user = models.BooleanField(default=True)

    # USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name', 'role']

    def save(self, *args, **kwargs):
        if not self.user_id:
            self.user_id = generate_user_id(self.role)
        if not self.username:
            self.username = self.email
        if not self.email:
            self.email = self.username

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.role})"


class ActivityLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=255)
    model_name = models.CharField(max_length=100)
    record_id = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} - {self.model_name}"
