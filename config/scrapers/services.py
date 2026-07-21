import logging
from listings.models import Listing, ListingImage
from .aqarmap_scraper import AqarmapScraper
from .bayut_scraper import BayutScraper
from .models import ScraperRun
from django.utils import timezone
from .nawy_scraper import NawyScraper

logger = logging.getLogger(__name__)

def run_aqarmap_scraper(location_path, max_pages=100):
    logger.info("[Aqarmap] Starting scraper for %s (max_pages=%d)", location_path, max_pages)
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
        logger.info("[Aqarmap] %s: found=%d created=%d updated=%d", location_path, len(listings), created, updated)

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        logger.error("[Aqarmap] Scraper failed for %s: %s", location_path, e)

    run.finished_at = timezone.now()
    run.save()
    return run


def run_bayut_scraper(max_pages=100):
    logger.info("[Bayut] Starting scraper (max_pages=%d)", max_pages)
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
        logger.info("[Bayut] found=%d created=%d updated=%d", len(listings), created, updated)

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        logger.error("[Bayut] Scraper failed: %s", e)

    run.finished_at = timezone.now()
    run.save()
    return run

def run_nawy_scraper(max_pages=100):
    logger.info("[Nawy] Starting scraper (max_pages=%d)", max_pages)
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
        logger.info("[Nawy] found=%d created=%d updated=%d", len(listings), created, updated)

    except Exception as e:
        run.status = "failed"
        run.error_message = str(e)
        logger.error("[Nawy] Scraper failed: %s", e)

    run.finished_at = timezone.now()
    run.save()
    return run