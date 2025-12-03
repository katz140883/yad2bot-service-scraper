"""
WhatsApp manager module for Yad2bot
Handles all WhatsApp operations with advanced anti-blocking mechanisms
"""
import logging
import aiohttp
import asyncio
import os
import random
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db
from whatsapp_rate_limiter import WhatsAppRateLimiter
from adaptive_backoff import AdaptiveBackoff
from blocking_detector import detect_blocking_indicators
import whatsapp_single_number
from database_sent_messages import SentMessagesTracker

logger = logging.getLogger(__name__)

class WhatsAppManager:
    """Manages WhatsApp operations with advanced anti-blocking protection"""
    
    def __init__(self):
        self.api_base_url = 'https://yad2bot.co.il/api/v1'
        self.default_message = os.getenv('DEFAULT_WHATSAPP_MESSAGE', 'היי! מצאתי את המודעה שלך ביד2. אשמח לקבל פרטים נוספים.')
        self.default_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJ5VHdwOFEzSVMxaHcwTUVUS2RyVjhmaUE0aGdYUDd3YiIsInJvbGUiOiJ1c2VyIiwiaWF0IjoxNzYwOTc0MjYwfQ.O7-9TyXcuFBNbK1fCKX6Y6oUYL3i1rAo_BT3DPWN-nY'
        
        # Cancel flag for stopping message sending
        self.cancel_sending = False
        self.current_user_id = None
        
        # Initialize anti-blocking mechanisms
        self.rate_limiter = WhatsAppRateLimiter(
            messages_per_minute=8,
            messages_per_hour=100
        )
        self.backoff = AdaptiveBackoff(
            base_delay=1.5,
            max_delay=300.0,
            backoff_multiplier=2.0,
            success_threshold=3
        )
        
        # Initialize sent messages tracker
        self.sent_tracker = SentMessagesTracker('/home/ubuntu/yad2bot/yad2bot.db')
        
        # Headers for realistic requests
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'he-IL,he;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
        
        logger.info("WhatsApp Manager initialized with anti-blocking protection")
    
    async def handle_single_number_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle single number sending request"""
        await whatsapp_single_number.handle_single_number_request(self, update, context)
    
    async def handle_single_number_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
        """Handle phone number input for single number sending"""
        await whatsapp_single_number.handle_single_number_input(self, update, context, phone_number)
    
    async def handle_connect_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle WhatsApp connection request"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Set user state to waiting for instance
            db.set_user_waiting_for(user_id, 'whatsapp_instance')
            
            message = "הכנס כאן את קוד החיבור שלך 🔗 כדי להתחיל\nאם עדיין אין לך קוד – לחץ על הכפתור \"קוד חיבור\" כדי ליצור קוד חדש." if language == 'hebrew' else "Enter your connection code here 🔗 to get started\nIf you don't have a code yet – click the \"Connection Code\" button to create a new one."
            
            from telegram import WebAppInfo
            keyboard = []
            
            # Check if user has saved instance code
            saved_instance = db.get_user_whatsapp_instance(user_id)
            if saved_instance:
                # Add button with saved code (show only first 20 chars)
                display_code = saved_instance[:20] + '...' if len(saved_instance) > 20 else saved_instance
                keyboard.append([InlineKeyboardButton(f"✅ {display_code}", callback_data="use_saved_instance")])
            
            # Add regular buttons
            keyboard.extend([
                [InlineKeyboardButton("🔗 קוד חיבור", web_app=WebAppInfo(url='https://yad2bot.co.il/user'))],
                [InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]
            ])
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling connect request: {e}")
    
    async def handle_instance_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, instance_code: str):
        """Handle WhatsApp instance code input"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Validate instance code
            if await self._validate_instance_code(instance_code):
                # Save instance code
                db.set_user_whatsapp_instance(user_id, instance_code)
                
                # Automatically save default token
                db.set_user_whatsapp_token(user_id, self.default_token)
                
                # Clear waiting state
                db.set_user_waiting_for(user_id, None)
                
                # Check if we're in single number flow
                if context.user_data.get('single_number_flow'):
                    # Clear the flag
                    context.user_data.pop('single_number_flow', None)
                    
                    # Continue to single number flow - ask for phone number
                    import whatsapp_single_number
                    await whatsapp_single_number.continue_to_phone_number(update, context, language)
                else:
                    # Regular flow - show available results for sending
                    await self._show_available_results(update, context)
                
            else:
                error_message = "❌ קוד החיבור לא תקין. נסה שוב." if language == 'hebrew' else "❌ Invalid connection code. Try again."
                
                # Check if this is from callback or message
                if update.callback_query:
                    await update.callback_query.answer(error_message, show_alert=True)
                    await self.handle_connect_request(update, context)
                else:
                    await update.message.reply_text(error_message)
                    # Ask for code again
                    await self.handle_connect_request(update, context)
                
        except Exception as e:
            logger.error(f"Error handling instance input: {e}")
            error_message = "❌ שגיאה בשמירת הקוד" if language == 'hebrew' else "❌ Error saving code"
            
            # Check if this is from callback or message
            if update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)
            elif update.message:
                await update.message.reply_text(error_message)
    
    async def handle_token_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, token: str):
        """Handle WhatsApp token input"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Validate token
            if await self._validate_token(token):
                # Save token
                db.set_user_whatsapp_token(user_id, token)
                
                # Clear waiting state
                db.set_user_waiting_for(user_id, None)
                
                success_message = f"✅ הטוקן נשמר בהצלחה!\n\n🎉 וואטסאפ מוכן לשימוש!" if language == 'hebrew' else f"✅ Token saved successfully!\n\n🎉 WhatsApp is ready to use!"
                
                await update.message.reply_text(success_message)
                
                # Show available results for sending
                await self._show_available_results(update, context)
                
            else:
                error_message = "❌ הטוקן לא תקין. נסה שוב." if language == 'hebrew' else "❌ Invalid token. Try again."
                await update.message.reply_text(error_message)
                
        except Exception as e:
            logger.error(f"Error handling token input: {e}")
            error_message = "❌ שגיאה בשמירת הטוקן" if language == 'hebrew' else "❌ Error saving token"
            await update.message.reply_text(error_message)
    
    async def handle_help_request(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle WhatsApp help request"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            help_text = """📱 **איך מפעילים וואטסאפ?**

**שלב 1:** היכנס לאתר yad2bot.co.il/user
**שלב 2:** צור חשבון או התחבר לחשבון הקיים
**שלב 3:** הוסף אינסטנס וואטסאפ חדש
**שלב 4:** העתק את קוד החיבור והטוקן
**שלב 5:** הדבק אותם כאן בבוט

🔗 **קישור:** https://yad2bot.co.il/user

💡 **טיפ:** שמור את הקוד והטוקן במקום בטוח!""" if language == 'hebrew' else """📱 **How to activate WhatsApp?**

**Step 1:** Go to yad2bot.co.il/user
**Step 2:** Create account or login to existing account
**Step 3:** Add new WhatsApp instance
**Step 4:** Copy the connection code and token
**Step 5:** Paste them here in the bot

🔗 **Link:** https://yad2bot.co.il/user

💡 **Tip:** Save the code and token in a safe place!"""
            
            keyboard = [[InlineKeyboardButton("🔙 חזרה", callback_data="whatsapp_menu")]]
            await update.callback_query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling help request: {e}")
    
    async def handle_config_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whatsapp_config command"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Get user's WhatsApp instance
            instance_code = db.get_user_whatsapp_instance(user_id)
            token = db.get_user_whatsapp_token(user_id)
            
            if instance_code and token:
                config_text = f"⚙️ הגדרות וואטסאפ:\n\n🔗 קוד חיבור: {instance_code}\n🔑 טוקן: {token[:10]}...\n📱 סטטוס: מחובר\n\n💡 לשינוי ההגדרות, השתמש בתפריט וואטסאפ." if language == 'hebrew' else f"⚙️ WhatsApp Settings:\n\n🔗 Connection code: {instance_code}\n🔑 Token: {token[:10]}...\n📱 Status: Connected\n\n💡 To change settings, use WhatsApp menu."
            else:
                config_text = "⚙️ הגדרות וואטסאפ:\n\n❌ לא מחובר\n\n💡 השתמש בתפריט וואטסאפ כדי להתחבר." if language == 'hebrew' else "⚙️ WhatsApp Settings:\n\n❌ Not connected\n\n💡 Use WhatsApp menu to connect."
            
            await update.message.reply_text(config_text)
            
        except Exception as e:
            logger.error(f"Error in WhatsApp config command: {e}")
    
    async def send_whatsapp_messages(self, user_id: int, phone_numbers: list, custom_message: str = None) -> dict:
        """Send WhatsApp messages to phone numbers with anti-blocking protection"""
        try:
            # Reset cancel flag for new sending process
            self.reset_cancel_flag(user_id)
            
            instance_code = db.get_user_whatsapp_instance(user_id)
            if not instance_code:
                return {'success': False, 'error': 'No WhatsApp instance configured'}
            
            message = custom_message or self.default_message
            
            # Filter out phone numbers that were already sent
            original_count = len(phone_numbers)
            phone_numbers = self.sent_tracker.filter_unsent_phones(user_id, phone_numbers)
            skipped_count = original_count - len(phone_numbers)
            
            results = {
                'sent': 0, 
                'failed': 0, 
                'errors': [], 
                'blocked': False, 
                'aborted': False, 
                'cancelled': False, 
                'expired_plan': False,
                'skipped_duplicates': skipped_count
            }
            
            if skipped_count > 0:
                logger.info(f"Skipped {skipped_count} phone numbers that were already sent")
            
            if len(phone_numbers) == 0:
                logger.info("All phone numbers were already sent, nothing to send")
                return results
            
            logger.info(f"Starting WhatsApp message sending to {len(phone_numbers)} numbers (after filtering duplicates)")
            
            async with aiohttp.ClientSession(headers=self.headers) as session:
                for i, phone in enumerate(phone_numbers):
                    try:
                        # Check if user cancelled the sending
                        if self.cancel_sending:
                            logger.info("Message sending cancelled by user")
                            results['cancelled'] = True
                            break
                        
                        # Check if we should abort due to too many failures
                        if self.backoff.should_abort():
                            logger.warning("Aborting message sending due to excessive failures")
                            results['aborted'] = True
                            break
                        
                        # Rate limiting check
                        if not self.rate_limiter.can_send_message():
                            wait_time = self.rate_limiter.get_wait_time()
                            if wait_time:
                                logger.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                                await asyncio.sleep(wait_time)
                        
                        # Adaptive backoff delay
                        backoff_delay = self.backoff.get_delay()
                        
                        # Add randomization to base delay (6.0-8.0 seconds)
                        random_delay = random.uniform(6.0, 8.0)
                        total_delay = max(backoff_delay, random_delay)
                        
                        logger.debug(f"Waiting {total_delay:.2f}s before sending to {phone} "
                                   f"(backoff: {backoff_delay:.2f}s, random: {random_delay:.2f}s)")
                        
                        await asyncio.sleep(total_delay)
                        
                        # Format phone number
                        formatted_phone = self._format_phone_number(phone)
                        
                        # Send message with monitoring
                        start_time = time.time()
                        success, response_data = await self._send_single_message_monitored(
                            session, instance_code, formatted_phone, message
                        )
                        response_time = time.time() - start_time
                        
                        # Add response time to data
                        response_data['response_time'] = response_time
                        
                        # Check for blocking indicators
                        blocking_indicators = detect_blocking_indicators(response_data)
                        
                        if success:
                            results['sent'] += 1
                            self.rate_limiter.register_message_sent()
                            self.backoff.register_success()
                            
                            # Mark phone as sent in tracker
                            self.sent_tracker.mark_phone_sent(user_id, phone, message)
                            
                            logger.info(f"✅ Message sent successfully to {phone} ({i+1}/{len(phone_numbers)})")
                        else:
                            results['failed'] += 1
                            
                            # Don't mark failed messages as sent
                            
                            # Check if it's an expired plan error
                            if response_data.get('error_type') == 'expired_plan':
                                results['expired_plan'] = True
                                results['errors'].append(f"Expired plan: {phone}")
                                logger.warning(f"⏰ Expired plan detected for {phone}")
                            else:
                                results['errors'].append(f"Failed to send to {phone}")
                            
                            # Register failure with error info
                            error_info = {
                                'status_code': response_data.get('status_code'),
                                'message': response_data.get('text', ''),
                                'headers': response_data.get('headers', {}),
                                'error_type': response_data.get('error_type')
                            }
                            
                            # Don't count expired plan as consecutive failure for backoff
                            if response_data.get('error_type') != 'expired_plan':
                                self.backoff.register_failure(error_info)
                            
                            logger.warning(f"❌ Failed to send to {phone}: {error_info}")
                        
                        # Handle blocking indicators
                        if blocking_indicators:
                            high_risk_indicators = [ind for ind in blocking_indicators 
                                                  if ind.severity in ['high', 'critical']]
                            
                            if high_risk_indicators:
                                logger.error(f"🚨 High risk blocking indicators detected: {len(high_risk_indicators)}")
                                for indicator in high_risk_indicators:
                                    logger.error(f"  - {indicator.severity.upper()}: {indicator.reason}")
                                
                                results['blocked'] = True
                                
                                # If critical, stop immediately
                                if any(ind.severity == 'critical' for ind in high_risk_indicators):
                                    logger.error("🛑 Critical blocking detected - stopping immediately")
                                    break
                        
                        # Log progress every 10 messages
                        if (i + 1) % 10 == 0:
                            logger.info(f"Progress: {i+1}/{len(phone_numbers)} messages processed")
                        
                    except Exception as e:
                        logger.error(f"Error sending to {phone}: {e}")
                        results['failed'] += 1
                        results['errors'].append(f"Error sending to {phone}: {str(e)}")
                        
                        # Register failure
                        self.backoff.register_failure({'message': str(e)})
            
            # Log final statistics
            success_rate = (results['sent'] / len(phone_numbers)) * 100 if phone_numbers else 0
            logger.info(f"WhatsApp sending completed: {results['sent']}/{len(phone_numbers)} sent ({success_rate:.1f}%)")
            
            # Log backoff and rate limiter stats
            backoff_stats = self.backoff.get_stats()
            rate_stats = self.rate_limiter.get_stats()
            logger.info(f"Backoff stats: {backoff_stats}")
            logger.info(f"Rate limiter stats: {rate_stats}")
            
            # Save activity log
            db.log_activity(user_id, 'whatsapp_send', 
                           f"Sent {results['sent']}, Failed {results['failed']}, "
                           f"Success rate: {success_rate:.1f}%")
            
            return {'success': True, 'results': results}
            
        except Exception as e:
            logger.error(f"Error sending WhatsApp messages: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _validate_instance_code(self, instance_code: str) -> bool:
        """Validate WhatsApp instance code"""
        try:
            # Basic validation - check format
            if not instance_code or len(instance_code) < 10:
                return False
            
            # TODO: Add actual API validation
            # For now, accept any code with reasonable length
            return True
            
        except Exception as e:
            logger.error(f"Error validating instance code: {e}")
            return False
    
    async def _validate_token(self, token: str) -> bool:
        """Validate WhatsApp token"""
        try:
            # Basic validation - check format
            if not token or len(token) < 10:
                return False
            
            # TODO: Add actual API validation
            # For now, accept any token with reasonable length
            return True
            
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False
    
    async def _show_available_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show available results for WhatsApp sending"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Get user's latest results
            results = db.get_user_results(user_id, limit=5)
            
            if not results:
                no_results_message = "❌ אין תוצאות זמינות לשליחה.\n\nבצע סריקה תחילה כדי לקבל מספרי טלפון." if language == 'hebrew' else "❌ No results available for sending.\n\nRun a scan first to get phone numbers."
                
                keyboard = [[InlineKeyboardButton("🔙 חזרה", callback_data="whatsapp_menu")]]
                
                # Check if this is from callback or message
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        no_results_message,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                else:
                    await update.message.reply_text(
                        no_results_message,
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                return
            
            # Show results selection menu
            results_text = "בחר את קבוצת הלידים שאליה יישלחו ההודעות שלך 🚀💬\n\nהשתמש בתאריך ובסוג המודעות (שכירות/מכירה) כדי לזהות את הסריקה הנכונה שביצעת.\n\nאו שלח קובץ CSV/Excel עם מספרי טלפון 📄\n\n" if language == 'hebrew' else "Select the leads group to send your messages to 🚀💬\nUse the date and type to identify the correct scan.\n\nOr send a CSV/Excel file with phone numbers 📄\n\n"
            
            keyboard = []
            for result in results:
                # Map city codes to names
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
                city_text = city_names.get(result.get('city_code'), 'כל הארץ') if result.get('city_code') else 'כל הארץ'
                result_text = f"🏙️ {city_text} | {result['mode']} - {result['filter_type']} | 📞 {result['phone_numbers_count']}"
                keyboard.append([InlineKeyboardButton(result_text, callback_data=f"whatsapp_send_{result['id']}")])
            
            keyboard.append([InlineKeyboardButton("🔙 חזרה", callback_data="whatsapp_menu")])
            
            # Check if this is from callback or message
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    results_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    results_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
        except Exception as e:
            logger.error(f"Error showing available results: {e}")
            error_message = "❌ שגיאה בטעינת התוצאות" if language == 'hebrew' else "❌ Error loading results"
            
            # Check if this is from callback or message
            if update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)
            elif update.message:
                await update.message.reply_text(error_message)
    
    async def _send_single_message_monitored(self, session: aiohttp.ClientSession, 
                                           instance_code: str, phone: str, message: str) -> tuple:
        """Send a single message with monitoring using yad2bot.co.il API"""
        response_data = {
            'status_code': 0,
            'text': '',
            'headers': {},
            'success': False
        }
        
        try:
            # Use default token
            user_token = self.default_token
            
            # Format JID (phone number in WhatsApp format)
            jid = f"{phone}@s.whatsapp.net"
            
            # Build URL with GET parameters
            url = f"{self.api_base_url}/send-text"
            params = {
                'token': user_token,
                'instance_id': instance_code,
                'jid': jid,
                'msg': message
            }
            
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                response_data['status_code'] = response.status
                response_data['headers'] = dict(response.headers)
                
                try:
                    response_text = await response.text()
                    response_data['text'] = response_text
                    
                    if response.status == 200:
                        try:
                            result = await response.json()
                            response_data['json'] = result
                            
                            # Check if API returned success
                            if result.get('success') == True:
                                response_data['success'] = True
                                return True, response_data
                            else:
                                # API returned failure
                                response_data['success'] = False
                                error_msg = result.get('message', 'Unknown error')
                                
                                # Check if it's an expired plan error
                                if 'expired' in error_msg.lower() or 'renew' in error_msg.lower():
                                    response_data['error_type'] = 'expired_plan'
                                    logger.warning(f"API returned expired plan error: {error_msg}")
                                else:
                                    logger.warning(f"API returned failure: {error_msg}")
                                
                                return False, response_data
                                
                        except Exception as json_error:
                            logger.warning(f"Failed to parse JSON response: {json_error}")
                            # If we can't parse JSON but status is 200, consider it a failure
                            response_data['success'] = False
                            return False, response_data
                    else:
                        # HTTP error status
                        response_data['success'] = False
                        logger.warning(f"HTTP error {response.status}: {response_text}")
                        return False, response_data
                        
                except Exception as e:
                    logger.error(f"Error reading response: {e}")
                    response_data['text'] = f"Error reading response: {str(e)}"
                    return False, response_data
                    
        except asyncio.TimeoutError:
            logger.warning(f"Timeout sending message to {phone}")
            response_data['text'] = 'Request timeout'
            return False, response_data
            
        except Exception as e:
            logger.error(f"Error sending message to {phone}: {e}")
            response_data['text'] = str(e)
            return False, response_data
    
    def _format_phone_number(self, phone: str) -> str:
        """Format phone number for WhatsApp API"""
        try:
            # Remove all non-digit characters
            clean_phone = ''.join(filter(str.isdigit, phone))
            
            # Add country code if missing (assume Israel +972)
            if clean_phone.startswith('0'):
                clean_phone = '972' + clean_phone[1:]
            elif not clean_phone.startswith('972'):
                clean_phone = '972' + clean_phone
            
            return clean_phone
            
        except Exception as e:
            logger.error(f"Error formatting phone number {phone}: {e}")
            return phone
    
    def cancel_current_sending(self, user_id: int):
        """Cancel current message sending process"""
        if self.current_user_id == user_id:
            self.cancel_sending = True
            logger.info(f"Message sending cancelled by user {user_id}")
            return True
        return False
    
    def reset_cancel_flag(self, user_id: int):
        """Reset cancel flag for new sending process"""
        self.cancel_sending = False
        self.current_user_id = user_id
        logger.info(f"Cancel flag reset for user {user_id}")

