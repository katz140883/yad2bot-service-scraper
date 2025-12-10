"""
Enhanced Yad2 Scraper - Supports both Rentals and Sales
Compatible with Manus2yad2bot
"""
import argparse
import csv
import datetime
import json
import logging
import os
import re
import subprocess
import sys
import time
from typing import Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

# Import database check function
sys.path.insert(0, '/home/ubuntu/yad2bot-service-scraper')
try:
    from database import check_lead_exists_in_mysql
    DB_CHECK_AVAILABLE = True
    print("[INIT] Database check function imported successfully")
except ImportError as e:
    print(f"[INIT] Could not import database check function: {e}")
    DB_CHECK_AVAILABLE = False
    def check_lead_exists_in_mysql(url):
        return False

# Configuration
BASE_URLS = {
    'rent': 'https://www.yad2.co.il/realestate/rent?',
    'sale': 'https://www.yad2.co.il/realestate/forsale?'
}

ZENROWS_API_KEY = os.environ.get('ZENROWS_API_KEY')
if not ZENROWS_API_KEY:
    raise ValueError("ZENROWS_API_KEY environment variable is required")
ZENROWS_API_URL = 'https://api.zenrows.com/v1/'

# Directory configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = '/home/ubuntu/yad2bot_scraper/data'
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, f'scraper_{datetime.datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Yad2Scraper:
    """Enhanced Yad2 scraper supporting both rentals and sales."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def fetch_with_zenrows(self, url: str) -> Optional[str]:
        """Fetch URL using ZenRows API with simplified parameters."""
        try:
            # Simplified parameters to avoid timeouts
            params = {
                'url': url,
                'apikey': ZENROWS_API_KEY,
                'js_render': 'true',
                'premium_proxy': 'true',
                'proxy_country': 'IL'
            }
            
            response = requests.get(ZENROWS_API_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                logger.info(f"Successfully fetched {url} (content length: {len(response.text)})")
                return response.text
            else:
                logger.error(f"ZenRows API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_nextjs_data(self, html: str) -> Optional[Dict]:
        """Extract Next.js data from HTML."""
        try:
            # Look for __NEXT_DATA__ script
            pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
            match = re.search(pattern, html, re.DOTALL)
            
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
            else:
                logger.warning("No __NEXT_DATA__ found in HTML")
                return None
                
        except Exception as e:
            logger.error(f"Error extracting Next.js data: {e}")
            return None
    
    def extract_listings_from_nextjs(self, nextjs_data: Dict) -> List[Dict]:
        """Extract listings from Next.js data with enhanced strategy."""
        try:
            listings = []
            
            # Navigate through the data structure to find listings
            if 'props' in nextjs_data and 'pageProps' in nextjs_data['props']:
                page_props = nextjs_data['props']['pageProps']
                
                # Enhanced feed locations based on previous fixes
                feed_locations = [
                    # Original paths (with corrected feedItems)
                    page_props.get('feed', {}).get('feedItems', []),
                    page_props.get('initialData', {}).get('feed', {}).get('feedItems', []),
                    page_props.get('serverPage', {}).get('feed', {}).get('feedItems', []),
                    
                    # Legacy paths (keep for compatibility)
                    page_props.get('feed', {}).get('feed_items', []),
                    page_props.get('initialData', {}).get('feed', {}).get('feed_items', []),
                    page_props.get('serverPage', {}).get('feed', {}).get('feed_items', []),
                    
                    # Additional paths found in previous fixes
                    page_props.get('feedData', {}).get('items', []),
                    page_props.get('searchResults', {}).get('items', []),
                    page_props.get('listings', []),
                    page_props.get('items', [])
                ]
                
                for location in feed_locations:
                    if location and isinstance(location, list):
                        # Check if items have feedData structure
                        for item in location:
                            if isinstance(item, dict) and 'feedData' in item:
                                listings.append(item['feedData'])
                            elif isinstance(item, dict):
                                listings.append(item)
                        
                        if listings:
                            logger.info(f"Found {len(listings)} listings in feed location")
                            break
                
                # If still no listings, do a deep search
                if not listings:
                    listings = self._deep_search_for_listings(page_props)
                    if listings:
                        logger.info(f"Found {len(listings)} listings via deep search")
            
            logger.info(f"Extracted {len(listings)} listings from Next.js data")
            return listings
            
        except Exception as e:
            logger.error(f"Error extracting listings from Next.js data: {e}")
            return []
    
    def _deep_search_for_listings(self, data) -> List[Dict]:
        """Recursively search for listings in data structure with enhanced patterns."""
        listings = []
        
        def search_recursive(obj, path=""):
            nonlocal listings
            
            if isinstance(obj, dict):
                # Check for known listing array patterns
                listing_keys = [
                    'feed_items', 'feedItems', 'items', 'listings', 'results', 
                    'data', 'content', 'ads', 'properties', 'realestate'
                ]
                
                for key in listing_keys:
                    if key in obj and isinstance(obj[key], list) and obj[key]:
                        # Validate that this looks like a listings array
                        sample_item = obj[key][0] if obj[key] else {}
                        if isinstance(sample_item, dict) and self._looks_like_listing(sample_item):
                            logger.info(f"Found listings array at path: {path}.{key}")
                            return obj[key]
                
                # Continue recursive search
                for key, value in obj.items():
                    result = search_recursive(value, f"{path}.{key}" if path else key)
                    if result:
                        return result
            
            elif isinstance(obj, list) and obj:
                # Check if this list contains listings
                sample_item = obj[0] if obj else {}
                if isinstance(sample_item, dict) and self._looks_like_listing(sample_item):
                    logger.info(f"Found listings list at path: {path}")
                    return obj
                
                # Search within list items
                for i, item in enumerate(obj):
                    result = search_recursive(item, f"{path}[{i}]" if path else f"[{i}]")
                    if result:
                        return result
            
            return None
        
        result = search_recursive(data)
        return result if result else []
    
    def _looks_like_listing(self, item: Dict) -> bool:
        """Check if an item looks like a real estate listing."""
        if not isinstance(item, dict):
            return False
        
        # Check for common listing fields
        listing_indicators = [
            'id', 'title', 'price', 'rooms', 'address', 'city', 
            'contact', 'phone', 'merchant', 'date', 'url', 'link',
            'propertyType', 'adType', 'coordinates', 'images'
        ]
        
        # Must have at least 3 listing indicators
        found_indicators = sum(1 for key in listing_indicators if key in item)
        return found_indicators >= 3
    
    def is_private_owner(self, listing: Dict) -> bool:
        """Check if listing is from a private owner."""
        try:
            # Check adType field (new structure)
            ad_type = listing.get('adType', '')
            if ad_type == 'private':
                return True
            elif ad_type == 'business':
                return False
            
            # Check merchant type (legacy)
            if listing.get('merchantType') == 'private':
                return True
            
            # Check for agency indicators in various fields
            agency_indicators = ['תיווך', 'מתווך', 'משרד', 'רימקס', 'אנגלו סכסון', 'קבלן', 'חברה', 'נדל"ן']
            
            fields_to_check = [
                listing.get('title', ''),
                listing.get('subtitle', ''),
                listing.get('merchant_name', ''),
                listing.get('contact_name', ''),
                listing.get('description', ''),
                # Check nested fields
                listing.get('contact', {}).get('name', ''),
                listing.get('merchant', {}).get('name', ''),
            ]
            
            for field in fields_to_check:
                if field:
                    field_lower = str(field).lower()
                    if any(indicator.lower() in field_lower for indicator in agency_indicators):
                        return False
            
            # If adType is 'private', it's definitely private
            if ad_type == 'private':
                return True
            
            # Default to True if no clear agency indicators found
            return True
            
        except Exception as e:
            logger.error(f"Error checking if private owner: {e}")
            return False
    
    def extract_listing_details(self, listing: Dict) -> Optional[Dict]:
        """Extract detailed information from a listing."""
        try:
            # Extract basic information using the actual data structure
            listing_data = {
                'id': listing.get('token', ''),
                'title': '',
                'price': listing.get('price', ''),
                'rooms': '',
                'size': '',
                'address': '',
                'phone_number': '',
                'owner_name': '',
                'publish_date': '',
                'listing_url': f"https://www.yad2.co.il/item/{listing.get('token', '')}"
            }
            
            # Extract address from the nested structure
            address_parts = []
            address_info = listing.get('address', {})
            
            if address_info.get('city', {}).get('text'):
                address_parts.append(address_info['city']['text'])
            if address_info.get('neighborhood', {}).get('text'):
                address_parts.append(address_info['neighborhood']['text'])
            if address_info.get('street', {}).get('text'):
                address_parts.append(address_info['street']['text'])
            if address_info.get('house', {}).get('number'):
                address_parts.append(str(address_info['house']['number']))
            
            listing_data['address'] = ', '.join(address_parts)
            
            # Extract property details
            additional_details = listing.get('additionalDetails', {})
            property_info = additional_details.get('property', {})
            
            # rooms is in additionalDetails.roomsCount
            if additional_details.get('roomsCount'):
                listing_data['rooms'] = str(additional_details['roomsCount'])
            # size is in additionalDetails.squareMeter
            if additional_details.get('squareMeter'):
                listing_data['size'] = str(additional_details['squareMeter'])
            
            # Extract title from metadata or create one
            meta_data = listing.get('metaData', {})
            if meta_data.get('title'):
                listing_data['title'] = meta_data['title']
            else:
                # Create title from available info
                title_parts = []
                if listing_data['rooms']:
                    title_parts.append(f"{listing_data['rooms']} חדרים")
                if address_info.get('neighborhood', {}).get('text'):
                    title_parts.append(address_info['neighborhood']['text'])
                listing_data['title'] = ', '.join(title_parts) if title_parts else 'דירה להשכרה'
            
            # Extract real phone number from individual listing page
            listing_data["phone_number"] = "0501234567"  # Stage 1 placeholder
            
            return listing_data
            
        except Exception as e:
            logger.error(f"Error extracting listing details: {e}")
            return None
    
    def get_phone_number_from_listing(self, listing_url: str) -> str:
        """Get phone number from individual listing page using ZenRows."""
        try:
            logger.info(f"Attempting to get phone number for listing: {listing_url}")
            
            # First attempt: Try with JavaScript instructions to click "Show Phone" button
            js_instructions = [
                {"wait": 3000},
                {"click": ".viewPhone"},
                {"wait": 2000},
                {"click": "[data-testid='contact-info-phone']"},
                {"wait": 2000}
            ]
            
            params = {
                'url': listing_url,
                'apikey': ZENROWS_API_KEY,
                'js_render': 'true',
                'js_instructions': json.dumps(js_instructions),
                'premium_proxy': 'true',
                'proxy_country': 'IL',
                'outputs': 'phone_numbers',
                'wait': '5000'
            }
            
            response = requests.get(ZENROWS_API_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                html_content = response.text
                
                # Try to extract phone number using regex
                phone_patterns = [
                    r'05\d-?\d{7}',
                    r'0\d{1,2}-?\d{7}',
                    r'\+972-?5\d-?\d{7}',
                    r'tel:(\+?972-?5\d-?\d{7})',
                    r'href="tel:([^"]+)"'
                ]
                
                for pattern in phone_patterns:
                    matches = re.findall(pattern, html_content)
                    if matches:
                        phone = matches[0]
                        # Clean the phone number
                        phone = re.sub(r'[^\d]', '', phone)
                        if phone.startswith('972'):
                            phone = '0' + phone[3:]
                        if len(phone) == 10 and phone.startswith('05'):
                            logger.info(f"Found phone number: {phone}")
                            return phone
                
                # Try to find phone in specific HTML elements
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Look for phone in various elements
                phone_selectors = [
                    '.contact-info-phone',
                    '[data-testid="contact-info-phone"]',
                    '.phone-number',
                    '.viewPhone',
                    '[href^="tel:"]'
                ]
                
                for selector in phone_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text() or element.get('href', '')
                        phone_matches = re.findall(r'05\d{8}', text)
                        if phone_matches:
                            logger.info(f"Found phone number in element: {phone_matches[0]}")
                            return phone_matches[0]
            
            logger.warning(f"Could not extract phone number from {listing_url}")
            return ""
            
        except Exception as e:
            logger.error(f"Error getting phone number from {listing_url}: {e}")
            return ""
    
    def get_listing_details_from_page(self, listing_url: str) -> Dict[str, str]:
        """Extract additional details (rooms, floor, owner_name, publish_date) from individual listing page."""
        details = {
            'rooms': '',
            'floor': '',
            'owner_name': '',
            'publish_date': ''
        }
        
        try:
            logger.info(f"Extracting additional details from: {listing_url}")
            
            # Fetch the listing page
            html_content = self.fetch_with_zenrows(listing_url)
            if not html_content:
                logger.warning(f"Failed to fetch listing page: {listing_url}")
                return details
            
            # Extract __NEXT_DATA__ JSON from the page
            next_data = self.extract_nextjs_data(html_content)
            if not next_data:
                logger.warning(f"No __NEXT_DATA__ found in listing page: {listing_url}")
                return details
            
            # Navigate to the listing data in __NEXT_DATA__
            try:
                props = next_data.get('props', {})
                page_props = props.get('pageProps', {})
                item = page_props.get('item', {})
                
                # Extract rooms
                additional_details = item.get('additionalDetails', {})
                property_info = additional_details.get('property', {})
                if property_info.get('rooms'):
                    details['rooms'] = str(property_info['rooms'])
                    logger.info(f"Found rooms: {details['rooms']}")
                
                # Extract floor
                if property_info.get('floor'):
                    details['floor'] = str(property_info['floor'])
                    logger.info(f"Found floor: {details['floor']}")
                
                # Extract owner name from contact info
                contact_info = item.get('contactInfo', {})
                if contact_info.get('name'):
                    details['owner_name'] = contact_info['name']
                    logger.info(f"✅ Found owner name from contactInfo: {details['owner_name']}")
                else:
                    # Try to extract from searchText
                    search_text = item.get('searchText', '')
                    if 'שם מוכר' in search_text:
                        import re as re_module
                        match = re_module.search(r'שם מוכר\s+(\S+)', search_text)
                        if match:
                            details['owner_name'] = match.group(1)
                            logger.info(f"✅ Found owner name from searchText: {details['owner_name']}")
                    if not details['owner_name']:
                        logger.warning("owner_name not found")
                
                # Extract publish date
                dates = item.get('dates', {})
                if dates.get('publishDate'):
                    # publishDate might be in ISO format, extract just the date part
                    publish_date_str = dates['publishDate']
                    # Try to parse and format as DD/MM/YY
                    try:
                        from datetime import datetime
                        if 'T' in publish_date_str:  # ISO format
                            dt = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                            details['publish_date'] = dt.strftime('%d/%m/%y')
                        else:
                            details['publish_date'] = publish_date_str
                        logger.info(f"Found publish date: {details['publish_date']}")
                    except Exception as e:
                        logger.warning(f"Error parsing publish date {publish_date_str}: {e}")
                        details['publish_date'] = publish_date_str
                
            except Exception as e:
                logger.error(f"Error navigating __NEXT_DATA__ structure: {e}")
            
            return details
            
        except Exception as e:
            logger.error(f"Error extracting listing details from {listing_url}: {e}")
            return details
    
    def extract_listing_details(self, listing: Dict) -> Optional[Dict]:
        """Extract detailed information from a listing."""
        try:
            # Extract basic information using the actual data structure
            listing_data = {
                'id': listing.get('token', ''),
                'title': '',
                'price': listing.get('price', ''),
                'rooms': '',
                'size': '',
                'address': '',
                'phone_number': '',
                'owner_name': '',
                'publish_date': '',
                'listing_url': f"https://www.yad2.co.il/item/{listing.get('token', '')}"
            }
            
            # Extract address from the nested structure
            address_parts = []
            address_info = listing.get('address', {})
            
            if address_info.get('city', {}).get('text'):
                address_parts.append(address_info['city']['text'])
            if address_info.get('neighborhood', {}).get('text'):
                address_parts.append(address_info['neighborhood']['text'])
            if address_info.get('street', {}).get('text'):
                address_parts.append(address_info['street']['text'])
            if address_info.get('house', {}).get('number'):
                address_parts.append(str(address_info['house']['number']))
            
            listing_data['address'] = ', '.join(address_parts)
            
            # Extract property details
            additional_details = listing.get('additionalDetails', {})
            property_info = additional_details.get('property', {})
            
            # rooms is in additionalDetails.roomsCount
            if additional_details.get('roomsCount'):
                listing_data['rooms'] = str(additional_details['roomsCount'])
            # size is in additionalDetails.squareMeter
            if additional_details.get('squareMeter'):
                listing_data['size'] = str(additional_details['squareMeter'])
            
            # Extract title from metadata or create one
            meta_data = listing.get('metaData', {})
            if meta_data.get('title'):
                listing_data['title'] = meta_data['title']
            else:
                # Create title from available info
                title_parts = []
                if listing_data['rooms']:
                    title_parts.append(f"{listing_data['rooms']} חדרים")
                if address_info.get('neighborhood', {}).get('text'):
                    title_parts.append(address_info['neighborhood']['text'])
                listing_data['title'] = ', '.join(title_parts) if title_parts else 'דירה להשכרה'
            
            # Extract real phone number from individual listing page
            listing_data["phone_number"] = "0501234567"  # Stage 1 placeholder
            
            return listing_data
            
        except Exception as e:
            logger.error(f"Error extracting listing details: {e}")
            return None
    
    def normalize_phone_number(self, phone: str) -> Optional[str]:
        """Normalize Israeli phone number."""
        try:
            # Remove all non-digit characters
            phone = re.sub(r'\D', '', phone)
            
            # Handle different formats
            if phone.startswith('972'):
                phone = '0' + phone[3:]
            elif phone.startswith('+972'):
                phone = '0' + phone[4:]
            elif len(phone) == 9 and phone.startswith('5'):
                phone = '0' + phone
            
            # Validate Israeli mobile number format
            if re.match(r'^05\d{8}$', phone):
                return phone
            
            return None
            
        except Exception as e:
            logger.error(f"Error normalizing phone number {phone}: {e}")
            return None
    
    def is_today_listing(self, listing: Dict) -> bool:
        """Check if listing was posted in the LAST 24 HOURS by actually checking the listing page."""
        try:
            from datetime import datetime, date, timedelta
            import re
            
            today = date.today()
            yesterday = today - timedelta(days=1)
            
            # Get the listing URL
            token = listing.get('token')
            if not token:
                logger.debug(f"❌ No token found for listing")
                return False
            
            listing_url = f"https://www.yad2.co.il/item/{token}"
            logger.debug(f"🔍 Checking publication date for listing: {listing_url}")
            
            # Fetch the listing page to get the actual publication date
            try:
                html_content = self.fetch_with_zenrows(listing_url)
                if not html_content:
                    logger.debug(f"❌ Failed to fetch listing page: {token}")
                    return False
                
                # Parse the HTML to find the publication date
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Look for date patterns in the HTML
                # Common patterns: "29/08/25", "פורסם ב-24/09/25", etc.
                date_patterns = [
                    r'(\d{1,2}/\d{1,2}/\d{2,4})',  # DD/MM/YY or DD/MM/YYYY
                    r'(\d{4}-\d{1,2}-\d{1,2})',    # YYYY-MM-DD
                    r'פורסם ב-(\d{1,2}/\d{1,2}/\d{2,4})',  # Hebrew "published on"
                ]
                
                found_dates = []
                page_text = soup.get_text()
                
                for pattern in date_patterns:
                    matches = re.findall(pattern, page_text)
                    found_dates.extend(matches)
                
                # Try to parse found dates
                for date_str in found_dates:
                    try:
                        # Try different date formats
                        for fmt in ['%d/%m/%y', '%d/%m/%Y', '%Y-%m-%d']:
                            try:
                                parsed_date = datetime.strptime(date_str, fmt).date()
                                
                                # Check if it's today or yesterday
                                if parsed_date == today:
                                    logger.info(f"✅ TODAY listing found: {token} - {date_str}")
                                    return True
                                elif parsed_date == yesterday:
                                    logger.info(f"✅ YESTERDAY listing found: {token} - {date_str}")
                                    return True
                                else:
                                    logger.debug(f"❌ Old listing: {token} - {date_str} (not in last 24h)")
                                    return False
                                    
                            except ValueError:
                                continue
                                
                    except Exception as e:
                        logger.debug(f"Error parsing date {date_str}: {e}")
                        continue
                
                # If no date found in text, try to find it in specific elements
                # Look for elements that might contain the date
                date_elements = soup.find_all(['span', 'div', 'p'], string=re.compile(r'\d{1,2}/\d{1,2}/\d{2,4}'))
                for element in date_elements:
                    date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', element.get_text())
                    if date_match:
                        date_str = date_match.group(1)
                        try:
                            for fmt in ['%d/%m/%y', '%d/%m/%Y']:
                                try:
                                    parsed_date = datetime.strptime(date_str, fmt).date()
                                    if parsed_date == today or parsed_date == yesterday:
                                        logger.info(f"✅ RECENT listing found in element: {token} - {date_str}")
                                        return True
                                    else:
                                        logger.debug(f"❌ Old listing in element: {token} - {date_str}")
                                        return False
                                except ValueError:
                                    continue
                        except Exception as e:
                            continue
                
                # If still no date found, assume it's old
                logger.debug(f"❌ No publication date found for listing: {token} - assuming old")
                return False
                
            except Exception as e:
                logger.error(f"Error fetching/parsing listing page {token}: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error checking if recent listing: {e}")
            return False
    
    def scrape_listings(self, mode: str, filter_type: str = 'all', city_code: str = None, max_pages: int = None) -> List[Dict]:
        """Scrape listings for the specified mode and filter with multiple pages support."""
        try:
            base_url = BASE_URLS.get(mode)
            if not base_url:
                logger.error(f"Invalid mode: {mode}")
                return []
            
            # If city_code is provided, enforce it in the URL
            if city_code:
                if 'city=' in base_url:
                    base_url = re.sub(r'city=\d+', f'city={city_code}', base_url)
                else:
                    sep = '' if base_url.endswith('?') else '&'
                    base_url = f'{base_url}{sep}city={city_code}'
                logger.info(f"Using city code: {city_code}")
            
            # Add date sorting to get newest listings first (especially important for 'today' filter)
            if filter_type == 'today':
                sep = '&' if '?' in base_url else '?'
                base_url = f'{base_url}{sep}orderBy=date'
                logger.info("Added date sorting for last 24 hours filter")
            
            logger.info(f"Scraping {mode} listings with filter {filter_type}")
            
            # Define variables for progress tracking
            from datetime import date
            today_str = date.today().strftime('%Y-%m-%d')
            # Map city codes to names (same as save_to_csv)
            city_code_to_name = {
                '5000': 'TelAviv',      # תל אביב-יפו
                '3000': 'Jerusalem',    # ירושלים
                '4000': 'Haifa',        # חיפה
                '7000': 'BeerSheva',    # באר שבע
                '8300': 'RishonLeZion', # ראשון לציון
                '7900': 'PetahTikva',   # פתח תקווה
                '7400': 'Netanya',      # נתניה
                '0070': 'Ashdod',       # אשדוד
            }
            
            # Get city name from code
            if city_code and city_code.isdigit():
                city_name = city_code_to_name.get(city_code, f'City{city_code}')
            else:
                city_name = city_code if city_code else "all_cities"
            
            all_listings = []
            duplicates_skipped = 0  # Counter for duplicate listings skipped
            page = 1
            # Set max pages based on filter type or explicit limit
            # Write debug info to file
            with open('/tmp/scraper_debug.log', 'a') as f:
                f.write(f"filter_type={filter_type}, max_pages={max_pages}\n")
            logger.info(f"[DEBUG] Received max_pages parameter: {max_pages}")
            # Force test mode to always use 1 page
            if filter_type == 'test':
                max_pages = 1  # Test scraping: always only 1 page
            elif max_pages is None:
                max_pages = 10  # Default: check more pages
            # else: use the provided max_pages value
            logger.info(f"[DEBUG] Final max_pages value: {max_pages}")
            # Write final value to file
            with open('/tmp/scraper_debug.log', 'a') as f:
                f.write(f"AFTER IF: filter_type={filter_type}, max_pages={max_pages}\n")
            
            # Create initial progress file immediately so monitor can read correct max_pages
            initial_progress_file = os.path.join(DATA_DIR, f"{city_name}_{mode}_{filter_type}_{today_str}_checking_progress.json")
            try:
                initial_progress_data = {
                    "stage": "starting",
                    "current_listing": 0,
                    "total_listings_to_check": 0,
                    "current_page": 1,
                    "total_pages": max_pages,
                    "city_name": city_name,
                    "filter_type": filter_type,
                    "message": "🔄 מתחיל סריקה..."
                }
                with open(initial_progress_file, 'w', encoding='utf-8') as f:
                    json.dump(initial_progress_data, f, ensure_ascii=False, indent=2)
                logger.info(f"Created initial progress file with max_pages={max_pages}")
            except Exception as e:
                logger.warning(f"Error creating initial progress file: {e}")
            
            while page <= max_pages:
                # Check for cancellation flag
                cancel_file = os.path.join(DATA_DIR, f"{city_name}_{mode}_{filter_type}_{today_str}_cancel.flag")
                if os.path.exists(cancel_file):
                    logger.info("Cancellation flag detected, stopping scraper")
                    break
                
                # Add page parameter to URL
                url = f"{base_url}&page={page}" if page > 1 else base_url
                logger.info(f"Fetching page {page}: {url}")
                
                # Fetch page content
                html_content = self.fetch_with_zenrows(url)
                if not html_content:
                    logger.error(f"Failed to fetch page {page}")
                    break
                
                # Extract Next.js data
                nextjs_data = self.extract_nextjs_data(html_content)
                if not nextjs_data:
                    logger.warning(f"No Next.js data found on page {page}")
                    if page >= max_pages:
                        logger.info(f"Reached max_pages ({max_pages}), stopping")
                        break
                    page += 1
                    logger.info(f"Trying next page ({page}/{max_pages})")
                    continue
                
                # Extract raw listings from this page
                raw_listings = self.extract_listings_from_nextjs(nextjs_data)
                if not raw_listings:
                    logger.info(f"No listings found on page {page}")
                    if page >= max_pages:
                        logger.info(f"Reached max_pages ({max_pages}), stopping")
                        break
                    page += 1
                    logger.info(f"Trying next page ({page}/{max_pages})")
                    continue
                
                logger.info(f"Found {len(raw_listings)} raw listings on page {page}")
                
                # Update progress at start of page
                progress_data_page = {
                    'stage': 'checking_dates',
                    'current_listing': len(all_listings),
                    'total_listings_to_check': len(raw_listings) * max_pages,
                    'current_title': f'סורק דף {page}/{max_pages}',
                    'found_recent': len(all_listings),
                    'duplicates_skipped': duplicates_skipped,
                    'current_page': page,
                    'total_pages': max_pages,
                    'city_name': city_name,
                    'filter_type': filter_type,
                    'message': f"📄 סורק דף {page}/{max_pages}..."
                }
                progress_file = os.path.join(DATA_DIR, f"{city_name}_{mode}_{filter_type}_{today_str}_checking_progress.json")
                try:
                    with open(progress_file, 'w', encoding='utf-8') as f:
                        json.dump(progress_data_page, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logger.debug(f"Error saving progress: {e}")
                
                # Process listings with filtering
                processed_listings = []
                
                for index, listing in enumerate(raw_listings):
                    # Check for cancellation flag before processing each listing
                    cancel_file = os.path.join(DATA_DIR, f"{city_name}_{mode}_{filter_type}_{today_str}_cancel.flag")
                    if os.path.exists(cancel_file):
                        logger.info("Cancellation flag detected during listing processing, stopping")
                        break
                    
                    # Update progress for each listing being checked
                    total_checked = len(all_listings) + index + 1
                    
                    # Extract title from the actual data structure
                    listing_title = 'ללא כותרת'
                    
                    # Try different title fields
                    if listing.get('title'):
                        listing_title = listing['title']
                    elif listing.get('headline'):
                        listing_title = listing['headline']
                    elif listing.get('description'):
                        listing_title = listing['description']
                    elif listing.get('address', {}).get('street', {}).get('text'):
                        # Use street address as fallback
                        street = listing['address']['street']['text']
                        city = listing.get('address', {}).get('city', {}).get('text', '')
                        listing_title = f"{street}, {city}" if city else street
                    elif listing.get('merchant', {}).get('name'):
                        listing_title = f"מודעה של {listing['merchant']['name']}"
                    
                    # Truncate title for display
                    listing_title = listing_title[:30]
                    
                    # Create progress file for real-time monitoring
                    progress_data = {
                        'stage': 'checking_dates',
                        'current_listing': total_checked,
                        'total_listings_to_check': len(raw_listings) * max_pages,
                        'current_title': listing_title,
                        'found_recent': len(all_listings) + len(processed_listings),
                        'duplicates_skipped': duplicates_skipped,
                        'current_page': page,
                        'total_pages': max_pages,
                        'city_name': city_name,
                        'filter_type': filter_type,
                        'message': f"🔍 בודק מודעה {total_checked}: {listing_title}..."
                    }
                    
                    # Save progress to file
                    progress_file = os.path.join(DATA_DIR, f"{city_name}_{mode}_{filter_type}_{today_str}_checking_progress.json")
                    try:
                        with open(progress_file, 'w', encoding='utf-8') as f:
                            json.dump(progress_data, f, ensure_ascii=False, indent=2)
                    except Exception as e:
                        logger.debug(f"Error saving progress: {e}")
                    
                    # Small delay to allow monitor to read progress file
                    time.sleep(0.5)
                    
                    logger.info(f"🔍 Checking listing {total_checked}: {listing.get('token')} - {listing_title}")
                    
                    # Check if listing already exists in CRM (Fix #3: Skip already scraped listings)
                    listing_token = listing.get('token', '')
                    logger.info(f"[DUPLICATE CHECK] token={listing_token}, DB_CHECK_AVAILABLE={DB_CHECK_AVAILABLE}")
                    if listing_token and DB_CHECK_AVAILABLE:
                        listing_url = f"https://www.yad2.co.il/item/{listing_token}"
                        logger.info(f"[DUPLICATE CHECK] Checking URL: {listing_url}")
                        try:
                            exists = check_lead_exists_in_mysql(listing_url)
                            logger.info(f"[DUPLICATE CHECK] Result: {exists}")
                            if exists:
                                duplicates_skipped += 1
                                logger.info(f"⏭️  Listing already in CRM, skipping ({duplicates_skipped} total): {listing_url}")
                                continue
                        except Exception as check_error:
                            logger.warning(f"Could not check CRM, continuing with processing: {check_error}")
                    
                    # Check if private owner - NOW ENABLED
                    if not self.is_private_owner(listing):
                        logger.debug(f"Skipping non-private listing: {listing.get('token')}")
                        continue
                    
                    # Apply date filter if needed - STRICT TODAY ONLY
                    # Bonus filter behaves like 'all' (no date filtering)
                    if filter_type == 'today' and not self.is_today_listing(listing):
                        logger.debug(f"Skipping listing not from last 24h: {listing.get('token')}")
                        continue
                    
                    # Extract details
                    listing_details = self.extract_listing_details(listing)
                    if listing_details:
                        processed_listings.append(listing_details)
                        logger.debug(f"Added listing: {listing_details.get('id')} with phone: {listing_details.get('phone_number', 'no-phone')}")
                
                logger.info(f"Processed {len(processed_listings)} listings from page {page}")
                all_listings.extend(processed_listings)
                
                # Check if we should continue to next page
                if len(raw_listings) < 20:  # If less than full page, probably last page
                    logger.info(f"Page {page} has less than 20 listings, assuming last page")
                    break
                
                page += 1
            
            logger.info(f"Total processed listings across {page-1} pages: {len(all_listings)}")
            return all_listings
            
        except Exception as e:
            logger.error(f"Error scraping listings: {str(e)}")
            return []
    
    def save_to_csv(self, listings: List[Dict], mode: str, filter_type: str, city: str = 'haifa') -> str:
        """Save listings to CSV file."""
        try:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            
            # Map city codes to names (verified Yad2 codes)
            city_code_to_name = {
                '5000': 'TelAviv',      # תל אביב-יפו
                '3000': 'Jerusalem',    # ירושלים
                '4000': 'Haifa',        # חיפה
                '7000': 'BeerSheva',    # באר שבע
                '8300': 'RishonLeZion', # ראשון לציון
                '7900': 'PetahTikva',   # פתח תקווה
                '7400': 'Netanya',      # נתניה
                '0070': 'Ashdod',       # אשדוד
            }
            
            # Get city name from code, or use the city parameter if it's already a name
            if city and city.isdigit():
                city_name = city_code_to_name.get(city, f'City{city}')
            else:
                city_name = city.capitalize() if city else 'Unknown'
            
            filename = f"{city_name}_{mode}_{filter_type}_{timestamp}.csv"
            filepath = os.path.join(DATA_DIR, filename)
            
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                if listings:
                    fieldnames = listings[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writeheader()
                    writer.writerows(listings)
                else:
                    # Create empty file with headers
                    writer = csv.writer(csvfile)
                    writer.writerow(['phone_number', 'owner_name', 'address', 'price', 'rooms', 'size', 'title', 'listing_url'])
            
            logger.info(f"Saved {len(listings)} listings to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            return ""

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Yad2 Scraper for Rentals and Sales')
    parser.add_argument('--mode', choices=['rent', 'sale'], required=True, help='Scraping mode')
    parser.add_argument('--filter', choices=['all', 'today', 'test'], default='all', help='Filter type')
    parser.add_argument('--city', type=str, help='City code for scraping')
    parser.add_argument('--max-pages', type=int, default=None, help='Maximum number of pages to scrape')
    
    args = parser.parse_args()
    
    try:
        scraper = Yad2Scraper()
        listings = scraper.scrape_listings(args.mode, args.filter, args.city, max_pages=args.max_pages)
        
        if listings:
            csv_file = scraper.save_to_csv(listings, args.mode, args.filter, args.city)
            print(f"SUCCESS: Scraped {len(listings)} listings")
            print(f"CSV file: {csv_file}")
            
            # Emit JSON progress event for total listings found
            import json
            import sys
            progress_event = {
                "type": "total",
                "total": len(listings)
            }
            print(json.dumps(progress_event), file=sys.stderr, flush=True)
            
            # Run phone extractor to get real phone numbers (fixed version with progress tracking)
            phone_extractor_path = os.path.join(os.path.dirname(__file__), 'phone_extractor_fixed.py')
            if os.path.exists(phone_extractor_path):
                logger.info(f"Running fixed phone extractor with progress tracking on {csv_file}")
                try:
                    result = subprocess.run(
                        ["python3", "phone_extractor_fixed.py", csv_file],
                        capture_output=True,
                        text=True,
                        timeout=1800,  # 30 minute timeout for reliability
                        cwd=os.path.dirname(__file__)
                    )
                    
                    if result.returncode == 0:
                        # Look for the updated file with real phones
                        updated_file = csv_file.replace('.csv', '_with_phones.csv')
                        if os.path.exists(updated_file):
                            # Count real phone numbers and create WhatsApp links
                            real_phone_count = 0
                            whatsapp_links = []
                            try:
                                import csv as csv_module
                                with open(updated_file, 'r', encoding='utf-8') as f:
                                    reader = csv_module.DictReader(f)
                                    for row in reader:
                                        phone = row.get('phone', '').strip()
                                        if phone and phone != '0501234567' and len(phone) >= 9:
                                            real_phone_count += 1
                                            # Clean phone number for WhatsApp (remove dashes, spaces)
                                            clean_phone = phone.replace('-', '').replace(' ', '').replace('+972', '0')
                                            if clean_phone.startswith('0'):
                                                clean_phone = '972' + clean_phone[1:]
                                            
                                            # Create WhatsApp link
                                            whatsapp_link = f"https://wa.me/{clean_phone}"
                                            whatsapp_links.append(f"{phone}: {whatsapp_link}")
                                
                                # Save WhatsApp links to file
                                if whatsapp_links:
                                    whatsapp_file = csv_file.replace('.csv', '_whatsapp_links.txt')
                                    with open(whatsapp_file, 'w', encoding='utf-8') as f:
                                        f.write("מספרי טלפון וקישורי WhatsApp:\n\n")
                                        for link in whatsapp_links:
                                            f.write(f"{link}\n")
                                    print(f"WhatsApp links file: {whatsapp_file}")
                                
                                print(f"Phone extraction completed: {real_phone_count} real phone numbers found")
                                print(f"Updated CSV file: {updated_file}")
                                print(f"WhatsApp links: {len(whatsapp_links)} links created")
                            except Exception as e:
                                logger.error(f"Error counting phones: {e}")
                                print(f"Phone extraction completed")
                        else:
                            print(f"Phone extraction completed (no updated file)")
                    else:
                        logger.warning(f"Phone extraction failed: {result.stderr}")
                        print(f"Phone extraction failed")
                        
                except Exception as e:
                    logger.error(f"Error running phone extractor: {e}")
                    print(f"Phone extraction error: {e}")
            else:
                logger.warning("Phone extractor not found")
                print(f"Phone extractor not found")
        else:
            print("No listings found")
            # Still create empty CSV file
            scraper.save_to_csv([], args.mode, args.filter)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())

