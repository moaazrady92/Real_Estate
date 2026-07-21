from django.contrib import admin
from .models import ScraperRun


@admin.register(ScraperRun)
class ScraperRunAdmin(admin.ModelAdmin):
    list_display = ["source", "status", "listings_found", "listings_created", "listings_updated", "started_at"]
    list_filter = ["source", "status"]
    readonly_fields = ["source", "started_at", "finished_at"]
