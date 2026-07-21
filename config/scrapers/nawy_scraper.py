import asyncio
import logging
import re
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class NawyScraper:
    BASE_URL = "https://www.nawy.com"

    CITY_MAP = {
        "new cairo": "cairo",
        "new capital": "new_capital",
        "6th of october": "6th_of_october",
        "october": "6th_of_october",
        "sheikh zayed": "giza",
        "new zayed": "giza",
        "zayed": "giza",
        "giza": "giza",
        "cairo": "cairo",
        "alexandria": "alexandria",
        "hurghada": "hurghada",
        "ain sokhna": "suez",
        "north coast": "alexandria",
        "sahel": "alexandria",
        "mansoura": "mansoura",
        "luxor": "luxor",
        "aswan": "aswan",
        "mostakbal": "cairo",
        "heliopolis": "cairo",
    }

    URLS = [
        ("type=apartment&purpose=sale", "for_sale"),
        ("type=apartment&purpose=rent", "for_rent"),
        ("type=villa&purpose=sale", "for_sale"),
        ("type=villa&purpose=rent", "for_rent"),
        ("type=townhouse&purpose=sale", "for_sale"),
        ("type=townhouse&purpose=rent", "for_rent"),
        ("type=duplex&purpose=sale", "for_sale"),
        ("type=duplex&purpose=rent", "for_rent"),
        ("type=penthouse&purpose=sale", "for_sale"),
        ("type=penthouse&purpose=rent", "for_rent"),
    ]

    def __init__(self, max_pages=100):
        self.max_pages = max_pages

    def scrape(self):
        return asyncio.run(self._scrape_all())

    async def _scrape_all(self):
        all_listings = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
            for params, listing_type in self.URLS:
                page = await context.new_page()
                for page_num in range(1, self.max_pages + 1):
                    url = f"{self.BASE_URL}/search?{params}&page={page_num}"
                    try:
                        await page.goto(url, wait_until="networkidle", timeout=30000)
                        await page.wait_for_timeout(3000)

                        cards = await page.query_selector_all(
                            "a[data-testid='search-result-card-link']"
                        )
                        logger.info("[Nawy] %s page %d: %d cards", params, page_num, len(cards))

                        if not cards:
                            break

                        for card in cards:
                            listing = await self._parse_card(card, listing_type)
                            if listing:
                                all_listings.append(listing)

                    except Exception as e:
                        logger.error("[Nawy] Failed on %s page %d: %s", params, page_num, e)
                        break
                await page.close()

            await browser.close()
        return all_listings

    async def _parse_card(self, card, listing_type="for_sale"):
        try:
            href = await card.get_attribute("href") or ""
            if not href:
                return None

            source_url = f"{self.BASE_URL}{href}"

            # Title from href slug e.g. /compound/2248-mountain-view-5th-settlement
            slug = href.split("/")[-1]  # "2248-mountain-view-5th-settlement"
            # Remove leading ID number
            title_slug = re.sub(r"^\d+-", "", slug)
            title = title_slug.replace("-", " ").title()

            # Image
            img_el = await card.query_selector("div.cover-image img")
            image_url = await img_el.get_attribute("src") if img_el else None

            # Price — try developer price first, then resale
            price = 0.0
            price_els = await card.query_selector_all("span.price")
            for price_el in price_els:
                price_text = await price_el.inner_text()
                parsed = self._parse_price(price_text)
                if parsed > 0:
                    price = parsed
                    break

            # Address — look for area/location text near the card
            # It appears as text nodes in the parent container
            parent = await card.evaluate_handle("el => el.parentElement")
            parent_text = await parent.evaluate("el => el.innerText") if parent else ""

            # Extract address lines — usually first 2 lines of card text
            lines = [l.strip() for l in parent_text.split("\n") if l.strip()]
            # Filter out noise (Compare, No Units, EGP, numbers only)
            address_lines = [
                l for l in lines
                if l and not l.isdigit()
                and l not in ("Compare", "No Units", "EGP", "Developer Start Price", "Resale Start Price")
                and not re.match(r"^[\d,]+$", l)
            ]
            address = address_lines[0] if address_lines else ""
            city = self._extract_city(address + " " + title)

            return {
                "title": title,
                "price": price,
                "city": city,
                "address": address,
                "listing_type": listing_type,
                "source_url": source_url,
                "image_url": image_url,
                "source": "nawy",
            }

        except Exception as e:
            logger.warning("[Nawy] Card parse error: %s", e)
            return None

    def _parse_price(self, text):
        digits = re.sub(r"[^\d]", "", text)
        return float(digits) if digits else 0.0

    def _extract_city(self, text):
        text_lower = text.lower()
        for keyword, city_key in self.CITY_MAP.items():
            if keyword in text_lower:
                return city_key
        return ""