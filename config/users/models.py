from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone
from datetime import timedelta


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "seller")
        extra_fields.setdefault("first_name", "Admin")
        extra_fields.setdefault("last_name", "User")
        extra_fields.setdefault("phone_number", "00000000000")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"

    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pics/", blank=True, null=True)
    phone_number = models.CharField(max_length=20)
    role = models.CharField(max_length=10, choices=Role.choices)
    national_id = models.CharField(max_length=14, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.display_name or self.first_name} ({self.email})"


class PasswordResetCode(models.Model):
    email = models.EmailField()
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    def is_valid(self):
        return not self.used and timezone.now() < self.expires_at

    @classmethod
    def create_code(cls, email, expiry_minutes=10):
        import random
        code = "".join([str(random.randint(0, 9)) for _ in range(6)])
        return cls.objects.create(
            email=email,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes),
        )

    class Meta:
        ordering = ["-created_at"]