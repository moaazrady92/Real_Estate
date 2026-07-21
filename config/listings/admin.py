from django.contrib import admin
from .models import Listing, ListingImage


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ["title", "city", "price", "listing_type", "source", "owner", "is_active", "created_at"]
    list_filter = ["source", "listing_type", "city", "is_active"]
    search_fields = ["title", "address"]
    readonly_fields = ["source", "source_url"]

    fieldsets = (
        ("Listing Info", {
            "fields": ("title", "description", "price", "city", "address", "listing_type", "owner", "is_active")
        }),
        ("Source (Admin Only)", {
            "fields": ("source", "source_url"),
            "classes": ("collapse",),
        }),
    )


@admin.register(ListingImage)
class ListingImageAdmin(admin.ModelAdmin):
    list_display = ["id", "listing", "is_primary"]