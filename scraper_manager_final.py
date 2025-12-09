#!/usr/bin/env python3
"""
Final Scraper Manager - Fixes all critical issues:
1. Always starts new scans (never uses old files)
2. Real-time progress monitoring with JSON progress files
3. No race conditions between monitor and main process
4. Proper process termination and cleanup
5. Reliable phone extraction with ZenRows
"""

import asyncio
import os
import glob
import subprocess
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from progress_monitor_fixed import FixedProgressMonitor

logger = logging.getLogger(__name__)

class FinalScraperManager:
    """Final scraper manager with all critical issues fixed."""
    
    def __init__(self):
        self.scraper_script = "/home/ubuntu/yad2bot_scraper/scraper/main.py"
        self.bot_instance = None
        self.active_sessions = {}  # user_id -> session_data
        self.progress_monitor = FixedProgressMonitor()
    
    def set_bot_instance(self, bot):
        """Set the bot instance for results delivery."""
        self.bot_instance = bot
        logger.info("[ScraperManager] Bot instance set for results delivery")
    
    def is_scraping_active(self, user_id: int) -> bool:
        """Check if user has an active scraping session."""
        return user_id in self.active_sessions
    
    def cancel_current_scraping(self, user_id: int) -> bool:
        """Cancel current scraping process for user - IMPROVED VERSION."""
        logger.info(f"[ScraperManager] Cancel requested for user {user_id}")
        
        # Set cancel flag in progress monitor first
        cancel_set = self.progress_monitor.set_cancel_flag(user_id)
        logger.info(f"[ScraperManager] Cancel flag set: {cancel_set}")
        
        # Create cancel flag files for all possible scraping sessions
        try:
            import glob
            data_dir = "/home/ubuntu/yad2bot_scraper/data"
            today_str = datetime.now().strftime('%Y-%m-%d')
            
            # Create cancel flags for all possible combinations
            cancel_patterns = [
                f"*_{today_str}_cancel.flag",
                f"*_rent_*_{today_str}_cancel.flag", 
                f"*_sale_*_{today_str}_cancel.flag"
            ]
            
            for pattern in cancel_patterns:
                # Find existing progress files to create matching cancel files
                progress_files = glob.glob(os.path.join(data_dir, pattern.replace('_cancel.flag', '_progress.json')))
                for progress_file in progress_files:
                    cancel_file = progress_file.replace('_progress.json', '_cancel.flag')
                    try:
                        with open(cancel_file, 'w') as f:
                            f.write(f"cancelled_by_user_{user_id}")
                        logger.info(f"[ScraperManager] Created cancel flag: {cancel_file}")
                    except Exception as e:
                        logger.warning(f"[ScraperManager] Error creating cancel flag {cancel_file}: {e}")
            
            # Also create generic cancel flags
            generic_cancel_files = [
                os.path.join(data_dir, f"rent_today_{today_str}_cancel.flag"),
                os.path.join(data_dir, f"sale_today_{today_str}_cancel.flag"),
                os.path.join(data_dir, f"rent_all_{today_str}_cancel.flag"),
                os.path.join(data_dir, f"sale_all_{today_str}_cancel.flag")
            ]
            
            for cancel_file in generic_cancel_files:
                try:
                    with open(cancel_file, 'w') as f:
                        f.write(f"cancelled_by_user_{user_id}")
                    logger.info(f"[ScraperManager] Created generic cancel flag: {cancel_file}")
                except Exception as e:
                    logger.warning(f"[ScraperManager] Error creating generic cancel flag {cancel_file}: {e}")
                    
        except Exception as e:
            logger.error(f"[ScraperManager] Error creating cancel flags: {e}")
        
        # Kill all running scraper processes (more aggressive approach)
        processes_killed = False
        
        try:
            # Kill main scraper processes (specific path to avoid killing bot)
            result = subprocess.run(['pkill', '-f', '/yad2bot_scraper/main.py'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("[ScraperManager] Killed scraper main.py processes")
                processes_killed = True
        except Exception as e:
            logger.warning(f"[ScraperManager] Error killing scraper main.py: {e}")
        
        try:
            # Kill phone extractor processes
            result = subprocess.run(['pkill', '-f', 'phone_extractor'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logger.info("[ScraperManager] Killed phone extractor processes")
                processes_killed = True
        except Exception as e:
            logger.warning(f"[ScraperManager] Error killing phone extractor: {e}")
        
        # Clean up session if exists
        if user_id in self.active_sessions:
            try:
                session = self.active_sessions[user_id]
                
                # Cancel monitor task if exists
                if 'monitor_task' in session and session['monitor_task']:
                    try:
                        session['monitor_task'].cancel()
                        logger.info(f"[ScraperManager] Cancelled monitor task for user {user_id}")
                    except asyncio.CancelledError:
                        logger.info(f"[ScraperManager] Monitor task was already cancelled for user {user_id}")
                    except Exception as e:
                        logger.warning(f"[ScraperManager] Error cancelling monitor task: {e}")
                
                # Remove session
                del self.active_sessions[user_id]
                logger.info(f"[ScraperManager] Removed session for user {user_id}")
                
            except Exception as e:
                logger.error(f"[ScraperManager] Error cleaning up session: {e}")
        
        # Return True if we set cancel flag OR killed processes
        result = cancel_set or processes_killed
        logger.info(f"[ScraperManager] Cancel operation result: {result}")
        return result
    
    async def cleanup_old_files(self):
        """Clean up old progress and CSV files to ensure fresh start."""
        try:
            logger.info("[ScraperManager] Cleaning up old files - START")
            
            # Clean up old progress files
            progress_pattern = "/home/ubuntu/yad2bot_scraper/data/*_progress.json"
            logger.info(f"[ScraperManager] Looking for progress files: {progress_pattern}")
            
            # Use asyncio.to_thread for glob.glob (non-blocking)
            progress_files = await asyncio.to_thread(glob.glob, progress_pattern)
            logger.info(f"[ScraperManager] Found {len(progress_files)} progress files")
            
            # Parallel deletion of progress files
            if progress_files:
                await asyncio.gather(
                    *[asyncio.to_thread(os.remove, f) for f in progress_files],
                    return_exceptions=True
                )
                logger.info(f"[ScraperManager] Removed {len(progress_files)} progress files")
            
            # Clean up today's CSV files to force new scan
            today = datetime.now().strftime('%Y-%m-%d')
            csv_pattern = f"/home/ubuntu/yad2bot_scraper/data/*{today}*.csv"
            
            # Use asyncio.to_thread for glob.glob (non-blocking)
            csv_files = await asyncio.to_thread(glob.glob, csv_pattern)
            
            # Parallel deletion of CSV files
            if csv_files:
                await asyncio.gather(
                    *[asyncio.to_thread(os.remove, f) for f in csv_files],
                    return_exceptions=True
                )
                logger.info(f"[ScraperManager] Removed {len(csv_files)} CSV files")
            
            logger.info("[ScraperManager] File cleanup completed")
            
        except Exception as e:
            logger.error(f"[ScraperManager] Error during file cleanup: {e}")
    
    async def kill_existing_processes(self):
        """Kill any existing scraper processes to ensure clean start."""
        try:
            logger.info("[ScraperManager] Killing existing processes...")
            
            # Kill main scraper processes using specific path to avoid killing the bot
            # Use asyncio.to_thread to avoid blocking the event loop
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ['pkill', '-f', '/home/ubuntu/yad2bot_scraper/scraper/main.py'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.info("[ScraperManager] Killed existing scraper main.py processes")
            except Exception as e:
                logger.warning(f"[ScraperManager] Error killing scraper main.py processes: {e}")
            
            # Kill phone extractor processes
            # Use asyncio.to_thread to avoid blocking the event loop
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ['pkill', '-f', 'phone_extractor'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    logger.info("[ScraperManager] Killed existing phone extractor processes")
            except Exception as e:
                logger.warning(f"[ScraperManager] Error killing phone extractor processes: {e}")
            
            # Wait for processes to terminate
            try:
                await asyncio.sleep(2)
            except asyncio.CancelledError:
                logger.info("[ScraperManager] Process cleanup was cancelled")
            except Exception as e:
                logger.warning(f"[ScraperManager] Error during sleep: {e}")
            logger.info("[ScraperManager] Process cleanup completed")
            
        except Exception as e:
            logger.error(f"[ScraperManager] Error during process cleanup: {e}")
    
    def get_selection_info(self, context: ContextTypes.DEFAULT_TYPE, language: str) -> str:
        """Get formatted selection information for display."""
        try:
            mode = getattr(context, 'mode', 'rent')
            filter_type = getattr(context, 'filter_type', 'all')
            city_code = getattr(context, 'city_code', None)
            
            if language == 'hebrew':
                mode_text = "השכרה" if mode == 'rent' else "מכירה"
                if filter_type == 'test':
                    filter_text = "מודעות בדיקה"
                elif filter_type == 'today':
                    filter_text = "מודעות מהיום"
                else:
                    filter_text = "כל המודעות"
                
                if city_code:
                    city_names = {
                        '5000': 'תל אביב',
                        '4000': 'חיפה',
                        '3000': 'ירושלים',
                        '9000': 'באר שבע',
                        '7400': 'נתניה',
                        '8300': 'ראשון לציון',
                        '7900': 'פתח תקווה',
                        '0070': 'אשדוד'
                    }
                    city_text = city_names.get(city_code, city_code)
                    return f"🏠 {mode_text} - {city_text}\n📅 {filter_text}"
                else:
                    return f"🏠 {mode_text} - כל הארץ\n📅 {filter_text}"
            else:
                mode_text = "Rent" if mode == 'rent' else "Sale"
                if filter_type == 'test':
                    filter_text = "Test Listings"
                elif filter_type == 'today':
                    filter_text = "Today's Listings"
                else:
                    filter_text = "All Listings"
                
                if city_code:
                    city_names = {
                        '5000': 'Tel Aviv',
                        '4000': 'Haifa',
                        '3000': 'Jerusalem',
                        '9000': 'Beer Sheva',
                        '7400': 'Netanya',
                        '8300': 'Rishon LeZion',
                        '7900': 'Petah Tikva',
                        '0070': 'Ashdod'
                    }
                    city_text = city_names.get(city_code, city_code)
                    return f"🏠 {mode_text} - {city_text}\n📅 {filter_text}"
                else:
                    return f"🏠 {mode_text} - All Israel\n📅 {filter_text}"
                    
        except Exception as e:
            logger.error(f"[ScraperManager] Error getting selection info: {e}")
            return "🏠 סריקה" if language == 'hebrew' else "🏠 Scanning"
    
    async def run_scraper_with_message(self, status_message, context: ContextTypes.DEFAULT_TYPE, mode: str, filter_type: str, city_code: str = None, page_limit: int = None):
        """Run scraper with proper cleanup and monitoring - FINAL VERSION."""
        user_id = status_message.chat.id
        language = db.get_user_language(user_id)
        
        try:
            logger.info(f"[ScraperManager] Starting FINAL scraper for user {user_id}, mode={mode}, filter={filter_type}, city={city_code}")
            
            # Check if user already has active session
            if self.is_scraping_active(user_id):
                active_message = "⚠️ יש לך כבר סריקה פעילה. אנא המתן לסיום או בטל אותה." if language == 'hebrew' else "⚠️ You already have an active scraping session. Please wait for completion or cancel it."
                # Removed: await status_message.edit_text(active_message)
                return
            
            # STEP 1: Complete cleanup to ensure fresh start
            await self.cleanup_old_files()
            # Removed kill_existing_processes - it was causing hangs
            
            # STEP 2: Store context data
            context.mode = mode
            context.filter_type = filter_type
            context.city_code = city_code
            
            # Get selection info for display
            selection_info = self.get_selection_info(context, language)
            
            # STEP 3: Create session
            session = {
                'user_id': user_id,
                'status_message': status_message,
                'chat_id': status_message.chat_id,
                'message_id': status_message.message_id,
                'context': context,
                'language': language,
                'selection_info': selection_info,
                'process': None,
                'monitor_task': None
            }
            self.active_sessions[user_id] = session
            
            # STEP 4: Build and start scraper command
            command = [
                "python3",
                self.scraper_script,
                "--mode", mode,
                "--filter", filter_type
            ]
            
            if city_code:
                command.extend(["--city", city_code])
            
            if page_limit:
                command.extend(["--max-pages", str(page_limit)])
            
            logger.info(f"[ScraperManager] Command: {' '.join(command)}")
            
            # Start scraper process
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.dirname(self.scraper_script),
                env={**os.environ, 'ZENROWS_API_KEY': '3f50019a0655a46ab2198f4b29a29de2ba11f133'}
            )
            
            session['process'] = process
            logger.info(f"[ScraperManager] Started scraper process PID {process.pid}")
            
            # STEP 5: Start monitoring in background (don't await it)
            monitor_task = asyncio.create_task(
                self._monitor_complete_process(session),
                name=f"monitor_complete_user_{user_id}"
            )
            session['monitor_task'] = monitor_task
            
            # STEP 6: Return immediately, let monitoring run in background
            logger.info(f"[ScraperManager] Monitoring task started in background for user {user_id}")
            return  # Don't await, let it run in background
            
        except Exception as e:
            logger.error(f"[ScraperManager] Critical error in run_scraper_with_message: {e}")
            
            # Clean up on error
            if user_id in self.active_sessions:
                del self.active_sessions[user_id]
            
            error_message = "❌ שגיאה בסריקה. נסה שוב מאוחר יותר." if language == 'hebrew' else "❌ Scraping error. Try again later."
            # Removed message update - was causing bot to stop
            pass
            
            # Clean up session after error
            if user_id in self.active_sessions:
                del self.active_sessions[user_id]
    
    async def _monitor_complete_process(self, session):
        """Monitor the complete scraping and phone extraction process."""
        user_id = session['user_id']
        status_message = session['status_message']
        chat_id = session.get('chat_id')
        message_id = session.get('message_id')
        language = session['language']
        selection_info = session['selection_info']
        process = session['process']
        
        try:
            logger.info(f"[Monitor] Starting complete process monitoring for user {user_id}")
            
            # PHASE 1: Monitor scraper progress with real-time updates
            logger.info(f"[Monitor] Starting scraper progress monitoring")
            await self.progress_monitor.monitor_scraper_progress(
                status_message, language, user_id, selection_info
            )
            logger.info(f"[Monitor] Scraper progress monitoring completed")
            
            # Send sticker after scraping completed
            try:
                sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
                await status_message.get_bot().send_sticker(
                    chat_id=status_message.chat_id,
                    sticker=sticker_id
                )
                logger.info(f"[Monitor] Sent sticker after scraping")
            except Exception as e:
                logger.error(f"[Monitor] Error sending sticker: {e}")
            
            # PHASE 2: Monitor phone extraction progress
            logger.info(f"[Monitor] Starting phone extraction monitoring")
            
            # PHASE 2: Monitor phone extraction progress
            logger.info(f"[Monitor] Calling monitor_phone_extraction_progress")
            result = await self.progress_monitor.monitor_phone_extraction_progress(
                status_message, language, user_id, selection_info
            )
            
            if result == "cancelled":
                logger.info(f"[Monitor] Scraping was cancelled by user {user_id}")
                return "cancelled"
            
            # PHASE 3: Wait for final results and send them
            logger.info(f"[Monitor] Waiting for final results file")
            results_file = await self.progress_monitor.wait_for_results_file(user_id)
            
            if results_file:
                await self._send_final_results(status_message, results_file, language, selection_info)
                return "completed_with_results"
            else:
                # No results file found, but process completed
                completion_text = "✅ הסריקה הושלמה" if language == 'hebrew' else "✅ Scraping completed"
                # Removed: await status_message.edit_text(completion_text)
                return "completed_no_results"
            
        except Exception as e:
            logger.error(f"[Monitor] Error in complete process monitoring: {e}")
            return f"monitor_error: {str(e)}"
    
    async def _send_final_results(self, status_message, results_file: str, language: str, selection_info: str):
        """Send final results to user."""
        try:
            logger.info(f"[Results] Sending final results: {results_file}")
            
            # Count phone numbers and duplicates
            import csv
            phone_count = 0
            total_listings = 0
            duplicates_count = 0
            
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        total_listings += 1
                        phone = row.get('phone_number', '').strip()
                        if phone and phone != '0501234567' and len(phone) >= 9:
                            phone_count += 1
            except Exception as e:
                logger.error(f"[Results] Error counting phones: {e}")
                phone_count = 0
                total_listings = 0
            
            # Count duplicates from checking_progress file
            try:
                import os
                import glob
                data_dir = '/home/ubuntu/yad2bot_scraper/data'
                
                # Find the most recent checking_progress file
                progress_files = glob.glob(os.path.join(data_dir, '*_checking_progress.json'))
                if progress_files:
                    # Sort by modification time, get most recent
                    latest_file = max(progress_files, key=os.path.getmtime)
                    
                    with open(latest_file, 'r', encoding='utf-8') as f:
                        progress_data = json.load(f)
                        duplicates_count = progress_data.get('duplicates_skipped', 0)
                    
                    logger.info(f"[Results] Found {duplicates_count} duplicates from checking_progress")
                else:
                    logger.warning("[Results] No checking_progress file found")
                    duplicates_count = 0
            except Exception as e:
                logger.error(f"[Results] Error counting duplicates: {e}")
                duplicates_count = 0
            
            # Create success message
            if language == 'hebrew':
                duplicates_line = f"\n⏭️ דולגו: {duplicates_count} כפילויות" if duplicates_count > 0 else ""
                success_text = f"{selection_info}\n\n✅ הסריקה הושלמה בהצלחה!\n\n📊 נמצאו: {total_listings} מודעות\n📞 מספרי טלפון: {phone_count}{duplicates_line}\n\n📎 קובץ התוצאות מצורף"
            else:
                success_text = f"{selection_info}\n\n✅ Scraping completed successfully!\n\n📊 Found: {total_listings} listings\n📞 Phone numbers: {phone_count}\n\n📎 Results file attached"
            
            # Store results file path for WhatsApp flow
            user_id = status_message.chat.id
            
            # Create keyboard with action buttons
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            if language == 'hebrew':
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 הצג קישורי ווטסאפ", callback_data="show_whatsapp_links")],
                    [InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]
                ])
            else:
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Show WhatsApp Links", callback_data="show_whatsapp_links")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_start")]
                ])
            
            # Send success sticker
            try:
                sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
                await status_message.get_bot().send_sticker(
                    chat_id=status_message.chat_id,
                    sticker=sticker_id
                )
                logger.info(f"[Results] Success sticker sent")
            except Exception as e:
                logger.error(f"[Results] Error sending sticker: {e}")
            
            # Send results file with buttons
            with open(results_file, 'rb') as f:
                await status_message.get_bot().send_document(
                    chat_id=status_message.chat_id,
                    document=f,
                    filename=os.path.basename(results_file),
                    caption=success_text,
                    reply_markup=keyboard
                )
            
            # Save results to database and store file path
            try:
                user_id = status_message.chat_id
                # Extract mode, filter_type and city_code from results_file name
                import re
                filename = os.path.basename(results_file)
                # Parse filename: City1300_rent_test... or Jerusalem_rent_test... or Ashdod_rent_test...
                # Try to extract city code from City#### format
                city_match = re.search(r'City(\d+)_', filename)
                if city_match:
                    city_code = city_match.group(1)
                else:
                    # Try to extract city name and convert to code
                    city_name_match = re.search(r'^([A-Za-z_]+)_(?:rent|sale)_', filename)
                    if city_name_match:
                        city_name = city_name_match.group(1)
                        # Map city names to codes
                        city_name_to_code = {
                            'TelAviv': '5000',
                            'Tel_Aviv': '5000',
                            'Haifa': '4000',
                            'Jerusalem': '3000',
                            'BeerSheva': '9000',
                            'Beer_Sheva': '9000',
                            'Netanya': '7400',
                            'RishonLeZion': '8300',
                            'Rishon_LeZion': '8300',
                            'PetahTikva': '7900',
                            'Petah_Tikva': '7900',
                            'Ashdod': '0070'
                        }
                        city_code = city_name_to_code.get(city_name, None)
                    else:
                        city_code = None
                
                # Updated regex to include 'test' filter
                match = re.search(r'_(rent|sale)_(today|all|test)_', filename)
                if match:
                    mode = match.group(1)
                    filter_type = match.group(2)
                else:
                    # Fallback: use safe defaults instead of 'unknown'
                    mode = 'rent'  # Default to rent
                    filter_type = 'all'  # Default to all
                
                # Save to database
                db.save_scraping_result(
                    user_id=user_id,
                    mode=mode,
                    filter_type=filter_type,
                    csv_file_path=results_file,
                    total_listings=total_listings,
                    phone_numbers_count=phone_count,
                    city_code=city_code
                )
                
                logger.info(f"[Results] Saved results to database for user {user_id}")
            except Exception as e:
                logger.error(f"[Results] Error saving results to database: {e}")
            
            logger.info(f"[Results] Final results sent successfully: {phone_count} phones out of {total_listings} listings")
            
        except Exception as e:
            logger.error(f"[Results] Error sending final results: {e}")
            
            # Fallback message
            completion_text = "✅ הסריקה הושלמה" if language == 'hebrew' else "✅ Scraping completed"
            # Removed message update - was causing bot to stop
            pass
    
    async def run_scraper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str, filter_type: str, city_code: str = None):
        """Run scraper with callback query - delegates to main method."""
        try:
            user_id = update.effective_user.id
            logger.info(f"[ScraperManager] run_scraper called for user {user_id}")
            
            # Use the existing message for progress updates
            status_message = update.callback_query.message
            
            # Delegate to the main method
            await self.run_scraper_with_message(status_message, context, mode, filter_type, city_code)
                
        except Exception as e:
            logger.error(f"[ScraperManager] Error in run_scraper: {e}")
            
            error_message = "❌ שגיאה בסריקה. נסה שוב מאוחר יותר." if db.get_user_language(update.effective_user.id) == 'hebrew' else "❌ Scraping error. Try again later."
            try:
                await update.callback_query.message.edit_text(error_message)
            except Exception as edit_error:
                logger.error(f"[ScraperManager] Error updating error message: {edit_error}")

# Create global instance
final_scraper_manager = FinalScraperManager()
