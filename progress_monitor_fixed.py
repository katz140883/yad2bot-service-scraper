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
        cancel_text = "🛑 בטל סריקה" if language == 'hebrew' else "🛑 Cancel Scraping"
        cancel_button = InlineKeyboardButton(cancel_text, callback_data="CANCEL_SCRAPE")
        return InlineKeyboardMarkup([[cancel_button]])
    
    async def monitor_scraper_progress(self, status_message, language: str, user_id: int, selection_info: str = ""):
        """Monitor main scraper progress with real-time listing checking updates."""
        try:
            logger.info(f"[ProgressMonitor] Starting scraper progress monitoring for user {user_id}")
            
            # Reset cancel flag
            self.reset_cancel_flag(user_id)
            
            # Create cancel keyboard
            keyboard = self.create_cancel_keyboard(language)
            
            # Get expected progress file path
            from datetime import date
            today_str = date.today().strftime('%Y-%m-%d')
            # Search for progress files with both old and new naming patterns
            progress_patterns = [
                f"/root/yad2bot/yad2bot_package/war_yad2bot/data/*{today_str}_checking_progress.json",
                f"/root/yad2bot/yad2bot_package/war_yad2bot/data/*{today_str}*progress*.json"
            ]
            
            # Initial message
            initial_msg = "🔄 מתחבר לאתר yad2..." if language == 'hebrew' else "🔄 Connecting to yad2..."
            full_message = f"{selection_info}\n\n{initial_msg}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור את הסריקה" if language == 'hebrew' else f"{selection_info}\n\n{initial_msg}\n\n⏹️ Click cancel button to stop scraping"
            
            await status_message.edit_text(full_message, reply_markup=keyboard)
            logger.info(f"[ProgressMonitor] Updated scraper progress: {initial_msg}")
            
            # Monitor for progress file and real-time updates
            last_message = ""
            for attempt in range(600):  # Monitor for up to 30 minutes (600 * 3 seconds)
                if self.cancel_flag:
                    logger.info(f"[ProgressMonitor] Cancel detected during scraper monitoring")
                    break
                
                # Try to find and read progress file
                try:
                    import glob
                    progress_files = []
                    
                    # Search all patterns
                    for pattern in progress_patterns:
                        progress_files.extend(glob.glob(pattern))
                    
                    if progress_files:
                        progress_file = progress_files[0]  # Take the first match
                        
                        with open(progress_file, 'r', encoding='utf-8') as f:
                            progress_data = json.load(f)
                        
                        # Create progress message
                        current = progress_data.get('current_listing', 0)
                        found = progress_data.get('found_recent', 0)
                        title = progress_data.get('current_title', '')
                        current_page = progress_data.get('current_page', 1)
                        total_pages = progress_data.get('total_pages', 10)
                        city_name = progress_data.get('city_name', '')
                        
                        if language == 'hebrew':
                            progress_msg = f"🔍 בודק מודעה {current}\n📋 {title}\n📄 דף {current_page}/{total_pages}\n✅ נמצאו: {found} מודעות מהיום"
                        else:
                            progress_msg = f"🔍 Checking listing {current}\n📋 {title}\n📄 Page {current_page}/{total_pages}\n✅ Found: {found} recent listings"
                        
                        full_message = f"{selection_info}\n\n{progress_msg}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור את הסריקה" if language == 'hebrew' else f"{selection_info}\n\n{progress_msg}\n\n⏹️ Click cancel button to stop scraping"
                        
                        # Update only if message changed
                        if progress_msg != last_message:
                            await status_message.edit_text(full_message, reply_markup=keyboard)
                            logger.info(f"[ProgressMonitor] Updated scraper progress: {progress_msg}")
                            last_message = progress_msg
                    
                    else:
                        # Show generic progress if no file yet
                        if attempt < 10:
                            generic_msg = "🔍 סורק מודעות..." if language == 'hebrew' else "🔍 Scanning listings..."
                            if generic_msg != last_message:
                                full_message = f"{selection_info}\n\n{generic_msg}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור את הסריקה" if language == 'hebrew' else f"{selection_info}\n\n{generic_msg}\n\n⏹️ Click cancel button to stop scraping"
                                await status_message.edit_text(full_message, reply_markup=keyboard)
                                logger.info(f"[ProgressMonitor] Updated scraper progress: {generic_msg}")
                                last_message = generic_msg
                
                except Exception as e:
                    logger.debug(f"[ProgressMonitor] Error reading progress file: {e}")
                
                # Check if CSV file was created (indicates scraper completed data collection)
                try:
                    from datetime import datetime
                    today = datetime.now().strftime('%Y-%m-%d')
                    csv_pattern = f"/root/yad2bot/yad2bot_package/war_yad2bot/data/*{today}*.csv"
                    all_csv_files = glob.glob(csv_pattern)
                    csv_files = [f for f in all_csv_files if '_progress' not in f and '_checking_progress' not in f and '_with_phones' not in f]
                    
                    # If CSV exists and we have progress files, scraper completed
                    if csv_files and progress_files:
                        logger.info(f"[ProgressMonitor] CSV file detected, scraper completed data collection, exiting monitoring")
                        break
                except:
                    pass
                
                await asyncio.sleep(3)  # Check every 3 seconds
                
                # Reset attempt counter if we got new progress (to avoid timeout during active scraping)
                if progress_files and attempt > 60:  # After 3 minutes, reset if still getting updates
                    attempt = 60  # Reset to give more time
            
            logger.info(f"[ProgressMonitor] Scraper progress monitoring completed for user {user_id}")
            
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error in scraper progress monitoring: {e}")
    
    async def monitor_phone_extraction_progress(self, status_message, language: str, user_id: int, selection_info: str = ""):
        """Monitor phone extraction with real-time JSON progress reading."""
        try:
            logger.info(f"[ProgressMonitor] Starting phone extraction progress monitoring for user {user_id}")
            
            # Create cancel keyboard
            keyboard = self.create_cancel_keyboard(language)
            
            # Find progress file pattern
            today = datetime.now().strftime('%Y-%m-%d')
            progress_pattern = f"/root/yad2bot/yad2bot_package/war_yad2bot/data/*{today}*_progress.json"
            
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
                
                # Look for progress files
                progress_files = glob.glob(progress_pattern)
                
                if progress_files and not progress_file_found:
                    progress_file_found = True
                    logger.info(f"[ProgressMonitor] Progress file found: {progress_files[0]}")
                
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
                            progress_text = f"{selection_info}\n\n📱 מחלץ מספרי טלפון...\n\n📊 התקדמות: {percent:.1f}% ({current}/{total})\n📞 נמצאו: {phones_found} מספרים\n⏱️ זמן נותר: {time_str}\n\n⏹️ לחץ על כפתור הביטול כדי לעצור"
                        else:
                            progress_text = f"{selection_info}\n\n📱 Extracting phone numbers...\n\n📊 Progress: {percent:.1f}% ({current}/{total})\n📞 Found: {phones_found} numbers\n⏱️ Time remaining: {time_str}\n\n⏹️ Click cancel button to stop"
                        
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
                            
                    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                        logger.warning(f"[ProgressMonitor] Error reading progress file: {e}")
                        # Continue with fallback animation
                        
                else:
                    # No progress file yet, show loading animation
                    progress_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
                    char_index = (wait_time // 2) % len(progress_chars)
                    
                    if language == 'hebrew':
                        progress_text = f"{selection_info}\n\n📱 {progress_chars[char_index]} מחלץ מספרי טלפון...\n\n⏱️ מתחיל עיבוד...\n\n⏹️ לחץ על כפתור הביטול כדי לעצור"
                    else:
                        progress_text = f"{selection_info}\n\n📱 {progress_chars[char_index]} Extracting phone numbers...\n\n⏱️ Starting processing...\n\n⏹️ Click cancel button to stop"
                    
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
                
                await asyncio.sleep(3)  # Check every 3 seconds
                wait_time += 3
            
            if self.cancel_flag:
                logger.info(f"[ProgressMonitor] Phone extraction monitoring cancelled by user {user_id}")
                return "cancelled"
            
            logger.info(f"[ProgressMonitor] Phone extraction monitoring completed for user {user_id}")
            return "completed"
            
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error in phone extraction progress monitoring: {e}")
            return f"error: {str(e)}"
    
    async def wait_for_results_file(self, user_id: int, timeout: int = 300):
        """Wait for the final results CSV file to be created."""
        try:
            logger.info(f"[ProgressMonitor] Waiting for results file for user {user_id}")
            
            today = datetime.now().strftime('%Y-%m-%d')
            csv_pattern = f"/root/yad2bot/yad2bot_package/war_yad2bot/data/*{today}*_with_phones.csv"
            
            wait_time = 0
            while wait_time < timeout and not self.cancel_flag:
                csv_files = glob.glob(csv_pattern)
                if csv_files:
                    latest_csv = max(csv_files, key=os.path.getctime)
                    logger.info(f"[ProgressMonitor] Results file found: {latest_csv}")
                    return latest_csv
                
                await asyncio.sleep(2)
                wait_time += 2
            
            if self.cancel_flag:
                logger.info(f"[ProgressMonitor] Results file wait cancelled for user {user_id}")
                return None
            
            logger.warning(f"[ProgressMonitor] Timeout waiting for results file for user {user_id}")
            return None
        
        except Exception as e:
            logger.error(f"[ProgressMonitor] Error waiting for results file: {e}")
            return None
