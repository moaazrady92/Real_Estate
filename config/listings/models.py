from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Listing(models.Model):
    LISTING_TYPE_CHOICES = [
        ("for_sale", "For Sale"),
        ("for_rent", "For Rent"),
    ]

    CITY_CHOICES = [
        ("cairo", "Cairo"),
        ("alexandria", "Alexandria"),
        ("giza", "Giza"),
        ("new_capital", "New Capital"),
        ("6th_of_october", "6th of October"),
        ("sharm_el_sheikh", "Sharm El Sheikh"),
        ("hurghada", "Hurghada"),
        ("mansoura", "Mansoura"),
        ("tanta", "Tanta"),
        ("luxor", "Luxor"),
        ("aswan", "Aswan"),
        ("suez", "Suez"),
        ("ismailia", "Ismailia"),
        ("port_said", "Port Said"),
        ("zagazig", "Zagazig"),
    ]

    SOURCE_CHOICES = [
        ("manual", "User Posted"),
        ("bayut", "Bayut"),
        ("aqarmap", "Aqarmap"),
        ("nawy", "Nawy")
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    city = models.CharField(max_length=50, choices=CITY_CHOICES, blank=True)
    address = models.CharField(max_length=300, blank=True)
    listing_type = models.CharField(max_length=10, choices=LISTING_TYPE_CHOICES, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_url = models.URLField(blank=True, null=True, unique=True)
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    bathrooms = models.PositiveSmallIntegerField(null=True, blank=True)
    area = models.PositiveIntegerField(null=True, blank=True)
    rating = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["source"]),
            models.Index(fields=["listing_type"]),
        ]

    def __str__(self):
        return f"{self.title}"

    @property
    def primary_image_url(self):
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.image_url or (primary.image.url if primary.image else None)
        first = self.images.first()
        if first:
            return first.image_url or (first.image.url if first.image else None)
        return None

class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="listing_images/", null=True, blank=True)
    image_url = models.URLField(blank=True, null=True)  # for scraped images we just store the link
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.listing.title}"