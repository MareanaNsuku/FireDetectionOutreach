import sys, time, urllib.parse, re, csv, random, os
from playwright.sync_api import sync_playwright

LOCATIONS = [
    "Gauteng", "Western Cape", "KwaZulu-Natal", "Eastern Cape", "Free State",
    "Limpopo", "Mpumalanga", "Northern Cape", "North West",
    "Johannesburg", "Cape Town", "Durban", "Pretoria", "Gqeberha",
    "East London", "Bloemfontein", "Polokwane", "Mbombela", "Kimberley",
    "Rustenburg", "Pietermaritzburg", "George", "Stellenbosch", "Knysna",
    "Richards Bay", "Witbank", "Potchefstroom", "Klerksdorp", "Welkom",
    "Vanderbijlpark"
]

CATEGORIES = [
    "fire detection company",
    "fire protection services",
    "security systems company",
    "software development company"
]

MAX_PER_QUERY = 6
PROCESSED_FILE = "processed_queries.txt"
RAW_CSV = "master_companies_raw.csv"

def load_processed():
    if not os.path.exists(PROCESSED_FILE):
        return set()
    with open(PROCESSED_FILE) as f:
        return set(line.strip() for line in f if line.strip())

def save_processed(query):
    with open(PROCESSED_FILE, "a") as f:
        f.write(query + "\n")

def append_raw(name, website):
    file_exists = os.path.exists(RAW_CSV)
    with open(RAW_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Company Name", "Website"])
        writer.writerow([name, website])

def load_raw():
    if not os.path.exists(RAW_CSV):
        return []
    rows = []
    with open(RAW_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((row.get("Company Name", ""), row.get("Website", "")))
    return rows

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

def extract_via_clicks(page, max_results=6):
    results = []
    seen_names = set()

    # Only left-panel result cards, not side-panel website buttons
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
            if aria.startswith(("Visit ", "Open website", "Call ", "About ", "Ad ·")):
                continue
            if low.startswith(("visit", "open", "call", "about", "ad")):
                continue
            if aria in seen_names:
                continue
            seen_names.add(aria)

            card.click()
            page.wait_for_timeout(2500)

            hrefs = page.eval_on_selector_all(
                "div[role='main'] a[href]",
                "els => els.map(e => e.href)"
            )
            website = ""
            for h in hrefs:
                if h.startswith("http") and "google" not in h:
                    website = h
                    break

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
        return url

def main():
    queries = []
    for loc in LOCATIONS:
        for cat in CATEGORIES:
            queries.append(f"{cat} {loc}")

    processed = load_processed()
    all_raw = load_raw()

    print(f"🚀 Starting improved Google Maps scraper: {len(queries)} total queries")
    print(f"✅ Already processed: {len(processed)} queries")
    print(f"✅ Existing raw companies loaded: {len(all_raw)}\n")

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
            if q in processed:
                continue
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

                # Scroll to load lazy results
                try:
                    page.mouse.wheel(0, 1500)
                    page.wait_for_timeout(1500)
                except:
                    pass

                results = extract_via_clicks(page, max_results=MAX_PER_QUERY)
                print(f"  ✅ Extracted {len(results)} companies")

                for name, website in results:
                    all_raw.append((name, website))
                    append_raw(name, website)

                save_processed(q)

            except Exception as e:
                print(f"  ❌ Error: {e}")

            time.sleep(random.uniform(4, 7))

        browser.close()

    # Deduplicate by domain
    seen_domains = set()
    unique = []
    for name, website in all_raw:
        d = domain_of(website)
        if d and d not in seen_domains:
            seen_domains.add(d)
            unique.append((name, website))

    print(f"\n🎯 Total unique companies: {len(unique)}")
    with open("master_companies.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Company Name", "Website", "Emails Found", "Status"])
        for name, website in unique:
            writer.writerow([name, website, "", ""])
    print("✅ Saved to master_companies.csv")

if __name__ == "__main__":
    main()
