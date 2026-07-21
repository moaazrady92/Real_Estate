from listings.models import Listing, ListingImage
from .aqarmap_scraper import AqarmapScraper
from .bayut_scraper import BayutScraper
from .models import ScraperRun
from django.utils import timezone
from .nawy_scraper import NawyScraper

def run_aqarmap_scraper(location_path, max_pages=100):
    run = ScraperRun.objects.create(source="aqarmap")
    created = 0
    updated = 0

    try:
        scraper = AqarmapScraper(location_path=location_path, max_pages=max_pages)
        listings = scraper.scrape()

        for item in listings:
            obj, was_created = Listing.objects.update_or_create(
                source_url=item["source_url"],
                defaults={
                    "title": item["title"],
                    "price": item["price"],
                    "city": item.get("city", ""),
                    "address": item["address"],
                    "listing_type": item.get("listing_type", ""),
                    "source": "aqarmap",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            if item.get("image_url"):
                ListingImage.objects.update_or_create(
                    listing=obj,
                    image_url=item["image_url"],
                    defaults={"is_primary": True},
                )

        run.status = "success"
        run.listings_found = len(listings)
        run.listings_created = created
        run.listings_updated = updated

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)

    run.finished_at = timezone.now()
    run.save()
    return run


def run_bayut_scraper(max_pages=100):
    run = ScraperRun.objects.create(source="bayut")
    created = 0
    updated = 0

    try:
        scraper = BayutScraper(max_pages=max_pages)
        listings = scraper.scrape()

        for item in listings:
            obj, was_created = Listing.objects.update_or_create(
                source_url=item["source_url"],
                defaults={
                    "title": item["title"],
                    "price": item["price"],
                    "city": item.get("city", ""),
                    "address": item["address"],
                    "listing_type": item.get("listing_type", ""),
                    "source": "bayut",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            if item.get("image_url"):
                ListingImage.objects.update_or_create(
                    listing=obj,
                    image_url=item["image_url"],
                    defaults={"is_primary": True},
                )

        run.status = "success"
        run.listings_found = len(listings)
        run.listings_created = created
        run.listings_updated = updated

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)

    run.finished_at = timezone.now()
    run.save()
    return run

def run_nawy_scraper(max_pages=100):
    run = ScraperRun.objects.create(source="nawy")
    created = 0
    updated = 0

    try:
        scraper = NawyScraper(max_pages=max_pages)
        listings = scraper.scrape()

        for item in listings:
            obj, was_created = Listing.objects.update_or_create(
                source_url=item["source_url"],
                defaults={
                    "title": item["title"],
                    "price": item["price"],
                    "city": item.get("city", ""),
                    "address": item["address"],
                    "listing_type": item.get("listing_type", "for_sale"),
                    "source": "nawy",
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

            if item.get("image_url"):
                ListingImage.objects.update_or_create(
                    listing=obj,
                    image_url=item["image_url"],
                    defaults={"is_primary": True},
                )

        run.status = "success"
        run.listings_found = len(listings)
        run.listings_created = created
        run.listings_updated = updated

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)

    run.finished_at = timezone.now()
    run.save()
    return run