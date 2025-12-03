"""
Single number WhatsApp sending functionality
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import db

logger = logging.getLogger(__name__)

async def handle_single_number_request(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle single number sending request - always ask for connection code first"""
    try:
        user_id = update.effective_user.id
        language = db.get_user_language(user_id)
        
        # Mark that we're in single number flow
        context.user_data['single_number_flow'] = True
        
        # Always ask for connection code (same as regular WhatsApp flow)
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
        logger.error(f"Error handling single number request: {e}")
        error_message = "❌ שגיאה" if language == 'hebrew' else "❌ Error"
        await update.callback_query.answer(error_message, show_alert=True)

async def continue_to_phone_number(update: Update, context: ContextTypes.DEFAULT_TYPE, language: str):
    """Continue to phone number input after connection code is validated"""
    try:
        user_id = update.effective_user.id
        
        # Set user state to waiting for phone number
        db.set_user_waiting_for(user_id, 'single_phone_number')
        
        message = """📱 **שליחה למספר בודד**

הכנס מספר טלפון""" if language == 'hebrew' else """📱 **Send to Single Number**

Enter phone number"""
        
        keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]]
        
        # Check if this is from callback or message
        if update.message:
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error continuing to phone number: {e}")

async def handle_instance_code_for_single(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, instance_code: str):
    """Handle instance code input specifically for single number flow"""
    try:
        user_id = update.effective_user.id
        language = db.get_user_language(user_id)
        
        # Validate instance code
        if await whatsapp_manager._validate_instance_code(instance_code):
            # Save instance code
            db.set_user_whatsapp_instance(user_id, instance_code)
            
            # Automatically save default token
            db.set_user_whatsapp_token(user_id, whatsapp_manager.default_token)
            
            # Clear waiting state
            db.set_user_waiting_for(user_id, None)
            
            # Now continue to single number flow - ask for phone number
            success_msg = "✅ התחברת בהצלחה!\n\n" if language == 'hebrew' else "✅ Connected successfully!\n\n"
            await update.message.reply_text(success_msg)
            
            # Trigger single number request again (now with connection)
            from telegram import CallbackQuery
            # Create a fake callback query to reuse the flow
            context.user_data['has_connection'] = True
            await _ask_for_phone_number(update, context, language)
        else:
            error_message = "❌ קוד החיבור לא תקין. נסה שוב." if language == 'hebrew' else "❌ Invalid connection code. Try again."
            await update.message.reply_text(error_message)
            # Don't clear waiting state - let user try again
    except Exception as e:
        logger.error(f"Error handling instance code for single: {e}")
        await update.message.reply_text("❌ שגיאה" if db.get_user_language(update.effective_user.id) == 'hebrew' else "❌ Error")

async def _ask_for_phone_number(update, context, language):
    """Ask user for phone number"""
    user_id = update.effective_user.id
    db.set_user_waiting_for(user_id, 'single_phone_number')
    
    message = """📱 **שליחה למספר בודד**

הכנס מספר טלפון""" if language == 'hebrew' else """📱 **Send to Single Number**

Enter phone number"""
    
    keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]]
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_single_number_input(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str):
    """Handle phone number input for single number sending"""
    try:
        user_id = update.effective_user.id
        language = db.get_user_language(user_id)
        
        # Normalize phone number
        phone = phone_number.strip().replace('-', '').replace(' ', '')
        
        # Validate phone number format
        if not phone:
            await update.message.reply_text("❌ מספר לא תקין" if language == 'hebrew' else "❌ Invalid number")
            return
        
        # Convert to international format
        if phone.startswith('0'):
            phone = '972' + phone[1:]
        elif phone.startswith('+'):
            phone = phone[1:]
        
        # Validate it's a number
        if not phone.isdigit() or len(phone) < 10:
            await update.message.reply_text("❌ מספר לא תקין" if language == 'hebrew' else "❌ Invalid number")
            return
        
        # Save phone number temporarily in context
        context.user_data['single_phone_number'] = phone
        
        # Clear waiting state
        db.set_user_waiting_for(user_id, None)
        
        # Show message template selection
        await _show_template_selection(whatsapp_manager, update, context, phone)
        
    except Exception as e:
        logger.error(f"Error handling single number input: {e}")
        await update.message.reply_text("❌ שגיאה" if language == 'hebrew' else "❌ Error")

async def _show_template_selection(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
    """Show message template selection for single number"""
    try:
        user_id = update.effective_user.id
        language = db.get_user_language(user_id)
        
        message = f"""✅ המספר נשמר: {phone}

עכשיו בחר תבנית הודעה:""" if language == 'hebrew' else f"""✅ Number saved: {phone}

Now choose a message template:"""
        
        keyboard = [
            [InlineKeyboardButton("📝 תבנית 1: שאלה כללית", callback_data="single_template_1")],
            [InlineKeyboardButton("🏠 תבנית 2: מכירת דירה", callback_data="single_template_2")],
            [InlineKeyboardButton("✍️ הודעה מותאמת אישית", callback_data="single_template_custom")],
            [InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]
        ]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error showing template selection: {e}")


async def handle_template_selection(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Handle template selection for single number"""
    try:
        user_id = update.callback_query.from_user.id
        language = db.get_user_language(user_id)
        
        # Get saved phone number
        phone = context.user_data.get('single_phone_number')
        if not phone:
            await update.callback_query.answer("❌ מספר לא נמצא", show_alert=True)
            return
        
        templates = {
            'single_template_1': 'היי, בקשר למודעה - האם יש אופציה של מכירת הדירה?',
            'single_template_2': 'שלום! בקשר לדירה למכירה, יש לי מספר לקוחות פוטנציאליים, האם תיהיו מעוניינים לקבל פרטים נוספים או לתאם שיחה טלפונית?'
        }
        
        if callback_data == 'single_template_custom':
            # Ask for custom message
            db.set_user_waiting_for(user_id, 'single_custom_message')
            message = "✍️ הכנס את ההודעה המותאמת אישית:" if language == 'hebrew' else "✍️ Enter your custom message:"
            keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]]
            await update.callback_query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        message_text = templates.get(callback_data, '')
        if not message_text:
            await update.callback_query.answer("❌ תבנית לא נמצאה", show_alert=True)
            return
        
        # Save message text
        context.user_data['single_message_text'] = message_text
        
        # Ask about AI
        await _show_ai_choice(whatsapp_manager, update, context, phone, message_text)
        
    except Exception as e:
        logger.error(f"Error handling template selection: {e}")
        await update.callback_query.answer("❌ שגיאה", show_alert=True)

async def handle_custom_message_input(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    """Handle custom message input for single number"""
    try:
        user_id = update.effective_user.id
        
        # Get saved phone number
        phone = context.user_data.get('single_phone_number')
        if not phone:
            await update.message.reply_text("❌ מספר לא נמצא")
            return
        
        # Clear waiting state
        db.set_user_waiting_for(user_id, None)
        
        # Save message text
        context.user_data['single_message_text'] = message_text
        
        # Ask about AI
        await _show_ai_choice_message(whatsapp_manager, update, context, phone, message_text)
        
    except Exception as e:
        logger.error(f"Error handling custom message input: {e}")
        await update.message.reply_text("❌ שגיאה")

async def _show_ai_choice(whatsapp_manager, update, context, phone, message_text):
    """Show AI choice for callback query"""
    try:
        user_id = update.callback_query.from_user.id
        language = db.get_user_language(user_id)
        
        ai_choice_text = f"""📱 **מספר:** {phone}
📝 **הודעה:** {message_text}

🤖 **האם להפעיל AI לתגובות אוטומטיות?**

אם תבחר כן - כשהמפרסם יענה, AI יגיב אוטומטית לפי הפרומפט שתגדיר.""" if language == 'hebrew' else f"""📱 **Number:** {phone}
📝 **Message:** {message_text}

🤖 **Activate AI for automatic responses?**

If you choose yes - when the advertiser responds, AI will reply automatically according to the prompt you set."""
        
        keyboard = [
            [InlineKeyboardButton("✅ כן, הפעל AI", callback_data="single_ai_yes")],
            [InlineKeyboardButton("❌ לא, שלח רגיל", callback_data="single_ai_no")],
            [InlineKeyboardButton("🔙 חזור", callback_data="whatsapp_menu")]
        ]
        
        await update.callback_query.edit_message_text(
            ai_choice_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing AI choice: {e}")

async def _show_ai_choice_message(whatsapp_manager, update, context, phone, message_text):
    """Show AI choice for regular message"""
    try:
        user_id = update.effective_user.id
        language = db.get_user_language(user_id)
        
        ai_choice_text = f"""📱 **מספר:** {phone}
📝 **הודעה:** {message_text}

🤖 **האם להפעיל AI לתגובות אוטומטיות?**

אם תבחר כן - כשהמפרסם יענה, AI יגיב אוטומטית לפי הפרומפט שתגדיר.""" if language == 'hebrew' else f"""📱 **Number:** {phone}
📝 **Message:** {message_text}

🤖 **Activate AI for automatic responses?**

If you choose yes - when the advertiser responds, AI will reply automatically according to the prompt you set."""
        
        keyboard = [
            [InlineKeyboardButton("✅ כן, הפעל AI", callback_data="single_ai_yes")],
            [InlineKeyboardButton("❌ לא, שלח רגיל", callback_data="single_ai_no")],
            [InlineKeyboardButton("🔙 חזור", callback_data="whatsapp_menu")]
        ]
        
        await update.message.reply_text(
            ai_choice_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error showing AI choice: {e}")

async def handle_ai_choice(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Handle AI choice for single number"""
    try:
        user_id = update.callback_query.from_user.id
        language = db.get_user_language(user_id)
        
        phone = context.user_data.get('single_phone_number')
        message_text = context.user_data.get('single_message_text')
        
        if not phone or not message_text:
            await update.callback_query.answer("❌ שגיאה - חסרים נתונים", show_alert=True)
            return
        
        if callback_data == 'single_ai_yes':
            # Enable AI - directly generate webhook
            context.user_data['single_ai_enabled'] = True
            
            # Generate webhook URL
            webhook_url = "https://3000-id8lqdvlt6ype8inajckp-8ed70fe1.manus-asia.computer/webhook/whatsapp"
            db.set_user_webhook_url(user_id, webhook_url)
            context.user_data['single_webhook_url'] = webhook_url
            
            webhook_text = f"""🪝 **זה ה-webhook שלך להפעיל תגובות AI**

העתק אותו ולחץ "🔢המספרים שלי" לחבר אותו:

```
{webhook_url}
```

לאחר מכן לחץ ✅ חיברתי אפשר להמשיך""" if language == 'hebrew' else f"""🪝 **This is your webhook to activate AI responses**

Copy it and click "🔢My Numbers" to connect it:

```
{webhook_url}
```

Then click ✅ Connected, can continue"""
            
            from telegram import WebAppInfo
            keyboard = [
                [InlineKeyboardButton("✅ חיברתי אפשר להמשיך", callback_data="webhook_continue")],
                [InlineKeyboardButton("🔢 המספרים שלי", web_app=WebAppInfo(url="https://yad2bot.co.il/user"))],
                [InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]
            ]
            
            await update.callback_query.edit_message_text(
                webhook_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            # No AI - send directly
            context.user_data['single_ai_enabled'] = False
            await _send_single_message(whatsapp_manager, update, context)
        
    except Exception as e:
        logger.error(f"Error handling AI choice: {e}")
        await update.callback_query.answer("❌ שגיאה", show_alert=True)

async def handle_webhook_choice(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Handle webhook URL choice (use saved or enter new)"""
    try:
        user_id = update.callback_query.from_user.id
        language = db.get_user_language(user_id)
        
        if callback_data == 'use_saved_webhook':
            # Use saved webhook
            saved_webhook = db.get_user_webhook_url(user_id)
            context.user_data['single_webhook_url'] = saved_webhook
            
            # Continue to AI prompt
            await _ask_for_ai_prompt(whatsapp_manager, update, context)
        else:
            # Generate webhook URL
            webhook_url = "https://3000-id8lqdvlt6ype8inajckp-8ed70fe1.manus-asia.computer/webhook/whatsapp"
            
            # Save webhook URL
            db.set_user_webhook_url(user_id, webhook_url)
            context.user_data['single_webhook_url'] = webhook_url
            
            webhook_text = f"""🪝 **זה ה-webhook שלך להפעיל תגובות AI**

העתק אותו ולחץ "🔢המספרים שלי" לחבר אותו:

```
{webhook_url}
```

לאחר מכן לחץ ✅ חיברתי אפשר להמשיך""" if language == 'hebrew' else f"""🪝 **This is your webhook to activate AI responses**

Copy it and click "🔢My Numbers" to connect it:

```
{webhook_url}
```

Then click ✅ Connected, can continue"""
            
            from telegram import WebAppInfo
            keyboard = [
                [InlineKeyboardButton("✅ חיברתי אפשר להמשיך", callback_data="webhook_continue")],
                [InlineKeyboardButton("🔢 המספרים שלי", web_app=WebAppInfo(url="https://yad2bot.co.il/user"))],
                [InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]
            ]
            await update.callback_query.edit_message_text(
                webhook_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error handling webhook choice: {e}")
        await update.callback_query.answer("❌ שגיאה", show_alert=True)

async def handle_webhook_continue(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle webhook continue button after user pastes webhook on yad2bot.co.il"""
    try:
        # Continue to AI prompt
        await _ask_for_ai_prompt(whatsapp_manager, update, context)
    except Exception as e:
        logger.error(f"Error handling webhook continue: {e}")
        await update.callback_query.answer("❌ שגיאה", show_alert=True)

async def handle_webhook_url_input(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, webhook_url: str):
    """Handle webhook URL input for single number"""
    try:
        user_id = update.effective_user.id
        
        # Clear waiting state
        db.set_user_waiting_for(user_id, None)
        
        # Save webhook URL
        db.set_user_webhook_url(user_id, webhook_url)
        context.user_data['single_webhook_url'] = webhook_url
        
        # Continue to AI prompt
        await _ask_for_ai_prompt_message(whatsapp_manager, update, context)
        
    except Exception as e:
        logger.error(f"Error handling webhook URL input: {e}")
        await update.message.reply_text("❌ שגיאה")

async def _ask_for_ai_prompt(whatsapp_manager, update, context):
    """Ask for AI prompt (from callback)"""
    try:
        user_id = update.callback_query.from_user.id
        language = db.get_user_language(user_id)
        
        db.set_user_waiting_for(user_id, 'single_ai_prompt')
        
        prompt_text = """🤖 **הגדר את הפרומפט ל-AI**

דוגמה:
```
שלום אתה סוכן נדל״ן בשם יניב גולן, התפקיד שלך הוא לאתר דירות שאפשר להוציא אותן למכירה.

נשלחה הודעה ראשונית למפרסמים בלוחות נדל״ן לגבי הדירה שלהם להשכרה:
 "היי, בקשר למודעה - האם יש אופציה של מכירת הדירה?"

כעת אתה מקבל את התגובות שלהם.
אם התגובה חיובית או פתוחה - תענה באופן טבעי, אישי ומקצועי.
המטרה שלך היא להמשיך את השיחה ולחתור לכיוון קביעת פגישה או שיחת טלפון.
```

הכנס את הפרומפט שלך:""" if language == 'hebrew' else """🤖 **Set AI Prompt**

Example:
```
You are a real estate agent named Yaniv Golan...
```

Enter your prompt:"""
        
        keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]]
        await update.callback_query.edit_message_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error asking for AI prompt: {e}")

async def _ask_for_ai_prompt_message(whatsapp_manager, update, context):
    """Ask for AI prompt (from message)"""
    try:
        user_id = update.effective_user.id
        language = db.get_user_language(user_id)
        
        db.set_user_waiting_for(user_id, 'single_ai_prompt')
        
        prompt_text = """🤖 **הגדר את הפרומפט ל-AI**

דוגמה:
```
שלום אתה סוכן נדל״ן בשם יניב גולן...
```

הכנס את הפרומפט שלך:""" if language == 'hebrew' else """🤖 **Set AI Prompt**

Example:
```
You are a real estate agent named Yaniv Golan...
```

Enter your prompt:"""
        
        keyboard = [[InlineKeyboardButton("❌ ביטול", callback_data="whatsapp_menu")]]
        await update.message.reply_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error asking for AI prompt: {e}")

async def handle_ai_prompt_input(whatsapp_manager, update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_text: str):
    """Handle AI prompt input for single number"""
    try:
        user_id = update.effective_user.id
        
        # Clear waiting state
        db.set_user_waiting_for(user_id, None)
        
        # Save AI settings
        context.user_data['single_ai_enabled'] = True
        context.user_data['single_ai_prompt'] = prompt_text
        
        # Send message
        await _send_single_message(whatsapp_manager, update, context)
        
    except Exception as e:
        logger.error(f"Error handling AI prompt input: {e}")
        await update.message.reply_text("❌ שגיאה")

async def _send_single_message(whatsapp_manager, update, context):
    """Send message to single number"""
    try:
        user_id = update.effective_user.id if hasattr(update, 'effective_user') else update.callback_query.from_user.id
        language = db.get_user_language(user_id)
        
        phone = context.user_data.get('single_phone_number')
        message_text = context.user_data.get('single_message_text')
        ai_enabled = context.user_data.get('single_ai_enabled', False)
        ai_prompt = context.user_data.get('single_ai_prompt', '')
        
        if not phone or not message_text:
            error_msg = "❌ נתונים חסרים" if language == 'hebrew' else "❌ Missing data"
            if hasattr(update, 'message'):
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.answer(error_msg, show_alert=True)
            return
        
        # Get WhatsApp credentials
        whatsapp_config = db.get_user_whatsapp_config(user_id)
        instance_id = whatsapp_config.get('instance_id', '')
        token = whatsapp_config.get('token', '')
        
        if not instance_id or not token:
            error_msg = "❌ חיבור WhatsApp לא נמצא" if language == 'hebrew' else "❌ WhatsApp connection not found"
            if hasattr(update, 'message'):
                await update.message.reply_text(error_msg)
            else:
                await update.callback_query.answer(error_msg, show_alert=True)
            return
        
        # Send loading message
        loading_msg = "🚀 שולח הודעה..." if language == 'hebrew' else "🚀 Sending message..."
        if hasattr(update, 'message'):
            status_message = await update.message.reply_text(loading_msg)
        else:
            await update.callback_query.answer(loading_msg)
            status_message = await update.callback_query.message.reply_text(loading_msg)
        
        # Send message via WhatsApp API
        import aiohttp
        async with aiohttp.ClientSession(headers=whatsapp_manager.headers) as session:
            # Format phone number
            formatted_phone = whatsapp_manager._format_phone_number(phone)
            
            success, response_data = await whatsapp_manager._send_single_message_monitored(
                session=session,
                instance_code=instance_id,
                phone=formatted_phone,
                message=message_text
            )
        
        if success:
            # Save AI settings if enabled
            if ai_enabled:
                db.set_ai_enabled(user_id, True)
                if ai_prompt:
                    db.set_ai_prompt(user_id, ai_prompt)
            
            success_text = f"""✅ **ההודעה נשלחה בהצלחה!**

📱 מספר: {phone}
📝 הודעה: {message_text}
🤖 AI: {'מופעל ✅' if ai_enabled else 'כבוי ❌'}""" if language == 'hebrew' else f"""✅ **Message sent successfully!**

📱 Number: {phone}
📝 Message: {message_text}
🤖 AI: {'Enabled ✅' if ai_enabled else 'Disabled ❌'}"""
            
            await status_message.edit_text(success_text, parse_mode='Markdown')
        else:
            # Check for specific error types
            error_detail = response_data.get('error_type', 'Unknown')
            if response_data.get('error_type') == 'expired_plan':
                error_text = "❌ המנוי פג תוקף\n\nיש לחדש את המנוי באתר yad2bot.co.il" if language == 'hebrew' else "❌ Subscription expired\n\nPlease renew at yad2bot.co.il"
            else:
                error_text = f"❌ שליחת ההודעה נכשלה\n\nסוג שגיאה: {error_detail}" if language == 'hebrew' else f"❌ Message sending failed\n\nError: {error_detail}"
            await status_message.edit_text(error_text)
        
        # Clear context data
        context.user_data.pop('single_phone_number', None)
        context.user_data.pop('single_message_text', None)
        context.user_data.pop('single_ai_enabled', None)
        context.user_data.pop('single_ai_prompt', None)
        
    except Exception as e:
        logger.error(f"Error sending single message: {e}")
        error_msg = "❌ שגיאה בשליחת ההודעה" if language == 'hebrew' else "❌ Error sending message"
        if hasattr(update, 'message'):
            await update.message.reply_text(error_msg)
        else:
            try:
                await update.callback_query.message.reply_text(error_msg)
            except:
                pass
