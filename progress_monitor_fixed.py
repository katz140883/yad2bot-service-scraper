"""
Fixed Progress Monitor - Real-time progress tracking with JSON file reading
"""

import asyncio
import json
import logging
import os
import glob
import subprocess
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class FixedProgressMonitor:
    """Fixed progress monitor with real-time JSON progress tracking."""
    
    def __init__(self):
        self.cancel_flag = False
        self.current_user_id = None
        
    def set_cancel_flag(self, user_id: int):
        """Set cancel flag for specific user."""
        if self.current_user_id == user_id:
            self.cancel_flag = True
            logger.info(f"[ProgressMonitor] Cancel flag set for user {user_id}")
            return True
        return False
    
    def reset_cancel_flag(self, user_id: int):
        """Reset cancel flag for new monitoring session."""
        self.cancel_flag = False
        self.current_user_id = user_id
        logger.info(f"[ProgressMonitor] Cancel flag reset for user {user_id}")
    
    def create_cancel_keyboard(self, language: str = 'hebrew'):
        """Create cancel button keyboard."""
        cancel_text = "⏹️ בטל סריקה" if language == 'hebrew' else "⏹️ Cancel Scraping"
        cancel_button = InlineKeyboardButton(cancel_text, callback_data="CANCEL_SCRAPE")
        return InlineKeyboardMarkup([[cancel_button]])
    
    async def _read_and_display_final_stats(self, progress_file, status_message, selection_info, 
                                             language, keyboard, total_pages, city_name, mode, filter_type, reason="completed"):
        """Read final progress file and update display with final stats.
        
        Args:
            progress_file: Path to the progress JSON file
            status_message: Telegram message object to update
            selection_info: Selection information text
            language: 'hebrew' or 'english'
            keyboard: Telegram keyboard markup
            total_pages: Total number of pages
            city_name: City name for CSV lookup
            mode: Mode (sale/rent) for CSV lookup
            filter_type: Filter type (today/test/pages_X) for CSV lookup
            reason: Exit reason - "completed", "timeout", or "cancelled"
        """
        try:
            if progress_file and os.path.exists(progress_file):
                with open(progress_file, 'r', encoding='utf-8') as f:
                    final_progress = json.load(f)
                
                # Extract data
                final_found = final_progress.get('found_recent', 0)
                final_duplicates = final_progress.get('duplicates_skipped', 0)
                final_current_global = final_progress.get('current_listing', 0)
                final_current_page = final_progress.get('current_page', 1)
                
                # Calculate position in current page
                listings_per_page = 20
                final_current_in_page = ((final_current_global - 1) % listings_per_page) + 1 if final_current_global > 0 else 0
                
                # --------------------------------------------------------------------------
                # Critical fix: Override found/duplicates counts in case of Timeout
                # --------------------------------------------------------------------------
                if reason == "timeout":
                    import csv
                    from datetime import datetime
                    import glob
                    
                    today_str = datetime.now().strftime('%Y-%m-%d')
                    
                    # 1. Read Found count from CSV (most reliable source)
                    if city_name and mode and filter_type:
                        expected_csv_pattern = f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}_{today_str}_*.csv"
                        csv_files = glob.glob(expected_csv_pattern)
                        
                        if csv_files:
                            csv_file_path = max(csv_files, key=os.path.getmtime)
                            try:
                                with open(csv_file_path, 'r', encoding='utf-8') as f:
                                    reader = csv.reader(f)
                                    final_found_from_csv = sum(1 for row in reader) - 1  # Subtract header
                                    
                                    if final_found_from_csv > 0:
                                        final_found = final_found_from_csv
                                        logger.info(f"[ProgressMonitor] Timeout correction: Found {final_found} listings by reading CSV: {csv_file_path}")
                            except Exception as e:
                                logger.error(f"[ProgressMonitor] Error reading CSV for final count in timeout: {e}")
                    
                    # 2. Read Duplicates and Page from memory (self.last_good_progress)
                    # This handles the case where JSON is corrupted and contains 0/0 duplicates/pages
                    if final_duplicates == 0 and hasattr(self, 'last_good_progress') and self.last_good_progress['duplicates'] > 0:
                        final_duplicates = self.last_good_progress['duplicates']
                        final_current_page = self.last_good_progress['page']
                        logger.info(f"[ProgressMonitor] Timeout correction: Duplicates count restored from memory: {final_duplicates}")
                
                logger.info(f"[ProgressMonitor] Final stats ({reason}): {final_found} found, {final_duplicates} duplicates, page {final_current_page}/{total_pages}")
                
                # Build message based on reason
                if language == 'hebrew':
                    if reason == "timeout":
                        final_msg = f"שלב 1/2 (הופסק עקב Timeout)\nסריקת מודעות\n\n🔍 נבדקו עד: מודעה {final_current_in_page}/{listings_per_page}\n📄 דף {final_current_page}/{total_pages}\n\n✅ נמצאו: {final_found} מודעות\n⏭️ כפילויות: {final_duplicates}"
                    elif reason == "cancelled":
                        final_msg = f"שלב 1/2 (בוטל על ידי המשתמש)\nסריקת מודעות\n\n🔍 נבדקו עד: מודעה {final_current_in_page}/{listings_per_page}\n📄 דף {final_current_page}/{total_pages}\n\n✅ נמצאו: {final_found} מודעות\n⏭️ כפילויות: {final_duplicates}"
                    else:  # completed
                        final_msg = f"שלב 1/2\nסריקת מודעות\n\n🔍 בודק מודעה {final_current_in_page}/{listings_per_page}\n📄 דף {final_current_page}/{total_pages}\n\n✅ נמצאו: {final_found} מודעות\n⏭️ כפילויות: {final_duplicates}"
                else:  # english
                    if reason == "timeout":
                        final_msg = f"Step 1/2 (Stopped due to Timeout)\nScanning Listings\n\n🔍 Checked up to: listing {final_current_in_page}/{listings_per_page}\n📄 Page {final_current_page}/{total_pages}\n\n✅ Found: {final_found} listings\n⏭️ Duplicates: {final_duplicates}"
                    elif reason == "cancelled":
                        final_msg = f"Step 1/2 (Cancelled by user)\nScanning Listings\n\n🔍 Checked up to: listing {final_current_in_page}/{listings_per_page}\n📄 Page {final_current_page}/{total_pages}\n\n✅ Found: {final_found} listings\n⏭️ Duplicates: {final_duplicates}"
                    else:  # completed
                        final_msg = f"Step 1/2\nScanning Listings\n\n🔍 Checking listing {final_current_in_page}/{listings_per_page}\n📄 Page {final_current_page}/{total_pages}\n\n✅ Found: {final_found} listings\n⏭️ Duplicates: {final_duplicates}"
                
                full_message = f"{selection_info}\n\n{final_msg}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור את הסריקה" if language == 'hebrew' else f"{selection_info}\n\n{final_msg}\n\n⏹️ Click cancel button to stop scraping"
                await status_message.edit_text(full_message, reply_markup=keyboard)
                logger.info(f"[ProgressMonitor] Updated display with final stats after {reason}")
                
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error reading final progress ({reason}): {e}")
    
    async def monitor_scraper_progress(self, status_message, language: str, user_id: int, selection_info: str = "", city_name: str = None, mode: str = None, filter_type: str = None):
        """Monitor main scraper progress with real-time listing checking updates."""
        try:
            logger.info(f"[ProgressMonitor] Starting scraper progress monitoring for user {user_id}")
            
            # Reset cancel flag
            self.reset_cancel_flag(user_id)
            
            # Create cancel keyboard
            keyboard = self.create_cancel_keyboard(language)
            
            # Get expected progress file path
            from datetime import date
            import glob
            today_str = date.today().strftime('%Y-%m-%d')
            # Search for progress files with city and mode filter
            if city_name and mode and filter_type:
                progress_patterns = [
                    f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}*{today_str}*_checking_progress.json",
                    f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}*progress*.json"
                ]
                logger.info(f"[ProgressMonitor] Looking for progress files: {city_name}_{mode}_{filter_type}")
            else:
                # Fallback to old behavior
                progress_patterns = [
                    f"/home/ubuntu/yad2bot_scraper/data/*{today_str}_checking_progress.json",
                    f"/home/ubuntu/yad2bot_scraper/data/*{today_str}*progress*.json"
                ]
                logger.warning(f"[ProgressMonitor] No city/mode specified, using fallback patterns")
            
            # Initial message with correct format
            initial_msg = "שלב 1/2\nסריקת מודעות\n\n🔄 מתחיל..." if language == 'hebrew' else "Step 1/2\nScanning Listings\n\n🔄 Starting..."
            full_message = f"{selection_info}\n\n{initial_msg}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור את הסריקה" if language == 'hebrew' else f"{selection_info}\n\n{initial_msg}\n\n⏹️ Click cancel button to stop scraping"
            
            await status_message.edit_text(full_message, reply_markup=keyboard)
            logger.info(f"[ProgressMonitor] Updated scraper progress: {initial_msg}")
            
            # Wait for scraper to create initial progress file with total_pages field
            for wait_attempt in range(10):  # Wait up to 10 seconds
                await asyncio.sleep(1)
                try:
                    for pattern in progress_patterns:
                        temp_files = glob.glob(pattern)
                        if temp_files:
                            temp_file = max(temp_files, key=os.path.getmtime)
                            with open(temp_file, 'r', encoding='utf-8') as f:
                                temp_data = json.load(f)
                                if 'total_pages' in temp_data:
                                    logger.info(f"[ProgressMonitor] Progress file ready with total_pages={temp_data.get('total_pages')}")
                                    break
                    else:
                        continue
                    break
                except:
                    continue
            
            logger.info(f"[ProgressMonitor] Starting to monitor progress file")
            
            # Monitor for progress file and real-time updates
            last_message = ""
            scraper_finished = False
            cached_total_pages = None  # Store total_pages once it's read
            
            # While loop with proper timeout mechanism (as recommended by expert)
            max_attempts = 1800  # Maximum 30 minutes (1800 seconds)
            current_attempt = 0
            last_update_attempt = 0  # Track when we last got progress update
            prev_current_listing = 0  # Track previous listing number to detect real changes
            timeout_occurred = False  # Track if loop exited due to timeout
            
            # Track last good progress state (before listing=0 reset)
            self.last_good_progress = {
                'found': 0,
                'duplicates': 0,
                'page': 1,
                'listing': 0
            }
            
            while current_attempt < max_attempts:
                logger.debug(f"[ProgressMonitor] Loop iteration started: attempt={current_attempt}")
                
                if self.cancel_flag:
                    logger.info(f"[ProgressMonitor] Exiting loop: reason=cancel_flag, attempt={current_attempt}")
                    break
                
                # Check if CSV file was created (indicates scraping finished)
                # Use exact filename pattern to avoid matching old files
                csv_files = []
                csv_file_exists = False
                
                # Try to find and read progress file
                try:
                    progress_files = []
                    
                    # Search all patterns
                    for pattern in progress_patterns:
                        progress_files.extend(glob.glob(pattern))
                    
                    if progress_files:
                        # Sort by modification time and take the newest file
                        progress_file = max(progress_files, key=os.path.getmtime)
                        
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        
                        # Create progress message
                        current_listing_global = progress_data.get('current_listing', 0)
                        total_listings_global = progress_data.get('total_listings_to_check', 20)
                        found = progress_data.get('found_recent', 0)
                        duplicates = progress_data.get('duplicates_skipped', 0)
                        title = progress_data.get('current_title', '')
                        current_page = progress_data.get('current_page', 1)
                        
                        # Calculate position in current page (each page has ~20 listings)
                        listings_per_page = 20
                        current_in_page = ((current_listing_global - 1) % listings_per_page) + 1 if current_listing_global > 0 else 0
                        total_in_page = listings_per_page
                        
                        # Cache total_pages once it's available, don't let it change back to default
                        if cached_total_pages is None and 'total_pages' in progress_data:
                            cached_total_pages = progress_data['total_pages']
                            logger.info(f"[ProgressMonitor] Cached total_pages={cached_total_pages}")
                        total_pages = cached_total_pages if cached_total_pages is not None else progress_data.get('total_pages', 10)
                        city_name = progress_data.get('city_name', '')
                        filter_type = progress_data.get('filter_type', '')
                        
                        # Check for CSV file with exact filename pattern (only after we have city_name)
                        if city_name:
                            expected_csv_pattern = f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}_*.csv"
                            csv_files = glob.glob(expected_csv_pattern)
                            csv_file_exists = len(csv_files) > 0
                            if csv_file_exists:
                                logger.debug(f"[ProgressMonitor] Found CSV file: {csv_files[0]}")
                        
                        # Update last_update_attempt only if progress actually changed
                        # Ignore listing 0 as it's not a real update (scraper reset)
                        if current_listing_global != prev_current_listing and current_listing_global > 0:
                            last_update_attempt = current_attempt
                            prev_current_listing = current_listing_global
                            logger.debug(f"[ProgressMonitor] Progress changed: listing {current_listing_global}, resetting timeout timer")
                            
                            # Save last good progress state (for timeout recovery)
                            self.last_good_progress = {
                                'found': found,
                                'duplicates': duplicates,
                                'page': current_page,
                                'listing': current_listing_global
                            }
                        elif current_listing_global == 0 and prev_current_listing > 0:
                            logger.warning(f"[ProgressMonitor] Detected listing reset to 0 (was {prev_current_listing}), NOT resetting timeout timer")
                        
                        # Build title line only if title exists
                        title_line = f"\n📋 {title}" if title else ""
                        
                        if language == 'hebrew':
                            # Show 'מהיום' only if filter_type is 'today'
                            if filter_type == 'today':
                                progress_msg = f"שלב 1/2\nסריקת מודעות\n\n🔍 בודק מודעה {current_in_page}/{total_in_page}\n📄 דף {current_page}/{total_pages}{title_line}\n\n✅ נמצאו: {found} מודעות\n⏭️ כפילויות: {duplicates}"
                            else:
                                progress_msg = f"שלב 1/2\nסריקת מודעות\n\n🔍 בודק מודעה {current_in_page}/{total_in_page}\n📄 דף {current_page}/{total_pages}{title_line}\n\n✅ נמצאו: {found} מודעות\n⏭️ כפילויות: {duplicates}"
                        else:
                            # Show 'recent' only if filter_type is 'today'
                            if filter_type == 'today':
                                progress_msg = f"Step 1/2\nScanning Listings\n\n🔍 Checking listing {current_in_page}/{total_in_page}\n📄 Page {current_page}/{total_pages}{title_line}\n\n✅ Found: {found} listings\n⏭️ Duplicates: {duplicates}"
                            else:
                                progress_msg = f"Step 1/2\nScanning Listings\n\n🔍 Checking listing {current_in_page}/{total_in_page}\n📄 Page {current_page}/{total_pages}{title_line}\n\n✅ Found: {found} listings\n⏭️ Duplicates: {duplicates}"
                        
                        full_message = f"{selection_info}\n\n{progress_msg}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור את הסריקה" if language == 'hebrew' else f"{selection_info}\n\n{progress_msg}\n\n⏹️ Click cancel button to stop scraping"
                        
                        # Update only if message changed
                        if progress_msg != last_message:
                            await status_message.edit_text(full_message, reply_markup=keyboard)
                            logger.info(f"[ProgressMonitor] Updated scraper progress: {progress_msg}")
                            last_message = progress_msg
                        
                        # Check if scraping is complete (reached total listings or stage is completed)
                        stage = progress_data.get('stage', '')
                        if stage == 'completed':
                            logger.info(f"[ProgressMonitor] Stage is 'completed', scraper finished")
                            scraper_finished = True
                        elif current_listing_global >= total_listings_global and total_listings_global > 0:
                            logger.info(f"[ProgressMonitor] Scraping reached {current_listing_global}/{total_listings_global}, checking if process finished...")
                            scraper_finished = True
                    
                    else:
                        # Wait for progress file instead of showing generic message
                        pass
                
                except Exception as e:
                    logger.debug(f"[ProgressMonitor] Error reading progress file: {e}")
                    logger.debug(f"[ProgressMonitor] Exception occurred at attempt={current_attempt}")
                
                # Check for timeout (no updates for 3 minutes)
                if current_attempt - last_update_attempt > 180:  # 3 minutes without updates
                    logger.warning(f"[ProgressMonitor] Exiting loop: reason=timeout_no_updates_for_3min, attempt={current_attempt}")
                    timeout_occurred = True  # Set flag for post-loop handling
                    break
                
                # If scraper finished processing all listings and CSV file created, exit loop
                if scraper_finished and csv_file_exists:
                    logger.info(f"[ProgressMonitor] Exiting loop: reason=scraper_finished_and_csv_exists, attempt={current_attempt}, current={current_listing_global}, total={total_listings_global}, csv_files={len(csv_files)}")
                    logger.info(f"[ProgressMonitor] Scraper finished processing all listings, waiting for final update...")
                    
                    # Wait 2 seconds for scraper to write final progress update
                    await asyncio.sleep(2)
                    
                    # Update display with final stats using helper function
                    await self._read_and_display_final_stats(
                        progress_file, status_message, selection_info,
                        language, keyboard, total_pages, city_name, mode, filter_type, reason="completed"
                    )
                    
                    logger.info(f"[ProgressMonitor] Moving to phase 2...")
                    await asyncio.sleep(1)  # Give time for file system sync
                    break
                
                await asyncio.sleep(1)  # Check every 1 second for faster updates
                
                logger.debug(f"[ProgressMonitor] End of iteration: attempt={current_attempt}, scraper_finished={scraper_finished}, csv_exists={csv_file_exists}, time_since_update={current_attempt - last_update_attempt}s")
                
                # Increment counter
                current_attempt += 1
            
            # Handle final display after loop exit based on reason
            if timeout_occurred:
                logger.info(f"[ProgressMonitor] Handling final display after timeout...")
                # Update display with final stats from progress file
                await self._read_and_display_final_stats(
                    progress_file, status_message, selection_info,
                    language, keyboard, total_pages, city_name, mode, filter_type, reason="timeout"
                )
            elif self.cancel_flag:
                logger.info(f"[ProgressMonitor] Handling final display after cancellation...")
                # Update display with final stats from progress file
                await self._read_and_display_final_stats(
                    progress_file, status_message, selection_info,
                    language, keyboard, total_pages, city_name, mode, filter_type, reason="cancelled"
                )
            
            # Log why loop ended
            logger.info(f"[ProgressMonitor] ===== LOOP EXITED =====")
            logger.info(f"[ProgressMonitor] Loop ended: attempt={current_attempt}, scraper_finished={scraper_finished}, csv_exists={csv_file_exists}, cancel_flag={self.cancel_flag}, timeout={timeout_occurred}")
            logger.info(f"[ProgressMonitor] Total iterations completed: {current_attempt}, time_since_last_update={current_attempt - last_update_attempt}s")
            logger.info(f"[ProgressMonitor] Scraper progress monitoring completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error in scraper progress monitoring: {e}")
    
    async def monitor_phone_extraction_progress(self, status_message, language: str, user_id: int, selection_info: str = "", city_name: str = None, mode: str = None, filter_type: str = None):
        """Monitor phone extraction with real-time JSON progress reading."""
        try:
            logger.info(f"[ProgressMonitor] Starting phone extraction progress monitoring for user {user_id}")
            
            # Create cancel keyboard
            keyboard = self.create_cancel_keyboard(language)
            
            # Send a NEW message for phone extraction progress (separate from scraping progress)
            initial_text = "📱 מחלץ מספרי טלפון..." if language == 'hebrew' else "📱 Extracting phone numbers..."
            phone_progress_message = await status_message.get_bot().send_message(
                chat_id=status_message.chat_id,
                text=initial_text,
                reply_markup=keyboard
            )
            logger.info(f"[ProgressMonitor] Sent new message for phone extraction progress")
            
            # Use the new message for updates instead of status_message
            status_message = phone_progress_message
            
            # Check if CSV is empty (no ads to extract)
            if hasattr(self, 'csv_listings_count') and self.csv_listings_count == 0:
                logger.info(f"[ProgressMonitor] CSV is empty, showing 'no ads to extract' message")
                no_ads_text = (
                    f"{selection_info}\n\n"
                    f"שלב 2/2\n"
                    f"חילוץ מספרים\n\n"
                    f"❌ אין מודעות לחילוץ מספרים"
                )
                await status_message.edit_text(no_ads_text, reply_markup=None)
                await asyncio.sleep(2)  # Show message for 2 seconds
                return "completed_no_ads"
            
            # Find progress file pattern
            today = datetime.now().strftime('%Y-%m-%d')
            if city_name and mode and filter_type:
                progress_pattern = f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}*{today}*_progress.json"
                logger.info(f"[ProgressMonitor] Looking for phone progress: {city_name}_{mode}_{filter_type}")
            else:
                progress_pattern = f"/home/ubuntu/yad2bot_scraper/data/*{today}*_progress.json"
                logger.warning(f"[ProgressMonitor] No city/mode for phone extraction, using fallback")
            
            max_wait = 1800  # 30 minutes maximum
            wait_time = 0
            last_progress_text = ""
            progress_file_found = False
            
            while wait_time < max_wait and not self.cancel_flag:
                # Check if phone extraction process is still running
                try:
                    result = subprocess.run(['pgrep', '-f', 'phone_extractor_fixed.py'], 
                                          capture_output=True, text=True, timeout=2)
                    phone_extractor_running = result.returncode == 0
                except:
                    phone_extractor_running = False
                
                # Look for progress files (exclude checking_progress files)
                all_progress_files = glob.glob(progress_pattern)
                # Filter out checking_progress files - we only want phone extraction progress
                progress_files = [f for f in all_progress_files if '_checking_progress.json' not in f]
                
                if progress_files and not progress_file_found:
                    progress_file_found = True
                    logger.info(f"[ProgressMonitor] Phone extraction progress file found: {progress_files[0]}")
                elif all_progress_files and not progress_files:
                    logger.debug(f"[ProgressMonitor] Only found checking_progress files, waiting for phone extraction progress...")
                
                if progress_files:
                    # Read the most recent progress file
                    progress_file = max(progress_files, key=os.path.getctime)
                    
                    try:
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        
                        current = progress_data.get('current', 0)
                        total = progress_data.get('total', 0)
                        percent = progress_data.get('percent', 0)
                        phones_found = progress_data.get('phones_found', 0)
                        status = progress_data.get('status', 'processing')
                        
                        # Calculate estimated time remaining
                        if current > 0 and total > 0 and percent > 0:
                            elapsed_time = wait_time
                            estimated_total_time = elapsed_time / (percent / 100)
                            remaining_time = max(0, estimated_total_time - elapsed_time)
                            
                            if remaining_time > 60:
                                time_str = f"{int(remaining_time // 60)} דקות" if language == 'hebrew' else f"{int(remaining_time // 60)} minutes"
                            else:
                                time_str = f"{int(remaining_time)} שניות" if language == 'hebrew' else f"{int(remaining_time)} seconds"
                        else:
                            time_str = "חישוב..." if language == 'hebrew' else "calculating..."
                        
                        # Create progress message
                        if language == 'hebrew':
                            progress_text = f"{selection_info}\n\nשלב 2/2\nחילוץ מספרים\n\n📊 התקדמות: {percent:.1f}% ({current}/{total})\n📞 נמצאו: {phones_found} מספרים\n⏱️ זמן נותר: {time_str}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור"
                        else:
                            progress_text = f"{selection_info}\n\nStep 2/2\nExtracting Numbers\n\n📊 Progress: {percent:.1f}% ({current}/{total})\n📞 Found: {phones_found} numbers\n⏱️ Time remaining: {time_str}\n\n⏹️ Click cancel button to stop"
                        
                        # Update message only if progress changed significantly
                        if progress_text != last_progress_text:
                            try:
                                await status_message.edit_text(progress_text, reply_markup=keyboard)
                                last_progress_text = progress_text
                                logger.info(f"[ProgressMonitor] Updated phone extraction progress: {percent:.1f}% ({current}/{total}) - {phones_found} phones")
                            except Exception as e:
                                logger.error(f"[ProgressMonitor] Error updating progress message: {e}")
                        
                        # Check if completed
                        if status == 'completed' or (current >= total and total > 0):
                            logger.info(f"[ProgressMonitor] Phone extraction completed: {phones_found} phones found")
                            break
                        
                        # Check if no listings to process (all duplicates)
                        if total == 0 and current == 0 and status != 'processing':
                            logger.info(f"[ProgressMonitor] No new listings to process (all duplicates)")
                            break
                            
                    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                        logger.warning(f"[ProgressMonitor] Error reading progress file: {e}")
                        # Continue with fallback animation
                        
                else:
                    # No progress file yet, show loading animation
                    progress_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                    char_index = (wait_time // 2) % len(progress_chars)
                    
                    if language == 'hebrew':
                        progress_text = f"{selection_info}\n\nשלב 2/2\nחילוץ מספרים\n\n📱 {progress_chars[char_index]} מתחיל עיבוד...\n\n⏹️ לחץ על כפתור הביטול כדי לעצור"
                    else:
                        progress_text = f"{selection_info}\n\nStep 2/2\nExtracting Numbers\n\n📱 {progress_chars[char_index]} Starting processing...\n\n⏹️ Click cancel button to stop"
                    
                    # Update animation only every 6 seconds to avoid too many updates
                    if wait_time % 6 == 0 and progress_text != last_progress_text:
                        try:
                            await status_message.edit_text(progress_text, reply_markup=keyboard)
                            last_progress_text = progress_text
                            logger.debug(f"[ProgressMonitor] Updated loading animation")
                        except Exception as e:
                            logger.error(f"[ProgressMonitor] Error updating animation: {e}")
                
                # Check if phone extractor process stopped
                if not phone_extractor_running and progress_file_found:
                    logger.info(f"[ProgressMonitor] Phone extractor process stopped, checking final results...")
                    await asyncio.sleep(3)  # Give time for final file writes
                    break
                
                await asyncio.sleep(1)  # Check every 1 second for faster updates
                wait_time += 1
            
            if self.cancel_flag:
                logger.info(f"[ProgressMonitor] Phone extraction monitoring cancelled by user {user_id}")
                return "cancelled"
            
            logger.info(f"[ProgressMonitor] Phone extraction monitoring completed for user {user_id}")
            return "completed"
            
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error in phone extraction progress monitoring: {e}")
            return f"error: {str(e)}"
    
    async def wait_for_results_file(self, user_id: int, city_name: str = None, mode: str = None, filter_type: str = None, timeout: int = 300):
        """Wait for the final results CSV file to be created."""
        try:
            logger.info(f"[ProgressMonitor] Waiting for results file for user {user_id}")
            
            today = datetime.now().strftime('%Y-%m-%d')
            if city_name and mode and filter_type:
                csv_pattern_with_phones = f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}*{today}*_with_phones.csv"
                csv_pattern_regular = f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}*{today}*.csv"
                logger.info(f"[ProgressMonitor] Looking for results file: {city_name}_{mode}_{filter_type}")
            else:
                csv_pattern_with_phones = f"/home/ubuntu/yad2bot_scraper/data/*{today}*_with_phones.csv"
                csv_pattern_regular = f"/home/ubuntu/yad2bot_scraper/data/*{today}*.csv"
                logger.warning(f"[ProgressMonitor] No city/mode for results file, using fallback")
            
            wait_time = 0
            extraction_in_progress = False
            
            while wait_time < timeout and not self.cancel_flag:
                # Check if phone extraction is in progress by looking at progress file
                progress_pattern = f"/home/ubuntu/yad2bot_scraper/data/{city_name}_{mode}_{filter_type}*{today}*_progress.json" if city_name else f"/home/ubuntu/yad2bot_scraper/data/*{today}*_progress.json"
                progress_files = glob.glob(progress_pattern)
                
                if progress_files:
                    latest_progress = max(progress_files, key=os.path.getmtime)
                    try:
                        with open(latest_progress, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                            status = progress_data.get('status', '')
                            
                            if status == 'completed':
                                # Extraction completed, look for _with_phones file
                                csv_files = glob.glob(csv_pattern_with_phones)
                                if csv_files:
                                    latest_csv = max(csv_files, key=os.path.getctime)
                                    logger.info(f"[ProgressMonitor] Results file found (with phones): {latest_csv}")
                                    return latest_csv
                                else:
                                    logger.warning(f"[ProgressMonitor] Extraction completed but no _with_phones file found yet, waiting...")
                            elif status in ['extracting', 'processing']:
                                extraction_in_progress = True
                                logger.info(f"[ProgressMonitor] Phone extraction in progress: {progress_data.get('current', 0)}/{progress_data.get('total', 0)}")
                    except Exception as e:
                        logger.error(f"[ProgressMonitor] Error reading progress file: {e}")
                
                # If no extraction in progress and enough time passed, check for regular CSV
                if not extraction_in_progress and wait_time >= 30:
                    csv_files = glob.glob(csv_pattern_regular)
                    csv_files = [f for f in csv_files if '_with_phones' not in f]
                    if csv_files:
                        latest_csv = max(csv_files, key=os.path.getctime)
                        logger.warning(f"[ProgressMonitor] No extraction in progress, using regular CSV: {latest_csv}")
                        return latest_csv
                
                extraction_in_progress = False  # Reset for next iteration
                await asyncio.sleep(3)
                wait_time += 3
            
            if self.cancel_flag:
                logger.info(f"[ProgressMonitor] Results file wait cancelled for user {user_id}")
                return None
            
            logger.warning(f"[ProgressMonitor] Timeout waiting for results file for user {user_id}")
            return None
        
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error waiting for results file: {e}")
            return None
