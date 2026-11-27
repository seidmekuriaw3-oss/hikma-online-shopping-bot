# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - የመጀመሪያ ሜኑ እጅ አያያዝ
ይህ ፋይል የ /start ትዕዛዝ እና የመጀመሪያ ሜኑ እጅ አያያዞችን ይይዛል
"""

import logging
import html
from typing import Optional
from datetime import datetime
from pathlib import Path

from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from config import BASE_DIR, config
from database import Database
from utils.helpers import get_text, get_lang, get_user_lang
from keyboards.reply import get_main_menu, get_language_menu
from keyboards.inline import get_start_keyboard
from services.notifications import notify_admin
from handlers.support import clear_support_state, show_help_center

logger = logging.getLogger(__name__)

HELP_TEXT_KEYWORDS = {'እርዳታ', 'እፈልጋለሁ', 'help'}
MAIN_MENU_TEXT_KEYWORDS = {
    'ወደ መጀመሪያ',
    'ዋና ማውጫ',
    'main menu',
}


def _normalize_menu_keyword(text: Optional[str]) -> str:
    return ''.join(
        character
        for character in (text or '').casefold()
        if character.isalnum()
    )


def _matches_menu_keywords(text: Optional[str], keywords: set) -> bool:
    normalized = _normalize_menu_keyword(text)
    return normalized in {_normalize_menu_keyword(keyword) for keyword in keywords}


def show_welcome(chat_id: int, user_id: int, db: Database, bot: TeleBot):
    """Send the branded welcome photo and localized customer menus."""
    lang = get_user_lang(db, user_id)
    user = db.get_user(user_id)
    first_name = (user or {}).get('first_name') or get_text(
        lang, 'customer_name'
    )
    caption = (
        f"<b>Hikma Online Shopping</b>\n"
        f"👋 {get_text(lang, 'welcome_greeting')} "
        f"{html.escape(first_name).replace('*', '&#42;')}!\n\n"
        f"{get_text(lang, 'welcome_intro')}\n\n"
        f"⚡ {get_text(lang, 'welcome_fast_delivery')}\n"
        f"🔒 {get_text(lang, 'welcome_secure_payment')}\n"
        f"✨ {get_text(lang, 'welcome_quality')}\n\n"
        f"{get_text(lang, 'quick_start_hint')}"
    )
    quick_actions = get_start_keyboard(lang)
    configured_photo = (
        config.bot.WELCOME_BANNER_FILE_ID
        or config.bot.WELCOME_BANNER_URL
    )
    local_banner = BASE_DIR / 'assets' / 'welcome_banner.png'
    photo_sent = False

    if configured_photo:
        try:
            bot.send_photo(
                chat_id,
                configured_photo,
                caption=caption,
                parse_mode='HTML',
                reply_markup=quick_actions,
            )
            photo_sent = True
        except Exception:
            logger.exception("Configured welcome banner could not be sent")

    if not photo_sent and local_banner.is_file():
        try:
            with local_banner.open('rb') as photo:
                bot.send_photo(
                    chat_id,
                    photo,
                    caption=caption,
                    parse_mode='HTML',
                    reply_markup=quick_actions,
                )
            photo_sent = True
        except Exception:
            logger.exception("Local welcome banner could not be sent")

    if not photo_sent:
        logger.error("No welcome banner could be sent; using text welcome")
        bot.send_message(
            chat_id,
            caption,
            parse_mode='HTML',
            reply_markup=quick_actions,
        )

    bot.send_message(
        chat_id,
        get_text(lang, 'main_menu_hint'),
        reply_markup=get_main_menu(user_id, db),
    )


def register(bot: TeleBot, db: Database):
    """የ /start ትዕዛዝ እና ተዛማጅ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== /start ትዕዛዝ ====================
    
    @bot.message_handler(commands=['start'])
    def start_command(message: Message):
        """የ /start ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        clear_support_state(user_id)
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        
        # ተጠቃሚን መመዝገብ
        user = db.get_user(user_id)
        
        is_new_user = not user
        if is_new_user:
            # አዲስ ተጠቃሚ
            db.create_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                lang='am'  # ነባሪ ቋንቋ
            )
            logger.info(f"🆕 አዲስ ተጠቃሚ: {user_id} (@{username})")
            
            # ለአስተዳዳሪ ማሳወቅ
            notify_admin(
                bot,
                f"🆕 *አዲስ ተጠቃሚ ተመዝግቧል!*\n\n"
                f"👤 ስም: {first_name} {last_name or ''}\n"
                f"🔹 @{username or 'Unknown'}\n"
                f"🆔 ID: {user_id}\n"
                f"📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            # ነባር ተጠቃሚን ማዘመን
            db.update_user(
                user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                last_active=datetime.now().isoformat()
            )
        
        # የእንቅስቃሴ ሎግ
        db.log_activity(user_id, 'start', 'ቦቱን ጀምሯል')
        
        # ቋንቋ ምርጫ ማሳየት
        lang = get_user_lang(db, user_id)
        
        if is_new_user:
            show_welcome(message.chat.id, user_id, db, bot)
        elif not lang or lang not in ['am', 'en']:
            # ቋንቋ ካልተመረጠ - የቋንቋ ምርጫ ማሳየት
            markup = get_language_menu()
            bot.send_message(
                message.chat.id,
                "👋 " + get_text(
                    config.language.DEFAULT_LANGUAGE,
                    'welcome',
                ) + "\n\n" + get_text(
                    config.language.DEFAULT_LANGUAGE,
                    'choose_language',
                ),
                reply_markup=markup
            )
        else:
            # ዋና ሜኑ ማሳየት
            show_welcome(message.chat.id, user_id, db, bot)
    
    # ==================== የቋንቋ ምርጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
    def handle_language_selection(call: CallbackQuery):
        """የቋንቋ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = 'am' if call.data == 'lang_am' else 'en'
        
        # ቋንቋ ማስቀመጥ
        db.update_user(user_id, lang=lang)
        db.log_activity(user_id, 'set_lang', f'ቋንቋ: {lang}')
        
        # ማስታወቂያ
        welcome_msg = get_text(lang, 'welcome')
        bot.answer_callback_query(call.id, welcome_msg)
        
        # መልዕክቱን መሰረዝ
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        # ዋና ሜኑ ማሳየት
        show_welcome(call.message.chat.id, user_id, db, bot)
    
    # ==================== ወደ ዋና ሜኑ መመለስ ====================
    
    @bot.message_handler(commands=['menu'])
    def menu_command(message: Message):
        """የ /menu ትዕዛዝ - ዋና ሜኑ ማሳየት"""
        user_id = message.from_user.id
        clear_support_state(user_id)
        show_welcome(message.chat.id, user_id, db, bot)
    
    @bot.message_handler(commands=['help'])
    def help_command(message: Message):
        """የ /help ትዕዛዝ - እርዳታ ማሳየት"""
        user_id = message.from_user.id
        show_help_center(message.chat.id, user_id, db, bot)

    @bot.message_handler(
        func=lambda message: _matches_menu_keywords(
            message.text, HELP_TEXT_KEYWORDS
        )
    )
    def help_text_command(message: Message):
        help_command(message)

    @bot.message_handler(
        func=lambda message: _matches_menu_keywords(
            message.text, MAIN_MENU_TEXT_KEYWORDS
        )
    )
    def menu_text_command(message: Message):
        menu_command(message)

    @bot.message_handler(commands=['lang'])
    def language_command(message: Message):
        lang = get_user_lang(db, message.from_user.id)
        bot.send_message(
            message.chat.id,
            "🌍 " + get_text(lang, 'choose_language'),
            reply_markup=get_language_menu()
        )

    @bot.message_handler(
        func=lambda message: message.text in ('🇪🇹 አማርኛ', '🇬🇧 English')
    )
    def handle_language_text(message: Message):
        lang = 'am' if message.text == '🇪🇹 አማርኛ' else 'en'
        user_id = message.from_user.id
        db.update_user(user_id, lang=lang)
        db.log_activity(user_id, 'set_lang', f'Language: {lang}')
        show_welcome(message.chat.id, user_id, db, bot)
    
    # ==================== የመጀመሪያ ሜኑ ማሳየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
    def handle_main_menu(call: CallbackQuery):
        """ወደ ዋና ሜኑ መመለስ"""
        user_id = call.from_user.id
        clear_support_state(user_id)
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_welcome(call.message.chat.id, user_id, db, bot)
    
# ==================== ተጨማሪ ትዕዛዞች ====================

def register_additional_commands(bot: TeleBot, db: Database):
    """ተጨማሪ ትዕዛዞችን መመዝገብ"""
    
    @bot.message_handler(commands=['profile'])
    def profile_command(message: Message):
        """የ /profile ትዕዛዝ - መገለጫ ማሳየት"""
        from handlers.user import show_user_profile
        show_user_profile(message, db, bot)
    
    @bot.message_handler(commands=['orders'])
    def orders_command(message: Message):
        """የ /orders ትዕዛዝ - ትዕዛዞችን ማሳየት"""
        from handlers.orders import show_user_orders
        show_user_orders(message, db, bot)
    
    @bot.message_handler(commands=['cart'])
    def cart_command(message: Message):
        """የ /cart ትዕዛዝ - ጋሪ ማሳየት"""
        from handlers.orders import show_cart
        show_cart(message, db, bot)
    
    @bot.message_handler(commands=['admin'])
    def admin_command(message: Message):
        """የ /admin ትዕዛዝ - የአስተዳዳሪ ፓነል"""
        from handlers.admin import show_admin_panel
        show_admin_panel(message, db, bot)
    
    @bot.message_handler(commands=['stats'])
    def stats_command(message: Message):
        """የ /stats ትዕዛዝ - ስታቲስቲክስ ማሳየት"""
        from handlers.admin import show_stats
        show_stats(message, db, bot)