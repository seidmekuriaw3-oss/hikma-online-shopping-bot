# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - የመልዕክት እጅ አያያዝ
ይህ ፋይል ሁሉንም የመደበኛ መልዕክቶች እጅ አያያዝን ይይዛል
"""

import logging
import re
from typing import Optional
from datetime import datetime

from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang
from keyboards.inline import get_contact_keyboard

logger = logging.getLogger(__name__)


def show_contact_info(message: Message, db: Database, bot: TeleBot):
    lang = get_user_lang(db, message.from_user.id)
    text = (
        "🛍️ ሂክማ ኦንላይን ሾፒንግ\n\n"
        "📍 የመላኪያ አድራሻ ለማዘጋጀት ከግዢ ሂደቱ ውስጥ ያስገቡ።\n"
        "💬 ለጥያቄዎች ከታች ያለውን አዝራር ይጠቀሙ።"
        if lang == 'am'
        else "🛍️ Hikma Online Shopping\n\n"
        "📍 Add your delivery address during checkout.\n"
        "💬 For questions, use the contact button below."
    )
    return bot.send_message(
        message.chat.id,
        text,
        reply_markup=get_contact_keyboard(lang),
    )


def toggle_subscription(message: Message, db: Database, bot: TeleBot, subscribe: bool):
    """Update the user's notification subscription from the reply keyboard."""
    user_id = message.from_user.id
    status = 1 if subscribe else 0
    db.update_user(user_id, is_subscribed=status)
    db.log_activity(user_id, 'toggle_subscription', f'አዲስ ሁኔታ: {status}')
    lang = get_user_lang(db, user_id)
    key = 'subscribed' if subscribe else 'unsubscribed'
    bot.send_message(message.chat.id, f"✅ {get_text(lang, 'subscription')}: {get_text(lang, key)}")


def register(bot: TeleBot, db: Database):
    """የመልዕክት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ሁሉንም መልዕክቶች አያያዝ ====================
    
    @bot.message_handler(
        func=lambda message: bool(message.text) and not message.text.lstrip().startswith('/'),
        content_types=['text'],
    )
    def handle_text_messages(message: Message):
        """ሁሉንም የጽሁፍ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        text = message.text
        lang = get_user_lang(db, user_id)

        if not db.get_user(user_id):
            db.create_user(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                lang='am'
            )
        
        # የተጠቃሚ እንቅስቃሴ መመዝገብ
        db.log_activity(user_id, 'message', f'ተጠቃሚ: {text[:50]}')
        
        # የአስተዳዳሪ ሜኑ
        if text in [
            '⚙️ አስተዳደር', '⚙️ Admin', 'አስተዳደር ⚙️', 'Admin ⚙️',
            '⚙️ አስተዳዳሪ', '⚙️ Admin Panel',
        ]:
            from handlers.admin import show_admin_panel
            show_admin_panel(message, db, bot)
            return

        if text in ['🛍️ ምርቶች', '🛍️ Products']:
            from handlers.products import show_category_menu
            show_category_menu(message, db, bot)
            return
        
        # የምርት ምድቦች
        if text in ['👕 የወንድ ልብሶች', '👕 Men\'s Clothing', 'የወንድ ልብሶች 👕', 'Men\'s Clothing 👕']:
            from handlers.products import show_category_products
            show_category_products(message, 'Men', db, bot)
            return
        
        if text in ['👗 የሴት ልብሶች', '👗 Women\'s Clothing', 'የሴት ልብሶች 👗', 'Women\'s Clothing 👗']:
            from handlers.products import show_category_products
            show_category_products(message, 'Women', db, bot)
            return
        
        # ትዕዛዞች
        if text in ['📋 ትዕዛዞቼ', '📋 My Orders', 'ትዕዛዞቼ 📋', 'My Orders 📋']:
            from handlers.orders import show_user_orders
            show_user_orders(message, db, bot)
            return
        
        # ጋሪ
        if text in ['🛒 ጋሪ', '🛒 Cart', 'ጋሪ 🛒', 'Cart 🛒']:
            from handlers.orders import show_cart
            show_cart(message, db, bot)
            return
        
        # መገለጫ
        if text in ['👤 መገለጫ', '👤 Profile', 'መገለጫ 👤', 'Profile 👤']:
            from handlers.user import show_user_profile
            show_user_profile(message, db, bot)
            return

        if text in ['❤️ ተወዳጆች', '❤️ Wishlist', 'My Wishlist']:
            from handlers.callback import show_wishlist
            show_wishlist(message.chat.id, user_id, db, bot)
            return
        
        # አድራሻ
        if text in [
            '📍 አድራሻ', '📍 Address', 'አድራሻ እና ስልክ 📍',
            'Address & Phone 📍', '📍 አድራሻ እና ስልክ', '📍 Address & Phone',
            '📍 Contact',
        ]:
            show_contact_info(message, db, bot)
            return
        
        # ማስታወቂያ
        if text in ['📢 ለማስታወቂያ ተመዝገብ', '📢 Subscribe', 'ለማስታወቂያ ተመዝገብ 📢', 'Subscribe 📢']:
            toggle_subscription(message, db, bot, subscribe=True)
            return
        
        if text in [
            '🔕 ከማስታወቂያ ተመዝገብ', '🔕 Unsubscribe',
            'ከማስታወቂያ ተመዝገብ 🔕', 'Unsubscribe 🔕', '🔕 ከማስታወቂያ ውጣ',
        ]:
            toggle_subscription(message, db, bot, subscribe=False)
            return
        
        # ሌላ መልዕክት
        handle_other_messages(message, db, bot)
    
    # ==================== የፎቶ እጅ አያያዝ ====================
    
    @bot.message_handler(content_types=['photo'])
    def handle_photo_messages(message: Message):
        """የፎቶ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        
        # ተጠቃሚ በአስተዳዳሪ ሁነታ ላይ መሆኑን ማረጋገጥ
        from handlers.admin import is_admin_uploading
        if is_admin_uploading(user_id):
            from handlers.admin import handle_admin_photo
            handle_admin_photo(message, db, bot)
            return
        
        # መደበኛ የፎቶ መልዕክት
        db.log_activity(user_id, 'photo', 'ፎቶ ልኳል')
        bot.reply_to(message, "📸 ፎቶዎ ተቀብያለሁ! በቅርቡ እንመለከተዋለን.")
    
    # ==================== ሌሎች የመልዕክት አይነቶች ====================
    
    @bot.message_handler(content_types=['document'])
    def handle_document_messages(message: Message):
        """የዶክመንት መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        db.log_activity(user_id, 'document', 'ዶክመንት ልኳል')
        bot.reply_to(message, "📄 ዶክመንትዎ ተቀብያለሁ!")
    
    @bot.message_handler(content_types=['contact'])
    def handle_contact_messages(message: Message):
        """የእውቂያ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        contact = message.contact
        
        if contact:
            # የስልክ ቁጥር ማስቀመጥ
            phone = contact.phone_number
            db.update_user(user_id, phone=phone)
            db.log_activity(user_id, 'contact', f'ስልክ: {phone}')
            
            bot.reply_to(
                message,
                f"✅ የስልክ ቁጥርዎ {phone} ተመዝግቧል! 🙏"
            )
    
    @bot.message_handler(content_types=['location'])
    def handle_location_messages(message: Message):
        """የመገኛ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        location = message.location
        
        if location:
            db.log_activity(
                user_id, 
                'location', 
                f'Lat: {location.latitude}, Lon: {location.longitude}'
            )
            bot.reply_to(
                message,
                f"📍 መገኛዎ ተቀብያለሁ!\n"
                f"🗺️ ኬክሮስ: {location.latitude}\n"
                f"🗺️ ኬንትሮስ: {location.longitude}"
            )
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_contact_info(message: Message, db: Database, bot: TeleBot):
        return globals()['show_contact_info'](message, db, bot)
    
    def handle_other_messages(message: Message, db: Database, bot: TeleBot):
        """ሌሎች መልዕክቶችን አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        text = message.text
        
        # የተወሰኑ ቁልፍ ቃላት
        keywords = {
            'hi': get_text(lang, 'greeting'),
            'hello': get_text(lang, 'greeting'),
            'እንዴት': get_text(lang, 'how_are_you'),
            'አመሰግናለሁ': get_text(lang, 'thank_you_response'),
            'thank you': get_text(lang, 'thank_you_response'),
            'bye': get_text(lang, 'bye_response'),
            'ሰላም': get_text(lang, 'greeting'),
        }
        
        # ቁልፍ ቃል መፈተሽ
        for key, response in keywords.items():
            if key.lower() in text.lower():
                bot.reply_to(message, response)
                return
        
        # ቅናሽ ኮድ መፈተሽ
        discount_pattern = r'^[A-Z0-9]{5,20}$'
        if re.match(discount_pattern, text.upper()):
            from handlers.orders import apply_discount_code
            apply_discount_code(message, text.upper(), db, bot)
            return
        
        # የምርት ፍለጋ
        if len(text) > 2:
            from handlers.products import search_products
            search_products(message, text, db, bot)
            return
        
        # ነባሪ መልስ
        bot.reply_to(
            message,
            f"❓ እባክዎ ከሜኑ አዝራሮች ይምረጡ.\n\n"
            f"💡 እርዳታ ከፈለጉ /help ይጫኑ"
        )
    
    # ==================== ስህተት አያያዝ ====================
    
    @bot.message_handler(content_types=['voice', 'video', 'audio', 'sticker'])
    def handle_other_content_types(message: Message):
        """ሌሎች የመልዕክት አይነቶች አያያዝ"""
        user_id = message.from_user.id
        content_type = message.content_type
        
        db.log_activity(user_id, content_type, f'የ{content_type} መልዕክት ልኳል')
        
        # ለአስተዳዳሪ ማሳወቅ
        from services.notifications import notify_admin
        notify_admin(
            bot,
            f"📨 አዲስ {content_type} መልዕክት\n"
            f"👤 ተጠቃሚ: {message.from_user.first_name}\n"
            f"🆔 ID: {user_id}"
        )
        
        bot.reply_to(
            message,
            f"📨 መልዕክትዎ ተቀብያለሁ! "
            f"በቅርቡ እንመለከተዋለን. 🙏"
        )