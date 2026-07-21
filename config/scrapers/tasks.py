import logging
from celery import shared_task
from .services import run_aqarmap_scraper, run_bayut_scraper, run_nawy_scraper

logger = logging.getLogger(__name__)

AQARMAP_LOCATIONS = [
    "for-sale/property-type/cairo",
    "for-rent/property-type/cairo",
    "for-sale/property-type/alexandria",
    "for-rent/property-type/alexandria",
    "for-sale/property-type/giza",
    "for-rent/property-type/giza",
    "for-sale/property-type/new-capital",
    "for-rent/property-type/new-capital",
    "for-sale/property-type/6th-of-october",
    "for-rent/property-type/6th-of-october",
    "for-sale/property-type/sharm-el-sheikh",
    "for-rent/property-type/sharm-el-sheikh",
    "for-sale/property-type/hurghada",
    "for-rent/property-type/hurghada",
    "for-sale/property-type/mansoura",
    "for-rent/property-type/mansoura",
    "for-sale/property-type/tanta",
    "for-rent/property-type/tanta",
    "for-sale/property-type/luxor",
    "for-rent/property-type/luxor",
    "for-sale/property-type/aswan",
    "for-rent/property-type/aswan",
    "for-sale/property-type/suez",
    "for-rent/property-type/suez",
    "for-sale/property-type/ismailia",
    "for-rent/property-type/ismailia",
    "for-sale/property-type/port-said",
    "for-rent/property-type/port-said",
    "for-sale/property-type/zagazig",
    "for-rent/property-type/zagazig",
]


@shared_task
def scrape_aqarmap_location(location_path, max_pages=100):
    logger.info("Task started: scrape_aqarmap_location(%s)", location_path)
    run = run_aqarmap_scraper(location_path, max_pages=max_pages, scrape_details=True)
    result = {
        "location": location_path,
        "status": run.status,
        "found": run.listings_found,
        "created": run.listings_created,
        "updated": run.listings_updated,
    }
    logger.info("Task completed: scrape_aqarmap_location(%s) -> %s", location_path, result)
    return result


@shared_task
def scrape_all_aqarmap():
    logger.info("Task started: scrape_all_aqarmap")
    for location in AQARMAP_LOCATIONS:
        scrape_aqarmap_location.delay(location, max_pages=100)
    logger.info("Task completed: scrape_all_aqarmap - dispatched %d locations", len(AQARMAP_LOCATIONS))


@shared_task
def scrape_bayut(max_pages=100):
    logger.info("Task started: scrape_bayut")
    run = run_bayut_scraper(max_pages=max_pages, scrape_details=True)
    result = {
        "status": run.status,
        "found": run.listings_found,
        "created": run.listings_created,
        "updated": run.listings_updated,
    }
    logger.info("Task completed: scrape_bayut -> %s", result)
    return result


@shared_task
def scrape_nawy(max_pages=100):
    logger.info("Task started: scrape_nawy")
    run = run_nawy_scraper(max_pages=max_pages, scrape_details=True)
    result = {
        "status": run.status,
        "found": run.listings_found,
        "created": run.listings_created,
        "updated": run.listings_updated,
    }
    logger.info("Task completed: scrape_nawy -> %s", result)
    return result


@shared_task
def scrape_all_sources():
    logger.info("Task started: scrape_all_sources")
    scrape_all_aqarmap.delay()
    scrape_bayut.delay()
    scrape_nawy.delay()
    logger.info("Task completed: scrape_all_sources - all scrapers dispatched")
