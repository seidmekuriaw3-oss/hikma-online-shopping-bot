# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - የመልዕክት እጅ አያያዝ
ይህ ፋይል ሁሉንም የመደበኛ መልዕክቶች እጅ አያያዝን ይይዛል
"""

import logging
import re
from functools import wraps
from typing import Optional
from datetime import datetime

import psycopg2
from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang
from keyboards.reply import get_main_menu, get_admin_menu
from utils.helpers import format_currency

logger = logging.getLogger(__name__)


class _DatabaseErrorReportingBot:
    """Report PostgreSQL failures from message and callback handlers safely."""

    def __init__(self, bot, db=None):
        self._bot = bot
        self._db = db

    def __getattr__(self, name):
        return getattr(self._bot, name)

    def _wrap(self, handler):
        @wraps(handler)
        def guarded(update, *args, **kwargs):
            try:
                return handler(update, *args, **kwargs)
            except psycopg2.Error:
                from config import config
                lang = config.language.DEFAULT_LANGUAGE
                user = getattr(update, 'from_user', None)
                if self._db is not None and user is not None:
                    try:
                        lang = get_user_lang(self._db, user.id)
                    except psycopg2.Error:
                        logger.warning(
                            "Could not load user language while reporting a database failure"
                        )
                message = "⚠️ " + get_text(
                    lang,
                    'database_unavailable',
                )
                try:
                    if hasattr(update, 'data') and hasattr(update, 'id'):
                        self._bot.answer_callback_query(update.id, message, show_alert=True)
                    elif getattr(update, 'chat', None):
                        self._bot.send_message(update.chat.id, message)
                except Exception:
                    logger.exception("Could not notify the user about a database failure")
                return None
        return guarded

    def message_handler(self, *args, **kwargs):
        decorator = self._bot.message_handler(*args, **kwargs)
        return lambda handler: decorator(self._wrap(handler))

    def callback_query_handler(self, *args, **kwargs):
        decorator = self._bot.callback_query_handler(*args, **kwargs)
        return lambda handler: decorator(self._wrap(handler))

    def register_next_step_handler(self, message, callback, *args, **kwargs):
        return self._bot.register_next_step_handler(
            message, self._wrap(callback), *args, **kwargs
        )


def toggle_subscription(message: Message, db: Database, bot: TeleBot, subscribe: bool):
    """Update notification subscription from the reply keyboard."""
    user_id = message.from_user.id
    status = 1 if subscribe else 0
    db.update_user(user_id, is_subscribed=status)
    db.log_activity(user_id, 'toggle_subscription', f'አዲስ ሁኔታ: {status}')
    lang = get_user_lang(db, user_id)
    key = 'subscribed' if subscribe else 'unsubscribed'
    bot.send_message(
        message.chat.id,
        f"✅ {get_text(lang, 'subscription')}: {get_text(lang, key)}"
    )


def show_products_by_category(message: Message, category: str, db: Database, bot: TeleBot):
    from handlers.products import show_category_products as show
    return show(message, category, db, bot)


def show_user_orders(message: Message, db: Database, bot: TeleBot):
    from handlers.orders import show_user_orders as show
    if show:
        return show(message, db, bot)
    return None


def show_cart(message: Message, db: Database, bot: TeleBot):
    from handlers.orders import show_cart as show
    if show:
        return show(message, db, bot)
    return None


def show_user_profile(message: Message, db: Database, bot: TeleBot):
    from handlers.user import show_user_profile as show
    return show(message, db, bot)


def show_admin_panel(message: Message, db: Database, bot: TeleBot):
    """Display the admin keyboard for an admin user."""
    from config import config
    if message.from_user.id not in config.bot.ADMIN_IDS:
        lang = get_user_lang(db, message.from_user.id)
        bot.send_message(
            message.chat.id,
            "⛔ " + get_text(lang, 'not_admin'),
        )
        return False
    lang = get_user_lang(db, message.from_user.id)
    bot.send_message(
        message.chat.id,
        "⚙️ " + get_text(lang, 'admin_panel'),
        reply_markup=get_admin_menu(message.from_user.id, lang),
    )
    return True


def register_handlers(bot: TeleBot, db: Database):
    """Package-level API expected by main.py."""
    from handlers import start, products, orders, payments, user, admin, callback

    guarded_bot = _DatabaseErrorReportingBot(bot, db)
    # Register specific handlers before messages.py's catch-all text handler.
    for module in (start, products, orders, payments, user, admin, callback):
        module.register(guarded_bot, db)
    start.register_additional_commands(guarded_bot, db)
    register(guarded_bot, db)


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

        # ለአስተዳዳሪ የምርት መጨመር ተራ እውቅና ያለው ግብዓት በእውነተኛ ሂደት እንዲተካ ይደረጋል
        try:
            from handlers.admin import admin_states, route_admin_product_step
            if user_id in admin_states and admin_states[user_id].get('action') == 'add_product':
                if route_admin_product_step(message, db, bot):
                    return
        except Exception:
            pass

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
            show_products_by_category(message, 'Men', db, bot)
            return
        
        if text in ['👗 የሴት ልብሶች', '👗 Women\'s Clothing', 'የሴት ልብሶች 👗', 'Women\'s Clothing 👗']:
            show_products_by_category(message, 'Women', db, bot)
            return
        
        # ትዕዛዞች
        if text in ['📋 ትዕዛዞቼ', '📋 My Orders', 'ትዕዛዞቼ 📋', 'My Orders 📋']:
            show_user_orders(message, db, bot)
            return
        
        # ጋሪ
        if text in ['🛒 ጋሪ', '🛒 Cart', 'ጋሪ 🛒', 'Cart 🛒']:
            show_cart(message, db, bot)
            return
        
        # መገለጫ
        if text in ['👤 መገለጫ', '👤 Profile', 'መገለጫ 👤', 'Profile 👤']:
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
        lang = get_user_lang(db, user_id)
        bot.reply_to(message, "📸 " + get_text(lang, 'photo_received'))
    
    # ==================== ሌሎች የመልዕክት አይነቶች ====================
    
    @bot.message_handler(content_types=['document'])
    def handle_document_messages(message: Message):
        """የዶክመንት መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        db.log_activity(user_id, 'document', 'ዶክመንት ልኳል')
        bot.reply_to(message, "📄 " + get_text(lang, 'document_received'))
    
    @bot.message_handler(content_types=['contact'])
    def handle_contact_messages(message: Message):
        """የእውቂያ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        contact = message.contact
        
        if contact:
            # የስልክ ቁጥር ማስቀመጥ
            phone = contact.phone_number
            db.update_user(user_id, phone=phone)
            db.log_activity(user_id, 'contact', f'ስልክ: {phone}')
            
            bot.reply_to(
                message,
                "✅ " + get_text(lang, 'contact_received').format(phone)
            )
    
    @bot.message_handler(content_types=['location'])
    def handle_location_messages(message: Message):
        """የመገኛ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        location = message.location
        
        if location:
            db.log_activity(
                user_id, 
                'location', 
                f'Lat: {location.latitude}, Lon: {location.longitude}'
            )
            bot.reply_to(
                message,
                "📍 " + get_text(lang, 'location_received').format(
                    location.latitude,
                    location.longitude,
                )
            )
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_contact_info(message: Message, db: Database, bot: TeleBot):
        from handlers.messages import show_contact_info as show
        return show(message, db, bot)
    
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
            "❓ " + get_text(lang, 'menu_help_hint')
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
            "📨 " + get_text(get_user_lang(db, user_id), 'unsupported_content_received')
        )