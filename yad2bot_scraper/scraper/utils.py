import json
import os
import re
import time
import datetime
import random
import requests # Ensure requests is imported for fetch_yad2_data
from zenrows import ZenRowsClient

# API Key from environment variable
ZENROWS_API_KEY = os.environ.get('ZENROWS_API_KEY')
if not ZENROWS_API_KEY:
    raise ValueError("ZENROWS_API_KEY environment variable is required")

# Define a path for saving debug responses
DEBUG_RESPONSE_DIR = "/home/ubuntu/yad2_scraper_final/yad2_scraper/data/raw/json/"
os.makedirs(DEBUG_RESPONSE_DIR, exist_ok=True)
DEBUG_RESPONSE_FILE = os.path.join(DEBUG_RESPONSE_DIR, "zenrows_debug_response.json")

def get_phone_number_with_zenrows(url: str) -> str | None:
    """
    Fetches a webpage using ZenRows, attempts to click a 'show phone number' button,
    and extracts phone numbers using the 'outputs' feature.
    Saves the full ZenRows response to a debug file if extraction fails or is empty.
    """
    client = ZenRowsClient(ZENROWS_API_KEY)
    show_phone_button_selector = '[data-testid="show-phone-button"]'
    js_instructions_payload = [
        {"click": show_phone_button_selector},
        {"wait": 3500}
    ]
    params = {
        "js_render": "true",
        "js_instructions": json.dumps(js_instructions_payload),
        "premium_proxy": "true",
        "proxy_country": "il",
        "outputs": "phone_numbers"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://www.yad2.co.il"
    }
    try:
        print(f"Attempting to get phone number from URL: {url} using ZenRows.")
        response = client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        with open(DEBUG_RESPONSE_FILE, 'w', encoding='utf-8') as f_debug:
            json.dump(data, f_debug, indent=2, ensure_ascii=False)
        print(f"Saved full ZenRows response for {url} to {DEBUG_RESPONSE_FILE}")
        if "phone_numbers" in data and data["phone_numbers"]:
            extracted_phone = data["phone_numbers"][0]
            print(f"Successfully extracted phone number for {url}: {extracted_phone}")
            return str(extracted_phone)
        else:
            print(f"Phone number not found in ZenRows 'outputs' for {url}. Check {DEBUG_RESPONSE_FILE} for details.")
            return None
    except Exception as e:
        print(f"Error during ZenRows request or processing for {url}: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            error_response_content = response.text
            try:
                error_data = json.loads(error_response_content)
                with open(DEBUG_RESPONSE_FILE, 'w', encoding='utf-8') as f_debug:
                    json.dump(error_data, f_debug, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                with open(DEBUG_RESPONSE_FILE.replace('.json', '.txt'), 'w', encoding='utf-8') as f_debug_text:
                    f_debug_text.write(error_response_content)
            print(f"Saved error response for {url} to {DEBUG_RESPONSE_FILE} (or .txt variant).")
        return None

# --- Adding missing utility functions ---

def normalize_text(text: str | None) -> str:
    if text is None:
        return ""
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_phone_number(phone: str | None) -> str:
    if phone is None:
        return ""
    return re.sub(r'[^0-9]', '', phone)

def is_date_today(date_str: str | None) -> bool:
    if not date_str:
        return False
    # This is a placeholder. Actual implementation would depend on date_str format.
    # Assuming date_str is in 'YYYY-MM-DD' format for simplicity or a known format from Yad2.
    # For Yad2, it might be 'היום' (today) or a specific date.
    if date_str == "היום":
        return True
    try:
        # Example: if date_str is like "2023-10-27"
        listing_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        return listing_date == datetime.date.today()
    except ValueError:
        # Add more sophisticated date parsing if needed based on actual data
        return False # Or True if we want to be lenient for now

def random_delay(min_seconds: int = 1, max_seconds: int = 3) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))

def get_current_date() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d")

# Placeholder functions for data fetching and processing - these would ideally come from the original task's utils.py
# For now, these will be very basic or return dummy data to allow main.py to run.

RAW_HTML_DIR_UTILS = "/home/ubuntu/yad2_scraper_final/yad2_scraper/data/raw/html/"
os.makedirs(RAW_HTML_DIR_UTILS, exist_ok=True)
RAW_JSON_DIR_UTILS = "/home/ubuntu/yad2_scraper_final/yad2_scraper/data/raw/json/"
os.makedirs(RAW_JSON_DIR_UTILS, exist_ok=True)

def fetch_yad2_data(url: str) -> dict:
    print(f"[Placeholder] Fetching Yad2 data from {url}")
    # This should use ZenRows as per previous logic in main.py
    # For now, returning a structure that main.py might expect to avoid immediate crashes.
    # The actual ZenRows call for the main feed should be here.
    client = ZenRowsClient(ZENROWS_API_KEY)
    params = {
        "js_render": "true",
        "premium_proxy": "true",
        "proxy_country": "il"
    }
    try:
        response = client.get(url, params=params)
        response.raise_for_status()
        # Assuming the main feed returns HTML that contains a JSON script tag
        # Or if it can return JSON directly, that would be better.
        # For now, let's assume it returns HTML and we need to extract JSON from it.
        return {"html": response.text} # Simplified, main.py expects this structure
    except Exception as e:
        print(f"Error in placeholder fetch_yad2_data: {e}")
        return {"html": "<html><body>Error fetching data</body></html>"}

def save_raw_html(html_content: str, filename: str) -> None:
    filepath = os.path.join(RAW_HTML_DIR_UTILS, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"[Placeholder] Saved raw HTML to {filepath}")

def save_raw_json(data: dict, filename: str) -> None:
    filepath = os.path.join(RAW_JSON_DIR_UTILS, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[Placeholder] Saved raw JSON to {filepath}")

def extract_nextjs_data(html_content: str) -> dict | None:
    print("[Placeholder] Extracting Next.js data")
    # This function needs to parse HTML to find the __NEXT_DATA__ script tag
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tag = soup.find('script', {'id': '__NEXT_DATA__'})
    if script_tag:
        try:
            return json.loads(script_tag.string)
        except json.JSONDecodeError:
            print("Error decoding __NEXT_DATA__ JSON")
            return None
    return None

def extract_listings_from_nextjs_data(nextjs_data: dict | None) -> list:
    print("[Placeholder] Extracting listings from Next.js data")
    if not nextjs_data:
        return []
    # This is highly dependent on the actual structure of Yad2's __NEXT_DATA__
    # Looking for a path that might contain listings, e.g., props.pageProps.feed.feedItems
    try:
        # This path is a guess and needs to be verified with actual Yad2 data
        items = nextjs_data.get('props', {}).get('pageProps', {}).get('feed', {}).get('feedItems', [])
        # The items might be nested further, e.g., item.feedData
        listings = []
        for item_container in items:
            if isinstance(item_container, dict) and 'feedData' in item_container:
                 listings.append(item_container['feedData'])
            elif isinstance(item_container, dict): # If structure is flatter
                 listings.append(item_container)
        return listings

    except AttributeError:
        print("Error accessing listings in Next.js data structure.")
        return []
    return [] # Default empty list

def is_private_owner(listing_data: dict) -> bool:
    print(f"[Placeholder] Checking if private owner for listing: {listing_data.get('id', 'N/A')}")
    # Example logic: check for 'business' or 'agency' type fields
    # This depends on Yad2's data structure for listings
    # Based on main.py: adType, merchantType
    ad_type = listing_data.get('adType')
    merchant_type = listing_data.get('merchantType')
    # Assuming 'private' or similar values indicate a private owner
    # and other values (like 'business', 'agency', 'נדל"ן מסחרי') indicate non-private.
    # This needs to be confirmed with actual data.
    if ad_type == "private" or (not ad_type and not merchant_type): # Simple heuristic
        return True
    if merchant_type and 'private' in merchant_type.lower():
        return True
    return False

def extract_listing_data(listing_item: dict, direct_phone_number: str | None = None) -> dict | None:
    print(f"[Placeholder] Extracting data for listing: {listing_item.get('id', 'N/A')}")
    # This function should map fields from the raw listing_item to a structured dict
    # This is highly dependent on Yad2's data structure.
    data = {}
    data['id'] = listing_item.get('id') or listing_item.get('token')
    data['title'] = normalize_text(listing_item.get('title_1')) # Example field
    data['price'] = normalize_text(listing_item.get('price'))
    # Address might be composed of multiple fields
    city = listing_item.get('city', '')
    street = listing_item.get('street', '')
    house_number = listing_item.get('address_home_number', '')
    data['address'] = normalize_text(f"{city} {street} {house_number}".strip())
    data['description'] = normalize_text(listing_item.get('info')) # Example field
    data['apartment_size'] = normalize_text(listing_item.get('square_meters'))
    data['rooms_count'] = normalize_text(listing_item.get('Rooms_text'))
    data['publish_date'] = listing_item.get('date_added_text') or listing_item.get('date') # Example: 'היום', 'אתמול', or a date
    data['owner_name'] = normalize_text(listing_item.get('contact_name'))
    data['phone_number'] = direct_phone_number or normalize_phone_number(listing_item.get('phone')) # Use direct if available
    data['listing_url'] = f"https://www.yad2.co.il/item/{data['id']}" if data['id'] else None
    data['timestamp'] = get_current_date()
    data['property_type'] = normalize_text(listing_item.get('type')) # Example

    # Basic validation: if no ID or title, might be an invalid listing item
    if not data['id'] and not data['title']:
        return None
    return data


