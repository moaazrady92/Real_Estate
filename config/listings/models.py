from django.db import models
from django.conf import settings


class Listing(models.Model):
    SOURCE_CHOICES = [
        ("manual", "User Posted"),
        ("dubizzle", "Dubizzle"),
        ("aqarmap", "Aqarmap"),
        ("facebook", "Facebook Marketplace"),
    ]
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    address = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="manual")
    source_url = models.URLField(blank=True, null=True)  # original link if scraped
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="listings",
        null=True,
        blank=True,  # null = scraped listing, not posted by a user
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["source"]),
        ]

    def __str__(self):
        return f"{self.title}"


class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="listing_images/", null=True, blank=True)
    image_url = models.URLField(blank=True, null=True)  # for scraped images we just store the link
    is_primary = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.listing.title}"