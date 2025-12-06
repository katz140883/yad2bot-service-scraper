#!/usr/bin/env python3
"""
Fixed Phone Extractor - Improved reliability and progress tracking
"""

import csv
import json
import logging
import os
import re
import sys
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'logs', f'phone_extractor_{time.strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ZenRows configuration
ZENROWS_API_KEY = '3f50019a0655a46ab2198f4b29a29de2ba11f133'
ZENROWS_API_URL = 'https://api.zenrows.com/v1/'

class FixedPhoneExtractor:
    """Fixed phone number extraction with improved reliability and progress tracking."""
    
    def __init__(self):
        self.progress_file = None
        
    def create_progress_file(self, csv_file_path: str):
        """Create progress tracking file."""
        try:
            base_name = os.path.basename(csv_file_path).replace('.csv', '')
            progress_dir = os.path.dirname(csv_file_path)
            self.progress_file = os.path.join(progress_dir, f"{base_name}_progress.json")
            
            # Initialize progress file
            progress_data = {
                'current': 0,
                'total': 0,
                'percent': 0,
                'phones_found': 0,
                'status': 'starting',
                'start_time': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Progress file created: {self.progress_file}")
            
        except Exception as e:
            logger.error(f"Error creating progress file: {e}")
            self.progress_file = None
    
    def update_progress(self, current: int, total: int, phones_found: int, status: str = 'processing'):
        """Update progress tracking file."""
        if not self.progress_file:
            return
            
        try:
            percent = int((current / total) * 100) if total > 0 else 0
            
            progress_data = {
                'current': current,
                'total': total,
                'percent': percent,
                'phones_found': phones_found,
                'status': status,
                'last_updated': datetime.now().isoformat()
            }
            
            # Read existing data to preserve start_time
            if os.path.exists(self.progress_file):
                try:
                    with open(self.progress_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                        progress_data['start_time'] = existing_data.get('start_time', datetime.now().isoformat())
                except:
                    progress_data['start_time'] = datetime.now().isoformat()
            else:
                progress_data['start_time'] = datetime.now().isoformat()
            
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
                
            logger.info(f"Progress updated: {current}/{total} ({percent}%) - {phones_found} phones found")
            
        except Exception as e:
            logger.error(f"Error updating progress: {e}")
    
    def get_listing_details_from_page(self, listing_url: str) -> dict:
        """Extract phone number and additional details from listing page."""
        details = {
            'phone_number': '',
            'rooms': '',
            'floor': '',
            'owner_name': '',
            'publish_date': ''
        }
        
        try:
            logger.info(f"Extracting details from: {listing_url}")
            
            # Improved JavaScript with longer waits for reliability
            js_instructions = [
                {"wait": 2000},   # 2 seconds to load page
                {"click": "button:contains('הצגת מספר טלפון')"},
                {"wait": 3000},   # 3 seconds for phone to appear
                {"click": "[data-testid*='phone'], .phone-button, button[aria-label*='טלפון']"},
                {"wait": 2000}    # 2 seconds additional wait
            ]
            
            params = {
                'url': listing_url,
                'apikey': ZENROWS_API_KEY,
                'js_render': 'true',
                'premium_proxy': 'true',
                'proxy_country': 'il',
                'js_instructions': json.dumps(js_instructions),
                'wait': '7000'  # Total 7 seconds wait
            }
            
            response = requests.get(ZENROWS_API_URL, params=params, timeout=60)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Enhanced selectors for phone numbers
                phone_selectors = [
                    'a[href^="tel:"]',  # Phone links
                    'a[href*="05"]',    # Links with 05 in href
                    'a:contains("05")',  # Links containing 05
                    'span:contains("05")',  # Spans containing 05
                    'div:contains("05")',  # Divs containing 05
                    '[data-testid*="phone"]',  # Phone test IDs
                    '[data-testid*="contact"]',  # Contact test IDs
                    '.phone-number',  # Phone number classes
                    '.contact-phone',  # Contact phone classes
                    '.phone-display',  # Phone display classes
                    '[class*="phone"]',  # Any class containing "phone"
                    '[id*="phone"]',  # Any ID containing "phone"
                    'button[aria-label*="טלפון"]',  # Phone buttons
                    '.contact-info a',  # Contact info links
                    '.seller-phone',  # Seller phone classes
                    '.advertiser-phone'  # Advertiser phone classes
                ]
                
                phone_found = False
                for selector in phone_selectors:
                    if phone_found:
                        break
                    try:
                        elements = soup.select(selector)
                        for element in elements:
                            if phone_found:
                                break
                            # Check both text content and href attribute
                            text_sources = [
                                element.get_text(strip=True),
                                element.get('href', ''),
                                element.get('title', ''),
                                element.get('aria-label', '')
                            ]
                            
                            for text in text_sources:
                                if phone_found:
                                    break
                                if not text:
                                    continue
                                    
                                # Look for Israeli mobile numbers with various formats
                                phone_patterns = [
                                    r'05[0-9]-?[0-9]{7}',  # Standard format
                                    r'\\+972-?5[0-9]-?[0-9]{7}',  # International format
                                    r'972-?5[0-9]-?[0-9]{7}',  # International without +
                                    r'05[0-9]\\s?[0-9]{3}\\s?[0-9]{4}',  # Spaced format
                                ]
                                
                                for pattern in phone_patterns:
                                    phone_matches = re.findall(pattern, text)
                                    if phone_matches:
                                        # Clean the phone number
                                        phone = re.sub(r'[^0-9]', '', phone_matches[0])
                                        
                                        # Handle international format
                                        if phone.startswith('972'):
                                            phone = '0' + phone[3:]
                                        
                                        # Validate Israeli mobile number
                                        if len(phone) == 10 and phone.startswith('05'):
                                            logger.info(f"✅ Found phone with selector '{selector}': {phone}")
                                            details['phone_number'] = phone
                                            phone_found = True
                                            break
                                            
                    except Exception as e:
                        logger.debug(f"Selector {selector} failed: {e}")
                        continue
                
                # Enhanced fallback: search entire page with multiple patterns (only if not found yet)
                if not phone_found:
                    page_text = soup.get_text()
                    
                    # Try multiple phone patterns on full page text
                    phone_patterns = [
                        r'05[0-9]-?[0-9]{7}',
                        r'\\+972-?5[0-9]-?[0-9]{7}',
                        r'972-?5[0-9]-?[0-9]{7}',
                        r'05[0-9]\\s[0-9]{3}\\s[0-9]{4}',
                        r'05[0-9]\\s[0-9]{7}'
                    ]
                    
                    for pattern in phone_patterns:
                        if phone_found:
                            break
                        phone_matches = re.findall(pattern, page_text)
                        if phone_matches:
                            for match in phone_matches:
                                phone = re.sub(r'[^0-9]', '', match)
                                
                                # Handle international format
                                if phone.startswith('972'):
                                    phone = '0' + phone[3:]
                                
                                # Validate
                                if len(phone) == 10 and phone.startswith('05'):
                                    logger.info(f"✅ Found phone in page text: {phone}")
                                    details['phone_number'] = phone
                                    phone_found = True
                                    break
                
                if not phone_found:
                    logger.warning(f"❌ No phone found for {listing_url}")
                    details['phone_number'] = ""
                
                # Extract __NEXT_DATA__ JSON for additional fields
                try:
                    # Debug: check if __NEXT_DATA__ exists
                    if '__NEXT_DATA__' in response.text:
                        logger.info("✅ __NEXT_DATA__ found in response")
                    else:
                        logger.warning("❌ __NEXT_DATA__ not in response text")
                    
                    pattern = r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>'
                    match = re.search(pattern, response.text, re.DOTALL)
                
                    if match:
                        json_str = match.group(1)
                        next_data = json.loads(json_str)
                        logger.info(f"✅ Parsed __NEXT_DATA__ JSON, top keys: {list(next_data.keys())}")
                        
                        # Navigate to item data
                        props = next_data.get('props', {})
                        logger.info(f"props keys: {list(props.keys()) if props else 'None'}")
                        
                        page_props = props.get('pageProps', {})
                        logger.info(f"pageProps keys: {list(page_props.keys())[:10] if page_props else 'None'}")
                        
                        # Try to get item from dehydratedState (React Query structure)
                        item = {}
                        dehydrated_state = page_props.get('dehydratedState', {})
                        if dehydrated_state:
                            logger.info("Found dehydratedState, extracting queries...")
                            queries = dehydrated_state.get('queries', [])
                            logger.info(f"Found {len(queries)} queries in dehydratedState")
                            
                            # Look for the item data in queries
                            for query in queries:
                                query_data = query.get('state', {}).get('data', {})
                                if query_data and isinstance(query_data, dict):
                                    # Check if this looks like item data
                                    if 'additionalDetails' in query_data or 'contactInfo' in query_data:
                                        item = query_data
                                        logger.info("✅ Found item data in dehydratedState")
                                        break
                        
                        # Fallback: try direct item path
                        if not item:
                            item = page_props.get('item', {})
                        
                        logger.info(f"item keys: {list(item.keys())[:10] if item else 'None'}")
                        
                        # Extract rooms
                        if item:
                            additional_details = item.get('additionalDetails', {})
                            logger.info(f"additionalDetails keys: {list(additional_details.keys())[:10] if additional_details else 'None'}")
                            
                            property_info = additional_details.get('property', {})
                            logger.info(f"property keys: {list(property_info.keys())[:10] if property_info else 'None'}")
                        else:
                            logger.warning("No item data found")
                            additional_details = {}
                            property_info = {}
                        
                        # Extract rooms - check both 'rooms' and 'roomsCount' in additionalDetails
                        rooms_count = additional_details.get('roomsCount') or property_info.get('rooms')
                        if rooms_count:
                            details['rooms'] = str(rooms_count)
                            logger.info(f"✅ Found rooms: {details['rooms']}")
                        else:
                            logger.warning("rooms not found")
                        
                        # Extract floor - check in address.house.floor
                        address = item.get('address', {})
                        house = address.get('house', {})
                        floor = house.get('floor')
                        if floor is not None:  # floor can be 0
                            details['floor'] = str(floor)
                            logger.info(f"✅ Found floor: {details['floor']}")
                        else:
                            logger.warning("floor not found")
                        
                        # Extract owner name - try contactInfo first, then searchText
                        contact_info = item.get('contactInfo', {})
                        if contact_info.get('name'):
                            details['owner_name'] = contact_info['name']
                            logger.info(f"✅ Found owner name from contactInfo: {details['owner_name']}")
                        else:
                            # Try to extract from searchText
                            search_text = item.get('searchText', '')
                            if 'שם מוכר' in search_text:  # "שם מוכר" in Hebrew
                                import re as re_module
                                match = re_module.search(r'שם מוכר\s+(\S+)', search_text)
                                if match:
                                    details['owner_name'] = match.group(1)
                                    logger.info(f"✅ Found owner name from searchText: {details['owner_name']}")
                            if not details['owner_name']:
                                logger.warning("owner_name not found")
                        
                        # Extract publish date - use createdAt
                        dates = item.get('dates', {})
                        publish_date_str = dates.get('createdAt') or dates.get('publishDate')
                        if publish_date_str:
                            try:
                                if 'T' in publish_date_str:
                                    dt = datetime.fromisoformat(publish_date_str.replace('Z', '+00:00'))
                                    details['publish_date'] = dt.strftime('%d/%m/%y')
                                else:
                                    details['publish_date'] = publish_date_str
                                logger.info(f"✅ Found publish date: {details['publish_date']}")
                            except Exception as e:
                                logger.warning(f"Error parsing publish date: {e}")
                                details['publish_date'] = publish_date_str
                        else:
                            logger.warning("publish_date not found")
                    else:
                        logger.warning(f"No __NEXT_DATA__ found in {listing_url}")
                except Exception as e:
                    logger.error(f"Error extracting additional details: {e}")
            else:
                logger.error(f"❌ HTTP {response.status_code}: {response.text[:200]}")
                details['phone_number'] = ""
            
            return details
            
        except Exception as e:
            logger.error(f"❌ Error extracting details from {listing_url}: {e}")
            return details
    
    def get_phone_improved(self, listing_url: str) -> str:
        """Legacy method - now calls get_listing_details_from_page."""
        details = self.get_listing_details_from_page(listing_url)
        return details.get('phone_number', '')
    
    def update_csv_with_progress(self, csv_file_path: str) -> str:
        """Update CSV with phone numbers and real-time progress tracking."""
        try:
            logger.info(f"Starting phone extraction with progress tracking for: {csv_file_path}")
            
            # Create progress tracking
            self.create_progress_file(csv_file_path)
            
            # Read CSV
            listings = []
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                listings = list(reader)
            
            total_listings = len(listings)
            logger.info(f"Processing {total_listings} listings")
            
            # Update initial progress
            self.update_progress(0, total_listings, 0, 'starting')
            
            # Extract phones with progress tracking
            updated_count = 0
            phones_found = 0
            
            for i, listing in enumerate(listings):
                current_index = i + 1
                listing_url = listing.get('listing_url', '')
                
                # Update progress
                self.update_progress(current_index, total_listings, phones_found, 'processing')
                
                # Check if listing already exists in CRM before extracting phone
                if listing_url:
                    try:
                        # Import the check function from database module
                        import sys
                        sys.path.insert(0, '/home/ubuntu/yad2bot-service-scraper')
                        from database import check_lead_exists_in_mysql
                        
                        if check_lead_exists_in_mysql(listing_url):
                            logger.info(f"⏭️  Listing {current_index}/{total_listings} already in CRM, skipping: {listing_url}")
                            # Count it as found since it exists
                            if listing.get('phone_number') and listing.get('phone_number') != '0501234567':
                                phones_found += 1
                            continue
                    except Exception as check_error:
                        logger.warning(f"Could not check CRM, continuing with extraction: {check_error}")
                
                if listing_url and listing.get('phone_number') == '0501234567':
                    logger.info(f"Processing {current_index}/{total_listings}: {listing_url}")
                    
                    # Extract all details from listing page
                    details = self.get_listing_details_from_page(listing_url)
                    
                    # Update listing with all extracted details
                    if details.get('phone_number') and details['phone_number'] != '0501234567':
                        listing['phone_number'] = details['phone_number']
                        updated_count += 1
                        phones_found += 1
                        logger.info(f"✅ Updated {current_index}: {details['phone_number']}")
                    else:
                        logger.warning(f"❌ Failed to get phone for {current_index}")
                    
                    # Update additional fields if they exist and are not already populated
                    if details.get('rooms') and not listing.get('rooms'):
                        listing['rooms'] = details['rooms']
                    if details.get('floor') is not None and not listing.get('floor'):
                        listing['floor'] = details['floor']
                    if details.get('owner_name') and not listing.get('owner_name'):
                        listing['owner_name'] = details['owner_name']
                    if details.get('publish_date') and not listing.get('publish_date'):
                        listing['publish_date'] = details['publish_date']
                    
                    # Update progress after each extraction
                    self.update_progress(current_index, total_listings, phones_found, 'processing')
                    
                    # Reasonable delay to prevent overwhelming the API
                    time.sleep(1)
                else:
                    # Skip listings that already have phones or no URL
                    if listing.get('phone_number') and listing.get('phone_number') != '0501234567':
                        phones_found += 1
            
            # Final progress update
            self.update_progress(total_listings, total_listings, phones_found, 'completed')
            
            # Save updated CSV
            output_path = csv_file_path.replace('.csv', '_with_phones.csv')
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                if listings:
                    fieldnames = listings[0].keys()
                    writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writeheader()
                    writer.writerows(listings)
            
            logger.info(f"✅ COMPLETED: {phones_found} total phones, {updated_count} newly extracted")
            return output_path
            
        except Exception as e:
            logger.error(f"Error in phone extraction: {e}")
            if self.progress_file:
                self.update_progress(0, 0, 0, f'error: {str(e)}')
            return ""

def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python3 phone_extractor_fixed.py <csv_file>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    if not os.path.exists(csv_file):
        print(f"Error: File not found: {csv_file}")
        sys.exit(1)
    
    extractor = FixedPhoneExtractor()
    result = extractor.update_csv_with_progress(csv_file)
    
    if result:
        print(f"SUCCESS: {result}")
    else:
        print("ERROR: Failed to extract phones")
        sys.exit(1)

if __name__ == "__main__":
    main()
