import logging
import requests
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)


class AqarmapScraper:
    BASE_URL = "https://aqarmap.com.eg"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    CITY_NAMES = {
        "cairo": "cairo",
        "alexandria": "alexandria",
        "giza": "giza",
        "new-capital": "new_capital",
        "6th-of-october": "6th_of_october",
        "sharm-el-sheikh": "sharm_el_sheikh",
        "hurghada": "hurghada",
        "mansoura": "mansoura",
        "tanta": "tanta",
        "luxor": "luxor",
        "aswan": "aswan",
        "suez": "suez",
        "ismailia": "ismailia",
        "port-said": "port_said",
        "zagazig": "zagazig",
    }

    def __init__(self, location_path, max_pages=100):
        self.location_path = location_path.strip("/")
        self.max_pages = max_pages

        parts = self.location_path.split("/")
        self.city_slug = parts[-1] if parts else "unknown"
        self.city_name = self.CITY_NAMES.get(self.city_slug, self.city_slug.replace("-", " ").title())

        # Extract listing type from path
        self.listing_type = "for_sale" if "for-sale" in self.location_path else "for_rent"

    def build_url(self, page=1):
        base = f"{self.BASE_URL}/en/{self.location_path}/"
        if page == 1:
            return f"{base}?durationOperator=gte&isFilterInitialized=true"
        return f"{base}?page={page}&durationOperator=gte&isFilterInitialized=true"

    def fetch_page(self, url):
        response = requests.get(url, headers=self.HEADERS, timeout=15)
        response.raise_for_status()
        return response.text

    def parse_listing_card(self, card):
        try:
            link_el = card.select_one("a[href*='/listing/']")
            price_el = card.select_one("data")
            title_el = card.select_one("h2[id^='listing-']")
            img_el = card.select_one("img")
            address_links = card.select("header .flex.text-caption-1 a")

            if not link_el or not title_el:
                return None

            address = " / ".join(a.get_text(strip=True) for a in address_links) if address_links else ""

            return {
                "title": title_el.get("title") or title_el.get_text(strip=True),
                "price": float(price_el.get("value")) if price_el and price_el.get("value") else 0.0,
                "city": self.city_name,
                "address": address,
                "listing_type": self.listing_type,
                "source_url": self._absolute_url(link_el.get("href", "")),
                "image_url": self._get_image_url(img_el),
                "source": "aqarmap",
            }
        except Exception as e:
            logger.warning("Failed to parse card: %s", e)
            return None

    def _get_image_url(self, img_el):
        if not img_el:
            return None
        return img_el.get("data-src") or img_el.get("src")

    def _absolute_url(self, href):
        if href.startswith("http"):
            return href
        return f"{self.BASE_URL}/en{href}" if not href.startswith("/en") else f"{self.BASE_URL}{href}"

    def scrape(self):
        all_listings = []
        for page in range(1, self.max_pages + 1):
            url = self.build_url(page)
            try:
                html = self.fetch_page(url)
            except Exception as e:
                logger.error("Failed to fetch %s: %s", url, e)
                break

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.select("article.listing-card")
            if not cards:
                break

            for card in cards:
                listing = self.parse_listing_card(card)
                if listing:
                    all_listings.append(listing)

            time.sleep(2)

        return all_listings