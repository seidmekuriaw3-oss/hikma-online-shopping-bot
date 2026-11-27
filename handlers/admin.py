# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - የአስተዳዳሪ ፓነል እጅ አያያዝ
ይህ ፋይል ሁሉንም የአስተዳዳሪ ፓነል እጅ አያያዞችን ይይዛል
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from database import Database
from config import config
from utils.helpers import (
    get_text, get_user_lang, format_number, format_currency, format_payment_method, is_admin,
)
from keyboards.inline import (
    get_admin_keyboard, get_confirm_keyboard, get_admin_order_actions_keyboard,
    get_admin_product_category_keyboard,
)
from keyboards.admin import (
    get_admin_products_keyboard,
    get_admin_orders_keyboard,
    get_admin_users_keyboard,
    get_admin_reports_keyboard,
    get_admin_discounts_keyboard,
)
from services.notifications import notify_admins, send_broadcast

logger = logging.getLogger(__name__)

# ለአስተዳዳሪ ሂደቶች ጊዜያዊ መረጃ
admin_states = {}
admin_uploading = set()

_ADMIN_CATEGORY_KEYS = {
    'men': 'category_men',
    "men's clothing": 'category_men',
    "men's fashion": 'category_men',
    'women': 'category_women',
    "women's clothing": 'category_women',
    "women's fashion": 'category_women',
    'kids': 'category_kids',
    'kids & baby': 'category_kids',
    'pajamas': 'category_pajamas',
    'pajamas & loungewear': 'category_pajamas',
    'shoes': 'category_shoes',
    'shoes & footwear': 'category_shoes',
    'accessories': 'category_accessories',
    'bags & accessories': 'category_accessories',
}


def _localized_category(category, lang: str) -> str:
    if not category:
        return get_text(lang, 'unknown')
    normalized = str(category).strip().lower().replace('_', ' ').replace('-', ' ')
    key = _ADMIN_CATEGORY_KEYS.get(normalized)
    return get_text(lang, key) if key else str(category)


def _ensure_add_product_state(user_id: int) -> Dict:
    """Return a complete add-product state, recovering cleanly if it is missing."""
    state = admin_states.setdefault(user_id, {})
    if state.get('action') != 'add_product':
        state.clear()
        state.update(action='add_product', step=1, data={})
    state.setdefault('step', 1)
    if not isinstance(state.get('data'), dict):
        state['data'] = {}
    return state


def _get_admin_chat_id(update) -> Optional[int]:
    message = getattr(update, 'message', None) or update
    chat_id = getattr(getattr(message, 'chat', None), 'id', None)
    if chat_id is None:
        chat_id = getattr(getattr(update, 'from_user', None), 'id', None)
    return chat_id


def _send_admin_message(bot: TeleBot, update, text: str, **kwargs):
    """Send to the chat without relying on the source message still existing."""
    chat_id = _get_admin_chat_id(update)
    if chat_id is None:
        logger.warning("Cannot send admin response: update has no chat or user ID")
        return None
    return bot.send_message(chat_id, text, **kwargs)


def _notify_product_added(
    bot: TeleBot,
    data: Dict,
    product_id: int,
    lang: str,
) -> None:
    message = get_text(lang, 'product_added_admin_notification').format(
        name=data.get('name_am' if lang == 'am' else 'name_en')
        or get_text(lang, 'product'),
        price=data.get('price', 0),
        size=data.get('size') or '—',
        category=_localized_category(data.get('category'), lang),
        stock=data.get('stock_quantity', 0),
        product_id=product_id,
    )
    notify_admins(bot, message, parse_mode=None)


def route_admin_product_step(message: Message, db: Database, bot: TeleBot):
    """Route an admin input through the active add-product state machine."""
    user_id = message.from_user.id
    state = admin_states.get(user_id)
    if not state or state.get('action') != 'add_product':
        return False

    step = state.get('step', 1)
    router = {
        1: process_add_product_name,
        2: process_add_product_name_en,
        3: process_add_product_price,
        4: process_add_product_size,
        5: process_add_product_category,
        6: process_add_product_stock,
        7: process_add_product_image,
    }
    func = router.get(step)
    if func:
        func(message, db, bot)
        return True
    return False


def start_add_product(
    message: Message,
    db: Database,
    bot: TeleBot,
    user_id: Optional[int] = None,
):
    """አዲስ ምርት መጨመር ሂደት መጀመር"""
    user_id = user_id if user_id is not None else message.from_user.id
    lang = get_user_lang(db, user_id)
    state = _ensure_add_product_state(user_id)
    state.update(step=1, data={})

    prompt = bot.send_message(
        _get_admin_chat_id(message),
        "📝 *" + get_text(lang, 'add_product') + "*\n\n"
        + get_text(lang, 'enter_product_name_am'),
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(prompt, process_add_product_name, db, bot)


def process_add_product_name(message: Message, db: Database, bot: TeleBot):
    """የምርት ስም በአማርኛ ማስኬድ"""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    state = _ensure_add_product_state(user_id)
    state['data']['name_am'] = message.text
    state['step'] = 2

    bot.send_message(
        message.chat.id,
        "📝 " + get_text(lang, 'enter_product_name_en')
    )
    bot.register_next_step_handler(message, process_add_product_name_en, db, bot)


def process_add_product_name_en(message: Message, db: Database, bot: TeleBot):
    """የምርት ስም በእንግሊዝኛ ማስኬድ"""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    state = _ensure_add_product_state(user_id)
    state['data']['name_en'] = message.text
    state['step'] = 3

    bot.send_message(
        message.chat.id,
        "💰 " + get_text(lang, 'enter_product_price')
    )
    bot.register_next_step_handler(message, process_add_product_price, db, bot)


def process_add_product_price(message: Message, db: Database, bot: TeleBot):
    """የምርት ዋጋ ማስኬድ"""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)

    try:
        price = float(message.text)
        state = _ensure_add_product_state(user_id)
        state['data']['price'] = price
        state['step'] = 4

        bot.send_message(
            message.chat.id,
            "📏 " + get_text(lang, 'enter_product_size')
        )
        bot.register_next_step_handler(message, process_add_product_size, db, bot)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ " + get_text(lang, 'invalid_number')
        )
        bot.register_next_step_handler(message, process_add_product_price, db, bot)


def process_add_product_size(message: Message, db: Database, bot: TeleBot):
    """የምርት መጠን ማስኬድ"""
    user_id = message.from_user.id
    state = _ensure_add_product_state(user_id)
    state['data']['size'] = message.text.upper()
    state['step'] = 5
    lang = get_user_lang(db, user_id)

    bot.send_message(
        message.chat.id,
        "📂 " + get_text(lang, 'choose_product_category'),
        reply_markup=get_admin_product_category_keyboard(lang),
    )
    bot.register_next_step_handler(message, process_add_product_category, db, bot)


def _finish_add_product_category(
    user_id: int,
    category: str,
    chat_id: int,
    db: Database,
    bot: TeleBot,
    step_source: Optional[Message] = None,
    stock_handler=None,
):
    state = _ensure_add_product_state(user_id)
    state['data']['category'] = category
    state['step'] = 6
    admin_uploading.discard(user_id)
    prompt = bot.send_message(
        chat_id,
        "📦 " + get_text(get_user_lang(db, user_id), 'enter_stock_quantity'),
    )
    bot.register_next_step_handler(
        step_source or prompt,
        stock_handler or process_add_product_stock,
        db,
        bot,
    )


def process_add_product_category(message: Message, db: Database, bot: TeleBot):
    """የምርት ምድብ ማስኬድ"""
    user_id = message.from_user.id
    category = (message.text or '').strip()
    if not category:
        bot.send_message(
            message.chat.id,
            "❌ " + get_text(
                get_user_lang(db, user_id),
                'select_or_type_category',
            ),
        )
        bot.register_next_step_handler(message, process_add_product_category, db, bot)
        return

    _finish_add_product_category(
        user_id, category, message.chat.id, db, bot, step_source=message
    )


def process_add_product_stock(message: Message, db: Database, bot: TeleBot):
    """የምርት ክምችት ማስኬድ"""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)

    try:
        stock = int(message.text)
        state = _ensure_add_product_state(user_id)
        state['data']['stock_quantity'] = stock
        state['step'] = 7

        bot.send_message(
            message.chat.id,
            "📸 " + get_text(lang, 'upload_product_photo')
        )
        admin_uploading.add(user_id)
        bot.register_next_step_handler(message, process_add_product_image, db, bot)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ " + get_text(lang, 'invalid_number')
        )
        bot.register_next_step_handler(message, process_add_product_stock, db, bot)


def process_add_product_image(message: Message, db: Database, bot: TeleBot):
    """የምርት ፎቶ ማስኬድ"""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)

    if message.content_type != 'photo':
        bot.send_message(
            message.chat.id,
            "❌ " + get_text(lang, 'invalid_photo')
        )
        bot.register_next_step_handler(message, process_add_product_image, db, bot)
        return

    admin_uploading.discard(user_id)
    image_id = message.photo[-1].file_id
    state = _ensure_add_product_state(user_id)
    data = state['data']
    required_fields = ('name_am', 'name_en', 'price', 'size', 'category', 'stock_quantity')
    if any(field not in data for field in required_fields):
        _send_admin_message(
            bot,
            message,
            "❌ " + get_text(lang, 'product_add_expired'),
        )
        admin_states.pop(user_id, None)
        return

    product_data = {
        'name_am': data['name_am'],
        'name_en': data['name_en'],
        'price': data['price'],
        'size': data['size'],
        'category': data['category'],
        'image_id': image_id,
        'stock_quantity': data['stock_quantity'],
        'status': 'In Stock'
    }

    product_id = db.create_product(product_data)

    if product_id:
        _notify_product_added(bot, data, product_id, lang)

        bot.send_message(
            message.chat.id,
            "✅ " + get_text(lang, 'product_added').format(
                data.get('name_am' if lang == 'am' else 'name_en')
                or get_text(lang, 'product'),
                product_id,
            )
        )

        db.log_activity(user_id, 'add_product',
                      f"ምርት: {data['name_am']}, ID: {product_id}")
    else:
        bot.send_message(
            message.chat.id,
            "❌ " + get_text(lang, 'product_add_failed')
        )

    admin_states.pop(user_id, None)
    _send_admin_message(bot, message, "⚙️ " + get_text(lang, 'admin_panel'))


def is_admin_uploading(user_id: int) -> bool:
    """Check whether an admin is currently waiting for a photo upload."""
    return user_id in admin_uploading


def handle_admin_photo(message: Message, db: Database, bot: TeleBot):
    """Handle a photo uploaded during an admin workflow such as add-product."""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    if not is_admin_uploading(user_id):
        return False

    admin_uploading.discard(user_id)
    state = admin_states.get(user_id)
    if not state or state.get('action') != 'add_product':
        _send_admin_message(bot, message, "📸 " + get_text(lang, 'photo_received'))
        return True

    try:
        image_id = message.photo[-1].file_id if message.photo else None
        if not image_id:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_photo'),
            )
            return False

        data = state.get('data', {})
        product_data = {
            'name_am': data.get('name_am'),
            'name_en': data.get('name_en'),
            'price': data.get('price'),
            'size': data.get('size'),
            'category': data.get('category'),
            'image_id': image_id,
            'stock_quantity': data.get('stock_quantity', 0),
            'status': 'In Stock'
        }

        product_id = db.create_product(product_data)
        if product_id:
            _notify_product_added(bot, data, product_id, lang)
            bot.send_message(
                message.chat.id,
                "✅ " + get_text(lang, 'product_added').format(
                    data.get('name_am' if lang == 'am' else 'name_en')
                    or get_text(lang, 'product'),
                    product_id,
                )
            )
            db.log_activity(user_id, 'add_product', f"ምርት: {data.get('name_am')}, ID: {product_id}")
        else:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'product_add_failed'),
            )

        admin_states.pop(user_id, None)
        return True
    except Exception as exc:
        logger.exception("Could not process the admin product photo: %s", exc)
        bot.send_message(
            message.chat.id,
            "❌ " + get_text(lang, 'product_photo_failed'),
        )
        admin_states.pop(user_id, None)
        return False


def register(bot: TeleBot, db: Database):
    """የአስተዳዳሪ እጅ አያያዞችን መመዝገብ"""

    @bot.message_handler(commands=['add'])
    def add_product_command(message: Message):
        lang = get_user_lang(db, message.from_user.id)
        if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
            _send_admin_message(bot, message, "⛔ " + get_text(lang, 'not_admin'))
            return
        start_add_product(message, db, bot)

    @bot.message_handler(commands=['delete'])
    def delete_product_command(message: Message):
        lang = get_user_lang(db, message.from_user.id)
        if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
            _send_admin_message(bot, message, "⛔ " + get_text(lang, 'not_admin'))
            return
        parts = (message.text or '').split(maxsplit=1)
        if len(parts) != 2:
            _send_admin_message(
                bot,
                message,
                get_text(lang, 'delete_command_usage'),
            )
            return
        process_delete_product(message, db, bot, parts[1])
    
    # ==================== የአስተዳዳሪ ፓነል ====================
    
    @bot.message_handler(func=lambda m: m.text in [
        '⚙️ አስተዳደር', '⚙️ Admin', 'አስተዳደር ⚙️', 'Admin ⚙️',
        '⚙️ አስተዳዳሪ', '⚙️ Admin Panel',
    ])
    def show_admin_panel(message: Message, user_id: Optional[int] = None):
        """የአስተዳዳሪ ፓነል ማሳየት"""
        user_id = user_id if user_id is not None else message.from_user.id
        lang = get_user_lang(db, user_id)
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            _send_admin_message(bot, message, "⛔ " + get_text(lang, 'not_admin'))
            return
        
        # ስታቲስቲክስ ማግኘት
        stats = get_admin_stats(db)

        # አስተዳዳሪ የሚገባ ግብዓት በድርድር ሁኔታ እንዳይተኛ ይቆጣጠራል
        if admin_states.get(user_id, {}).get('action') == 'add_product':
            route_admin_product_step(message, db, bot)
            return

        msg = f"⚙️ *{get_text(lang, 'admin_panel')}*\n\n"
        msg += (
            f"👥 {get_text(lang, 'users').replace('👥 ', '')}: "
            f"{stats['total_users']}\n"
        )
        msg += (
            f"📦 {get_text(lang, 'products').replace('📦 ', '')}: "
            f"{stats['total_products']}\n"
        )
        msg += f"📋 {get_text(lang, 'total_orders')}: {stats['total_orders']}\n"
        msg += f"⏳ {get_text(lang, 'pending')}: {stats['pending_orders']}\n"
        msg += f"💰 {get_text(lang, 'revenue')}: {format_currency(stats['total_revenue'])}\n"
        msg += (
            f"📅 {get_text(lang, 'today_orders')}: "
            f"{stats['today_orders']}\n\n"
        )
        msg += f"📌 {get_text(lang, 'choose_admin_menu_option')}"
        
        markup = get_admin_menu(user_id, lang)
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('add_product_category:')
    )
    def handle_add_product_category(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            bot.answer_callback_query(
                call.id,
                "⛔ " + get_text(lang, 'not_admin'),
            )
            return
        category = call.data.split(':', 1)[1]
        if category not in {
            'women', 'men', 'kids', 'pajamas', 'shoes', 'accessories',
        }:
            bot.answer_callback_query(
                call.id,
                "❌ " + get_text(lang, 'invalid_product_category'),
            )
            return
        bot.clear_step_handler_by_chat_id(call.message.chat.id)
        _finish_add_product_category(
            user_id,
            category,
            call.message.chat.id,
            db,
            bot,
            stock_handler=process_add_product_stock,
        )
        bot.answer_callback_query(call.id)
    
    # ==================== የምርት አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📦 ምርቶች', '📦 Products'])
    def manage_products(message: Message, user_id: Optional[int] = None):
        """የምርት አስተዳደር ሜኑ"""
        user_id = user_id if user_id is not None else message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = get_admin_products_keyboard(lang)
        bot.send_message(
            message.chat.id,
            f"📦 *{get_text(lang, 'product_management')}*\n\n"
            f"{get_text(lang, 'choose_admin_menu_option')}",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የትዕዛዝ አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📋 ትዕዛዞች', '📋 Orders'])
    def manage_orders(message: Message, user_id: Optional[int] = None):
        """የትዕዛዝ አስተዳደር ሜኑ"""
        user_id = user_id if user_id is not None else message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = get_admin_orders_keyboard(lang)
        bot.send_message(
            message.chat.id,
            f"📋 *{get_text(lang, 'order_management')}*\n\n"
            f"{get_text(lang, 'choose_admin_menu_option')}",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የተጠቃሚ አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['👥 ተጠቃሚዎች', '👥 Users'])
    def manage_users(message: Message, user_id: Optional[int] = None):
        """የተጠቃሚ አስተዳደር ሜኑ"""
        user_id = user_id if user_id is not None else message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = get_admin_users_keyboard(lang)
        bot.send_message(
            message.chat.id,
            f"👥 *{get_text(lang, 'user_management')}*\n\n"
            f"{get_text(lang, 'choose_admin_menu_option')}",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== ሪፖርቶች ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📊 ሪፖርቶች', '📊 Reports'])
    def show_reports(message: Message, user_id: Optional[int] = None):
        """የሪፖርት ሜኑ"""
        user_id = user_id if user_id is not None else message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = get_admin_reports_keyboard(lang)
        bot.send_message(
            message.chat.id,
            f"📊 *{get_text(lang, 'reports')}*\n\n"
            f"{get_text(lang, 'choose_admin_menu_option')}",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የቅናሽ አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['🏷️ ቅናሾች', '🏷️ Discounts'])
    def manage_discounts(message: Message, user_id: Optional[int] = None):
        """የቅናሽ አስተዳደር ሜኑ"""
        user_id = user_id if user_id is not None else message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = get_admin_discounts_keyboard(lang)
        bot.send_message(
            message.chat.id,
            f"🏷️ *{get_text(lang, 'discounts').replace('🏷️ ', '')}*\n\n"
            f"{get_text(lang, 'choose_admin_menu_option')}",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(func=lambda m: m.text in ['⚙️ ቅንብሮች', '⚙️ Settings'])
    def manage_settings(message: Message):
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        text = (
            f"{get_text(lang, 'settings')}\n\n"
            f"{get_text(lang, 'admin_settings_description')}"
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "🔙 " + get_text(lang, 'admin_panel'),
            callback_data="admin_back",
        ))
        bot.send_message(message.chat.id, text, reply_markup=markup)

    @bot.message_handler(func=lambda m: m.text in ['🔙 ወደ መጀመሪያ', '🔙 Main Menu'])
    def admin_back_to_main(message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        from handlers.start import show_welcome
        show_welcome(message.chat.id, user_id, db, bot)
    
    # ==================== የአስተዳዳሪ መልእክት ማስተናገጃ ====================
    
    # ከዚህ በታች የ Callback እጅ አያያዞች
    
    @bot.callback_query_handler(func=lambda call: (
        call.data.startswith('admin_')
        and not call.data.startswith(('admin_order_', 'admin_find_user', 'admin_toggle_ban_'))
    ))
    def handle_admin_callbacks(call: CallbackQuery):
        """የአስተዳዳሪ ጥሪ እጅ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            bot.answer_callback_query(
                call.id,
                "⛔ " + get_text(lang, 'not_admin'),
            )
            return
        
        data = call.data
        
        # ወደኋላ
        if data == 'admin_back':
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            show_admin_panel(call.message, user_id=user_id)
            return

        if data == 'admin_products':
            manage_products(call.message, user_id=user_id)
        elif data == 'admin_orders':
            manage_orders(call.message, user_id=user_id)
        elif data == 'admin_users':
            manage_users(call.message, user_id=user_id)
        elif data == 'admin_reports':
            show_reports(call.message, user_id=user_id)
        elif data == 'admin_discounts':
            manage_discounts(call.message, user_id=user_id)
        elif data == 'admin_settings':
            text = (
                f"{get_text(lang, 'settings')}\n\n"
                f"{get_text(lang, 'admin_settings_description')}"
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                "🔙 " + get_text(lang, 'admin_panel'),
                callback_data="admin_back",
            ))
            bot.send_message(call.message.chat.id, text, reply_markup=markup)
        elif data == 'admin_back_to_orders':
            show_orders_by_status(call.message, None, db, bot, user_id=user_id)
        elif data == 'admin_add_product':
            start_add_product(call, db, bot, user_id=user_id)
        
        # ምርት መጨመር
        # ምርቶች መዘርዘር
        elif data == 'admin_list_products':
            list_products(call.message, db, bot)
        
        # ምርት ማስተካከል
        elif data == 'admin_edit_product':
            start_edit_product(call.message, db, bot)
        
        # ምርት መሰረዝ
        elif data == 'admin_delete_product':
            start_delete_product(call.message, db, bot)
        
        # ዝቅተኛ ክምችት
        elif data == 'admin_low_stock':
            show_low_stock(call.message, db, bot)
        
        # ትዕዛዞች
        elif data == 'admin_all_orders':
            show_orders_by_status(call.message, None, db, bot, user_id=user_id)
        elif data == 'admin_pending_orders':
            show_orders_by_status(call.message, 'Pending', db, bot, user_id=user_id)
        elif data == 'admin_processing_orders':
            show_orders_by_status(call.message, 'Processing', db, bot, user_id=user_id)
        elif data == 'admin_shipped_orders':
            show_orders_by_status(call.message, 'Shipped', db, bot, user_id=user_id)
        elif data == 'admin_completed_orders':
            show_orders_by_status(call.message, 'Completed', db, bot, user_id=user_id)
        elif data == 'admin_cancelled_orders':
            show_orders_by_status(call.message, 'Cancelled', db, bot, user_id=user_id)
        
        # ተጠቃሚዎች
        elif data == 'admin_all_users':
            show_all_users(call.message, db, bot)
        elif data == 'admin_active_users':
            show_active_users(call.message, db, bot)
        elif data == 'admin_broadcast':
            start_broadcast(call.message, db, bot)
        elif data == 'admin_find_user':
            start_find_user(call.message, db, bot)
        
        # ሪፖርቶች
        elif data == 'admin_sales_report':
            show_sales_report(call.message, db, bot)
        elif data == 'admin_top_products':
            show_top_products(call.message, db, bot)
        elif data == 'admin_daily_report':
            show_daily_report(call.message, db, bot)
        elif data == 'admin_category_report':
            show_category_report(call.message, db, bot)
        
        # ቅናሾች
        elif data == 'admin_add_discount':
            start_add_discount(call.message, db, bot)
        elif data == 'admin_list_discounts':
            list_discounts(call.message, db, bot)
        
        bot.answer_callback_query(call.id)
    
    # ==================== ረዳት ተግባራት ====================
    
    def get_admin_menu(user_id: int, lang: str) -> ReplyKeyboardMarkup:
        """የአስተዳዳሪ ሜኑ መፍጠር"""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        buttons = [
            get_text(lang, 'products'),
            get_text(lang, 'admin_menu_orders'),
            get_text(lang, 'users'),
            get_text(lang, 'reports'),
            get_text(lang, 'discounts'),
            get_text(lang, 'settings'),
            "🔙 " + get_text(lang, 'back'),
        ]
        
        markup.add(*[KeyboardButton(btn) for btn in buttons])
        return markup
    
    def get_admin_stats(db: Database) -> Dict:
        """የአስተዳዳሪ ስታቲስቲክስ ማግኘት"""
        try:
            # ጠቅላላ ስታቲስቲክስ
            total_users = db.get_user_count()
            total_products = db.get_product_count()
            
            # ትዕዛዝ ስታቲስቲክስ
            order_stats = db.get_order_stats()
            
            total_orders = order_stats.get('summary', {}).get('total_orders', 0)
            total_revenue = order_stats.get('summary', {}).get('total_revenue', 0)
            pending_orders = order_stats.get('Pending', {}).get('count', 0)
            
            # የዕለት ስታቲስቲክስ
            daily_stats = db.get_daily_stats()
            today_orders = daily_stats.get('new_orders', 0)
            
            return {
                'total_users': total_users,
                'total_products': total_products,
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'pending_orders': pending_orders,
                'today_orders': today_orders
            }
        except Exception as e:
            logger.error(f"ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return {
                'total_users': 0,
                'total_products': 0,
                'total_orders': 0,
                'total_revenue': 0,
                'pending_orders': 0,
                'today_orders': 0
            }
    
    # ==================== ምርት መጨመር ሂደት ====================
    
    def start_add_product(
        message: Message,
        db: Database,
        bot: TeleBot,
        user_id: Optional[int] = None,
    ):
        """አዲስ ምርት መጨመር ሂደት መጀመር"""
        user_id = user_id if user_id is not None else message.from_user.id
        lang = get_user_lang(db, user_id)
        state = _ensure_add_product_state(user_id)
        state.update(step=1, data={})
        
        prompt = bot.send_message(
            _get_admin_chat_id(message),
            "📝 *" + get_text(lang, 'add_product') + "*\n\n"
            + get_text(lang, 'enter_product_name_am'),
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(prompt, process_add_product_name, db, bot)
    
    def process_add_product_name(message: Message, db: Database, bot: TeleBot):
        """የምርት ስም በአማርኛ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        state = _ensure_add_product_state(user_id)
        state['data']['name_am'] = message.text
        state['step'] = 2
        
        bot.send_message(
            message.chat.id,
            "📝 " + get_text(lang, 'enter_product_name_en')
        )
        bot.register_next_step_handler(message, process_add_product_name_en, db, bot)
    
    def process_add_product_name_en(message: Message, db: Database, bot: TeleBot):
        """የምርት ስም በእንግሊዝኛ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        state = _ensure_add_product_state(user_id)
        state['data']['name_en'] = message.text
        state['step'] = 3
        
        bot.send_message(
            message.chat.id,
            "💰 " + get_text(lang, 'enter_product_price')
        )
        bot.register_next_step_handler(message, process_add_product_price, db, bot)
    
    def process_add_product_price(message: Message, db: Database, bot: TeleBot):
        """የምርት ዋጋ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            price = float(message.text)
            state = _ensure_add_product_state(user_id)
            state['data']['price'] = price
            state['step'] = 4
            
            bot.send_message(
                message.chat.id,
                "📏 " + get_text(lang, 'enter_product_size')
            )
            bot.register_next_step_handler(message, process_add_product_size, db, bot)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_number')
            )
            bot.register_next_step_handler(message, process_add_product_price, db, bot)
    
    def process_add_product_size(message: Message, db: Database, bot: TeleBot):
        """የምርት መጠን ማስኬድ"""
        user_id = message.from_user.id
        state = _ensure_add_product_state(user_id)
        state['data']['size'] = message.text.upper()
        state['step'] = 5

        lang = get_user_lang(db, user_id)
        bot.send_message(
            message.chat.id,
            "📂 " + get_text(lang, 'choose_product_category'),
            reply_markup=get_admin_product_category_keyboard(lang),
        )
        bot.register_next_step_handler(message, process_add_product_category, db, bot)
    
    def process_add_product_category(message: Message, db: Database, bot: TeleBot):
        """የምርት ምድብ ማስኬድ"""
        user_id = message.from_user.id

        category = (message.text or '').strip()
        if not category:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(
                    get_user_lang(db, user_id),
                    'select_or_type_category',
                ),
            )
            bot.register_next_step_handler(message, process_add_product_category, db, bot)
            return

        _finish_add_product_category(
            user_id,
            category,
            message.chat.id,
            db,
            bot,
            step_source=message,
            stock_handler=process_add_product_stock,
        )
    
    def process_add_product_stock(message: Message, db: Database, bot: TeleBot):
        """የምርት ክምችት ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            stock = int(message.text)
            state = _ensure_add_product_state(user_id)
            state['data']['stock_quantity'] = stock
            state['step'] = 7
            
            bot.send_message(
                message.chat.id,
                "📸 " + get_text(lang, 'upload_product_photo')
            )
            admin_uploading.add(user_id)
            bot.register_next_step_handler(message, process_add_product_image, db, bot)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_number')
            )
            bot.register_next_step_handler(message, process_add_product_stock, db, bot)
    
    def process_add_product_image(message: Message, db: Database, bot: TeleBot):
        """የምርት ፎቶ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        if message.content_type != 'photo':
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_photo')
            )
            bot.register_next_step_handler(message, process_add_product_image, db, bot)
            return
        
        admin_uploading.discard(user_id)
        image_id = message.photo[-1].file_id
        state = _ensure_add_product_state(user_id)
        data = state['data']
        required_fields = ('name_am', 'name_en', 'price', 'size', 'category', 'stock_quantity')
        if any(field not in data for field in required_fields):
            _send_admin_message(
                bot,
                message,
                "❌ " + get_text(lang, 'product_add_expired'),
            )
            admin_states.pop(user_id, None)
            return
        
        # ምርት መፍጠር
        product_data = {
            'name_am': data['name_am'],
            'name_en': data['name_en'],
            'price': data['price'],
            'size': data['size'],
            'category': data['category'],
            'image_id': image_id,
            'stock_quantity': data['stock_quantity'],
            'status': 'In Stock'
        }
        
        product_id = db.create_product(product_data)
        
        if product_id:
            _notify_product_added(bot, data, product_id, lang)
            
            bot.send_message(
                message.chat.id,
                "✅ " + get_text(lang, 'product_added').format(
                    data.get('name_am' if lang == 'am' else 'name_en')
                    or get_text(lang, 'product'),
                    product_id,
                )
            )
            
            db.log_activity(user_id, 'add_product', 
                          f"ምርት: {data['name_am']}, ID: {product_id}")
        else:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'product_add_failed')
            )
        
        # ሁኔታን ማጽዳት
        admin_states.pop(user_id, None)
        show_admin_panel(message)


# ==================== ሌሎች የአስተዳዳሪ ተግባራት ====================

def show_orders_by_status(
    message: Message,
    status: Optional[str],
    db: Database,
    bot: TeleBot,
    user_id: Optional[int] = None,
):
    """ትዕዛዞችን በሁኔታ ማሳየት"""
    orders = db.get_orders_by_status(status)
    if not orders:
        lang = get_user_lang(db, user_id if user_id is not None else message.from_user.id)
        bot.send_message(
            message.chat.id,
            "📋 " + get_text(lang, 'no_orders_found'),
        )
        return orders

    lang = get_user_lang(db, user_id if user_id is not None else message.from_user.id)
    for order in orders[:20]:
        items = order.get('items') or []
        if isinstance(items, str):
            try:
                items = json.loads(items)
            except json.JSONDecodeError:
                logger.exception("Could not decode order items for order %s", order.get('id'))
                items = []
        order['items'] = items
        text, keyboard = format_admin_order_card(order, lang)
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=keyboard,
        )
    return orders


def format_admin_order_card(order: Dict, lang: str = 'am'):
    """Build a complete admin order card and its supported status actions."""
    items = order.get('items') or []
    item_lines = []
    for item in items:
        name = (
            item.get('name_am' if lang == 'am' else 'name_en')
            or get_text(lang, 'product')
        )
        item_lines.append(
            f"• {name} × {item.get('quantity', 0)}"
            f" · {format_currency(item.get('total_price', 0))}"
        )
    status = str(order.get('status') or 'pending')
    status_key = status.strip().lower()
    status_text = get_text(lang, status_key)
    if status_text == status_key:
        status_text = get_text(lang, 'unknown')
    status_emoji = {
        'pending': '⏳',
        'processing': '🔄',
        'shipped': '🚚',
        'delivered': '✅',
        'completed': '✅',
        'cancelled': '❌',
    }.get(status_key, '📦')
    text = (
        f"📋 {get_text(lang, 'order')} "
        f"#{order.get('order_number') or order.get('id') or get_text(lang, 'unknown')}\n"
        f"👤 {get_text(lang, 'customer_name')}: "
        f"{order.get('customer_name') or get_text(lang, 'unknown')}\n"
        f"📱 {get_text(lang, 'phone')}: {order.get('customer_phone') or '—'}\n"
        f"📌 {get_text(lang, 'status')}: {status_emoji} {status_text}\n"
        f"📦 {get_text(lang, 'order_items')}:\n"
        f"{chr(10).join(item_lines) if item_lines else '—'}\n"
        f"💰 {get_text(lang, 'total')}: "
        f"{format_currency(order.get('final_amount', 0))}\n"
        f"📍 {get_text(lang, 'shipping_address')}: "
        f"{order.get('shipping_address') or '—'}\n"
        f"💳 {get_text(lang, 'method')}: "
        f"{format_payment_method(order.get('payment_method'), lang)}"
    )
    keyboard = get_admin_order_actions_keyboard(
        order['id'],
        status=status,
        lang=lang,
    )
    return text, keyboard


def show_all_users(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ተጠቃሚዎች ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    try:
        users = db.get_all_users(limit=20)
    except TypeError:
        users = db.get_all_users()
    if not users:
        bot.send_message(
            message.chat.id,
            "👥 " + get_text(lang, 'no_users_found'),
        )
        return []

    text = "\n".join(
        f"• {user.get('first_name') or get_text(lang, 'unknown')} "
        f"(@{user.get('username') or get_text(lang, 'unknown')})"
        for user in users[:10]
    )
    bot.send_message(
        message.chat.id,
        f"👥 {get_text(lang, 'users').replace('👥 ', '')}\n\n{text}",
    )
    return users


def show_active_users(message: Message, db: Database, bot: TeleBot):
    """ንቁ ተጠቃሚዎችን ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    try:
        users = db.get_active_users(days=7)
    except TypeError:
        users = db.get_active_users()
    if not users:
        bot.send_message(
            message.chat.id,
            "📊 " + get_text(lang, 'no_active_users'),
        )
        return []

    text = "\n".join(
        f"• {user.get('first_name') or get_text(lang, 'unknown')} "
        f"({user.get('last_active') or get_text(lang, 'unknown')})"
        for user in users[:10]
    )
    bot.send_message(
        message.chat.id,
        f"📊 {get_text(lang, 'active_users')}\n\n{text}",
    )
    return users


def start_broadcast(message: Message, db: Database, bot: TeleBot):
    """ማስታወቂያ መላክ ሂደት መጀመር"""
    lang = get_user_lang(db, message.from_user.id)
    bot.send_message(
        message.chat.id,
        "📢 " + get_text(lang, 'broadcast_prompt'),
    )
    return "broadcast started"


def start_find_user(message: Message, db: Database, bot: TeleBot):
    """ተጠቃሚ መፈለግ ሂደት መጀመር"""
    lang = get_user_lang(db, message.from_user.id)
    bot.send_message(
        message.chat.id,
        "👤 " + get_text(lang, 'enter_user_id_or_username'),
    )
    return "find user started"


def show_sales_report(message: Message, db: Database, bot: TeleBot):
    """የሽያጭ ሪፖርት ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    report = db.get_sales_report(days=30)
    if not report:
        bot.send_message(
            message.chat.id,
            "📊 " + get_text(lang, 'no_sales_report'),
        )
        return []

    text = "\n".join(
        f"• {row.get('sale_date') or get_text(lang, 'unknown')}: "
        f"{row.get('total_sales', 0)} ETB"
        for row in report[:10]
    )
    bot.send_message(
        message.chat.id,
        f"📊 {get_text(lang, 'sales_report')}\n\n{text}",
    )
    return report


def show_top_products(message: Message, db: Database, bot: TeleBot):
    """ከፍተኛ ምርቶችን ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    products = db.get_top_products(limit=5)
    if not products:
        bot.send_message(
            message.chat.id,
            "🏆 " + get_text(lang, 'no_top_products'),
        )
        return []

    text = "\n".join(
        f"• {product.get('name_am' if lang == 'am' else 'name_en') or get_text(lang, 'product')} "
        f"({product.get('total_sold', 0)} {get_text(lang, 'sold')})"
        for product in products
    )
    bot.send_message(
        message.chat.id,
        f"🏆 {get_text(lang, 'top_products')}\n\n{text}",
    )
    return products


def show_daily_report(message: Message, db: Database, bot: TeleBot):
    """የዕለት ሪፖርት ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    stats = db.get_daily_stats()
    text = (
        f"📈 {get_text(lang, 'new_users')}: {stats.get('new_users', 0)}\n"
        f"📦 {get_text(lang, 'new_orders')}: {stats.get('new_orders', 0)}\n"
        f"💰 {get_text(lang, 'daily_revenue')}: {stats.get('daily_revenue', 0)} ETB"
    )
    bot.send_message(
        message.chat.id,
        f"📈 {get_text(lang, 'daily_report')}\n\n{text}",
    )
    return stats


def show_category_report(message: Message, db: Database, bot: TeleBot):
    """የምድብ ሪፖርት ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    stats = db.get_category_stats()
    if not stats:
        bot.send_message(
            message.chat.id,
            "📊 " + get_text(lang, 'no_category_report'),
        )
        return []

    text = "\n".join(
        f"• {_localized_category(row.get('category'), lang)}: "
        f"{row.get('product_count', 0)} {get_text(lang, 'products')}"
        for row in stats
    )
    bot.send_message(
        message.chat.id,
        f"📊 {get_text(lang, 'category_report')}\n\n{text}",
    )
    return stats


def start_add_discount(message: Message, db: Database, bot: TeleBot):
    """አዲስ ቅናሽ መፍጠር ሂደት መጀመር"""
    lang = get_user_lang(db, message.from_user.id)
    bot.send_message(
        message.chat.id,
        "🏷️ " + get_text(lang, 'enter_discount_code'),
    )
    return "discount started"


def list_discounts(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ቅናሾች ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    discounts = db.get_discounts() if hasattr(db, 'get_discounts') else []
    if not discounts:
        bot.send_message(message.chat.id, "🏷️ " + get_text(lang, 'no_discounts'))
        return []

    text = "\n".join(
        f"• {discount.get('code') or get_text(lang, 'unknown')} - "
        f"{discount.get('discount_percent', 0)}%"
        for discount in discounts[:10]
    )
    bot.send_message(message.chat.id, f"🏷️ {get_text(lang, 'discounts')}\n\n{text}")
    return discounts


def list_products(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ምርቶች ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    products = db.get_products(limit=10)
    if not products:
        bot.send_message(message.chat.id, "📦 " + get_text(lang, 'no_products'))
        return []

    text = "\n".join(
        f"• {product.get('name_am' if lang == 'am' else 'name_en') or get_text(lang, 'product')} "
        f"- {product.get('price', 0)} ETB"
        for product in products[:10]
    )
    bot.send_message(
        message.chat.id,
        f"📦 {get_text(lang, 'products').replace('📦 ', '')}\n\n{text}",
    )
    return products


def start_edit_product(message: Message, db: Database, bot: TeleBot):
    """ምርት ማስተካከል ሂደት መጀመር"""
    lang = get_user_lang(db, message.from_user.id)
    bot.send_message(message.chat.id, "✏️ " + get_text(lang, 'enter_product_id'))
    return "edit product started"


def start_delete_product(message: Message, db: Database, bot: TeleBot):
    """ምርት መሰረዝ ሂደት መጀመር"""
    lang = get_user_lang(db, message.from_user.id)
    prompt = bot.send_message(
        message.chat.id,
        "🗑️ " + get_text(lang, 'enter_product_id'),
    )
    bot.register_next_step_handler(prompt, process_delete_product, db, bot)
    return "delete product started"


def process_delete_product(
    message: Message,
    db: Database,
    bot: TeleBot,
    product_id_text: Optional[str] = None,
):
    """Validate and delete a product requested by an administrator."""
    lang = get_user_lang(db, message.from_user.id)
    if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
        _send_admin_message(
            bot,
            message,
            "⛔ " + get_text(lang, 'not_admin'),
        )
        return False

    value = product_id_text or (message.text or '').strip()
    try:
        product_id = int(value)
    except ValueError:
        _send_admin_message(
            bot,
            message,
            "❌ " + get_text(lang, 'enter_product_id_invalid'),
        )
        return False

    if product_id <= 0 or not db.get_product(product_id):
        _send_admin_message(
            bot,
            message,
            "❌ " + get_text(lang, 'product_not_found_admin'),
        )
        return False

    if not db.delete_product(product_id):
        _send_admin_message(
            bot,
            message,
            "❌ " + get_text(lang, 'product_delete_failed'),
        )
        return False

    _send_admin_message(
        bot,
        message,
        "✅ " + get_text(lang, 'product_deleted').format(product_id),
    )
    db.log_activity(message.from_user.id, 'delete_product', f'Product ID: {product_id}')
    return True


def show_low_stock(message: Message, db: Database, bot: TeleBot):
    """ዝቅተኛ ክምችት ያላቸውን ምርቶች ማሳየት"""
    lang = get_user_lang(db, message.from_user.id)
    products = db.get_low_stock_products(threshold=5)
    if not products:
        bot.send_message(
            message.chat.id,
            "📦 " + get_text(lang, 'no_low_stock_products'),
        )
        return []

    text = "\n".join(
        f"• {product.get('name_am' if lang == 'am' else 'name_en') or get_text(lang, 'product')} "
        f"({product.get('stock_quantity', 0)})"
        for product in products
    )
    bot.send_message(
        message.chat.id,
        f"📦 {get_text(lang, 'low_stock')}\n\n{text}",
    )
    return products


def show_admin_panel(message: Message, db: Database, bot: TeleBot):
    """Render the inline admin panel for commands and package-level callers."""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    if not is_admin(user_id, config.bot.ADMIN_IDS):
        return bot.send_message(
            message.chat.id,
            "⛔ " + get_text(lang, 'not_admin'),
        )
    return bot.send_message(
        message.chat.id,
        "⚙️ " + get_text(lang, 'admin_panel'),
        reply_markup=get_admin_keyboard(lang),
    )


def show_stats(message: Message, db: Database, bot: TeleBot):
    """Show the admin dashboard summary for the /stats command."""
    lang = get_user_lang(db, message.from_user.id)
    if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
        return bot.send_message(
            message.chat.id,
            "⛔ " + get_text(lang, 'not_admin'),
        )
    order_stats = db.get_order_stats()
    summary = order_stats.get('summary', {})
    pending = next(
        (value.get('count', 0) for key, value in order_stats.items() if key.lower() == 'pending'),
        0,
    )
    text = (
        f"👥 {get_text(lang, 'users').replace('👥 ', '')}: {db.get_user_count()}\n"
        f"📦 {get_text(lang, 'products').replace('📦 ', '')}: {db.get_product_count()}\n"
        f"📋 {get_text(lang, 'total_orders')}: {summary.get('total_orders', 0)}\n"
        f"⏳ {get_text(lang, 'pending')}: {pending}\n"
        f"💰 {get_text(lang, 'revenue')}: {format_currency(summary.get('total_revenue', 0))}"
    )
    return bot.send_message(message.chat.id, text)