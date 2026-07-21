import logging
from listings.models import Listing, ListingImage
from .aqarmap_scraper import AqarmapScraper
from .bayut_scraper import BayutScraper
from .models import ScraperRun
from django.utils import timezone
from .nawy_scraper import NawyScraper

logger = logging.getLogger(__name__)


def _save_images(listing_obj, image_urls, extra_urls=None):
    all_urls = list(image_urls)
    if extra_urls:
        existing = set(image_urls)
        for u in extra_urls:
            if u not in existing:
                all_urls.append(u)

    for i, url in enumerate(all_urls):
        if not url:
            continue
        img, created = ListingImage.objects.get_or_create(
            listing=listing_obj,
            image_url=url,
            defaults={"is_primary": (i == 0)},
        )
        if not created and i == 0 and not img.is_primary:
            img.is_primary = True
            img.save(update_fields=["is_primary"])


def _apply_detail(listing_obj, detail):
    if not detail:
        return
    updates = {}
    for field in ["description", "bedrooms", "bathrooms", "area", "latitude", "longitude"]:
        val = detail.get(field)
        if val is not None and val != "":
            updates[field] = val
    if updates:
        Listing.objects.filter(pk=listing_obj.pk).update(**updates)


def run_aqarmap_scraper(location_path, max_pages=100, scrape_details=False):
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

            _save_images(obj, item.get("image_urls", []))

            if scrape_details and was_created:
                detail = scraper.scrape_detail(item["source_url"])
                _apply_detail(obj, detail)
                _save_images(obj, [], detail.get("extra_image_urls", []))

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


def run_bayut_scraper(max_pages=100, scrape_details=False):
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

            _save_images(obj, item.get("image_urls", []))

            if scrape_details and was_created:
                detail = scraper.scrape_detail(item["source_url"])
                _apply_detail(obj, detail)
                _save_images(obj, [], detail.get("extra_image_urls", []))

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


def run_nawy_scraper(max_pages=100, scrape_details=False):
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

            _save_images(obj, item.get("image_urls", []))

            if scrape_details and was_created:
                detail = scraper.scrape_detail(item["source_url"])
                _apply_detail(obj, detail)
                _save_images(obj, [], detail.get("extra_image_urls", []))

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
