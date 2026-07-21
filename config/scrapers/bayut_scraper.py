import asyncio
import logging
from playwright.async_api import async_playwright
import re

logger = logging.getLogger(__name__)


class BayutScraper:
    BASE_URL = "https://www.bayut.eg"

    CITY_MAP = {
        "cairo": "cairo",
        "alexandria": "alexandria",
        "giza": "giza",
        "new cairo": "cairo",
        "new capital": "new_capital",
        "6th of october": "6th_of_october",
        "sheikh zayed": "giza",
        "sharm el sheikh": "sharm_el_sheikh",
        "hurghada": "hurghada",
        "mansoura": "mansoura",
        "luxor": "luxor",
        "aswan": "aswan",
        "suez": "suez",
        "ismailia": "ismailia",
        "port said": "port_said",
        "zagazig": "zagazig",
        "red sea": "hurghada",
        "north coast": "alexandria",
        "matruh": "alexandria",
    }

    URLS = [
        ("https://www.bayut.eg/en/property/apartments-for-sale/", "for_sale", "apartment"),
        ("https://www.bayut.eg/en/property/apartments-for-rent/", "for_rent", "apartment"),
        ("https://www.bayut.eg/en/property/villas-for-sale/", "for_sale", "villa"),
        ("https://www.bayut.eg/en/property/villas-for-rent/", "for_rent", "villa"),
        ("https://www.bayut.eg/en/property/townhouses-for-sale/", "for_sale", "townhouse"),
        ("https://www.bayut.eg/en/property/townhouses-for-rent/", "for_rent", "townhouse"),
        ("https://www.bayut.eg/en/property/duplexes-for-sale/", "for_sale", "duplex"),
        ("https://www.bayut.eg/en/property/duplexes-for-rent/", "for_rent", "duplex"),
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
            for url, listing_type, property_type in self.URLS:
                listings = await self._scrape_url(context, url, listing_type, property_type)
                all_listings.extend(listings)
                logger.info("[Bayut] %s -> %d listings", url, len(listings))
            await browser.close()
        return all_listings

    async def _scrape_url(self, context, start_url, listing_type, property_type):
        results = []
        page = await context.new_page()

        for page_num in range(1, self.max_pages + 1):
            url = start_url if page_num == 1 else f"{start_url}?page={page_num}"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

                cards = await page.query_selector_all("article")
                logger.info("[Bayut] Page %d: %d cards", page_num, len(cards))

                if not cards:
                    break

                for card in cards:
                    listing = await self._parse_card(card, listing_type, property_type)
                    if listing:
                        results.append(listing)

            except Exception as e:
                logger.error("[Bayut] Failed on %s: %s", url, e)
                break

        await page.close()
        return results

    async def _parse_card(self, card, listing_type, property_type):
        try:
            link_el = await card.query_selector("a[aria-label='Listing link']")
            if not link_el:
                return None
            href = await link_el.get_attribute("href") or ""
            title = await link_el.get_attribute("title") or ""

            if not href or not title:
                return None

            source_url = f"{self.BASE_URL}{href}" if href.startswith("/") else href

            # Images — get all
            image_urls = []
            img_els = await card.query_selector_all("source[type='image/webp'], img")
            for img_el in img_els:
                srcset = await img_el.get_attribute("srcset") or ""
                if srcset:
                    for part in srcset.split(","):
                        url = part.strip().split(" ")[0]
                        if url and url not in image_urls:
                            image_urls.append(url)
                else:
                    url = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""
                    if url and url not in image_urls:
                        image_urls.append(url)

            # Price
            price_el = await card.query_selector("[aria-label='Price']")
            if not price_el:
                price_el = await card.query_selector("span[class*='price'], [class*='price']")
            price_text = await price_el.inner_text() if price_el else "0"
            price = self._parse_price(price_text)

            # Address
            address_el = await card.query_selector("[aria-label='Property address'], [class*='address'], [class*='location']")
            address = await address_el.inner_text() if address_el else ""
            if not address:
                card_text = await card.inner_text()
                lines = [l.strip() for l in card_text.split("\n") if l.strip()]
                address = lines[-3] if len(lines) >= 3 else ""

            city = self._extract_city(address + " " + title)

            return {
                "title": title.strip(),
                "price": price,
                "city": city,
                "address": address.strip(),
                "listing_type": listing_type,
                "source_url": source_url,
                "image_urls": image_urls,
                "property_type": property_type,
                "source": "bayut",
            }

        except Exception as e:
            logger.warning("[Bayut] Card parse error: %s", e)
            return None

    async def scrape_detail_async(self, source_url):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(source_url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)
            except Exception as e:
                logger.warning("[Bayut] Failed to fetch detail %s: %s", source_url, e)
                await browser.close()
                return {}

            detail = {}

            try:
                desc_el = await page.query_selector("[aria-label='Property description'], [class*='description'], [class*='about']")
                if desc_el:
                    detail["description"] = (await desc_el.inner_text())[:2000]
            except Exception:
                pass

            try:
                extra_imgs = []
                imgs = await page.query_selector_all("[class*='gallery'] img, [class*='slider'] img, [aria-label='Property image']")
                for img in imgs:
                    url = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
                    if url and "placehold" not in url and url not in extra_imgs:
                        extra_imgs.append(url)
                detail["extra_image_urls"] = extra_imgs
            except Exception:
                pass

            try:
                feats = await page.query_selector_all("[aria-label='Property features'] li, [class*='amenities'] li, [class*='features'] span")
                text = " ".join([(await f.inner_text()) for f in feats])
                import re
                bed_match = re.search(r"(\d+)\s*Bed", text)
                if bed_match:
                    detail["bedrooms"] = int(bed_match.group(1))
                bath_match = re.search(r"(\d+)\s*Bath", text)
                if bath_match:
                    detail["bathrooms"] = int(bath_match.group(1))
                area_match = re.search(r"(\d+)\s*(sq.?ft|sq.?m|m²|sq.?\s*ft|sq.?\s*m)", text, re.IGNORECASE)
                if area_match:
                    area_val = int(area_match.group(1))
                    unit = area_match.group(2).lower()
                    if "ft" in unit:
                        detail["area"] = int(area_val / 10.764)
                    else:
                        detail["area"] = area_val
            except Exception:
                pass

            # Try extract lat/lng from map elements
            try:
                map_el = await page.query_selector("[data-lat], [data-latitude], [class*='map'], #property-map")
                if map_el:
                    lat = await map_el.get_attribute("data-lat") or await map_el.get_attribute("data-latitude")
                    lng = await map_el.get_attribute("data-lng") or await map_el.get_attribute("data-longitude")
                    if lat and lng:
                        detail["latitude"] = float(lat)
                        detail["longitude"] = float(lng)
            except Exception:
                pass

            if "latitude" not in detail:
                try:
                    scripts = await page.query_selector_all("script[type='application/ld+json']")
                    import json
                    for s in scripts:
                        try:
                            content = await s.inner_text()
                            data = json.loads(content or "{}")
                            if isinstance(data, dict) and "geo" in data:
                                geo = data["geo"]
                                if "latitude" in geo and "longitude" in geo:
                                    detail["latitude"] = float(geo["latitude"])
                                    detail["longitude"] = float(geo["longitude"])
                                    break
                        except (json.JSONDecodeError, ValueError, TypeError):
                            continue
                except Exception:
                    pass

            await browser.close()
            return detail

    def scrape_detail(self, source_url):
        import asyncio
        return asyncio.run(self.scrape_detail_async(source_url))

    def _parse_price(self, text):
        digits = re.sub(r"[^\d]", "", text)
        return float(digits) if digits else 0.0

    def _extract_city(self, text):
        text_lower = text.lower()
        for keyword, city_key in self.CITY_MAP.items():
            if keyword in text_lower:
                return city_key
        return ""