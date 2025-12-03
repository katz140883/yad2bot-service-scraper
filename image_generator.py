"""Image Generator Module for Yad2bot - Runware AI Integration"""
import logging
import aiohttp
import sqlite3
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import BotDatabase

logger = logging.getLogger(__name__)
db = BotDatabase()

class ImageGenerator:
    """Handle AI image generation using Runware API"""
    
    def __init__(self):
        self.api_url = "https://api.runware.ai/v1"
        self.api_key = "djTV5zcFHCqHqkxJ9yDX1DDQopRvRdVv"
        self.headers = {
            "Content-Type": "application/json"
        }
        # Use SDXL for image-to-image (better face preservation)
        self.model_img2img = "civitai:133005@782002"  # Juggernaut XL - photorealistic
        # Use FLUX for text-to-image (faster, high quality)
        self.model_txt2img = "runware:101@1"  # FLUX.1 Dev
        self.free_limit = 3
    
    async def show_image_gen_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show image generation menu"""
        try:
            user_id = update.effective_user.id
            
            # Send sticker first
            sticker_id = "CAACAgIAAxkBAAEP7xhpMHJ_HJWH51hm372vIXwHiOiFLAAClAsAAoSLEUrkF8J7k7Pq0jYE"
            await context.bot.send_sticker(
                chat_id=update.callback_query.message.chat_id,
                sticker=sticker_id
            )
            
            # Send message with options
            message = """אין כמו רושם ראשוני כובש במכירות.
כאן תוכל ליצור תמונת תדמית למספר הוואטסאפ שממנו ישלחו ההודעות.
בחר איך ליצור:"""
            
            keyboard = [
                [InlineKeyboardButton("🎨 צור תמונת סוכן", callback_data="image_gen_text")],
                [InlineKeyboardButton("📸 צור תמונת סוכן מתמונה", callback_data="image_gen_from_image")],
                [InlineKeyboardButton("↩️ חזרה", callback_data="my_account")]
            ]
            
            await context.bot.send_message(
                chat_id=update.callback_query.message.chat_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing image gen menu: {e}")
    
    async def check_usage_limit(self, user_id: int) -> tuple[bool, int]:
        """Check if user has reached the free limit"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT image_gen_used FROM users WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                
                if result:
                    used = result[0] or 0
                    return used < self.free_limit, used
                return True, 0
            
        except Exception as e:
            logger.error(f"Error checking usage limit: {e}")
            return True, 0
    
    async def show_limit_reached(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show message when limit is reached"""
        message = """ניצלת את 3 היצירות החינמיות 🎨  
כדי להמשיך להשתמש בפונקציה הזאת, רכש חבילת קרדיטים בחנות."""
        
        from telegram import WebAppInfo
        keyboard = [[
            InlineKeyboardButton("🛒 פתח את חנות הקרדיטים", 
                               web_app=WebAppInfo(url='https://yad2bot.co.il/user?page=credits'))
        ]]
        
        await update.callback_query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def start_text_to_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start text-to-image generation"""
        try:
            user_id = update.effective_user.id
            
            # Check limit
            can_use, used = await self.check_usage_limit(user_id)
            if not can_use:
                await self.show_limit_reached(update, context)
                return
            
            # Ask for description
            message = """איך תרצה שהסוכן ייראה?  
(למשל: חליפה קלילה, רקע לבן/אפור, שלט "נמכר")"""
            
            keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="image_gen_menu")]]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Set user state
            db.set_user_waiting_for(user_id, 'image_gen_description')
            
        except Exception as e:
            logger.error(f"Error starting text to image: {e}")
    
    async def start_image_to_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start image-to-image generation"""
        try:
            user_id = update.effective_user.id
            
            # Check limit
            can_use, used = await self.check_usage_limit(user_id)
            if not can_use:
                await self.show_limit_reached(update, context)
                return
            
            # Ask for image
            message = "שלח לכאן תמונת פנים/חצי גוף ברורה שלך 📸"
            
            keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="image_gen_menu")]]
            
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
            # Set user state
            db.set_user_waiting_for(user_id, 'image_gen_photo')
            
        except Exception as e:
            logger.error(f"Error starting image to image: {e}")
    
    async def generate_from_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE, description: str):
        """Generate image from text description"""
        try:
            user_id = update.effective_user.id
            
            # Show progress message
            progress_msg = await update.message.reply_text("יוצר עבורך תמונה... זה לוקח בערך חצי דקה ⏳")
            
            # Prepare prompt
            base_prompt = """Professional real estate agent portrait, 30-40 years old, confident warm smile, 
wearing elegant business casual attire (beige or grey blazer, white dress shirt), 
clean minimalist studio background (solid white or soft grey), 
professional studio lighting, 
confident professional pose with arms crossed or hands clasped, 
waist-up professional shot, 
high-end corporate photography, sharp focus, photorealistic, 
successful and trustworthy appearance"""
            if description:
                prompt = f"{base_prompt}, {description}"
            else:
                prompt = base_prompt
            
            # API request - Runware format: array with auth + task
            payload = [
                {
                    "taskType": "authentication",
                    "apiKey": self.api_key
                },
                {
                    "taskType": "imageInference",
                    "taskUUID": str(uuid.uuid4()),
                    "positivePrompt": prompt,
                    "model": self.model_txt2img,
                    "width": 1024,
                    "height": 1024,
                    "numberResults": 1
                }
            ]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Extract image URL
                        if result and 'data' in result and len(result['data']) > 0:
                            image_url = result['data'][0].get('imageURL')
                            
                            if image_url:
                                # Delete progress message
                                await progress_msg.delete()
                                
                                # Send image
                                await update.message.reply_photo(
                                    photo=image_url,
                                    caption="✅ התמונה שלך מוכנה!"
                                )
                                
                                # Show buttons
                                keyboard = [
                                    [InlineKeyboardButton("🎨 צור שוב", callback_data="image_gen_text")],
                                    [InlineKeyboardButton("↩️ תפריט ראשי", callback_data="back_to_main")]
                                ]
                                await update.message.reply_text(
                                    "מה תרצה לעשות?",
                                    reply_markup=InlineKeyboardMarkup(keyboard)
                                )
                                
                                # Increment usage counter
                                await self.increment_usage(user_id)
                                
                                # Clear state
                                db.set_user_waiting_for(user_id, None)
                                return
                    
                    # Failed
                    await progress_msg.edit_text("לא הצלחתי ליצור את התמונה כרגע. נסה שוב בעוד רגע.")
                    
        except Exception as e:
            logger.error(f"Error generating image from text: {e}")
            await update.message.reply_text("לא הצלחתי ליצור את התמונה כרגע. נסה שוב בעוד רגע.")
    
    async def generate_from_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Generate image from uploaded photo"""
        try:
            user_id = update.effective_user.id
            
            # Check if photo exists
            if not update.message.photo:
                await update.message.reply_text("לא זוהתה תמונה תקינה. נסה לשלוח קובץ אחר.")
                return
            
            # Show progress message
            progress_msg = await update.message.reply_text("יוצר עבורך תמונה חדשה… זה עשוי לקחת עד חצי דקה ⏳")
            
            # Get photo file
            photo = update.message.photo[-1]  # Get highest resolution
            file = await context.bot.get_file(photo.file_id)
            photo_url = file.file_path
            
            # API request - Runware format: array with auth + task
            payload = [
                {
                    "taskType": "authentication",
                    "apiKey": self.api_key
                },
                {
                    "taskType": "imageInference",
                    "taskUUID": str(uuid.uuid4()),
                    "positivePrompt": """Professional real estate agent portrait, preserve exact same facial features and identity, 
wearing elegant business suit with tie or smart blazer with dress shirt, 
clean minimalist studio background (solid white or light grey), 
remove all background objects furniture and clutter, 
professional studio lighting setup, 
confident professional business pose, 
confident professional business pose with arms crossed or hands visible, 
high-end corporate headshot photography, sharp focus, photorealistic""",
                    "negativePrompt": "casual clothing, t-shirt, hoodie, home background, messy background, blurry, low quality, distorted face, different person",
                    "model": self.model_img2img,
                    "seedImage": photo_url,
                    "strength": 0.65,
                    "width": 1024,
                    "height": 1024,
                    "numberResults": 1
                }
            ]
            
            logger.info(f"Sending image-to-image request to Runware API")
            logger.info(f"Photo URL: {photo_url}")
            logger.info(f"Payload: {payload}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.api_url, json=payload, headers=self.headers) as response:
                    logger.info(f"Runware API response status: {response.status}")
                    response_text = await response.text()
                    logger.info(f"Runware API raw response: {response_text}")
                    
                    try:
                        result = await response.json()
                        logger.info(f"Runware API parsed response: {result}")
                    except:
                        result = None
                        logger.error(f"Failed to parse JSON response")
                    
                    if response.status == 200 and result:
                        # Extract image URL
                        if 'data' in result and len(result['data']) > 0:
                            image_url = result['data'][0].get('imageURL')
                            logger.info(f"Image URL: {image_url}")
                            
                            if image_url:
                                # Delete progress message
                                await progress_msg.delete()
                                
                                # Send image
                                await update.message.reply_photo(
                                    photo=image_url,
                                    caption="✅ התמונה שלך מוכנה!"
                                )
                                
                                # Show buttons
                                keyboard = [
                                    [InlineKeyboardButton("🎨 צור שוב", callback_data="image_gen_from_image")],
                                    [InlineKeyboardButton("↩️ תפריט ראשי", callback_data="back_to_main")]
                                ]
                                await update.message.reply_text(
                                    "מה תרצה לעשות?",
                                    reply_markup=InlineKeyboardMarkup(keyboard)
                                )
                                
                                # Increment usage counter
                                await self.increment_usage(user_id)
                                
                                # Clear state
                                db.set_user_waiting_for(user_id, None)
                                return
                    
                    # Failed
                    logger.error(f"Failed to generate image. Status: {response.status}, Result: {result}")
                    await progress_msg.edit_text("לא הצלחתי ליצור את התמונה כרגע. נסה שוב בעוד רגע.")
                    
        except Exception as e:
            logger.error(f"Error generating image from photo: {e}")
            await update.message.reply_text("לא הצלחתי ליצור את התמונה כרגע. נסה שוב בעוד רגע.")
    
    async def increment_usage(self, user_id: int):
        """Increment image generation usage counter"""
        try:
            with sqlite3.connect(db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET image_gen_used = COALESCE(image_gen_used, 0) + 1 
                    WHERE user_id = ?
                """, (user_id,))
                conn.commit()
                logger.info(f"Incremented image_gen_used for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")

# Global instance
image_generator = ImageGenerator()

