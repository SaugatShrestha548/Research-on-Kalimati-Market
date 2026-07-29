"""
Kalimati Fruit & Vegetable Market Price Scraper
================================================
Scrapes daily wholesale prices from https://kalimatimarket.gov.np/price
Date range : 2021-05-14 (AD) → 2026-05-14 (AD)
             = approx BS 2078-01-31 → BS 2083-02-01

Requirements
------------
    pip install requests beautifulsoup4 nepali-datetime

Usage
-----
    python kalimati_scraper.py

Output
------
    kalimati_prices.csv   – all scraped rows
    kalimati_errors.csv   – dates that had no data / errors
"""

import csv
import time
import logging
import os
import sys
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

# ─── nepali-datetime for BS ↔ AD conversion ───────────────────────────────
try:
    import nepali_datetime
except ImportError:
    sys.exit(
        "❌  Please install:  pip install nepali-datetime\n"
        "   Then re-run this script."
    )

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    handlers=[
        logging.FileHandler("kalimati_scraper.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
START_DATE_AD = date(2021, 5, 14)   # Gregorian start date
END_DATE_AD   = date(2026, 7, 14)   # Gregorian end date (inclusive)

OUTPUT_CSV = "kalimati_prices.csv"
ERRORS_CSV = "kalimati_errors.csv"

DELAY_SECONDS  = 1.2   # Polite crawl delay between requests
MAX_RETRIES    = 3     # Retry failed requests up to this many times
RETRY_WAIT     = 5     # Seconds to wait between retries

BASE_URL       = "https://kalimatimarket.gov.np"
PRICE_URL      = BASE_URL + "/price"
LANG_EN_URL    = BASE_URL + "/lang/en"

# ─────────────────────────────────────────────────────────────────────────────
# NEPALI ↔ ENGLISH DIGIT / CURRENCY CONVERSION
# ─────────────────────────────────────────────────────────────────────────────
_NP_DIGIT_TABLE = str.maketrans("०१२३४५६७८९", "0123456789")


def devanagari_to_ascii(text: str) -> str:
    """Translate Devanagari digits and remove 'रू' currency prefix."""
    return text.replace("रू", "").replace(",", "").strip().translate(_NP_DIGIT_TABLE)


def parse_price(text: str) -> float | str:
    """Return float price or empty string if parsing fails."""
    cleaned = devanagari_to_ascii(text)
    try:
        return float(cleaned)
    except ValueError:
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# NEPALI COMMODITY & UNIT TRANSLATIONS
# ─────────────────────────────────────────────────────────────────────────────
COMMODITY_MAP: dict[str, str] = {
    # ── Tomatoes ──────────────────────────────────────────────────────────────
    "गोलभेडा ठूलो(नेपाली)":      "Large Tomato (Nepali)",
    "गोलभेडा ठूलो(भारतीय)":      "Large Tomato (Indian)",
    "गोलभेडा सानो(लोकल)":        "Small Tomato (Local)",
    "गोलभेडा सानो(टनेल)":        "Small Tomato (Tunnel)",
    "गोलभेडा सानो(भारतीय)":      "Small Tomato (Indian)",
    "गोलभेडा सानो(तराई)":        "Small Tomato (Terai)",
    # ── Potato ───────────────────────────────────────────────────────────────
    "आलु रातो(लाम्चो)":          "Red Potato (Long)",
    "आलु रातो(भारतीय)":          "Red Potato (Indian)",
    "रातो आलु(गोलो)":            "Red Potato (Round)",
    "आलु सेतो(मुस्ताङ)":         "White Potato (Mustang)",
    "आलु सेतो(भारतीय)":          "White Potato (Indian)",
    # ── Onion & Garlic ───────────────────────────────────────────────────────
    "प्याज सुकेको (भारतीय)":     "Dried Onion (Indian)",
    "प्याज सुकेको (नेपाली)":     "Dried Onion (Nepali)",
    "प्याज हरियो":               "Green Onion",
    "लसुन हरियो":                "Green Garlic",
    "लसुन सुकेको चाइनिज":        "Dried Garlic (Chinese)",
    "लसुन सुकेको नेपाली":        "Dried Garlic (Nepali)",
    # ── Root Vegetables ──────────────────────────────────────────────────────
    "गाजर(लोकल)":                "Carrot (Local)",
    "गाजर(भारतीय)":              "Carrot (Indian)",
    "मूला रातो":                  "Red Radish",
    "मूला सेतो(लोकल)":           "White Radish (Local)",
    "सेतो मूला(हाइब्रीड)":       "White Radish (Hybrid)",
    "गान्टे मूला":               "Turnip",
    "चुकुन्दर":                  "Beetroot",
    "सखरखण्ड":                   "Sweet Potato",
    "पिंडालू":                   "Taro Root",
    "अदुवा":                     "Ginger",
    # ── Leafy Greens ─────────────────────────────────────────────────────────
    "रायो साग":                   "Mustard Greens",
    "पालूगो साग":                 "Spinach",
    "चमसूरको साग":                "Garden Cress",
    "तोरीको साग":                 "Rape Greens",
    "मेथीको साग":                 "Fenugreek Leaves",
    "जिरीको साग":                 "Dill Greens",
    "सौफको साग":                  "Fennel Greens",
    "पुदीना":                     "Mint",
    "हरियो धनिया":               "Fresh Coriander",
    "न्यूरो":                     "Fiddlehead Fern",
    "सजिवन":                     "Moringa / Drumstick Leaves",
    # ── Brassicas ────────────────────────────────────────────────────────────
    "बन्दा(लोकल)":               "Cabbage (Local)",
    "रातो बन्दा":                "Red Cabbage",
    "काउली स्थानिय":             "Cauliflower (Local)",
    "ब्रोकाउली":                  "Broccoli",
    # ── Brinjal / Eggplant ───────────────────────────────────────────────────
    "भन्टा लाम्चो":              "Brinjal (Long)",
    "भन्टा डल्लो":               "Brinjal (Round)",
    # ── Beans & Legumes ──────────────────────────────────────────────────────
    "बोडी(तने)":                  "Yard Long Bean",
    "मकै बोडी":                   "Corn Bean",
    "घिउ सिमी(लोकल)":            "Butter Bean (Local)",
    "घिउ सिमी(हाइब्रीड)":        "Butter Bean (Hybrid)",
    "घिउ सिमी(राजमा)":           "Kidney Bean",
    "टाटे सिमी":                  "Flat Bean",
    "मटरकोशा":                   "Pea Pod",
    "भटमासकोशा":                 "Soybean Pod",
    # ── Gourds ───────────────────────────────────────────────────────────────
    "लौका":                       "Bottle Gourd",
    "फर्सी पाकेको":               "Ripe Pumpkin",
    "फर्सी हरियो(लाम्चो)":       "Green Pumpkin (Long)",
    "हरियो फर्सी(डल्लो)":        "Green Pumpkin (Round)",
    "परवर(लोकल)":                "Pointed Gourd (Local)",
    "परवर(तराई)":                "Pointed Gourd (Terai)",
    "चिचिण्डो":                  "Snake Gourd",
    "घिरौला":                    "Sponge Gourd",
    "झिगूनी":                    "Ridge Gourd",
    "तितो करेला":                 "Bitter Gourd",
    "स्कूस":                      "Chayote",
    # ── Okra / Others ────────────────────────────────────────────────────────
    "भिण्डी":                     "Okra / Lady Finger",
    "कुरीलो":                     "Asparagus",
    # ── Chilies ──────────────────────────────────────────────────────────────
    "खु्र्सानी सुकेको":           "Dried Chili",
    "खुर्सानी सुकेको":            "Dried Chili",
    "खुर्सानी हरियो(लाम्चो)":    "Green Chili (Long)",
    "खुर्सानी हरियो(बुलेट)":     "Green Chili (Bullet)",
    "खुर्सानी हरियो(माछे)":      "Green Chili (Mache)",
    "भेडे खु्र्सानी":            "Bell Pepper",
    "भेडे खुर्सानी":             "Bell Pepper",
    # ── Mushrooms ────────────────────────────────────────────────────────────
    "च्याउ(कन्य)":               "Oyster Mushroom",
    "च्याउ(डल्ले)":              "Button Mushroom",
    "राजा च्याउ":                "King Oyster Mushroom",
    "सिताके च्याउ":              "Shiitake Mushroom",
    # ── Misc Vegetables ──────────────────────────────────────────────────────
    "तामा":                       "Bamboo Shoot",
    "तोफु":                       "Tofu",
    "गुन्दुक":                   "Gundruk (Fermented Greens)",
    "इमली":                      "Tamarind",
    "छ्यापी सुकेको":             "Dried Timur (Szechuan Pepper)",
    "सेलरी":                     "Celery",
    "पार्सले":                   "Parsley",
    # ── Fruits ───────────────────────────────────────────────────────────────
    "स्याउ(झोले)":               "Apple (Jhole)",
    "स्याउ(फूजी)":               "Apple (Fuji)",
    "केरा(नेपाली)":              "Banana (Nepali)",
    "केरा(मालभोग)":              "Banana (Malbhog)",
    "कागती":                     "Lemon",
    "अनार":                      "Pomegranate",
    "अंगुर(हरियो)":              "Grape (Green)",
    "अंगुर(कालो)":               "Grape (Black)",
    "तरबुजा(हरियो)":             "Watermelon",
    "भुई कटहर":                  "Ground Jackfruit",
    "रुख कटहर":                  "Tree Jackfruit",
    "काक्रो(लोकल)":              "Cucumber (Local)",
    "काक्रो(हाइब्रीड)":          "Cucumber (Hybrid)",
    "काक्रो(लोकलक्रस)":          "Cucumber (Local Cross)",
    "मेवा(नेपाली)":              "Papaya (Nepali)",
    "मेवा(भारतीय)":              "Papaya (Indian)",
    "लीच्ची(लोकल)":              "Lychee (Local)",
    "आभोकाडो":                   "Avocado",
    "नरिवल(काँचो)":              "Coconut (Raw)",
    "नरिवल(हरियो)":              "Coconut (Green)",
    "आँप(दसहरी)":                "Mango (Dasheri)",
    "आँप(मालदह)":                "Mango (Malda)",
    "आँप(लोकल)":                 "Mango (Local)",
    # ── Fish ─────────────────────────────────────────────────────────────────
    "ताजा माछा(रहु)":            "Fresh Fish (Rohu)",
    "ताजा माछा(बचुवा)":          "Fresh Fish (Bachwa)",
    "ताजा माछा(छडी)":            "Fresh Fish (Chhadi)",
}

UNIT_MAP: dict[str, str] = {
    "के.जी.": "KG",
    "केजी":   "KG",
    "के जी":  "KG",
    "किलो":   "KG",
    "दर्जन":  "Dozen",
    "प्रति गोटा": "Per Piece",
    "गोटा":   "Piece",
    "मुठा":   "Bundle",
}


def translate_commodity(raw: str) -> str:
    """Look up Nepali commodity name; keep original if not found."""
    key = raw.strip()
    return COMMODITY_MAP.get(key, key)   # unknown names kept as-is


def translate_unit(raw: str) -> str:
    key = raw.strip()
    return UNIT_MAP.get(key, key)


# ─────────────────────────────────────────────────────────────────────────────
# DATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def ad_to_bs(ad: date) -> nepali_datetime.date:
    return nepali_datetime.date.from_datetime_date(ad)


def bs_date_str(bs: nepali_datetime.date) -> str:
    """Return 'YYYY-MM-DD' in BS (used as query param)."""
    return f"{bs.year}-{bs.month:02d}-{bs.day:02d}"


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def build_session() -> requests.Session:
    """Create a requests Session that looks like a browser and has English locale."""
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection":      "keep-alive",
    })
    # Set English language preference (site uses session/cookie-based lang)
    try:
        s.get(LANG_EN_URL, timeout=15)
    except Exception:
        pass
    return s


def fetch_price_page(session: requests.Session, bs: nepali_datetime.date) -> requests.Response | None:
    """
    Try several URL / POST patterns to load the price page for a given BS date.
    Returns the Response or None if all attempts fail.
    """
    date_str = bs_date_str(bs)

    # Pattern 1 – GET with query string  (most common Laravel approach)
    url_get = f"{PRICE_URL}?date={date_str}"

    # Pattern 2 – POST to /price  (form POST with CSRF)
    # We first GET the page to grab the CSRF token, then POST.

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # ── Attempt GET ──────────────────────────────────────────────────
            r = session.get(url_get, timeout=30)
            if r.status_code == 200:
                return r

            # ── Attempt POST (CSRF-aware) ────────────────────────────────────
            # Get a fresh page to extract the CSRF token
            r_base = session.get(PRICE_URL, timeout=20)
            soup_base = BeautifulSoup(r_base.content, "html.parser")

            # Look for CSRF in <meta> or hidden <input>
            csrf_token = ""
            meta_csrf = soup_base.find("meta", {"name": "csrf-token"})
            if meta_csrf:
                csrf_token = meta_csrf.get("content", "")
            else:
                hidden = soup_base.find("input", {"name": "_token"})
                if hidden:
                    csrf_token = hidden.get("value", "")

            post_data = {"price_date": date_str, "_token": csrf_token}
            r_post = session.post(
                PRICE_URL,
                data=post_data,
                headers={"Referer": PRICE_URL, "X-CSRF-TOKEN": csrf_token},
                timeout=30,
            )
            if r_post.status_code == 200:
                return r_post

        except requests.RequestException as exc:
            log.warning("Attempt %d/%d failed for BS %s: %s", attempt, MAX_RETRIES, date_str, exc)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_WAIT)

    return None


def parse_prices(response: requests.Response, ad: date, bs: nepali_datetime.date) -> list[dict]:
    """Parse the price table from the HTML response into a list of dicts."""
    soup = BeautifulSoup(response.content, "html.parser")
    table = soup.find("table")
    if not table:
        return []

    rows = table.find_all("tr")
    records = []

    for row in rows[1:]:   # skip header row
        cols = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(cols) < 4:
            continue

        # Standard layout: [Commodity, Unit, Min, Max, Avg]
        # Some rows have 4 cols (no unit column)
        if len(cols) == 4:
            commodity_raw, min_raw, max_raw, avg_raw = cols
            unit_raw = ""
        else:
            commodity_raw, unit_raw, min_raw, max_raw, avg_raw = cols[:5]

        records.append({
            "date_ad":    str(ad),
            "date_bs":    bs_date_str(bs),
            "commodity":  translate_commodity(commodity_raw),
            "unit":       translate_unit(unit_raw),
            "min_price":  parse_price(min_raw),
            "max_price":  parse_price(max_raw),
            "avg_price":  parse_price(avg_raw),
            # Keep raw Nepali name for reference / manual review
            "commodity_np": commodity_raw,
        })

    return records


# ─────────────────────────────────────────────────────────────────────────────
# RESUME SUPPORT  – load already-scraped dates so we can skip them
# ─────────────────────────────────────────────────────────────────────────────

def load_done_dates(csv_path: str) -> set[str]:
    done = set()
    if not os.path.exists(csv_path):
        return done
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            done.add(row.get("date_ad", ""))
    return done


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("Kalimati Price Scraper  |  %s → %s", START_DATE_AD, END_DATE_AD)

    # ── Check if we're resuming ───────────────────────────────────────────────
    done_dates = load_done_dates(OUTPUT_CSV)
    if done_dates:
        log.info("Resuming – %d dates already scraped, skipping them.", len(done_dates))

    # ── Open output files ─────────────────────────────────────────────────────
    output_mode = "a" if done_dates else "w"   # append if resuming, write-new otherwise

    fieldnames = ["date_ad", "date_bs", "commodity", "unit", "min_price", "max_price", "avg_price", "commodity_np"]
    err_fields  = ["date_ad", "date_bs", "reason"]

    out_f  = open(OUTPUT_CSV, output_mode, newline="", encoding="utf-8")
    err_f  = open(ERRORS_CSV, output_mode, newline="", encoding="utf-8")
    writer = csv.DictWriter(out_f, fieldnames=fieldnames)
    errs   = csv.DictWriter(err_f, fieldnames=err_fields)

    # Write header only if new file
    if output_mode == "w":
        writer.writeheader()
        errs.writeheader()

    session = build_session()

    # ── Date loop ─────────────────────────────────────────────────────────────
    total_days = (END_DATE_AD - START_DATE_AD).days + 1
    current_ad = START_DATE_AD
    scraped = 0
    errors  = 0

    try:
        while current_ad <= END_DATE_AD:
            ad_str = str(current_ad)

            # Skip already-done dates (resume support)
            if ad_str in done_dates:
                current_ad += timedelta(days=1)
                continue

            bs = ad_to_bs(current_ad)
            bs_str = bs_date_str(bs)

            elapsed_days = (current_ad - START_DATE_AD).days + 1
            log.info("[%d/%d]  AD %s  →  BS %s", elapsed_days, total_days, ad_str, bs_str)

            response = fetch_price_page(session, bs)

            if response is None:
                log.warning("  ⚠ Failed to fetch – logging to errors CSV")
                errs.writerow({"date_ad": ad_str, "date_bs": bs_str, "reason": "fetch_failed"})
                errors += 1
            else:
                records = parse_prices(response, current_ad, bs)
                if not records:
                    log.warning("  ⚠ No price data in response")
                    errs.writerow({"date_ad": ad_str, "date_bs": bs_str, "reason": "no_data"})
                    errors += 1
                else:
                    for rec in records:
                        writer.writerow(rec)
                    out_f.flush()
                    log.info("  ✓ %d items saved", len(records))
                    scraped += 1

            # Be a polite crawler
            time.sleep(DELAY_SECONDS)
            current_ad += timedelta(days=1)

    except KeyboardInterrupt:
        log.info("\nInterrupted by user – progress saved. Re-run to resume.")

    finally:
        out_f.close()
        err_f.close()

    # ── Summary ───────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("Done!  Dates scraped: %d  |  Errors/missing: %d", scraped, errors)
    log.info("Output : %s", os.path.abspath(OUTPUT_CSV))
    log.info("Errors : %s", os.path.abspath(ERRORS_CSV))


if __name__ == "__main__":
    main()