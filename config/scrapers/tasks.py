from celery import shared_task
from .services import run_aqarmap_scraper

AQARMAP_LOCATIONS = [
    # Cairo
    "for-sale/property-type/cairo",
    "for-rent/property-type/cairo",
    # Alexandria
    "for-sale/property-type/alexandria",
    "for-rent/property-type/alexandria",
    # Giza
    "for-sale/property-type/giza",
    "for-rent/property-type/giza",
    # New Capital
    "for-sale/property-type/new-capital",
    "for-rent/property-type/new-capital",
    # 6th of October
    "for-sale/property-type/6th-of-october",
    "for-rent/property-type/6th-of-october",
    # Sharm El Sheikh
    "for-sale/property-type/sharm-el-sheikh",
    "for-rent/property-type/sharm-el-sheikh",
    # Hurghada
    "for-sale/property-type/hurghada",
    "for-rent/property-type/hurghada",
    # Mansoura
    "for-sale/property-type/mansoura",
    "for-rent/property-type/mansoura",
    # Tanta
    "for-sale/property-type/tanta",
    "for-rent/property-type/tanta",
    # Luxor
    "for-sale/property-type/luxor",
    "for-rent/property-type/luxor",
    # Aswan
    "for-sale/property-type/aswan",
    "for-rent/property-type/aswan",
    # Suez
    "for-sale/property-type/suez",
    "for-rent/property-type/suez",
    # Ismailia
    "for-sale/property-type/ismailia",
    "for-rent/property-type/ismailia",
    # Port Said
    "for-sale/property-type/port-said",
    "for-rent/property-type/port-said",
    # Zagazig
    "for-sale/property-type/zagazig",
    "for-rent/property-type/zagazig",
]


@shared_task
def scrape_aqarmap_location(location_path, max_pages=3):
    run = run_aqarmap_scraper(location_path, max_pages=max_pages)
    return {
        "location": location_path,
        "status": run.status,
        "found": run.listings_found,
        "created": run.listings_created,
        "updated": run.listings_updated,
    }


@shared_task
def scrape_all_aqarmap():
    for location in AQARMAP_LOCATIONS:
        scrape_aqarmap_location.delay(location, max_pages=3)