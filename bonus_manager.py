"""
Bonus Manager for Yad2bot - Handle signup and daily bonuses
"""
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from database import BotDatabase

db = BotDatabase()

logger = logging.getLogger(__name__)

class BonusManager:
    """Manage bonus system for users"""
    
    # Sticker IDs
    SIGNUP_BONUS_STICKER = "CAACAgIAAxkBAAEPg0Ro4XScbBBSmXJJNNN-ZKOY4IcC-QAChwwAAvLaKEskd9-ZMiZZ4TYE"
    DAILY_BONUS_STICKER = "CAACAgIAAxkBAAEPgzho4XQtH7ltIiSriv8OH-lLxlGm7QACfQwAAsoPQEpP5RyRY3qVajYE"
    
    # Bonus amounts
    SIGNUP_BONUS_AMOUNT = 100.0
    DAILY_BONUS_AMOUNT = 50.0
    
    async def send_signup_bonus_offer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send signup bonus offer to new user"""
        try:
            user_id = update.effective_user.id
            
            # Check if already claimed
            if db.has_claimed_signup_bonus(user_id):
                return
            
            # Send sticker
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=self.SIGNUP_BONUS_STICKER
            )
            
            # Send bonus offer message
            message_text = f"""קבל בונוס הרשמה של {int(self.SIGNUP_BONUS_AMOUNT)} קרדיטים 💎
תחזור שוב מחר כדי לאסוף עוד קרדיטים או הזמן חברים וקבל קרדיטים נוספים!"""
            
            keyboard = [
                [InlineKeyboardButton("💎 קבל בונוס הרשמה", callback_data='claim_signup_bonus')],
                [InlineKeyboardButton("🚀 הזמן חברים וקבל קרדיטים", callback_data='invite_friends')]
            ]
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error sending signup bonus offer: {e}")
    
    async def claim_signup_bonus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle signup bonus claim"""
        try:
            user_id = update.effective_user.id
            
            # Check if already claimed
            if db.has_claimed_signup_bonus(user_id):
                await update.callback_query.answer("כבר ניצלת את בונוס ההרשמה.", show_alert=True)
                return
            
            # Claim the bonus
            success = db.claim_signup_bonus(user_id)
            
            if success:
                balance = db.get_user_credits_balance(user_id)
                success_text = f"""✅ קיבלת {int(self.SIGNUP_BONUS_AMOUNT)} קרדיטים לחשבון שלך!
💎 יתרתך הנוכחית: {int(balance)} קרדיטים"""
                
                keyboard = [
                    [InlineKeyboardButton("🚀 הזמן חברים וקבל קרדיטים", callback_data='invite_friends')],
                    [InlineKeyboardButton("↩️ תפריט ראשי", callback_data='back_to_main')]
                ]
                
                await update.callback_query.edit_message_text(
                    text=success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.callback_query.answer("❌ שגיאה בקבלת הבונוס", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error claiming signup bonus: {e}")
            await update.callback_query.answer("❌ שגיאה בקבלת הבונוס")
    
    async def send_daily_bonus_offer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send daily bonus offer or timer"""
        try:
            user_id = update.effective_user.id
            
            # Check if user has claimed signup bonus first
            if not db.has_claimed_signup_bonus(user_id):
                await self.send_signup_bonus_offer(update, context)
                return
            
            # Check last daily bonus time
            last_bonus_time = db.get_last_daily_bonus_time(user_id)
            now = datetime.utcnow()
            
            if last_bonus_time is None or (now - last_bonus_time) >= timedelta(hours=24):
                # Can claim bonus
                await self._send_daily_bonus_available(update, context)
            else:
                # Show timer
                remaining = timedelta(hours=24) - (now - last_bonus_time)
                await self._send_daily_bonus_timer(update, context, remaining)
                
        except Exception as e:
            logger.error(f"Error sending daily bonus offer: {e}")
    
    async def _send_daily_bonus_available(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send message when daily bonus is available"""
        try:
            user_id = update.effective_user.id
            balance = db.get_user_credits_balance(user_id)
            
            # Send sticker
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=self.DAILY_BONUS_STICKER
            )
            
            message_text = f"""🎁 קיבלת {int(self.DAILY_BONUS_AMOUNT)} קרדיטים יומיים לחשבון שלך!
יתרתך הנוכחית: {int(balance)} קרדיטים
תחזור שוב מחר כדי לאסוף עוד 🪙 או הזמן חברים חדשים עכשיו וקבל קרדיטים נוספים!"""
            
            keyboard = [
                [InlineKeyboardButton("🎁 קבל בונוס יומי", callback_data='claim_daily_bonus')],
                [InlineKeyboardButton("💎 רכישת קרדיטים", web_app=WebAppInfo(url='https://credits.yad2bot.co.il'))],
                [InlineKeyboardButton("🚀 הזמן חברים וקבל קרדיטים", callback_data='invite_friends')],
                [InlineKeyboardButton("🔍 מצא לידים", callback_data='run_scraper')]
            ]
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error sending daily bonus available message: {e}")
    
    async def _send_daily_bonus_timer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, remaining: timedelta):
        """Send timer message when daily bonus is not yet available"""
        try:
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEPlOFo8QAB9eiRVF_TreGZPGminqWTa04AAgYPAAIpzshKiB0rqCdPNu02BA"
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=sticker_id
            )
            
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            seconds = int(remaining.total_seconds() % 60)
            timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            message_text = """כבר ניצלת את הבונוס היומי
אפשר יהיה לקבל שוב מחר."""
            
            keyboard = [
                [InlineKeyboardButton(f"⏳ המתן {timer_text}", callback_data='timer_waiting')],
                [InlineKeyboardButton("👥 שתף חברים", callback_data='invite_friends')]
            ]
            
            message = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Schedule timer updates with all data in job.data
            end_time = datetime.utcnow() + remaining
            context.job_queue.run_repeating(
                self._update_timer,
                interval=60,
                first=60,
                data={
                    'user_id': update.effective_user.id,
                    'message_id': message.message_id,
                    'chat_id': message.chat_id,
                    'end_time': end_time
                },
                name=f'timer_{update.effective_user.id}'
            )
            
        except Exception as e:
            logger.error(f"Error sending daily bonus timer: {e}")
    
    async def _update_timer(self, context: ContextTypes.DEFAULT_TYPE):
        """Update timer message every minute"""
        try:
            job = context.job
            user_id = job.data['user_id']
            message_id = job.data['message_id']
            chat_id = job.data['chat_id']
            end_time = job.data['end_time']
            
            now = datetime.utcnow()
            remaining = end_time - now
            
            if remaining.total_seconds() <= 0:
                # Timer expired - show bonus available
                keyboard = [
                    [InlineKeyboardButton("🎁 קבל בונוס יומי", callback_data='claim_daily_bonus')],
                    [InlineKeyboardButton("🚀 הזמן חברים וקבל קרדיטים", callback_data='invite_friends')]
                ]
                
                await context.bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="🎁 הבונוס היומי זמין! לחץ כדי לקבל.",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
                # Clean up
                job.schedule_removal()
                return
            
            # Update timer
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            seconds = int(remaining.total_seconds() % 60)
            timer_text = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            message_text = """כבר ניצלת את הבונוס היומי
אפשר יהיה לקבל שוב מחר."""
            
            keyboard = [
                [InlineKeyboardButton(f"⏳ המתן {timer_text}", callback_data='timer_waiting')],
                [InlineKeyboardButton("👥 שתף חברים", callback_data='invite_friends')]
            ]
            
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=message_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error updating timer: {e}")
            # If error, stop the job
            if context.job:
                context.job.schedule_removal()
    
    async def claim_daily_bonus(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle daily bonus claim"""
        try:
            user_id = update.effective_user.id
            
            # Check if can claim
            last_bonus_time = db.get_last_daily_bonus_time(user_id)
            now = datetime.utcnow()
            
            if last_bonus_time and (now - last_bonus_time) < timedelta(hours=24):
                remaining = timedelta(hours=24) - (now - last_bonus_time)
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                await update.callback_query.answer(
                    f"כבר ניצלת את הבונוס היומי. תחזור בעוד {hours}:{minutes:02d}",
                    show_alert=True
                )
                return
            
            # Claim the bonus
            success = db.claim_daily_bonus(user_id, self.DAILY_BONUS_AMOUNT)
            
            if success:
                balance = db.get_user_credits_balance(user_id)
                success_text = f"""🎉 קיבלת {int(self.DAILY_BONUS_AMOUNT)} קרדיטים יומיים!
💰 יתרה: {int(balance)} קרדיטים."""
                
                keyboard = [
                    [InlineKeyboardButton("🔍 מצא לידים", callback_data='run_scraper')],
                    [InlineKeyboardButton("💎 רכישת קרדיטים", web_app=WebAppInfo(url='https://credits.yad2bot.co.il'))],
                    [InlineKeyboardButton("👥 שתף חברים", callback_data='invite_friends')]
                ]
                
                await update.callback_query.edit_message_text(
                    text=success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.callback_query.answer("❌ שגיאה בקבלת הבונוס", show_alert=True)
                
        except Exception as e:
            logger.error(f"Error claiming daily bonus: {e}")
            await update.callback_query.answer("❌ שגיאה בקבלת הבונוס")
    
    async def send_invite_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send invite friends promo message"""
        try:
            user_id = update.effective_user.id
            
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEPg41o4a2fIidHOck8vFsi7Ov3xDT4tAACFgADFm5MEoPbc3O3-IjONgQ"
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=sticker_id
            )
            
            # Create personal referral link
            referral_link = f"https://t.me/yad2bot_bot?start=YAD2_{user_id}"
            
            promo_text = f"""🎁 קבל בונוס מיוחד ב־Yad2bot!
בוט חכם לאיתור לידים חמים בנדל״ן –
הצטרף עכשיו וקבל קרדיטים במתנה!

{referral_link}"""
            
            # Format as code block for copy button
            formatted_text = f"```\n{promo_text}\n```"
            
            # Create share button
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [InlineKeyboardButton("📤 שתף בצ'אט", switch_inline_query=promo_text)],
                [InlineKeyboardButton("🔙 חזרה לתפריט ראשי", callback_data='back_to_main')]
            ]
            
            await update.callback_query.answer("שלח את ההודעה הזו לחברים שלך!")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=formatted_text,
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error sending invite message: {e}")

# Global instance
bonus_manager = BonusManager()

