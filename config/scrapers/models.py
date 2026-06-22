from django.db import models


class ScraperRun(models.Model):
    SOURCE_CHOICES = [
        ("dubizzle", "Dubizzle"),
        ("aqarmap", "Aqarmap"),
        ("facebook", "Facebook Marketplace"),
    ]
    STATUS_CHOICES = [
        ("success", "Success"),
        ("failed", "Failed"),
        ("partial", "Partial"),
    ]

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="success")
    listings_found = models.PositiveIntegerField(default=0)
    listings_created = models.PositiveIntegerField(default=0)
    listings_updated = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.source} run @ {self.started_at}"