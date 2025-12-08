"""
Bot menus module for Yad2bot
Contains all menu creation and management functions
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from database import db

logger = logging.getLogger(__name__)

class MenuManager:
    """Manages all bot menus and keyboards"""
    
    def __init__(self):
        self.translations = {
            'hebrew': {                 'welcome': '<b>‏🏡 ברוך הבא – Yad2bot ✌️</b>\n<blockquote>"הדרך המהירה להפוך מודעות נדל״ן ללידים חמים – עם סוכנים אוטומטיים שעובדים בשבילך 24/7."</blockquote>\n\nהיי בוס! אני העוזר הדיגיטלי שלך לאיתור לידים חמים מסביב לשעון✨🧲\n\nכדי ליצור חשבון או להתחבר, לחץ כאן:\n<a href="https://yad2bot.co.il/user/login">👉 לחץ להתחברות</a>\n\nהכפתור [My leads 🧲] בתחתית המסך פותח וסוגר את מערכת ניהול הלידים (CRM).\n\n📝 בכל שלב אפשר להקליד שם ומספר – והפרטים נשמרים אוטומטית.',
                'run_scraper': '🔍 איתור מודעות',
                'send_whatsapp': '🤳 שליחת הודעות',
                'auto_menu': '⌚ תזמון אוטומטי',
                'contact_menu': '🤙 צור קשר',
                'change_language': '🌐 שנה שפה',
                'language_changed': 'השפה שונתה בהצלחה!',
                'main_menu': 'תפריט ראשי',
                'schedule_scraping': '⏰ תזמון סריקת מודעות',
                'schedule_messages': '📨 תזמון שליחת הודעות',
                'show_current_schedule': '📅 הצג תזמון נוכחי',
                'cancel_schedule': '❌ בטל תזמון',
                'select_hour': 'בחר שעה:',
                'select_minute': 'בחר דקות:',
                'time_selected': 'נבחרה השעה {hour}:{minute}',
                'back': '🔙 חזרה',
                'login_register_button': 'התחברות / הרשמה',
                'agents_menu_button': '🧑‍💼 סוכן נדלן',
                'agents_welcome': 'הצלחה בתיווך מתחילה בצוות חכם!\n\nבחר סוכן קיים מהרשימה או צור סוכן חדש כדי להתחיל במשימה.',
                'rent_sale_agent': '🆕 סוכן השכרה למכירה',
                'real_estate_agent': 'סוכן נדלן',
                'advertising_agent': 'סוכן פרסום',
                'general_agent': 'סוכן כללי'
            },
            'english': {
                'welcome': 'Welcome to yad2bot!\n\nThe bot that scrapes listings, extracts phone numbers, and sends messages - all automatically and at your convenience.\n\nHere you can schedule listing scraping, WhatsApp messaging, and track everything with the click of a button.\n\nyad2bot.co.il',
                'run_scraper': '🔍 Run Scraper',
                'send_whatsapp': '📱 Send WhatsApp',
                'auto_menu': '⌚ תזמון אוטומטי',
                'help_menu': '❓ Help',
                'change_language': '🌐 Change Language',
                'language_changed': 'Language changed successfully!',
                'main_menu': 'Main Menu',
                'schedule_scraping': '⏰ Schedule Scraping',
                'schedule_messages': '📨 Schedule Messages',
                'show_current_schedule': '📅 Show Current Schedule',
                'cancel_schedule': '❌ Cancel Schedule',
                'select_hour': 'Select hour:',
                'select_minute': 'Select minutes:',
                'time_selected': 'Selected time {hour}:{minute}',
                'back': '🔙 Back'
            }
        }
    
    def get_translation(self, key: str, language: str = 'hebrew') -> str:
        """Get translation for a key"""
        return self.translations.get(language, self.translations['hebrew']).get(key, key)
    
    def create_main_menu_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
        """Create main menu keyboard"""
        keyboard = [
            # שורה 1: איתור לידים / תזמון סריקה
            [InlineKeyboardButton("🧲 איתור לידים", callback_data='scraper_menu'),
             InlineKeyboardButton("⏰ תזמון סריקת מודעות", callback_data='whatsapp_menu')],
            
            # שורה 2: החשבון שלי / הודעות נכנסות
            [InlineKeyboardButton("👤 החשבון שלי", callback_data='my_account'),
             InlineKeyboardButton("💬 הודעות נכנסות", web_app=WebAppInfo(url='https://yad2bot.co.il/user?page=inbox'))],
            
            # שורה 3: סוכן אוטומטי / היסטוריית פעילות
            [InlineKeyboardButton("🧑‍💼 סוכן אוטומטי", callback_data='auto_menu'),
             InlineKeyboardButton("📈 היסטוריית פעילות", callback_data='results_menu')],
            
            # שורה 4: חנות קרדיטים / חתימה דיגיטלית
            [InlineKeyboardButton("💎 חנות קרדיטים", web_app=WebAppInfo(url='https://credits.yad2bot.co.il')),
             InlineKeyboardButton("✍️ חתימה דיגיטלית", callback_data='signature_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_agents_menu_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
        """Create agents menu keyboard"""
        keyboard = [
            [InlineKeyboardButton(self.get_translation('rent_sale_agent', language), callback_data='rent_sale_agent')],
            [InlineKeyboardButton(self.get_translation('real_estate_agent', language), callback_data='real_estate_agent')],
            [InlineKeyboardButton(self.get_translation('advertising_agent', language), callback_data='advertising_agent')],
            [InlineKeyboardButton(self.get_translation('general_agent', language), callback_data='general_agent')],
            [InlineKeyboardButton(self.get_translation('back', language), callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_scraper_menu_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
        """Create scraper menu keyboard - first level (rent/sale)"""
        keyboard = [
            [
                InlineKeyboardButton("🔑 להשכרה", callback_data='scraper_rent'),
                InlineKeyboardButton("🏠 למכירה", callback_data='scraper_sale')
            ],
            [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_scraper_rent_keyboard(self) -> InlineKeyboardMarkup:
        """Create scraper rent submenu"""
        keyboard = [
            [InlineKeyboardButton("🆕 מהיום", callback_data='city_selection_rent_today'),
             InlineKeyboardButton("🔑 כללי", callback_data='city_selection_rent_all')],
            [InlineKeyboardButton("⏰ תזמון", callback_data='schedule_scraping_rent'),
             InlineKeyboardButton("📄 דף אחד", callback_data='city_selection_rent_test')],
            [InlineKeyboardButton("📊 25 דפים", callback_data='city_selection_rent_pages_25'),
             InlineKeyboardButton("📊 50 דפים", callback_data='city_selection_rent_pages_50')],
            [InlineKeyboardButton("📊 100 דפים", callback_data='city_selection_rent_pages_100'),
             InlineKeyboardButton("📊 200 דפים", callback_data='city_selection_rent_pages_200')],
            [InlineKeyboardButton("🔙 חזרה", callback_data='scraper_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_scraper_sale_keyboard(self) -> InlineKeyboardMarkup:
        """Create scraper sale submenu"""
        keyboard = [
            [InlineKeyboardButton("🆕 מהיום", callback_data='city_selection_sale_today'),
             InlineKeyboardButton("🏠 כללי", callback_data='city_selection_sale_all')],
            [InlineKeyboardButton("⏰ תזמון", callback_data='schedule_scraping_sale'),
             InlineKeyboardButton("📄 דף אחד", callback_data='city_selection_sale_test')],
            [InlineKeyboardButton("📊 25 דפים", callback_data='city_selection_sale_pages_25'),
             InlineKeyboardButton("📊 50 דפים", callback_data='city_selection_sale_pages_50')],
            [InlineKeyboardButton("📊 100 דפים", callback_data='city_selection_sale_pages_100'),
             InlineKeyboardButton("📊 200 דפים", callback_data='city_selection_sale_pages_200')],
            [InlineKeyboardButton("🔙 חזרה", callback_data='scraper_menu')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_whatsapp_menu_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
        """Create WhatsApp menu keyboard"""
        keyboard = [
            [InlineKeyboardButton("🚀 שלח הודעות", callback_data='whatsapp_connect'),
             InlineKeyboardButton("📱 שלח הודעה", callback_data='whatsapp_single_number')],
            [InlineKeyboardButton("🔥 חימום מספרים", callback_data='whatsapp_warmer'),
             InlineKeyboardButton("⏰ תזמון שליחת הודעות", callback_data='whatsapp_schedule')],
            [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_auto_menu_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
        """Create auto menu keyboard"""
        keyboard = [
            # שורה 1: סוכן השכרה למכירה (כפתור יחיד בשורה)
            [InlineKeyboardButton('🏢 סוכן השכרה למכירה', callback_data='rent_to_sale_agent')],
            
            # שורה 2: תזמון סריקה / תזמון הודעות
            [InlineKeyboardButton(self.get_translation('schedule_scraping', language), callback_data='schedule_scraping'),
             InlineKeyboardButton(self.get_translation('schedule_messages', language), callback_data='schedule_messages')],
            
            # שורה 3: חזרה לתפריט ראשי
            [InlineKeyboardButton('🔙 תפריט ראשי', callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_schedule_confirmation_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
        """Create keyboard with show/cancel schedule buttons after scheduling"""
        keyboard = [
            [InlineKeyboardButton(self.get_translation('show_current_schedule', language), callback_data='show_current_schedule'),
             InlineKeyboardButton(self.get_translation('cancel_schedule', language), callback_data='cancel_schedule')],
            [InlineKeyboardButton('🔙 תפריט ראשי', callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_extra_menu_keyboard(self) -> InlineKeyboardMarkup:
        """יצירת תפריט נוסף עם 4 אפשרויות"""
        keyboard = [
            [InlineKeyboardButton("🏠 התחלה", callback_data='back_to_main')],
            [InlineKeyboardButton("🔍 איתור לידים", callback_data='scraper_menu')],
            [InlineKeyboardButton("💬 שליחת הודעות", callback_data='whatsapp_menu')],
            [InlineKeyboardButton("🌐 שנה שפה", callback_data='language_menu')],
            [InlineKeyboardButton("↩️ חזרה", callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_language_menu_keyboard(self) -> InlineKeyboardMarkup:
        """Create language selection menu"""
        keyboard = [
            [InlineKeyboardButton("🇮🇱 עברית", callback_data='lang_he')],
            [InlineKeyboardButton("🇺🇸 English", callback_data='lang_en')],
            [InlineKeyboardButton("🔙 חזרה / Back", callback_data='back_to_main')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def create_hour_selection_keyboard(self) -> InlineKeyboardMarkup:
        """Create hour selection keyboard"""
        keyboard = []
        for i in range(0, 24, 4):
            row = []
            for j in range(4):
                if i + j < 24:
                    hour = i + j
                    row.append(InlineKeyboardButton(f"{hour:02d}:00", callback_data=f'hour_{hour}'))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("❌ ביטול", callback_data='cancel_time')])
        return InlineKeyboardMarkup(keyboard)
    
    def create_minute_selection_keyboard(self) -> InlineKeyboardMarkup:
        """Create minute selection keyboard"""
        keyboard = [
            [InlineKeyboardButton(":00", callback_data='minute_0'),
             InlineKeyboardButton(":15", callback_data='minute_15'),
             InlineKeyboardButton(":30", callback_data='minute_30'),
             InlineKeyboardButton(":45", callback_data='minute_45')],
            [InlineKeyboardButton("❌ ביטול", callback_data='cancel_time')]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def send_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
        """Send main menu to user"""
        try:
            language = db.get_user_language(user_id)
            keyboard = self.create_main_menu_keyboard(language)
            
            if update.callback_query:
                # If it's a callback query, edit the message text and keyboard
                welcome_text = self.get_translation('welcome', language)
                await update.callback_query.edit_message_text(
                    text=welcome_text,
                    reply_markup=keyboard,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
            else:
                # If it's a regular message, send with welcome text
                welcome_text = self.get_translation('welcome', language)
                await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode='HTML', disable_web_page_preview=True)
                
        except Exception as e:
            logger.error(f"Error sending main menu: {e}")
    
    async def send_agents_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send agents menu to user"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            agents_welcome_text = self.get_translation('agents_welcome', language)
            keyboard = self.create_agents_menu_keyboard(language)
            
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(
                chat_id=update.callback_query.message.chat_id,
                sticker=sticker_id
            )
            
            # Then send the agents menu message
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=agents_welcome_text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending agents menu: {e}")
    
    async def send_contact_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send contact menu to user"""
        try:
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(
                chat_id=update.callback_query.message.chat_id,
                sticker=sticker_id
            )
            
            # Then send the contact message
            contact_text = """שלום, נעים להכיר 👋

אנחנו Yad2bot – מפתחי טכנולוגיה חדשנית לעולם הנדל״ן, עם ניסיון רב שנים במכירות, שיווק וגיוס נכסים.

המערכת שפיתחנו יודעת לסרוק לוחות נדל״ן ואתרי מידע ציבורי, לאתר לידים איכותיים, לשלוח הודעות וואטסאפ אוטומטיות, להפעיל אוטומציות מתקדמות, לנהל CRM ייעודי, להפעיל סוכני AI חכמים, ואף לאפשר שימוש ב־API ייעודי.

לשאלות עסקיות או תמיכה ניתן לפנות במייל:
Yad2bot.co.il@gmail.com


<code>made in Haifa ❤️</code>"""
            
            keyboard = [[InlineKeyboardButton("🔙 חזרה", callback_data="back_to_main")]]
            
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=contact_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending contact menu: {e}")
    
    async def send_scraper_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send scraper menu"""
        try:
            keyboard = self.create_scraper_menu_keyboard()
            text = "בחר את קטגוריית המודעות שבה תרצה לבצע את הסריקה."
            
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending scraper menu: {e}")
    
    async def send_scraper_menu_combined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send scraper menu with combined message"""
        try:
            keyboard = self.create_scraper_menu_keyboard()
            text = """🏢 בחר קטגוריה לסריקה:

איזה סוג מודעות אתה רוצה לסרוק?"""
            
            # Handle both command and callback_query
            if update.callback_query:
                chat_id = update.callback_query.message.chat_id
            else:
                chat_id = update.effective_chat.id
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending combined scraper menu: {e}")
    
    async def send_scraper_rent_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send scraper rent submenu"""
        try:
            keyboard = self.create_scraper_rent_keyboard()
            text = "בחר את סוג הסריקה שתרצה לבצע להשכרה –\n\nתוכל לבחור בין מודעות חדשות שפורסמו היום, סריקה כוללת של כל המודעות, או מצב בדיקה לבדיקה זריזה."            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending scraper rent menu: {e}")
    
    async def send_scraper_sale_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send scraper sale submenu"""
        try:
            keyboard = self.create_scraper_sale_keyboard()
            text = "בחר את סוג הסריקה שתרצה לבצע למכירה –\n\nתוכל לבחור בין מודעות חדשות שפורסמו היום, סריקה כוללת של כל המודעות, או מצב בדיקה לבדיקה זריזה."
            
            await update.callback_query.edit_message_text(
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending scraper sale menu: {e}")
    
    async def send_whatsapp_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send WhatsApp menu"""
        try:
            keyboard = self.create_whatsapp_menu_keyboard()
            text = "כדי לשלוח הודעות וואטסאפ ללידים שאיתרנו, הכנס תחילה את 'קוד החיבור'.\n\nאין לך את הקוד? היכנס לקישור, שם תוכל ליצור חדש או להעתיק את הקוד הקיים שלך:\nhttps://yad2bot.co.il/user"
            
            # Handle both message and callback_query updates
            if update.callback_query:
                chat_id = update.callback_query.message.chat_id
            else:
                chat_id = update.effective_chat.id
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending WhatsApp menu: {e}")
    
    async def send_whatsapp_menu_combined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send WhatsApp menu with combined message"""
        try:
            keyboard = self.create_whatsapp_menu_keyboard()
            text = "מוכן להפוך את הלידים לעסקאות? כאן תוכל לשלוח הודעות וואטסאפ ללקוחות וללידים שמצאת🚀\n\nבחר את הפעולה הרצויה מהתפריט מטה."
            
            # Handle both message and callback_query updates
            if update.callback_query:
                chat_id = update.callback_query.message.chat_id
            else:
                chat_id = update.effective_chat.id
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending combined WhatsApp menu: {e}")
    
    async def send_auto_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send auto menu"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            keyboard = self.create_auto_menu_keyboard(language)
            text = "כאן תוכל להגדיר לבוט לעבוד בשבילך באופן קבוע, גם כשאתה לא ליד הטלפון.\n\nהבוט יפעל באופן אוטומטי ויעדכן אותך על כל התוצאות."
            
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending auto menu: {e}")
    
    async def send_auto_menu_combined(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send auto menu with combined message"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            keyboard = self.create_auto_menu_keyboard(language)
            text = "רוצה עוזר דיגיטלי שיאתר לך לידים חמים מסביב לשעון? 🤖\n\nכאן תוכל להגדיר לבוט לעבוד בשבילך באופן קבוע, גם כשאתה לא ליד הטלפון.\n\nהבוט יפעל באופן אוטומטי ויעדכן אותך על כל התוצאות."
            
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=text,
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Error sending combined auto menu: {e}")
    
    async def send_help_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
        """Send help menu"""
        try:
            help_text = """❓ **עזרה - מדריך למשתמש**

🔍 **הפעל סריקה** - סורק מודעות מיד2
📱 **שלח וואטסאפ** - שולח הודעות למספרי הטלפון שנמצאו
⏰ **Auto** - תזמון אוטומטי של פעולות
🌐 **שנה שפה** - החלף בין עברית לאנגלית

📞 **תמיכה:** yad2bot.co.il
💬 **קבוצת טלגרם:** @yad2bot_group""" if language == 'hebrew' else """❓ **Help - User Guide**

🔍 **Run Scraper** - Scrapes listings from Yad2
📱 **Send WhatsApp** - Sends messages to found phone numbers
⏰ **Auto** - Automatic scheduling of operations
🌐 **Change Language** - Switch between Hebrew and English

📞 **Support:** yad2bot.co.il
💬 **Telegram Group:** @yad2bot_group"""
            
            keyboard = [[InlineKeyboardButton("🔙 חזרה" if language == 'hebrew' else "🔙 Back", callback_data='back_to_main')]]
            await update.callback_query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error sending help menu: {e}")
    
    async def send_language_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send language selection menu"""
        try:
            keyboard = self.create_language_menu_keyboard()
            
            if update.callback_query:
                await update.callback_query.edit_message_text("Select language / בחר שפה", reply_markup=keyboard)
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="Select language / בחר שפה",
                    reply_markup=keyboard
                )
        except Exception as e:
            logger.error(f"Error sending language menu: {e}")
    
    async def send_schedule_scraper_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send schedule scraper menu"""
        try:
            keyboard = [
                [InlineKeyboardButton("🏠 השכרה - מהיום בלבד", callback_data="schedule_scraper_rent_today")],
                [InlineKeyboardButton("🏠 השכרה - כל המודעות", callback_data="schedule_scraper_rent_all")],
                [InlineKeyboardButton("🏢 מכירה - מהיום בלבד", callback_data="schedule_scraper_sale_today")],
                [InlineKeyboardButton("🏢 מכירה - כל המודעות", callback_data="schedule_scraper_sale_all")],
                [InlineKeyboardButton("🔙 חזרה", callback_data="auto_menu")]
            ]
            await update.callback_query.edit_message_text(
                "בחר את סוג הסריקה לתזמון אוטומטי:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error sending schedule scraper menu: {e}")
    
    async def send_schedule_whatsapp_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send schedule WhatsApp menu"""
        try:
            keyboard = [
                [InlineKeyboardButton("🏠 השכרה - מהיום בלבד", callback_data="schedule_whatsapp_rent_today")],
                [InlineKeyboardButton("🏠 השכרה - כל המודעות", callback_data="schedule_whatsapp_rent_all")],
                [InlineKeyboardButton("🏢 מכירה - מהיום בלבד", callback_data="schedule_whatsapp_sale_today")],
                [InlineKeyboardButton("🏢 מכירה - כל המודעות", callback_data="schedule_whatsapp_sale_all")],
                [InlineKeyboardButton("🔙 חזרה", callback_data="auto_menu")]
            ]
            await update.callback_query.edit_message_text(
                "בחר את סוג ההודעות לתזמון אוטומטי:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            logger.error(f"Error sending schedule WhatsApp menu: {e}")
    
    async def handle_language_change(self, update: Update, context: ContextTypes.DEFAULT_TYPE, new_language: str):
        """Handle language change"""
        try:
            # Send confirmation
            confirmation = self.get_translation('language_changed', new_language)
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=confirmation
            )
            
            # Send main menu in new language
            user_id = update.effective_user.id
            await self.send_main_menu(update, context, user_id)
            
        except Exception as e:
            logger.error(f"Error handling language change: {e}")
    
    async def start_time_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, action_type: str):
        """Start time selection process"""
        try:
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            # Store action type in context
            context.user_data['time_action'] = action_type
            
            # Send hour selection
            keyboard = self.create_hour_selection_keyboard()
            text = self.get_translation('select_hour', language)
            
            await update.callback_query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error starting time selection: {e}")
    
    async def handle_hour_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle hour selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == 'cancel_time':
                user_id = update.effective_user.id
                await self.send_main_menu(update, context, user_id)
                return
            
            # Extract hour from callback data
            hour = int(query.data.split('_')[1])
            context.user_data['selected_hour'] = hour
            
            # Send minute selection
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            keyboard = self.create_minute_selection_keyboard()
            text = self.get_translation('select_minute', language)
            
            await query.edit_message_text(text, reply_markup=keyboard)
            
        except Exception as e:
            logger.error(f"Error handling hour selection: {e}")
    
    async def handle_minute_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle minute selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            language = db.get_user_language(user_id)
            
            if query.data == 'cancel_time':
                await self.send_main_menu(update, context, user_id)
                return
            
            # Extract minute from callback data
            minute = int(query.data.split('_')[1])
            hour = context.user_data.get('selected_hour', 0)
            action_type = context.user_data.get('time_action', 'unknown')
            
            # Store the time
            selected_time = f"{hour:02d}:{minute:02d}"
            
            # Handle scheduling
            if action_type == 'schedule_time' and 'schedule_request' in context.user_data:
                from scheduler import scheduler
                schedule_request = context.user_data['schedule_request']
                
                if scheduler:
                    if schedule_request['type'] == 'scraper':
                        success = await scheduler.schedule_scraper(
                            user_id, 
                            schedule_request['mode'], 
                            schedule_request['filter_type'],
                            hour, 
                            minute
                        )
                    else:  # whatsapp
                        success = await scheduler.schedule_whatsapp(
                            user_id,
                            schedule_request['mode'],
                            schedule_request['filter_type'], 
                            hour,
                            minute
                        )
                    
                    if success:
                        schedule_type_text = "סריקה" if schedule_request['type'] == 'scraper' else "שליחת הודעות"
                        mode_text = "השכרה" if schedule_request['mode'] == 'rent' else "מכירה"
                        filter_text = "מהיום בלבד" if schedule_request['filter_type'] == 'today' else "כל המודעות"
                        
                        message = f"✅ תזמון הוגדר בהצלחה!\n\n🕐 {schedule_type_text} - {mode_text} {filter_text}\n⏰ בשעה: {selected_time}"
                    else:
                        message = "❌ שגיאה בהגדרת התזמון"
                else:
                    message = "❌ שירות התזמון לא זמין כרגע"
                
                # Clear schedule request
                context.user_data.pop('schedule_request', None)
                
            else:
                # Legacy time selection handling
                message = self.get_translation('time_selected', language).format(hour=hour, minute=minute)
            
            await query.edit_message_text(message)
            
            # Return to main menu after a short delay
            await self.send_main_menu(update, context, user_id)
            
        except Exception as e:
            logger.error(f"Error handling minute selection: {e}")

# Global menu manager instance
menu_manager = MenuManager()

def create_results_menu_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
    """Create results menu keyboard"""
    keyboard = [
        [InlineKeyboardButton("🔍 תוצאות סריקה", callback_data='see_scraper_results')],
        [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Add the method to the MenuManager class
MenuManager.create_results_menu_keyboard = create_results_menu_keyboard


def create_city_selection_keyboard(self, language: str = 'hebrew') -> InlineKeyboardMarkup:
    """Create city selection keyboard for scraping with 2 wide buttons per row like main menu"""
    keyboard = [
        [InlineKeyboardButton("🏙️ תל אביב - יפו", callback_data='city_tel_aviv'),
         InlineKeyboardButton("🕌 ירושלים", callback_data='city_jerusalem')],
        [InlineKeyboardButton("⚽ חיפה", callback_data='city_haifa'),
         InlineKeyboardButton("🏜️ באר שבע", callback_data='city_beer_sheva')],
        [InlineKeyboardButton("🌆 ראשון לציון", callback_data='city_rishon'),
         InlineKeyboardButton("🏢 פתח תקווה", callback_data='city_petah_tikva')],
        [InlineKeyboardButton("🏖️ נתניה", callback_data='city_netanya'),
         InlineKeyboardButton("🌊 אשדוד", callback_data='city_ashdod')],
        [InlineKeyboardButton("🔙 חזרה", callback_data='back_to_main')]
    ]
    return InlineKeyboardMarkup(keyboard)

# Add the method to the MenuManager class
MenuManager.create_city_selection_keyboard = create_city_selection_keyboard

# Add the missing methods to MenuManager class
async def send_my_account_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send my account menu to user"""
    try:
        # Send sticker first
        sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
        await context.bot.send_sticker(
            chat_id=update.callback_query.message.chat_id,
            sticker=sticker_id
        )
        
        user_id = update.effective_user.id
        user_credits = db.get_user_credits_balance(user_id)
        has_claimed_test = db.has_claimed_signup_test(user_id)
        
        # Get statistics from database
        total_listings = db.get_total_listings_scraped(user_id)
        total_messages = db.get_total_messages_sent(user_id)
        
        # Create account info text with table format using HTML
        account_text = f"""👤 החשבון שלי

<pre>יתרת קרדיטים:   {int(user_credits)}
מודעות שנסרקו:  {total_listings}
הודעות שנשלחו:  {total_messages}</pre>"""

        # Create keyboard
        keyboard = []
        
        # Add claim bonus button ONLY if not claimed
        if not has_claimed_test:
            keyboard.append([InlineKeyboardButton("🎁 קבל בונוס הרשמה (100 קרדיטים)", callback_data='claim_signup_test')])
        
        # Add other account options - 2 buttons per row
        keyboard.extend([
            [InlineKeyboardButton("🔢 המספרים שלי", web_app=WebAppInfo(url='https://yad2bot.co.il/user')),
             InlineKeyboardButton("🎨 צור תמונה של סוכן", callback_data='image_gen_menu')],
            [InlineKeyboardButton("💎 בונוס יומי", callback_data='daily_test_offer'),
             InlineKeyboardButton("🚀 שתף וקבל קרדיטים", callback_data='invite_friends')],
            [InlineKeyboardButton("🔙 תפריט ראשי", callback_data='back_to_main')]
        ])
        
        await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text=account_text,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error sending my account menu: {e}")
        await update.callback_query.answer("❌ שגיאה בטעינת החשבון")

async def send_promo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send promotional message"""
    try:
        promo_text = """🎉 ברוכים הבאים ל-Yad2bot!

🔥 הכלי החכם ביותר לסוכני נדל"ן:
• איתור לידים אוטומטי מיד2
• שליחת הודעות וואטסאפ המוניות
• ניהול מתקדם של לקוחות פוטנציאליים

💎 קבלו 10 קרדיטים חינם בהרשמה!
🚀 התחילו עכשיו ותראו תוצאות מיידיות"""

        await context.bot.send_message(
            chat_id=update.callback_query.message.chat_id,
            text=promo_text
        )
        
    except Exception as e:
        logger.error(f"Error sending promo message: {e}")

# Add the methods to MenuManager class
MenuManager.send_my_account_menu = send_my_account_menu
MenuManager.send_promo_message = send_promo_message

