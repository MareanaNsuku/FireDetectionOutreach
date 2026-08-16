import sys, time, urllib.parse, re, csv, random
from pathlib import Path
from playwright.sync_api import sync_playwright

LOCATIONS = [
    "Johannesburg", "Cape Town", "Durban", "Pretoria", "Gqeberha", "East London",
    "Bloemfontein", "Polokwane", "Mbombela", "Kimberley", "Rustenburg",
    "Pietermaritzburg", "George", "Stellenbosch", "Knysna", "Richards Bay",
    "Witbank", "Potchefstroom", "Klerksdorp", "Welkom", "Vanderbijlpark",
    "Soweto", "Khayelitsha", "Mitchells Plain", "Mamelodi"
]

CATEGORIES = [
    "fire detection company",
    "fire protection services",
    "security systems company",
    "software development company"
]

MAX_PER_QUERY = 5
MASTER_CSV = "master_companies.csv"

def accept_consent(page):
    try:
        for sel in [
            "button:has-text('Accept all')",
            "button:has-text('I agree')",
            "button:has-text('Agree')",
            "button[aria-label='Accept all']"
        ]:
            btn = page.locator(sel)
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(2000)
                return
    except:
        pass

def extract_via_clicks(page, max_results=5):
    results = []
    seen = set()
    loc = page.locator('div[role="feed"] a[aria-label]')
    count = loc.count()
    print(f"  Found {count} main result cards")
    for i in range(min(count, max_results)):
        try:
            card = page.locator('div[role="feed"] a[aria-label]').nth(i)
            aria = card.get_attribute("aria-label")
            if not aria:
                continue
            low = aria.lower()
            if low.startswith(("visit", "open", "call", "about", "ad")):
                continue
            if aria in seen:
                continue
            seen.add(aria)
            card.click()
            page.wait_for_timeout(2200)

            hrefs = page.eval_on_selector_all(
                "div[role='main'] a[href]",
                "els => els.map(e => e.href)"
            )
            website = next((h for h in hrefs if h.startswith("http") and "google" not in h), "")
            if website:
                results.append((aria, website))
                print(f"    ✅ {aria} → {website}")

            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
        except Exception as e:
            print(f"    ⚠️ Error on card {i}: {e}")
            continue
    return results

def domain_of(url):
    try:
        return urllib.parse.urlparse(url).netloc.lower().replace("www.", "")
    except:
        return url.lower()

def load_existing():
    existing = {}
    p = Path(MASTER_CSV)
    if not p.exists():
        return existing, ["Company Name", "Website", "Emails Found", "Status"]
    with open(p, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or ["Company Name", "Website", "Emails Found", "Status"]
        for row in reader:
            website = (row.get("Website") or "").strip()
            if website:
                existing[website.lower()] = row
    return existing, fields

def main():
    queries = []
    for loc in LOCATIONS:
        for cat in CATEGORIES:
            queries.append(f"{cat} {loc} South Africa")

    existing, fields = load_existing()
    print(f"🚀 Starting SA-focused Google Maps scraper: {len(queries)} queries")
    print(f"📁 Existing companies loaded: {len(existing)}")
    new_raw = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--headless=new",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
        )
        page = browser.new_page()
        for q in queries:
            print(f"\n🔎 {q}")
            url = f"https://www.google.com/maps/search/{urllib.parse.quote(q)}"
            try:
                page.goto(url, timeout=30000)
                accept_consent(page)
                try:
                    page.wait_for_selector('div[role="feed"] a[aria-label]', timeout=12000)
                except:
                    print("  ⚠️ No main result cards, waiting 6s anyway")
                    page.wait_for_timeout(6000)
                try:
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(1500)
                except:
                    pass
                results = extract_via_clicks(page, max_results=MAX_PER_QUERY)
                print(f"  ✅ Extracted {len(results)} companies")
                new_raw.extend(results)
            except Exception as e:
                print(f"  ❌ Error: {e}")
            time.sleep(random.uniform(4, 7))
        browser.close()

    # Add only unique new websites
    added = 0
    for name, website in new_raw:
        key = website.lower().rstrip('/')
        if key and key not in existing:
            existing[key] = {
                "Company Name": name,
                "Website": website,
                "Emails Found": "",
                "Status": ""
            }
            added += 1

    rows = list(existing.values())
    with open(MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})

    print(f"\n🎯 Added {added} new unique companies")
    print(f"📁 Total companies now: {len(rows)}")
    print("✅ Saved to master_companies.csv")

if __name__ == "__main__":
    main()
