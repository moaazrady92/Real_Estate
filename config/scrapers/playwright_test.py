# scrapers/playwright_test.py
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://dubizzle.com.eg/en/properties/", timeout=30000)
    page.wait_for_timeout(3000)
    print(page.title())
    browser.close()