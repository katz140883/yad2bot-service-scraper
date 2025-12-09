"""
Bot handlers module for Yad2bot
Contains all command and callback handlers
"""
import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
from telegram.error import BadRequest, Forbidden, TelegramError
from telegram.ext import ContextTypes
from database import db
from bot_menus import MenuManager
from scraper_manager_final import final_scraper_manager
# Removed: whatsapp_manager and bonus_manager

logger = logging.getLogger(__name__)

# --- Whitelist: Only authorized users can use the bot ---
ALLOWED_USER_IDS = [7238791533]  # Add your Telegram ID here

def is_user_authorized(user_id: int) -> bool:
    """Check if user is in the whitelist"""
    return user_id in ALLOWED_USER_IDS

# --- Channel join gate (simple version) ---

CHANNEL_ID = "@yad2credits"  # Username של הקבוצה
CHANNEL_INVITE_URL = "https://t.me/yad2credits"

async def check_channel_membership(context, user_id: int) -> bool:
    """Check if user is a member of the required channel"""
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

class BotHandlers:
    def __init__(self):
        self.menu_manager = MenuManager()
        self.scraper_manager = final_scraper_manager  # Use the global final scraper manager
        # Removed: self.whatsapp_manager = WhatsAppManager()
    
    def set_bot_instance(self, bot):
        """Set the bot instance for all managers"""
        self.scraper_manager.set_bot_instance(bot)
        # Add other managers if they need bot instance
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        try:
            user_id = update.effective_user.id
            user_name = update.effective_user.first_name or "משתמש"
            
            # Check whitelist
            if not is_user_authorized(user_id):
                await update.message.reply_text(
                    "⛔ אין לך הרשאה להשתמש בבוט זה.\n\n"
                    f"🆔 Telegram ID שלך: {user_id}"
                )
                logger.warning(f"Unauthorized access attempt by user {user_id} ({user_name})")
                return
            
            # Initialize user in database
            db.add_user(user_id, user_name)
            
            # Send welcome GIF with keyboard (no caption)
            keyboard = [
                [
                    InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data='schedule_menu'),
                    InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data='scraper_menu')
                ],
                [
                    InlineKeyboardButton("ℹ️", callback_data='show_info')
                ]
            ]
            
            # Use file_id for instant sending (no upload needed)
            await context.bot.send_animation(
                chat_id=update.message.chat_id,
                animation="CgACAgQAAxkDAAICYGk3beqnCTNllztcH0o5JArgO_RXAAIHHwACOya5UQ9R2fn6D5JRNgQ",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"Start command processed for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("שגיאה בהפעלת הבוט. נסה שוב.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all button callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            
            # Check whitelist
            if not is_user_authorized(user_id):
                await query.edit_message_text("⛔ אין לך הרשאה להשתמש בבוט זה.")
                return
            
            callback_data = query.data
            language = db.get_user_language(user_id)
            
            logger.info(f"Button callback: {callback_data} from user {user_id}")
            
            # Route to appropriate handler
            if callback_data == 'back_to_main' or callback_data == 'back_to_start':
                await self._handle_back_to_main(update, context)
            
            elif callback_data == 'show_main_menu':
                await self._handle_show_main_menu(update, context)
            
            elif callback_data == 'show_info':
                await self._handle_show_info(update, context)
            
            elif callback_data == 'scraper_menu':
                await self._handle_scraper_menu(update, context)
            
            elif callback_data == 'schedule_menu':
                await self._handle_schedule_menu(update, context)
            
            elif callback_data == 'run_scraper':
                await self._handle_scraper_menu(update, context)
            
            elif callback_data == 'scraper_rent':
                await self.menu_manager.send_scraper_rent_menu(update, context)
            
            elif callback_data == 'scraper_sale':
                await self.menu_manager.send_scraper_sale_menu(update, context)
            
            # Removed: whatsapp_menu callback
            
            elif callback_data == 'auto_menu':
                await self._handle_auto_menu(update, context)
            
            elif callback_data == 'rent_to_sale_agent':
                await self._handle_rent_to_sale_agent(update, context)
            
            elif callback_data == 'contact_menu':
                await self._handle_contact_menu(update, context)
            
            elif callback_data == 'language_menu':
                await self._handle_language_menu(update, context)
            
            elif callback_data == 'agents_menu':
                await self._handle_agents_menu(update, context)
            
            elif callback_data == 'my_account':
                await self._handle_my_account(update, context)
            
            elif callback_data == 'claim_test':
                await self._handle_claim_test(update, context)
            
            # Removed: bonus_manager callbacks (claim_signup_test, claim_daily_test, daily_test_offer)
            
            elif callback_data == 'timer_waiting':
                # Timer button - just answer without action
                await update.callback_query.answer("הטיימר מתעדכן אוטומטית כל דקה")
                return
            
            elif callback_data == 'activity_history':
                await self._handle_activity_history(update, context)
            
            elif callback_data == 'buy_credits':
                await self._handle_buy_credits(update, context)
            
            # Removed: bonus_manager callback (invite_friends)
            
            elif callback_data == 'share_referral':
                await self._handle_share_referral(update, context)
            
            elif callback_data in ['rent_sale_agent', 'real_estate_agent', 'advertising_agent', 'general_agent']:
                await self._handle_agent_selection(update, context, callback_data)
            
            elif callback_data == 'results_menu':
                await self._handle_results_menu(update, context, language)
            
            elif callback_data.startswith('lang_'):
                await self._handle_language_selection(update, context, callback_data)
            
            elif callback_data.startswith('scrape_'):
                await self._handle_scraper_action(update, context, callback_data)
            
            elif callback_data.startswith('city_selection_'):
                await self._handle_city_selection_menu(update, context, callback_data)
            
            elif callback_data.startswith('city_'):
                await self._handle_city_selection(update, context, callback_data)
            
            elif callback_data.startswith('cancel_scraping_'):
                await self._handle_cancel_scraping(update, context, callback_data)
                return  # Important: return immediately after handling cancel
            
            elif callback_data == 'schedule_new':
                await self._handle_schedule_new(update, context)
            
            elif callback_data == 'schedule_cancel':
                await self._handle_schedule_cancel(update, context)
            
            elif callback_data.startswith('schedule_hour_'):
                await self._handle_schedule_hour_selected(update, context, callback_data)
            
            elif callback_data.startswith('schedule_'):
                await self._handle_schedule_action(update, context, callback_data)
            
            elif callback_data in ['show_current_schedule', 'cancel_schedule']:
                await self._handle_schedule_management(update, context, callback_data, language)
            
            elif callback_data == 'rent_to_sale_use_saved_code':
                await self._handle_rent_to_sale_code_selected(update, context)
            
            elif callback_data.startswith('rent_to_sale_day_'):
                await self._handle_rent_to_sale_day_selected(update, context, callback_data)
            
            elif callback_data.startswith('rent_to_sale_timing_'):
                await self._handle_rent_to_sale_timing_selected(update, context, callback_data)
            
            elif callback_data.startswith('rent_to_sale_hour_'):
                await self._handle_rent_to_sale_hour_selected(update, context, callback_data)
            
            elif callback_data in ['whatsapp_connect', 'whatsapp_help', 'whatsapp_back', 'whatsapp_help_menu', 'whatsapp_warmer', 'whatsapp_single_number']:
                await self._handle_whatsapp_action(update, context, callback_data)
            
            elif callback_data == 'view_sent_numbers':
                await self._handle_view_sent_numbers(update, context)
            
            elif callback_data == 'reset_sent_numbers':
                await self._handle_reset_sent_numbers(update, context)
            
            elif callback_data == 'see_results':
                await self._handle_see_results(update, context, language)
            
            elif callback_data == 'show_whatsapp_links':
                await self._handle_show_whatsapp_links(update, context)
            
            elif callback_data == 'calculator_menu':
                await self._handle_calculator_menu(update, context)
            
            elif callback_data == 'signature_menu':
                await self._handle_signature_menu(update, context)
            
            elif callback_data.startswith('show_whatsapp_'):
                await self._handle_show_whatsapp_from_scraper(update, context, callback_data)
            
            elif callback_data == 'see_scraper_results':
                await self._handle_see_results(update, context, language)
            
            elif callback_data == 'see_whatsapp_results':
                await self._handle_see_whatsapp_results(update, context, language)
            
            elif callback_data in ['schedule_time', 'enable_auto', 'set_scrape_hour', 'set_whatsapp_hour']:
                await self._handle_time_selection(update, context, callback_data)
            
            elif callback_data.startswith('hour_'):
                await self._handle_hour_selection(update, context)
            
            elif callback_data.startswith('minute_'):
                await self._handle_minute_selection(update, context)
            
            elif callback_data == 'cancel_time':
                await self._handle_cancel_time(update, context)
            
            elif callback_data.startswith('whatsapp_send_'):
                await self._handle_whatsapp_send_selection(update, context, callback_data, language)
            
            elif callback_data.startswith('confirm_send_'):
                await self._handle_confirm_send(update, context, callback_data)
            
            elif callback_data.startswith('cancel_sending_'):
                await self._handle_cancel_sending(update, context, callback_data)
            
            elif callback_data.startswith('msg_template_'):
                await self._handle_message_template(update, context, callback_data)
            
            elif callback_data.startswith('ai_yes_'):
                await self._handle_ai_yes(update, context, callback_data)
            
            elif callback_data.startswith('ai_no_'):
                await self._handle_ai_no(update, context, callback_data)
            
            elif callback_data in ['CANCEL', 'CANCEL_SCRAPE']:
                await self._handle_cancel_scraping(update, context)
            
            elif callback_data == 'agree_to_terms':
                await self._handle_terms_agreement(update, context)
            
            elif callback_data == 'show_terms':
                await self._show_terms_of_service(update, context)
            
            elif callback_data == 'main_menu':
                await self._handle_show_main_menu(update, context)
            
            # Removed: image_generator callbacks (image_gen_menu, image_gen_text, image_gen_from_image)
            
            # Removed: WhatsApp callbacks (use_saved_instance, send_to_scraped_leads, whatsapp_single_number, templates, AI, webhook)

            else:
                logger.warning(f"Unhandled callback data: {callback_data}")
                await query.edit_message_text("פעולה לא זמינה")
                
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            try:
                await query.edit_message_text("שגיאה בעיבוד הבקשה. נסה שוב.")
            except:
                pass
    
    async def text_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle text messages"""
        try:
            user_id = update.effective_user.id
            text = update.message.text
            
            # Handle keyboard button presses
            if text == "🏠 התחלה":
                return await self.start_command(update, context)
            elif text == "🌐 שנה שפה":
                return await self.language_command(update, context)
            elif text == "📞 צור קשר":
                return await self._handle_contact_button(update, context)
            elif text == "💬 שליחת הודעות":
                return await self.send_whatsapp_command(update, context)
            
            # Check if user is waiting for specific input
            waiting_for = db.get_user_waiting_for(user_id)
            
            # Removed: WhatsApp waiting handlers (instance, token, single_number, custom_message, webhook, AI, message_csv)
            
            if waiting_for and waiting_for.startswith('ai_prompt_'):
                await self._handle_ai_prompt_input(update, context, text, waiting_for)
            else:
                # Default response for unexpected text
                language = db.get_user_language(user_id)
                response = "לא הבנתי. השתמש בכפתורים בתפריט." if language == 'hebrew' else "I don't understand. Please use the menu buttons."
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error in text message handler: {e}")
            await update.message.reply_text("שגיאה בעיבוד ההודעה.")
    
    async def photo_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle photo messages"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is waiting for photo input
            waiting_for = db.get_user_waiting_for(user_id)
            
            # Removed: image_gen_photo handler
            # Unexpected photo
            await update.message.reply_text("לא צפוי תמונה כרגע. השתמש בתפריט.")
                
        except Exception as e:
            logger.error(f"Error in photo message handler: {e}")
            await update.message.reply_text("שגיאה בעיבוד התמונה.")
    
    async def document_message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle document messages (CSV/Excel files)"""
        try:
            user_id = update.effective_user.id
            document = update.message.document
            
            # Check if user is in WhatsApp sending flow
            waiting_for = db.get_user_waiting_for(user_id)
            
            # Check file extension
            file_name = document.file_name.lower()
            if file_name.endswith(('.csv', '.xls', '.xlsx')):
                # Download and process the file
                await self._handle_csv_upload(update, context, document)
            else:
                await update.message.reply_text("קובץ לא נתמך. שלח קובץ CSV או Excel.")
                
        except Exception as e:
            logger.error(f"Error in document message handler: {e}")
            await update.message.reply_text("שגיאה בעיבוד הקובץ.")
    
    async def _handle_csv_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE, document) -> None:
        """Handle CSV/Excel file upload for WhatsApp sending"""
        try:
            user_id = update.effective_user.id
            
            # Download file
            file = await context.bot.get_file(document.file_id)
            file_path = f"/tmp/{document.file_name}"
            await file.download_to_drive(file_path)
            
            # Read phone numbers from file
            import pandas as pd
            
            if file_path.endswith('.csv'):
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)
            
            # Find phone number column (try common names)
            phone_col = None
            for col in df.columns:
                col_lower = str(col).lower()
                if any(keyword in col_lower for keyword in ['phone', 'טלפון', 'mobile', 'נייד', 'contact']):
                    phone_col = col
                    break
            
            if phone_col is None:
                # Use first column
                phone_col = df.columns[0]
            
            # Extract phone numbers
            phone_numbers = df[phone_col].astype(str).tolist()
            # Clean phone numbers
            phone_numbers = [p.strip().replace('-', '').replace(' ', '') for p in phone_numbers if p and p != 'nan']
            
            if not phone_numbers:
                await update.message.reply_text("❌ לא נמצאו מספרי טלפון בקובץ.")
                return
            
            # Set state to wait for message
            db.set_user_waiting_for(user_id, f'whatsapp_message_csv')
            
            # Store phone numbers in context
            context.user_data['csv_phone_numbers'] = phone_numbers
            
            # Ask for message
            message_text = f"✅ נבחרו {len(phone_numbers)} מספרי טלפון מהקובץ לשליחת הודעות וואטסאפ \n\n💬 כתוב את תוכן ההודעה שברצונך לשלוח ללידים, או בחר אחת מההודעות השמורות מהרשימה מטה 👇\n\nההודעה תישלח באופן אוטומטי לכל המספרים שנבחרו."
            
            keyboard = [
                [InlineKeyboardButton("💬 היי בקשר למודעה האם יש אופציה...", callback_data=f"msg_template_1_csv")],
                [InlineKeyboardButton("💬 שלום! בקשר לדירה, יש לי מספר לקוחות...", callback_data=f"msg_template_2_csv")],
                [InlineKeyboardButton("❌ ביטול", callback_data="back_to_main")]
            ]
            
            await update.message.reply_text(
                message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling CSV upload: {e}")
            await update.message.reply_text("❌ שגיאה בעיבוד הקובץ. וודא שהקובץ תקין.")
    
    async def _handle_show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle show main menu without login button"""
        try:
            user_id = update.effective_user.id
            await self.menu_manager.send_main_menu(update, context, user_id)
        except Exception as e:
            logger.error(f"Error showing main menu: {e}")
    
    async def _handle_back_to_main(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle back to main menu - show start message with GIF"""
        user_id = update.effective_user.id
        
        # Send welcome GIF with keyboard (same as /start, no caption)
        keyboard = [
            [
                InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data='schedule_menu'),
                InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data='scraper_menu')
            ],
            [
                InlineKeyboardButton("ℹ️", callback_data='show_info')
            ]
        ]
        
        # Use file_id for instant sending (no upload needed)
        await context.bot.send_animation(
            chat_id=update.callback_query.message.chat_id,
            animation="CgACAgQAAxkDAAICYGk3beqnCTNllztcH0o5JArgO_RXAAIHHwACOya5UQ9R2fn6D5JRNgQ",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def _handle_show_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle show info button - send technical documentation PDF only"""
        try:
            query = update.callback_query
            await query.answer()
            
            # Send the technical documentation file (PDF) only
            doc_path = '/home/ubuntu/yad2bot-service-scraper/service scraper v1.0.pdf'
            
            await context.bot.send_document(
                chat_id=query.message.chat_id,
                document=open(doc_path, 'rb'),
                filename='service scraper v1.0.pdf',
                caption="Developer Documentation v1.0"
            )
            
            logger.info(f"Technical documentation sent to user {query.from_user.id}")
            
        except Exception as e:
            logger.error(f"Error sending documentation: {e}")
            await query.message.reply_text("⚠️ שגיאה בשליחת המסמך. נסה שוב.")
    
    async def results_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /results command"""
        await self._handle_results_menu(update, context, "he")
    
    async def auto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /auto command"""
        await self._handle_auto_menu(update, context)
    
    async def language_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /language command"""
        await self._handle_language_menu(update, context)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        await self._handle_help_menu(update, context, "he")
    
    async def menu_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /menu command"""
        user_id = update.effective_user.id
        await self.menu_manager.send_main_menu(update, context, user_id)

    async def _handle_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language menu"""
        keyboard = [
            [InlineKeyboardButton("🇮🇱 עברית", callback_data="language_he")],
            [InlineKeyboardButton("🇺🇸 English", callback_data="language_en")],
            [InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text="בחר שפה / Choose Language:",
                reply_markup=reply_markup
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="בחר שפה / Choose Language:",
                reply_markup=reply_markup
            )

    async def _handle_scraper_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle scraper menu"""
        if not await check_channel_membership(context, update.effective_user.id):
            # Send sticker before channel join message
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            
            # Check if it's from callback query or direct command
            if update.callback_query:
                await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
                chat_id = update.effective_chat.id
            else:
                await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker_id)
                chat_id = update.effective_chat.id
            
            await context.bot.send_message(
                chat_id=chat_id,
                text="כדי להשתמש בבוט צריך קודם להצטרף לערוץ שלנו 👇\n" + CHANNEL_INVITE_URL
            )
            return
        
        # Send sticker first
        sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
        
        # Check if it's from callback query or direct command
        if update.callback_query:
            await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
        else:
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=sticker_id)
        
        # Send combined message with menu
        await self.menu_manager.send_scraper_menu_combined(update, context)
    
    async def _handle_auto_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle auto menu"""
        if not await check_channel_membership(context, update.effective_user.id):
            # Send sticker before channel join message
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="כדי להשתמש בבוט צריך קודם להצטרף לערוץ שלנו 👇\n" + CHANNEL_INVITE_URL
            )
            return
        
        # Send sticker first
        sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
        await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
        
        # Send combined message with menu
        await self.menu_manager.send_auto_menu_combined(update, context)
    
    async def _handle_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Handle help menu"""
        await self.menu_manager.send_help_menu(update, context, language)
    
    async def _handle_extra_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """טיפול בתפריט נוסף"""
        keyboard = self.menu_manager.create_extra_menu_keyboard()
        await update.callback_query.edit_message_text(
            text="📋 תפריט נוסף\n\nבחר את הפעולה שברצונך לבצע:",
            reply_markup=keyboard
        )
    
    async def _handle_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle language menu"""
        await self.menu_manager.send_language_menu(update, context)
    
    async def _handle_language_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle language selection"""
        user_id = update.effective_user.id
        new_language = 'hebrew' if callback_data == 'lang_he' else 'english'
        
        # Update language in database
        db.set_user_language(user_id, new_language)
        
        # Send confirmation and return to main menu
        await self.menu_manager.handle_language_change(update, context, new_language)
    
    async def _handle_scraper_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle scraper actions"""
        parts = callback_data.split('_')
        filter_type = parts[1]  # 'all' or 'today'
        mode = parts[2]  # 'rent' or 'sale'
        
        await self.scraper_manager.run_scraper(update, context, mode, filter_type)
    
    async def _handle_schedule_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle schedule actions"""
        from scheduler import scheduler
        
        if callback_data == 'schedule_scraping':
            await self.menu_manager.send_schedule_scraper_menu(update, context)
        elif callback_data == 'schedule_messages':
            await self.menu_manager.send_schedule_whatsapp_menu(update, context)
        else:
            # Handle specific schedule creation
            parts = callback_data.split('_')
            if len(parts) >= 4:
                schedule_type = parts[1]  # 'scraper' or 'whatsapp'
                mode = parts[2]  # 'rent' or 'sale'
                filter_type = parts[3]  # 'today' or 'all'
                
                # Store the schedule request
                context.user_data['schedule_request'] = {
                    'type': schedule_type,
                    'mode': mode,
                    'filter_type': filter_type
                }
                
                # Start time selection
                await self._handle_time_selection(update, context, 'schedule_time')
    
    async def _handle_schedule_management(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str, language: str):
        """Handle schedule management actions"""
        from scheduler import scheduler
        user_id = update.effective_user.id
        
        if callback_data == 'show_current_schedule':
            if scheduler:
                schedule_text = scheduler.get_user_schedules_text(user_id, language)
            else:
                schedule_text = "שירות התזמון לא זמין כרגע" if language == 'hebrew' else "Scheduling service not available"
            
            keyboard = [[InlineKeyboardButton("🔙 חזרה", callback_data="auto_menu")]]
            await update.callback_query.edit_message_text(schedule_text, reply_markup=InlineKeyboardMarkup(keyboard))
        
        elif callback_data == 'cancel_schedule':
            if scheduler:
                success = scheduler.cancel_user_schedules(user_id)
                if success:
                    cancel_text = "✅ כל התזמונים בוטלו בהצלחה!" if language == 'hebrew' else "✅ All schedules cancelled successfully!"
                else:
                    cancel_text = "❌ שגיאה בביטול התזמונים" if language == 'hebrew' else "❌ Error cancelling schedules"
            else:
                cancel_text = "שירות התזמון לא זמין כרגע" if language == 'hebrew' else "Scheduling service not available"
            
            keyboard = [[InlineKeyboardButton("🔙 חזרה", callback_data="auto_menu")]]
            await update.callback_query.edit_message_text(cancel_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _handle_see_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Handle see results action"""
        user_id = update.effective_user.id
        logger.info(f"[DEBUG] _handle_see_results called for user {user_id}")
        
        results = db.get_user_results(user_id, limit=5)
        logger.info(f"[DEBUG] Found {len(results)} results for user {user_id}")
        
        if results:
            latest_result = results[0]
            csv_file = latest_result['csv_file_path']
            logger.info(f"[DEBUG] Latest result CSV file: '{csv_file}'")
            
            # Check if csv_file path is valid
            if not csv_file or not csv_file.strip():
                logger.warning(f"Empty CSV file path for user {user_id}")
                return
            
            logger.info(f"[DEBUG] CSV file path is valid, proceeding with results display")
            
            # Send summary message with results info and buttons
            results_text = "📊 התוצאות האחרונות שלך:\n\n" if language == 'hebrew' else "📊 Your recent results:\n\n"
            for result in results:
                results_text += f"📅 {result['created_at']}\n"
                results_text += f"🔍 {result['mode']} - {result['filter_type']}\n"
                results_text += f"📞 {result['phone_numbers_count']} מספרי טלפון\n\n"
            
            logger.info(f"[DEBUG] Results text prepared: {results_text[:100]}...")
            
            keyboard = [
                [InlineKeyboardButton("הצג קישורי וואטאפ", callback_data="show_whatsapp_links")],
                [InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]
            ]
            
            await update.callback_query.edit_message_text(
                text=results_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"[DEBUG] Results message sent successfully")
            
            # CSV file is already sent when scraping completes, no need to send again
        else:
            logger.warning(f"[DEBUG] No results found for user {user_id}")
            no_results_text = "❌ לא נמצאו תוצאות.\n\n💡 תחילה בצע סריקה כדי לקבל תוצאות." if language == 'hebrew' else "❌ No results found.\n\n💡 First perform a scan to get results."
            keyboard = [[InlineKeyboardButton("🔙 חזרה", callback_data="back_to_main")]]
            await update.callback_query.edit_message_text(no_results_text, reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def _handle_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
        """Handle time selection start"""
        await self.menu_manager.start_time_selection(update, context, action_type)
    
    async def _handle_hour_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle hour selection"""
        await self.menu_manager.handle_hour_selection(update, context)
    
    async def _handle_minute_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle minute selection"""
        # Check if this is rent_to_sale mode
        if context.user_data.get('rent_to_sale_city_selected'):
            await self._handle_rent_to_sale_minute_selected(update, context)
        else:
            await self.menu_manager.handle_minute_selection(update, context)
    
    async def _handle_cancel_time(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle time selection cancellation"""
        user_id = update.effective_user.id
        await self.menu_manager.send_main_menu(update, context, user_id)

    async def _handle_results_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Handle results menu"""
        if not await check_channel_membership(context, update.effective_user.id):
            # Send sticker before channel join message
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="כדי להשתמש בבוט צריך קודם להצטרף לערוץ שלנו 👇\n" + CHANNEL_INVITE_URL
            )
            return
        
        # Always send sticker and new message
        sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
        await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
        
        keyboard = self.menu_manager.create_results_menu_keyboard(language)
        results_text = (
            "כל התוצאות שלך מרוכזות כאן 📊\n"
            "מכאן תוכל לבחור אם להציג את תוצאות הסריקה האחרונות שלך, או את הנתונים המלאים של הודעות שנשלחו – "
            "כדי לראות את התמונה המלאה של הביצועים שלך."
        )
        await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text=results_text,
            reply_markup=keyboard
        )
    
    async def _handle_city_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle city selection for scraping"""
        city_map = {
            'city_tel_aviv': ('תל אביב - יפו', '5000'),
            'city_jerusalem': ('ירושלים', '3000'),
            'city_haifa': ('חיפה', '4000'),
            'city_beer_sheva': ('באר שבע', '9000'),
            'city_rishon': ('ראשון לציון', '8300'),
            'city_petah_tikva': ('פתח תקווה', '7900'),
            'city_netanya': ('נתניה', '7400'),
            'city_ashdod': ('אשדוד', '0070'),
            'city_other': ('עיר אחרת', 'other')
        }
        
        if callback_data in city_map:
            city_name, city_code = city_map[callback_data]
            
            if callback_data == 'city_other':
                # Handle "other city" selection
                await context.bot.send_message(
                    chat_id=update.callback_query.message.chat_id,
                    text="🏙️ תכונה זו בפיתוח\n\nבקרוב תוכל לבחור עיר נוספת מרשימה מורחבת או להזין עיר באופן ידני.\n\nלעת עתה, בחר אחת מהערים הזמינות."
                )
                return
            
            # Check if we're in rent_to_sale mode
            if context.user_data.get('rent_to_sale_mode'):
                # In rent_to_sale mode, skip scraping and go to message selection
                await self._handle_rent_to_sale_city_selected(update, context, city_name, city_code)
                return
            
            # Get stored mode and filter from context, or use defaults
            mode = context.user_data.get('scraper_mode', 'rent')
            filter_type = context.user_data.get('scraper_filter', 'today')
            page_limit = context.user_data.get('page_limit', None)
            
            # Check if we're in schedule mode
            if context.user_data.get('in_schedule_mode'):
                # Save schedule instead of running scraper
                from scheduler import scheduler
                hour = context.user_data.get('schedule_hour', 10)
                
                success = await scheduler.add_schedule(
                    user_id=update.effective_user.id,
                    mode=mode,
                    filter_type=filter_type,
                    city=city_name,
                    hour=hour,
                    minute=0
                )
                
                # Clear schedule mode
                context.user_data['in_schedule_mode'] = False
                context.user_data.pop('schedule_hour', None)
                
                if success:
                    mode_text = "השכרה" if mode == 'rent' else "מכירה"
                    filter_text = "מהיום בלבד" if filter_type == 'today' else "כללי"
                    
                    await update.callback_query.answer("✅ התזמון הוגדר בהצלחה!", show_alert=True)
                    
                    message = (
                        "✅ **התזמון הוגדר בהצלחה!**\n\n"
                        "**פרטי התזמון:**\n"
                        f"🏠 {mode_text} - {filter_text}\n"
                        f"📍 {city_name}\n"
                        f"⏰ כל יום בשעה {hour:02d}:00"
                    )
                    
                    keyboard = [
                        [InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data='back_to_main')]
                    ]
                    
                    await update.callback_query.edit_message_text(
                        text=message,
                        reply_markup=InlineKeyboardMarkup(keyboard),
                        parse_mode='Markdown'
                    )
                else:
                    await update.callback_query.answer("❌ שגיאה בהגדרת התזמון", show_alert=True)
                
                return
            
            # Start scraping with real-time updates and cancel button
            # Use the existing callback message instead of creating a new one
            status_message = update.callback_query.message
            
            await self.scraper_manager.run_scraper_with_message(
                status_message,
                context,
                mode,
                filter_type,
                city_code,
                page_limit=page_limit
            )

    async def _handle_cancel_scraping(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str = None):
        """Handle cancel scraping button - Global handler with fast acknowledgment"""
        try:
            # Fast acknowledgment first
            await update.callback_query.answer("מבוטל")
            
            chat_id = update.callback_query.message.chat_id
            current_user_id = update.effective_user.id
            
            logger.info(f"Cancel requested for user {current_user_id}")
            
            # Cancel the scraping session using chat_id
            success = self.scraper_manager.cancel_current_scraping(current_user_id)
            
            if success:
                logger.info(f"Scraping cancelled successfully for user {current_user_id}")
            else:
                logger.info(f"No active scraping found for user {current_user_id}")
            
            # Return to main menu after cancellation - send new message with GIF
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            
            keyboard = [
                [
                    InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data="schedule_menu"),
                    InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data="scraper_menu")
                ],
                [
                    InlineKeyboardButton("ℹ️", callback_data="show_info")
                ]
            ]
            keyboard = [
                [
                    InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data="schedule_menu"),
                    InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data="scraper_menu")
                ],
                [
                    InlineKeyboardButton("ℹ️", callback_data="show_info")
                ]
            ]
            keyboard = [
                [
                    InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data="schedule_menu"),
                    InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data="scraper_menu")
                ],
                [
                    InlineKeyboardButton("ℹ️", callback_data="show_info")
                ]
            ]
            keyboard = [
                [
                    InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data="schedule_menu"),
                    InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data="scraper_menu")
                ],
                [
                    InlineKeyboardButton("ℹ️", callback_data="show_info")
                ]
            ]
            keyboard = [
                [
                    InlineKeyboardButton("⌚ תזמן סריקה ⌚", callback_data="schedule_menu"),
                    InlineKeyboardButton("⚡ התחל סריקה ⚡", callback_data="scraper_menu")
                ],
                [
                    InlineKeyboardButton("ℹ️", callback_data="show_info")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Send GIF with main menu (using file_id for instant sending)
            await self.bot.send_animation(
                chat_id=chat_id,
                animation="CgACAgQAAxkDAAICYGk3beqnCTNllztcH0o5JArgO_RXAAIHHwACOya5UQ9R2fn6D5JRNgQ",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in cancel scraping handler: {e}", exc_info=True)
            try:
                await update.callback_query.answer("שגיאה בביטול")
            except:
                pass
            try:
                await update.callback_query.message.edit_text("❌ שגיאה בביטול הפעולה")
            except:
                pass

    async def _handle_city_selection_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle city selection menu display"""
        logger.info(f"City selection menu called with: {callback_data}")
        
        # Extract mode and filter from callback_data
        # Format: city_selection_rent_today, city_selection_rent_all, city_selection_rent_test, city_selection_rent_pages_25, etc.
        parts = callback_data.split('_')
        mode = parts[2]  # rent or sale
        
        # Check if this is a pages selection
        if len(parts) > 4 and parts[3] == 'pages':
            filter_type = 'all'  # Pages selections are treated as 'all' mode
            page_limit = int(parts[4])  # 25, 50, 100, or 200
            context.user_data['page_limit'] = page_limit
        else:
            filter_type = parts[3]  # today, all, or test
            # If test mode, set page_limit to 1
            if filter_type == 'test':
                context.user_data['page_limit'] = 1
            else:
                context.user_data['page_limit'] = None  # No limit
        
        logger.info(f"Extracted mode: {mode}, filter: {filter_type}")
        
        # Store the selection in context for later use
        context.user_data['scraper_mode'] = mode
        context.user_data['scraper_filter'] = filter_type
        
        # Prepare summary text
        mode_text = "להשכרה" if mode == "rent" else "למכירה"
        filter_text_map = {
            "today": "מודעות חדשות",
            "all": "כל המודעות",
            "test": "דף אחד"
        }
        filter_text = filter_text_map.get(filter_type, filter_type)
        
        # Add page limit info if exists (but not for test mode)
        page_limit = context.user_data.get('page_limit')
        if page_limit and filter_type != 'test':
            filter_text = f"כל המודעות ({page_limit} דפים)"
        
        summary_text = f"בחרת לבצע:\nסוג מודעות: {mode_text}\nסוג סריקה: {filter_text}\n\n"
        
        # Send city selection keyboard - edit the previous message instead of sending new one
        keyboard = self.menu_manager.create_city_selection_keyboard()
        await update.callback_query.edit_message_text(
            text=summary_text + "🏙️ בחר עיר מהרשימה כדי להתחיל מיד בסריקת המודעות",
            reply_markup=keyboard
        )
    
    async def _handle_message_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle message template button click"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Parse callback data: msg_template_1_5 -> template_id=1, result_id=5
            parts = callback_data.replace('msg_template_', '').split('_')
            template_id = parts[0]
            result_id = parts[1]
            
            # Define message templates
            templates = {
                '1': 'היי בקשר למודעה האם יש אופציה של מכירת הדירה?',
                '2': 'שלום! בקשר לדירה למכירה, יש לי מספר לקוחות פוטנציאליים, האם תיהיו מעוניינים לקבל פרטים נוספים או לתאם שיחה טלפונית?'
            }
            
            message_text = templates.get(template_id, '')
            
            if message_text:
                # Check if this is CSV or regular result
                if result_id == 'csv':
                    # Handle CSV template - pass query instead of update
                    await self._handle_whatsapp_message_input_csv_from_callback(query, context, message_text)
                else:
                    # Handle regular result - pass query instead of update
                    await self._handle_whatsapp_message_input_from_callback(query, context, message_text, f'whatsapp_message_{result_id}')
            else:
                await query.answer('תבנית לא נמצאה')
                
        except Exception as e:
            logger.error(f"Error handling message template: {e}")
    
    # Removed: _handle_confirm_send (WhatsApp)
    async def _removed_handle_confirm_send(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle confirmation to send WhatsApp messages"""
        try:
            user_id = update.effective_user.id
            
            # Get pending message data
            pending = context.user_data.get('pending_message')
            if not pending:
                await update.callback_query.answer("לא נמצאו נתונים")
                return
            
            phone_numbers = pending['phone_numbers']
            message_text = pending['message_text']
            result_id = pending['result_id']
            
            # Update message to show sending progress
            progress_text = f"📱 מתחיל לשלוח הודעות ל-{len(phone_numbers)} מספרי טלפון...\n\n💬 תוכן ההודעה:\n{message_text}\n\n⌛ אנא המתן..."
            keyboard = [[InlineKeyboardButton("🛑 ביטול שליחה", callback_data=f"cancel_sending_{user_id}")]]
            await update.callback_query.edit_message_text(progress_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            # Send WhatsApp messages
            # Removed: result = await self.whatsapp_manager.send_whatsapp_messages(user_id, phone_numbers, message_text)
            
            if result['success']:
                results_data = result['results']
                
                # Check if sending was cancelled
                if results_data.get('cancelled', False):
                    cancel_text = f"🛑 שליחת ההודעות בוטלה על ידי המשתמש!\n\n📊 תוצאות עד לביטול:\n✅ נשלחו בהצלחה: {results_data['sent']}\n❌ נכשלו: {results_data['failed']}"
                    
                    if results_data['errors']:
                        cancel_text += f"\n\n🔍 שגיאות:\n" + "\n".join(results_data['errors'][:5])
                        if len(results_data['errors']) > 5:
                            cancel_text += f"\n... ועוד {len(results_data['errors']) - 5} שגיאות"
                    
                    keyboard = [[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]]
                    await update.callback_query.edit_message_text(cancel_text, reply_markup=InlineKeyboardMarkup(keyboard))
                    return
                
                # Check if plan expired
                if results_data.get('expired_plan', False):
                    success_text = f"⏰ המנוי פג תוקף!\n\n📊 תוצאות:\n✅ נשלחו בהצלחה: {results_data['sent']}\n❌ נכשלו: {results_data['failed']}\n\n💡 יש לחדש את המנוי ב-yad2bot.co.il"
                else:
                    success_text = f"✅ שליחת הודעות הושלמה!\n\n📊 תוצאות:\n✅ נשלחו בהצלחה: {results_data['sent']}\n❌ נכשלו: {results_data['failed']}"
                
                if results_data['errors']:
                    success_text += f"\n\n🔍 שגיאות:\n" + "\n".join(results_data['errors'][:5])
                    if len(results_data['errors']) > 5:
                        success_text += f"\n... ועוד {len(results_data['errors']) - 5} שגיאות"
                
                keyboard = [[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]]
                await update.callback_query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                error_text = f"❌ שגיאה בשליחת ההודעות: {result.get('error', 'שגיאה לא ידועה')}"
                keyboard = [[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]]
                await update.callback_query.edit_message_text(error_text, reply_markup=InlineKeyboardMarkup(keyboard))
            
            # Clear pending message and CSV data
            context.user_data.pop('pending_message', None)
            context.user_data.pop('csv_phone_numbers', None)
            
        except Exception as e:
            logger.error(f"Error handling confirm send: {e}")
            await update.callback_query.answer("❌ שגיאה בשליחת ההודעות")

    async def _handle_cancel_sending(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle cancel sending button"""
        try:
            # Extract user_id from callback_data
            user_id_str = callback_data.replace('cancel_sending_', '')
            user_id = int(user_id_str)
            
            # Check if this is the correct user
            if update.effective_user.id != user_id:
                await update.callback_query.answer("❌ לא ניתן לבטל שליחה של משתמש אחר")
                return
            
            # Cancel the sending process
            # Removed: cancelled = self.whatsapp_manager.cancel_current_sending(user_id)
            
            if cancelled:
                await update.callback_query.answer("🛑 שליחת ההודעות בוטלה")
                # Update the message to show cancellation
                cancel_text = "🛑 ביטול שליחת הודעות...\n\n⏳ אנא המתן לדוח סופי..."
                keyboard = []  # Remove the cancel button
                await update.callback_query.edit_message_text(cancel_text, reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                await update.callback_query.answer("❌ לא ניתן לבטל - השליחה לא פעילה")
                
        except Exception as e:
            logger.error(f"Error handling cancel sending: {e}")
            await update.callback_query.answer("❌ שגיאה בביטול השליחה")

    async def _send_terms_of_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_name: str):
        """Send terms of service message"""
        try:
            terms_message = """רגע לפני שמתחילים, יש לקרוא ולהסכים לתנאי השימוש של הבוט.

לחיצה על כפתור "✅ אני מסכים/ה" מהווה אישור לקריאת התנאים והסכמה להם.

https://telegra.ph/%D7%AA%D7%A0%D7%90%D7%99-%D7%A9%D7%99%D7%9E%D7%95%D7%A9---yad2bot-08-30"""

            keyboard = [[InlineKeyboardButton("✅ אני מסכים/ה", callback_data="agree_to_terms")]]
            
            # Check if it's from callback_query or message
            if update.callback_query:
                await context.bot.send_message(
                    chat_id=update.callback_query.message.chat_id,
                    text=terms_message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    disable_web_page_preview=False
                )
            else:
                await update.message.reply_text(
                    terms_message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    disable_web_page_preview=False
                )
            
        except Exception as e:
            logger.error(f"Error sending terms of service: {e}")

    async def _handle_terms_agreement(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle terms of service agreement"""
        try:
            user_id = update.effective_user.id
            
            # Mark user as agreed to terms
            db.set_user_terms_agreement(user_id, True)
            
            # Send sticker only
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(chat_id=update.callback_query.message.chat_id, sticker=sticker_id)
            
            # Send CRM welcome message
            welcome_text = (
                "👋 היי Admin, ברוך הבא לסקריפר! 🚀\n\n"
                "כאן תוכל לעשות סריקות ועדכונים ל-CRM של Yad2bot:\n\n"
                "🔍 סרוק מודעות חדשות\n"
                "📊 צפה בתוצאות הסריקה\n"
                "💾 עדכן את מאגר הנתונים\n"
                "⏰ תזמון סריקת מודעות\n\n"
                "בואו נתחיל! בחר פעולה מהתפריט:"
            )
            keyboard = [
                [
                    InlineKeyboardButton("🚀 התחל סריקה", callback_data='scraper_menu')
                ],
                [
                    InlineKeyboardButton("🌐 שנה שפה", callback_data='language_menu'),
                    InlineKeyboardButton("📞 צור קשר", callback_data='contact_menu')
                ]
            ]
            
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=welcome_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Removed: bonus_manager signup offer
            
            logger.info(f"User {user_id} agreed to terms of service")
            
        except Exception as e:
            logger.error(f"Error handling terms agreement: {e}")
            await update.callback_query.answer("❌ שגיאה בעיבוד ההסכמה")

    async def _show_terms_of_service(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show terms of service from main menu"""
        try:
            terms_message = """רגע לפני שמתחילים, יש לקרוא ולהסכים לתנאי השימוש של הבוט.

לחיצה על כפתור "✅ אני מסכים/ה" מהווה אישור לקריאת התנאים והסכמה להם.

https://telegra.ph/%D7%AA%D7%A0%D7%90%D7%99-%D7%A9%D7%99%D7%9E%D7%95%D7%A9---yad2bot-08-30"""

            keyboard = [
                [InlineKeyboardButton("✅ אני מסכים/ה", callback_data="agree_to_terms")],
                [InlineKeyboardButton("🔙 חזרה לתפריט", callback_data="back_to_main")]
            ]
            
            await update.callback_query.edit_message_text(
                terms_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=False  # Enable preview for Telegram Instant View
            )
            
        except Exception as e:
            logger.error(f"Error showing terms of service: {e}")
            await update.callback_query.answer("❌ שגיאה בהצגת תנאי השימוש")

    async def _handle_contact_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact menu selection"""
        try:
            await self.menu_manager.send_contact_menu(update, context)
        except Exception as e:
            logger.error(f"Error handling contact menu: {e}")
            await update.callback_query.edit_message_text("❌ שגיאה בהצגת תפריט צור קשר")
    
    async def _handle_contact_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle contact button press from ReplyKeyboard"""
        try:
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(
                chat_id=update.message.chat_id,
                sticker=sticker_id
            )
            
            # Then send the contact message
            contact_text = """שלום, נעים להכיר 👋

אנחנו Yad2bot – מפתחי טכנולוגיה חדשנית לעולם הנדל״ן, עם ניסיון רב שנים במכירות, שיווק וגיוס נכסים.

💬 רוצים לדבר איתנו? נשמח לעזור!

📧 אימייל: <a href=\"mailto:support@yad2bot.co.il\">support@yad2bot.co.il</a>
📞 טלפון: <a href=\"tel:+972501234567\">050-123-4567</a>
🌐 אתר: <a href=\"https://yad2bot.co.il\">yad2bot.co.il</a>"""
            
            keyboard = [[
                InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data='back_to_main')
            ]]
            
            await update.message.reply_text(
                text=contact_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error handling contact button: {e}")

    async def _handle_agents_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle agents menu selection"""
        try:
            await self.menu_manager.send_agents_menu(update, context)
        except Exception as e:
            logger.error(f"Error handling agents menu: {e}")
            await update.callback_query.edit_message_text("❌ שגיאה בהצגת תפריט הסוכנים")

    async def _handle_agent_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle specific agent selection"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Map callback data to agent types
            agent_types = {
                'rent_sale_agent': 'סוכן השכרה למכירה',
                'real_estate_agent': 'סוכן נדלן',
                'advertising_agent': 'סוכן פרסום',
                'general_agent': 'סוכן כללי'
            }
            
            selected_agent = agent_types.get(callback_data, 'סוכן לא מוגדר')
            
            # For now, show a placeholder message
            message = f"✅ נבחר: {selected_agent}\n\n🚧 תכונה זו בפיתוח ותהיה זמינה בקרוב!\n\nבינתיים, תוכל להשתמש בתפריט הראשי לאיתור מודעות ושליחת הודעות."
            
            keyboard = [[InlineKeyboardButton("🔙 חזרה לתפריט הסוכנים", callback_data="agents_menu"),
                        InlineKeyboardButton("🏠 תפריט ראשי", callback_data="back_to_main")]]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error handling agent selection: {e}")
            await update.callback_query.edit_message_text("❌ שגיאה בבחירת הסוכן")
    
    async def _handle_my_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle my account menu"""
        try:
            await self.menu_manager.send_my_account_menu(update, context)
        except Exception as e:
            logger.error(f"Error handling my account: {e}")
            await update.callback_query.answer("❌ שגיאה בטעינת החשבון")
    
    async def _handle_claim_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle claim bonus action"""
        try:
            user_id = update.effective_user.id
            
            # Check if already claimed
            if db.has_claimed_signup_test(user_id):
                await update.callback_query.answer("ℹ️ כבר ניצלת את הבונוס שלך.\nניתן לצבור קרדיטים נוספים על ידי הזמנת חברים.", show_alert=True)
                return
            
            # Claim the bonus
            success = db.claim_signup_test(user_id)
            
            if success:
                success_text = """🎉 מזל טוב!👌
✨ קיבלת 1.5 קרדיטים לחשבון שלך! ✅"""
                
                await update.callback_query.edit_message_text(
                    text=success_text,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("👤 החשבון שלי", callback_data='my_account'),
                        InlineKeyboardButton("🏠 תפריט ראשי", callback_data='back_to_main')
                    ]])
                )
            else:
                await update.callback_query.answer("❌ שגיאה בקבלת הבונוס", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error handling claim bonus: {e}")
            await update.callback_query.answer("❌ שגיאה בקבלת הבונוס")
    
    async def _handle_share_referral(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle share referral action"""
        try:
            user_id = update.effective_user.id
            referral_code = db.get_user_referral_code(user_id)
            
            share_text = f"""📢 הזמן חברים והרווח קרדיטים!

שתף את הקישור הזה עם חברים:
`t.me/yad2bot_bot?start={referral_code}`

כל חבר שמצטרף דרכך מזכה אותך בקרדיטים נוספים!"""
            
            # Create properly encoded URLs
            whatsapp_text = f"💬 מצאתי בוט מטורף שמאתר לידים חמים מהמודעות תוך שניות!\n🔥 נסה גם אתה: t.me/yad2bot_bot?start={referral_code}"
            telegram_text = f"💬 מצאתי בוט מטורף שמאתר לידים חמים מהמודעות תוך שניות!\n🔥 נסה גם אתה:"
            
            import urllib.parse
            whatsapp_url = f"https://wa.me/?text={urllib.parse.quote(whatsapp_text)}"
            telegram_url = f"https://t.me/share/url?url=t.me/yad2bot_bot?start={referral_code}&text={urllib.parse.quote(telegram_text)}"
            
            keyboard = [
                [InlineKeyboardButton("📤 שתף בוואטסאפ", url=whatsapp_url)],
                [InlineKeyboardButton("📤 שתף בטלגרם", url=telegram_url)],
                [InlineKeyboardButton("🔙 חזרה", callback_data='my_account')]
            ]
            
            await update.callback_query.edit_message_text(
                text=share_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling share referral: {e}")
            await update.callback_query.answer("❌ שגיאה בשיתוף")


    async def _handle_show_whatsapp_links(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle show WhatsApp links action"""
        user_id = update.effective_user.id
        logger.info(f"[DEBUG] _handle_show_whatsapp_links called for user {user_id}")
        
        results = db.get_user_results(user_id, limit=1)
        
        if results:
            latest_result = results[0]
            csv_file = latest_result['csv_file_path']
            logger.info(f"[DEBUG] CSV file path: '{csv_file}'")
            
            # Check if csv_file path is valid
            if not csv_file or not csv_file.strip():
                logger.warning(f"Empty CSV file path for user {user_id}")
                await update.callback_query.edit_message_text("❌ לא נמצא קובץ תוצאות")
                return
            
            if os.path.exists(csv_file):
                try:
                    # Read CSV file and extract phone numbers
                    import csv
                    phone_links = []
                    
                    with open(csv_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            phone = row.get('phone_number', '').strip()
                            if phone and phone != '0' and len(phone) >= 9:
                                # Clean phone number (remove spaces, dashes, etc.)
                                clean_phone = ''.join(filter(str.isdigit, phone))
                                if clean_phone.startswith('0'):
                                    clean_phone = '972' + clean_phone[1:]  # Convert to international format
                                elif not clean_phone.startswith('972'):
                                    clean_phone = '972' + clean_phone
                                
                                whatsapp_link = f"https://wa.me/{clean_phone}"
                                phone_links.append(f"📱 {phone}: {whatsapp_link}")
                    
                    logger.info(f"[DEBUG] Generated {len(phone_links)} WhatsApp links")
                    
                    if phone_links:
                        # Split into chunks of 13 phones per message
                        chunk_size = 13
                        for i in range(0, len(phone_links), chunk_size):
                            chunk = phone_links[i:i+chunk_size]
                            phones_text = f"📱 קישורי וואטסאפ ({len(chunk)} מספרים):\n\n"
                            phones_text += '\n'.join(chunk)
                            
                            await context.bot.send_message(
                                chat_id=update.callback_query.message.chat_id,
                                text=phones_text,
                                disable_web_page_preview=True
                            )
                        
                        # Done - no extra messages
                        logger.info(f"[DEBUG] WhatsApp links sent successfully")
                    else:
                        logger.warning(f"[DEBUG] No valid phone numbers found in CSV")
                        await update.callback_query.edit_message_text("❌ לא נמצאו מספרי טלפון תקינים")
                except Exception as e:
                    logger.error(f"Error processing CSV file for WhatsApp links: {e}")
                    await update.callback_query.edit_message_text("❌ שגיאה בעיבוד קובץ התוצאות")
            else:
                logger.warning(f"[DEBUG] CSV file does not exist: {csv_file}")
                await update.callback_query.edit_message_text("❌ קובץ התוצאות לא נמצא")
        else:
            logger.warning(f"[DEBUG] No results found for user {user_id}")
            await update.callback_query.edit_message_text("❌ לא נמצאו תוצאות")

    async def _handle_calculator_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle calculator menu"""
        try:
            text = """🧮 **מחשבון תשואה**

בקרוב יהיה זמין מחשבון תשואה מתקדם שיעזור לך לחשב:
• תשואה על השקעה בנדל"ן
• רווחיות השכרה
• חישובי מס ועלויות

הכלי נמצא בפיתוח ויהיה זמין בקרוב!"""

            keyboard = [
                [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='back_to_main')]
            ]
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling calculator menu: {e}")

    async def _handle_signature_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle signature menu"""
        try:
            text = """✍️ **חתימה דיגיטלית**

בקרוב יהיה זמין מערכת חתימה דיגיטלית מתקדמת שתאפשר:
• חתימה על חוזים דיגיטליים
• אימות זהות מאובטח
• שמירת מסמכים חתומים
• שליחה אוטומטית ללקוחות

הכלי נמצא בפיתוח ויהיה זמין בקרוב!"""

            keyboard = [
                [InlineKeyboardButton("🔙 חזרה לתפריט הראשי", callback_data='back_to_main')]
            ]
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling signature menu: {e}")


    async def _handle_activity_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle activity history menu"""
        try:
            text = """📈 **היסטוריית פעילות**

בקרוב יהיה זמין מעקב מפורט אחר הפעילות שלך:
• היסטוריית סריקות
• הודעות שנשלחו
• תגובות שהתקבלו
• סטטיסטיקות מפורטות

הכלי נמצא בפיתוח ויהיה זמין בקרוב!"""

            keyboard = [
                [InlineKeyboardButton("🔙 חזרה לחשבון שלי", callback_data='my_account')]
            ]
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling activity history: {e}")

    async def _handle_buy_credits(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle buy credits menu - open Mini-App"""
        try:
            text = """💳 **רכישת קרדיטים**

בחר חבילת קרדיטים מתאימה עבורך:

⭐ 50 קרדיטים - ₪50
⭐ 100 קרדיטים - ₪100  
⭐ 200 קרדיטים - ₪200
⭐ 400 קרדיטים - ₪400

לחץ על הכפתור למטה לפתיחת חנות הקרדיטים."""

            keyboard = [
                [InlineKeyboardButton("💳 פתח חנות קרדיטים", web_app=WebAppInfo(url='https://credits.yad2bot.co.il'))],
                [InlineKeyboardButton("🔙 חזרה לחשבון שלי", callback_data='my_account')]
            ]
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling buy credits: {e}")

    async def _handle_invite_friends(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle invite friends menu"""
        try:
            user_id = update.effective_user.id
            
            text = f"""👥 **הזמן חברים**

הזמן חברים ל-Yad2bot וקבל קרדיטים!

🎁 **איך זה עובד:**
• שלח לחבר את הקישור שלך
• כשהוא נרשם - אתה מקבל 2 קרדיטים
• הוא מקבל 1 קרדיט בונוס

🔗 **הקישור שלך:**
https://t.me/yad2bot_bot?start=ref_{user_id}

📊 **סטטיסטיקות:**
• חברים שהזמנת: 0
• קרדיטים שהרווחת: 0"""

            keyboard = [
                [InlineKeyboardButton("📤 שתף קישור", callback_data='share_referral')],
                [InlineKeyboardButton("🔙 חזרה לחשבון שלי", callback_data='my_account')]
            ]
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error handling invite friends: {e}")
    
    async def _handle_ai_yes(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle AI yes button - ask for AI prompt"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            result_id = callback_data.replace('ai_yes_', '')
            
            # Set waiting state for AI prompt
            db.set_user_waiting_for(user_id, f'ai_prompt_{result_id}')
            
            # Show prompt input screen
            prompt_text = "🤖 **הגדר שיחה של AI**\n\n"
            prompt_text += "כתוב את הפרומפט שיהיה המדריך ל-AI איך להגיב למפרסמים.\n\n"
            prompt_text += "📝 **דוגמה:**\n"
            prompt_text += "```"
            prompt_text += "שלום אתה סוכן נדל״ן בשם יניב גולן, התפקיד שלך הוא לאתר דירות שאפשר להוציא אותן למכירה.\n\n"
            prompt_text += "נשלחה הודעה ראשונית למפרסמים בלוחות נדל״ן לגבי הדירה שלהם להשכרה:\n"
            prompt_text += "\"היי, בקשר למודעה - האם יש אופציה של מכירת הדירה?\"\n\n"
            prompt_text += "כעת אתה מקבל את התגובות שלהם.\n"
            prompt_text += "אם התגובה חיובית או פתוחה - תענה באופן טבעי, אישי ומקצועי.\n"
            prompt_text += "המטרה שלך היא להמשיך את השיחה ולחתור לכיוון קביעת פגישה או שיחת טלפון."
            prompt_text += "```"
            
            await query.edit_message_text(prompt_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling AI yes: {e}")
            await query.message.reply_text("❌ שגיאה")
    
    async def _handle_ai_no(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle AI no button - continue with normal flow"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            result_id = callback_data.replace('ai_no_', '')
            
            # Disable AI for this user
            db.set_ai_enabled(user_id, False)
            
            # Get pending message from context
            pending_message = context.user_data.get('pending_message')
            if not pending_message:
                await query.message.reply_text("❌ שגיאה: לא נמצאה הודעה")
                return
            
            phone_numbers = pending_message['phone_numbers']
            message_text = pending_message['message_text']
            
            # Show confirmation screen
            confirm_text = f"📊 **סיכום שליחה**\n\n"
            confirm_text += f"📞 **מספר לידים:** {len(phone_numbers)}\n"
            confirm_text += f"💬 **תוכן ההודעה:**\n{message_text}\n\n"
            confirm_text += "✅ לחץ על 'שגר הודעות' כדי להתחיל את השליחה"
            
            keyboard = [
                [InlineKeyboardButton("🚀 שגר הודעות", callback_data=f"confirm_send_{result_id}")],
                [InlineKeyboardButton("❌ ביטול", callback_data="back_to_main")]
            ]
            await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling AI no: {e}")
            await query.message.reply_text("❌ שגיאה")
    
    async def _handle_ai_prompt_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_text: str, waiting_for: str):
        """Handle AI prompt input from user"""
        try:
            user_id = update.effective_user.id
            result_id = waiting_for.replace('ai_prompt_', '')
            
            # Clear waiting state
            db.set_user_waiting_for(user_id, None)
            
            # Save AI prompt and enable AI
            db.set_ai_prompt(user_id, prompt_text)
            db.set_ai_enabled(user_id, True)
            
            # Get pending message from context
            pending_message = context.user_data.get('pending_message')
            if not pending_message:
                await update.message.reply_text("❌ שגיאה: לא נמצאה הודעה")
                return
            
            phone_numbers = pending_message['phone_numbers']
            message_text = pending_message['message_text']
            
            # Show confirmation screen with AI enabled
            confirm_text = f"📊 **סיכום שליחה**\n\n"
            confirm_text += f"📞 **מספר לידים:** {len(phone_numbers)}\n"
            confirm_text += f"💬 **תוכן ההודעה:**\n{message_text}\n"
            confirm_text += f"🤖 **AI מופעל:** ✅ כן\n\n"
            confirm_text += "✅ לחץ על 'שגר הודעות' כדי להתחיל את השליחה"
            
            keyboard = [
                [InlineKeyboardButton("🚀 שגר הודעות", callback_data=f"confirm_send_{result_id}")],
                [InlineKeyboardButton("❌ ביטול", callback_data="back_to_main")]
            ]
            await update.message.reply_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error handling AI prompt input: {e}")
            await update.message.reply_text("❌ שגיאה בשמירת הפרומפט")
    
    async def _handle_view_sent_numbers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle viewing sent numbers list"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Get sent count
            # Removed: sent_count = self.whatsapp_manager.sent_tracker.get_sent_count(user_id)
            
            if sent_count == 0:
                await query.answer()
                await query.edit_message_text(
                    "📋 רשימת מספרים ששלחתי\n\n"
                    "אין מספרים ברשימה.\n\n"
                    "כשתשלח הודעות, המספרים יישמרו כאן.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ חזרה", callback_data="whatsapp_menu")]
                    ])
                )
                return
            
            # Get sent phones (last 50)
            # Removed: sent_phones = self.whatsapp_manager.sent_tracker.get_sent_phones(user_id, limit=50)
            
            message = f"📋 **רשימת מספרים ששלחתי**\n\n"
            message += f"📊 **סה\"כ מספרים:** {sent_count}\n"
            message += f"📱 **מספרים אחרונים (עד 50):**\n\n"
            
            for i, phone_data in enumerate(sent_phones[:10], 1):  # Show only first 10 in message
                phone = phone_data['phone']
                sent_at = phone_data['sent_at']
                message += f"{i}. {phone} - {sent_at}\n"
            
            if sent_count > 10:
                message += f"\n...ועוד {sent_count - 10} מספרים\n"
            
            message += "\n💡 **טיפ:** אם תרצה לשלוח שוב לאותם מספרים, לחץ על 'אפס רשימת מספרים'"
            
            await query.answer()
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 אפס רשימה", callback_data="reset_sent_numbers")],
                    [InlineKeyboardButton("↩️ חזרה", callback_data="whatsapp_menu")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error viewing sent numbers: {e}")
            await query.answer("❌ שגיאה בטעינת הרשימה", show_alert=True)
    
    async def _handle_reset_sent_numbers(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle resetting sent numbers list"""
        try:
            query = update.callback_query
            user_id = query.from_user.id
            
            # Get current count before reset
            # Removed: sent_count = self.whatsapp_manager.sent_tracker.get_sent_count(user_id)
            
            if sent_count == 0:
                await query.answer("אין מספרים לאיפוס", show_alert=True)
                return
            
            # Clear sent history
            # Removed: success = self.whatsapp_manager.sent_tracker.clear_sent_history(user_id)
            
            if success:
                await query.answer()
                await query.edit_message_text(
                    f"✅ **רשימת המספרים אופסה בהצלחה!**\n\n"
                    f"🗑️ נמחקו {sent_count} מספרים\n\n"
                    f"עכשיו תוכל לשלוח הודעות שוב לאותם מספרים.",
                    parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("↩️ חזרה לתפריט", callback_data="whatsapp_menu")]
                    ])
                )
                logger.info(f"User {user_id} reset sent numbers list ({sent_count} numbers)")
            else:
                await query.answer("❌ שגיאה באיפוס הרשימה", show_alert=True)
            
        except Exception as e:
            logger.error(f"Error resetting sent numbers: {e}")
            await query.answer("❌ שגיאה באיפוס הרשימה", show_alert=True)

    
    async def _handle_rent_to_sale_city_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, city_name: str, city_code: str):
        """Handle city selection in rent_to_sale mode - show WhatsApp message options"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            context.user_data['selected_city'] = city_name
            context.user_data['selected_city_code'] = city_code
            
            context.user_data['rent_to_sale_city_selected'] = True
            
            await query.answer()
            
            # Show connection code selection
            language = db.get_user_language(user_id)
            
            message = f"עיר נבחרת: {city_name}\n\nמודעות השכרה חדשות\n\nהכנס כאן את קוד החיבור שלך 🔗 כדי להתחיל\nאם עדיין אין לך קוד – לחץ על הכפתור \"קוד חיבור\" כדי ליצור קוד חדש."
            
            from telegram import WebAppInfo
            keyboard = []
            
            # Check if user has saved instance code
            saved_instance = db.get_user_whatsapp_instance(user_id)
            if saved_instance:
                display_code = saved_instance[:20] + '...' if len(saved_instance) > 20 else saved_instance
                keyboard.append([InlineKeyboardButton(f"✅ {display_code}", callback_data="rent_to_sale_use_saved_code")])
            
            keyboard.extend([
                [InlineKeyboardButton("🔗 קוד חיבור", web_app=WebAppInfo(url='https://yad2bot.co.il/user'))],
                [InlineKeyboardButton("❌ ביטול", callback_data="auto_menu")]
            ])
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"User {user_id} selected city {city_name} in rent_to_sale mode")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_city_selected: {e}")
            await query.answer("❌ שגיאה בבחירת העיר", show_alert=True)
    
    async def _handle_rent_to_sale_timing_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle timing selection in rent_to_sale mode"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            timing_type = callback_data.split('_')[-1]  # now, daily, custom
            
            if timing_type == 'now':
                # Immediate scraping
                context.user_data['rent_to_sale_timing'] = 'now'
                confirmation_text = "✅ **תזמון הושלם בהצלחה!**\n\n⚡ הסריקה תתחיל עכשיו!"
                
            elif timing_type == 'daily':
                # Daily scraping - show hour selection
                context.user_data['rent_to_sale_timing'] = 'daily'
                
                await query.answer()
                message = "⏰ **בחר שעה לסריקה יומית:**"
                keyboard = [
                    [InlineKeyboardButton("06:00", callback_data="rent_to_sale_hour_6"), InlineKeyboardButton("07:00", callback_data="rent_to_sale_hour_7")],
                    [InlineKeyboardButton("08:00", callback_data="rent_to_sale_hour_8"), InlineKeyboardButton("09:00", callback_data="rent_to_sale_hour_9")],
                    [InlineKeyboardButton("10:00", callback_data="rent_to_sale_hour_10"), InlineKeyboardButton("11:00", callback_data="rent_to_sale_hour_11")],
                    [InlineKeyboardButton("12:00", callback_data="rent_to_sale_hour_12"), InlineKeyboardButton("13:00", callback_data="rent_to_sale_hour_13")],
                    [InlineKeyboardButton("14:00", callback_data="rent_to_sale_hour_14"), InlineKeyboardButton("15:00", callback_data="rent_to_sale_hour_15")],
                    [InlineKeyboardButton("16:00", callback_data="rent_to_sale_hour_16"), InlineKeyboardButton("17:00", callback_data="rent_to_sale_hour_17")],
                    [InlineKeyboardButton("18:00", callback_data="rent_to_sale_hour_18"), InlineKeyboardButton("19:00", callback_data="rent_to_sale_hour_19")],
                    [InlineKeyboardButton("20:00", callback_data="rent_to_sale_hour_20"), InlineKeyboardButton("21:00", callback_data="rent_to_sale_hour_21")],
                    [InlineKeyboardButton("22:00", callback_data="rent_to_sale_hour_22"), InlineKeyboardButton("23:00", callback_data="rent_to_sale_hour_23")],
                    [InlineKeyboardButton("❌ ביטול", callback_data="auto_menu")]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                logger.info(f"User {user_id} selected daily timing in rent_to_sale mode")
                return
                
            elif timing_type == 'custom':
                # Custom date/time selection
                context.user_data['rent_to_sale_timing'] = 'custom'
                
                # Show day selection
                await query.answer()
                message = "📅 **בחר יום לסריקה:**\n\n👇 גרול דפן בטלפון כדי להרחיב את הכפתורים"
                keyboard = [
                    [InlineKeyboardButton("📅 ראשון 24.11", callback_data="rent_to_sale_day_0"), InlineKeyboardButton("📅 שני 25.11", callback_data="rent_to_sale_day_1")],
                    [InlineKeyboardButton("📅 שלישי 26.11", callback_data="rent_to_sale_day_2"), InlineKeyboardButton("📅 רביעי 27.11", callback_data="rent_to_sale_day_3")],
                    [InlineKeyboardButton("📅 חמישי 28.11", callback_data="rent_to_sale_day_4"), InlineKeyboardButton("📅 שישי 29.11", callback_data="rent_to_sale_day_5")],
                    [InlineKeyboardButton("📅 שבת 30.11", callback_data="rent_to_sale_day_6"), InlineKeyboardButton("❌ ביטול", callback_data="auto_menu")]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
                logger.info(f"User {user_id} selected custom timing in rent_to_sale mode")
                return
            
            # For now and daily options, show confirmation
            await query.answer()
            keyboard = [[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]]
            
            await query.edit_message_text(
                confirmation_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            logger.info(f"User {user_id} selected {timing_type} timing in rent_to_sale mode")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_timing_selected: {e}")
            await query.answer("❌ שגיאה בבחירת התזמון", show_alert=True)
    
    async def _handle_rent_to_sale_day_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle day selection in rent_to_sale mode"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Extract day from callback_data
            day_type = callback_data.split('_')[-1]  # today, tomorrow, after_tomorrow
            context.user_data['rent_to_sale_day'] = day_type
            
            await query.answer()
            
            # Show hour selection with large buttons
            message = "⏰ **בחר שעה לסריקה:**"
            keyboard = [
                [InlineKeyboardButton("06:00", callback_data="rent_to_sale_hour_6"), InlineKeyboardButton("07:00", callback_data="rent_to_sale_hour_7")],
                [InlineKeyboardButton("08:00", callback_data="rent_to_sale_hour_8"), InlineKeyboardButton("09:00", callback_data="rent_to_sale_hour_9")],
                [InlineKeyboardButton("10:00", callback_data="rent_to_sale_hour_10"), InlineKeyboardButton("11:00", callback_data="rent_to_sale_hour_11")],
                [InlineKeyboardButton("12:00", callback_data="rent_to_sale_hour_12"), InlineKeyboardButton("13:00", callback_data="rent_to_sale_hour_13")],
                [InlineKeyboardButton("14:00", callback_data="rent_to_sale_hour_14"), InlineKeyboardButton("15:00", callback_data="rent_to_sale_hour_15")],
                [InlineKeyboardButton("16:00", callback_data="rent_to_sale_hour_16"), InlineKeyboardButton("17:00", callback_data="rent_to_sale_hour_17")],
                [InlineKeyboardButton("18:00", callback_data="rent_to_sale_hour_18"), InlineKeyboardButton("19:00", callback_data="rent_to_sale_hour_19")],
                [InlineKeyboardButton("20:00", callback_data="rent_to_sale_hour_20"), InlineKeyboardButton("21:00", callback_data="rent_to_sale_hour_21")],
                [InlineKeyboardButton("22:00", callback_data="rent_to_sale_hour_22"), InlineKeyboardButton("23:00", callback_data="rent_to_sale_hour_23")],
                [InlineKeyboardButton("❌ ביטול", callback_data="auto_menu")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            logger.info(f"User {user_id} selected day {day_type} in rent_to_sale mode")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_day_selected: {e}")
            await query.answer("❌ שגיאה בבחירת היום", show_alert=True)
    
    async def _handle_rent_to_sale_hour_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle hour selection in rent_to_sale mode - schedule scraping"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Extract hour from callback_data
            hour = int(callback_data.split('_')[-1])
            
            # Get day from context
            day = context.user_data.get('rent_to_sale_day', 'today')
            city_name = context.user_data.get('selected_city', 'לא ידוע')
            
            await query.answer()
            
            # Show confirmation message
            day_names = {
                'today': 'היום',
                'tomorrow': 'מחר',
                'after_tomorrow': 'בעוד יומיים'
            }
            day_display = day_names.get(day, day)
            
            confirmation_text = f"✅ **תזמון הושלם בהצלחה!**\n\n🏙️ עיר: {city_name}\n📅 יום: {day_display}\n⏰ שעה: {hour:02d}:00\n\n📱 המערכת תסרוק מודעות השכרה חדשות ותשלח הודעות בזמן שנקבע."
            
            keyboard = [[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]]
            
            await query.edit_message_text(
                confirmation_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Store the scheduled task
            context.user_data['rent_to_sale_scheduled'] = {
                'day': day,
                'hour': hour,
                'city_name': city_name,
                'city_code': context.user_data.get('selected_city_code', ''),
                'message_template': context.user_data.get('message_template', 'היי בקשר למודעה האם יש אופציה של מכירת הדירה?')
            }
            
            logger.info(f"User {user_id} scheduled rent_to_sale scraping for {day} at {hour:02d}:00 in {city_name}")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_hour_selected: {e}")
            await query.answer("❌ שגיאה בבחירת השעה", show_alert=True)
    
    async def _handle_rent_to_sale_minute_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle minute selection in rent_to_sale mode - schedule scraping and sending"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            callback_data = query.data
            
            # Extract minute from callback_data (format: minute_0, minute_15, minute_30, minute_45)
            minute = int(callback_data.split('_')[1])
            
            # Get hour from context (should be stored by handle_hour_selection)
            hour = context.user_data.get('selected_hour', 0)
            
            # Get city and code from context
            city_name = context.user_data.get('selected_city', 'לא ידוע')
            city_code = context.user_data.get('selected_city_code', '')
            
            await query.answer()
            
            # Show confirmation message
            confirmation_text = f"✅ **תזמון הושלם בהצלחה!**\n\n🏙️ עיר: {city_name}\n⏰ זמן: {hour:02d}:{minute:02d}\n\n📱 המערכת תסרוק מודעות השכרה חדשות ותשלח הודעות בזמן שנקבע."
            
            keyboard = [[InlineKeyboardButton("🔙 תפריט ראשי", callback_data="back_to_main")]]
            
            await query.edit_message_text(
                confirmation_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Schedule the scraping and sending for the selected time
            # Store the scheduled task in context
            context.user_data['rent_to_sale_scheduled'] = {
                'hour': hour,
                'minute': minute,
                'city_name': city_name,
                'city_code': city_code,
                'message_template': context.user_data.get('message_template', 'היי בקשר למודעה האם יש אופציה של מכירת הדירה?')
            }
            
            logger.info(f"User {user_id} scheduled rent_to_sale scraping for {hour:02d}:{minute:02d} in {city_name}")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_minute_selected: {e}")
            await query.answer("❌ שגיאה בבחירת הזמן", show_alert=True)
    
    async def _handle_rent_to_sale_code_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle connection code selection in rent_to_sale mode - show timing selection"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            await query.answer()
            
            # Show timing selection (when to run the scraping)
            message = "בחר מתי תרצה שהמערכת תסרוק מודעות השכרה ותישלח הודעות פניה האם יש אופציה של מכירה.\n\n אתה יכול להפעיל עכשיו, להגדיר סריקה יומית קבועה, או לבחור תאריך וזמן מוגדר אישית."
            keyboard = [
                [InlineKeyboardButton("⚡ הפעל עכשיו", callback_data="rent_to_sale_timing_now"), InlineKeyboardButton("🔄 סריקה יומית", callback_data="rent_to_sale_timing_daily")],
                [InlineKeyboardButton("📅 בחר תאריך", callback_data="rent_to_sale_timing_custom"), InlineKeyboardButton("❌ ביטול", callback_data="auto_menu")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            logger.info(f"User {user_id} selected connection code in rent_to_sale mode - waiting for timing selection")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_code_selected: {e}")
            await query.answer("❌ שגיאה בבחירת קוד חיבור", show_alert=True)
    
    async def _handle_rent_to_sale_agent(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle rent to sale agent - scrape rent listings and send sale inquiry message"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            context.user_data['agent_mode'] = 'rent_to_sale'
            context.user_data['scraper_type'] = 'rent_today'
            context.user_data['message_template'] = 'היי בקשר למודעה האם יש אופציה של מכירת הדירה?'
            context.user_data['rent_to_sale_mode'] = True
            
            await query.answer()
            await query.edit_message_text(
                text="<b>סוכן השכרה למכירה</b>\n\nהמערכת תאתר עבורך מודעות השכרה חדשות ותפנה לבעלי דירות בשאלה עדינה על מכירה.\n\nכאן מגיעים המוכרים הטריים — כאלה שלא פירסמו למכירה, לא מוצפים במתווכים, ופתוחים להצעות.\nזו הדרך החכמה לגייס נכסים בבלעדיות בעיתיום המושלם.\n\n בחר עיר לביצוע הסריקה",
                reply_markup=self.menu_manager.create_city_selection_keyboard(),
                parse_mode='HTML'
            )
            
            logger.info(f"User {user_id} started rent_to_sale_agent mode")
            
        except Exception as e:
            logger.error(f"Error in rent_to_sale_agent: {e}")
            await query.answer("❌ שגיאה בתחילת התהליך", show_alert=True)


    async def _handle_schedule_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle schedule menu - show current schedule or create new"""
        try:
            from scheduler import scheduler
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(
                chat_id=query.message.chat_id,
                sticker=sticker_id
            )
            
            # Get current schedule
            schedule_info = scheduler.get_user_schedule_info(user_id)
            
            if schedule_info:
                # User has active schedule
                mode_text = "השכרה" if schedule_info['mode'] == 'rent' else "מכירה"
                filter_text = "מהיום בלבד" if schedule_info['filter_type'] == 'today' else "כללי"
                city = schedule_info.get('city', 'לא צוין')
                hour = schedule_info['hour']
                minute = schedule_info.get('minute', 0)
                
                message = (
                    "**⏰ הגדרת תזמון סריקה יומי**\n\n"
                    "**סטטוס נוכחי:** 🟢 סריקה יומית מתוזמנת\n"
                    f"**סוג:** {mode_text} - {filter_text}\n"
                    f"**עיר:** {city}\n"
                    f"**שעה:** {hour:02d}:{minute:02d}"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("❌ בטל תזמון נוכחי", callback_data='schedule_cancel'),
                        InlineKeyboardButton("✨ הגדר תזמון חדש", callback_data='schedule_new')
                    ],
                    [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='back_to_main')]
                ]
            else:
                # No active schedule
                message = (
                    "**⏰ הגדרת תזמון סריקה יומי**\n\n"
                    "המערכת תסרוק עבורך מודעות באופן אוטומטי כל יום בשעה שתבחר.\n\n"
                    "**סטטוס נוכחי:** 🔴 לא הוגדר תזמון."
                )
                
                keyboard = [
                    [InlineKeyboardButton("✨ הגדר תזמון חדש", callback_data='schedule_new')],
                    [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='back_to_main')]
                ]
            
            # Try to edit, if fails send new message
            try:
                await query.edit_message_text(
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            except Exception as edit_error:
                # If edit fails (e.g., message is a GIF), send new message
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error in schedule menu: {e}")
            try:
                await query.edit_message_text("שגיאה בטעינת תפריט התזמון. נסה שוב.")
            except:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="שגיאה בטעינת תפריט התזמון. נסה שוב."
                )
    
    async def _handle_schedule_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new schedule - show hour selection"""
        try:
            query = update.callback_query
            
            message = (
                "⏰ **תזמון סריקת מודעות**\n\n"
                "בואו נתחיל! בחר פעולה מהתפריט:\n\n"
                "**באיזו שעה תרצה שהסריקה תרוץ?**\n"
                "(השעה היא לפי שעון ישראל)"
            )
            
            # Create hour selection keyboard - only 4 time options
            keyboard = [
                [
                    InlineKeyboardButton("09:00", callback_data='schedule_hour_9'),
                    InlineKeyboardButton("12:00", callback_data='schedule_hour_12')
                ],
                [
                    InlineKeyboardButton("18:00", callback_data='schedule_hour_18'),
                    InlineKeyboardButton("21:00", callback_data='schedule_hour_21')
                ],
                [InlineKeyboardButton("🔙 חזרה", callback_data='schedule_menu')]
            ]
            
            await query.edit_message_text(
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in schedule new: {e}")
            await query.edit_message_text("שגיאה. נסה שוב.")
    
    async def _handle_schedule_hour_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
        """Handle hour selection - save and move to scraper flow"""
        try:
            query = update.callback_query
            user_id = update.effective_user.id
            
            # Extract hour from callback_data (schedule_hour_10 -> 10)
            hour = int(callback_data.split('_')[-1])
            
            # Save hour in context
            context.user_data['schedule_hour'] = hour
            context.user_data['in_schedule_mode'] = True
            
            # Show confirmation and move to scraper type selection
            message = (
                f"✅ **השעה נבחרה: {hour:02d}:00**\n\n"
                "עכשיו בחר סוג סריקה:"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🏠 השכרה", callback_data='scraper_rent'),
                    InlineKeyboardButton("🏢 מכירה", callback_data='scraper_sale')
                ],
                [InlineKeyboardButton("🔙 חזרה", callback_data='schedule_menu')]
            ]
            
            await query.edit_message_text(
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            logger.info(f"User {user_id} selected hour {hour} for schedule")
            
        except Exception as e:
            logger.error(f"Error in schedule hour selection: {e}")
            await query.edit_message_text("שגיאה. נסה שוב.")
    
    async def _handle_schedule_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle schedule cancellation"""
        query = update.callback_query
        user_id = update.effective_user.id
        
        try:
            # Get scheduler from application context
            from scraper_service_bot_main import application
            if hasattr(application, '_scheduler'):
                scheduler_instance = application._scheduler
            else:
                # Fallback: import and get global scheduler
                import scheduler as scheduler_module
                scheduler_instance = scheduler_module.scheduler
            
            success = await scheduler_instance.cancel_user_schedules(user_id)
            
            if success:
                await query.answer("✅ התזמון בוטל בהצלחה!", show_alert=True)
            else:
                await query.answer("❌ שגיאה בביטול התזמון", show_alert=True)
            
            # Return to schedule menu
            await self._handle_schedule_menu(update, context)
            
        except Exception as e:
            logger.error(f"Error in schedule cancel: {e}", exc_info=True)
            try:
                await query.answer("❌ שגיאה", show_alert=True)
            except:
                pass


# Global handlers instance
handlers = BotHandlers()
