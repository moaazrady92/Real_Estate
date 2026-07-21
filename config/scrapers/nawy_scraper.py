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

            slug = href.split("/")[-1]
            title_slug = re.sub(r"^\d+-", "", slug)
            title = title_slug.replace("-", " ").title()

            # Images — get all from card
            image_urls = []
            img_els = await card.query_selector_all("img")
            for img_el in img_els:
                src = await img_el.get_attribute("src") or await img_el.get_attribute("data-src") or ""
                if src and src not in image_urls and "placeholder" not in src.lower():
                    image_urls.append(src)

            # Price
            price = 0.0
            price_els = await card.query_selector_all("span.price")
            for price_el in price_els:
                price_text = await price_el.inner_text()
                parsed = self._parse_price(price_text)
                if parsed > 0:
                    price = parsed
                    break

            parent = await card.evaluate_handle("el => el.parentElement")
            parent_text = await parent.evaluate("el => el.innerText") if parent else ""
            lines = [l.strip() for l in parent_text.split("\n") if l.strip()]
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
                "image_urls": image_urls,
                "source": "nawy",
            }

        except Exception as e:
            logger.warning("[Nawy] Card parse error: %s", e)
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
                logger.warning("[Nawy] Failed to fetch detail %s: %s", source_url, e)
                await browser.close()
                return {}

            detail = {}

            try:
                desc_el = await page.query_selector("[class*='description'], [class*='about'], [class*='overview']")
                if desc_el:
                    detail["description"] = (await desc_el.inner_text())[:2000]
            except Exception:
                pass

            try:
                extra_imgs = []
                imgs = await page.query_selector_all("[class*='gallery'] img, [class*='carousel'] img, [class*='slider'] img")
                for img in imgs:
                    url = await img.get_attribute("src") or await img.get_attribute("data-src") or ""
                    if url and "placehold" not in url and url not in extra_imgs:
                        extra_imgs.append(url)
                detail["extra_image_urls"] = extra_imgs
            except Exception:
                pass

            try:
                feats = await page.query_selector_all("[class*='features'] li, [class*='specs'] li, [class*='amenities'] div")
                text = " ".join([(await f.inner_text()) for f in feats])
                import re
                bed_match = re.search(r"(\d+)\s*Bed", text)
                if bed_match:
                    detail["bedrooms"] = int(bed_match.group(1))
                bath_match = re.search(r"(\d+)\s*Bath", text)
                if bath_match:
                    detail["bathrooms"] = int(bath_match.group(1))
                area_match = re.search(r"(\d+)\s*(sq.?m|sq.?ft|m²)", text, re.IGNORECASE)
                if area_match:
                    area_val = int(area_match.group(1))
                    if "ft" in area_match.group(2).lower():
                        detail["area"] = int(area_val / 10.764)
                    else:
                        detail["area"] = area_val
            except Exception:
                pass

            # Try extract lat/lng
            try:
                map_el = await page.query_selector("[data-lat], [data-latitude], [class*='map-container'], #map")
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