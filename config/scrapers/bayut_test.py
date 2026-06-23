# scrapers/bayut_test2.py
import asyncio
from playwright.async_api import async_playwright

async def inspect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
        )
        await page.goto(
            "https://www.bayut.eg/en/property/apartments-for-sale/",
            wait_until="networkidle",
            timeout=30000
        )
        await page.wait_for_timeout(5000)

        articles = await page.query_selector_all("article")
        print(f"Found {len(articles)} articles\n")

        # Print first 3 cards HTML
        for i, article in enumerate(articles[:3]):
            html = await article.inner_html()
            print(f"--- CARD {i+1} ---")
            print(html[:2000])
            print()

        input("Press Enter to close...")
        await browser.close()

asyncio.run(inspect())