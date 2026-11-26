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
from services.notifications import notify_admins, send_broadcast

logger = logging.getLogger(__name__)

# ለአስተዳዳሪ ሂደቶች ጊዜያዊ መረጃ
admin_states = {}
admin_uploading = set()


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
    state = _ensure_add_product_state(user_id)
    state.update(step=1, data={})

    prompt = bot.send_message(
        _get_admin_chat_id(message),
        "📝 *አዲስ ምርት መጨመር*\n\n"
        "የምርቱን ስም በአማርኛ ያስገቡ:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(prompt, process_add_product_name, db, bot)


def process_add_product_name(message: Message, db: Database, bot: TeleBot):
    """የምርት ስም በአማርኛ ማስኬድ"""
    user_id = message.from_user.id
    state = _ensure_add_product_state(user_id)
    state['data']['name_am'] = message.text
    state['step'] = 2

    bot.send_message(
        message.chat.id,
        "📝 የምርቱን ስም በእንግሊዝኛ ያስገቡ:"
    )
    bot.register_next_step_handler(message, process_add_product_name_en, db, bot)


def process_add_product_name_en(message: Message, db: Database, bot: TeleBot):
    """የምርት ስም በእንግሊዝኛ ማስኬድ"""
    user_id = message.from_user.id
    state = _ensure_add_product_state(user_id)
    state['data']['name_en'] = message.text
    state['step'] = 3

    bot.send_message(
        message.chat.id,
        "💰 የምርቱን ዋጋ በብር ያስገቡ:"
    )
    bot.register_next_step_handler(message, process_add_product_price, db, bot)


def process_add_product_price(message: Message, db: Database, bot: TeleBot):
    """የምርት ዋጋ ማስኬድ"""
    user_id = message.from_user.id

    try:
        price = float(message.text)
        state = _ensure_add_product_state(user_id)
        state['data']['price'] = price
        state['step'] = 4

        bot.send_message(
            message.chat.id,
            "📏 የምርቱን መጠን (Size) ያስገቡ (S, M, L, XL, XXL):"
        )
        bot.register_next_step_handler(message, process_add_product_size, db, bot)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
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
        "📂 የምርቱን ምድብ ይምረጡ ወይም ብጁ ምድብ ይጻፉ:"
        if lang == 'am'
        else "📂 Choose a product category or type a custom category:",
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
        "📦 የምርቱን የክምችት ብዛት ያስገቡ:"
        if get_user_lang(db, user_id) == 'am'
        else "📦 Enter the product stock quantity:",
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
            "❌ እባክዎ ምድብ ይምረጡ ወይም ይጻፉ።"
            if get_user_lang(db, user_id) == 'am'
            else "❌ Select a category or type a custom category.",
        )
        bot.register_next_step_handler(message, process_add_product_category, db, bot)
        return

    _finish_add_product_category(
        user_id, category, message.chat.id, db, bot, step_source=message
    )


def process_add_product_stock(message: Message, db: Database, bot: TeleBot):
    """የምርት ክምችት ማስኬድ"""
    user_id = message.from_user.id

    try:
        stock = int(message.text)
        state = _ensure_add_product_state(user_id)
        state['data']['stock_quantity'] = stock
        state['step'] = 7

        bot.send_message(
            message.chat.id,
            "📸 የምርቱን ፎቶ ይላኩ:"
        )
        admin_uploading.add(user_id)
        bot.register_next_step_handler(message, process_add_product_image, db, bot)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
        )
        bot.register_next_step_handler(message, process_add_product_stock, db, bot)


def process_add_product_image(message: Message, db: Database, bot: TeleBot):
    """የምርት ፎቶ ማስኬድ"""
    user_id = message.from_user.id

    if message.content_type != 'photo':
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ፎቶ ይላኩ!"
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
            "❌ የምርት መጨመር ሂደቱ ጊዜው አልፏል። እባክዎ /add እንደገና ይጀምሩ።",
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
        notify_admins(
            bot,
            f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
            f"📦 {data['name_am']}\n"
            f"💰 ዋጋ: {data['price']:.2f} ETB\n"
            f"📏 መጠን: {data['size']}\n"
            f"📂 ምድብ: {data['category']}\n"
            f"📦 ክምችት: {data['stock_quantity']}\n"
            f"🆔 ID: {product_id}"
        )

        bot.send_message(
            message.chat.id,
            f"✅ ምርቱ \"{data['name_am']}\" በተሳካ ሁኔታ ተጨምሯል!\n"
            f"🆔 የምርት ID: {product_id}"
        )

        db.log_activity(user_id, 'add_product',
                      f"ምርት: {data['name_am']}, ID: {product_id}")
    else:
        bot.send_message(
            message.chat.id,
            "❌ ምርቱ መጨመር አልተቻለም!"
        )

    admin_states.pop(user_id, None)
    _send_admin_message(bot, message, "⚙️ የአስተዳዳሪ ፓነል")


def is_admin_uploading(user_id: int) -> bool:
    """Check whether an admin is currently waiting for a photo upload."""
    return user_id in admin_uploading


def handle_admin_photo(message: Message, db: Database, bot: TeleBot):
    """Handle a photo uploaded during an admin workflow such as add-product."""
    user_id = message.from_user.id
    if not is_admin_uploading(user_id):
        return False

    admin_uploading.discard(user_id)
    state = admin_states.get(user_id)
    if not state or state.get('action') != 'add_product':
        _send_admin_message(bot, message, "📸 ፎቶዎ ተቀብሏል።")
        return True

    try:
        image_id = message.photo[-1].file_id if message.photo else None
        if not image_id:
            bot.send_message(message.chat.id, "❌ እባክዎ ትክክለኛ ፎቶ ይላኩ!")
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
            notify_admins(
                bot,
                f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
                f"📦 {data.get('name_am')}\n"
                f"💰 ዋጋ: {data.get('price'):.2f} ETB\n"
                f"📏 መጠን: {data.get('size')}\n"
                f"📂 ምድብ: {data.get('category')}\n"
                f"📦 ክምችት: {data.get('stock_quantity')}\n"
                f"🆔 ID: {product_id}"
            )
            bot.send_message(
                message.chat.id,
                f"✅ ምርቱ \"{data.get('name_am')}\" በተሳካ ሁኔታ ተጨምሯል!\n"
                f"🆔 የምርት ID: {product_id}"
            )
            db.log_activity(user_id, 'add_product', f"ምርት: {data.get('name_am')}, ID: {product_id}")
        else:
            bot.send_message(message.chat.id, "❌ ምርቱ መጨመር አልተቻለልም!")

        admin_states.pop(user_id, None)
        return True
    except Exception as exc:
        logger.exception(f"ምርት ፎቶ ማስተካከል አልተቻለም: {exc}")
        bot.send_message(message.chat.id, "❌ ፎቶውን ማስተካከል አልተቻለም።")
        admin_states.pop(user_id, None)
        return False


def register(bot: TeleBot, db: Database):
    """የአስተዳዳሪ እጅ አያያዞችን መመዝገብ"""

    @bot.message_handler(commands=['add'])
    def add_product_command(message: Message):
        if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
            _send_admin_message(bot, message, "⛔ ይህን ለማድረግ ፈቃድ የለዎትም!")
            return
        start_add_product(message, db, bot)

    @bot.message_handler(commands=['delete'])
    def delete_product_command(message: Message):
        if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
            _send_admin_message(bot, message, "⛔ ይህን ለማድረግ ፈቃድ የለዎትም!")
            return
        parts = (message.text or '').split(maxsplit=1)
        if len(parts) != 2:
            _send_admin_message(bot, message, "Usage: /delete <id>")
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
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            _send_admin_message(bot, message, "⛔ ይህን ለማድረግ ፈቃድ የለዎትም!")
            return
        
        lang = get_user_lang(db, user_id)
        
        # ስታቲስቲክስ ማግኘት
        stats = get_admin_stats(db)

        # አስተዳዳሪ የሚገባ ግብዓት በድርድር ሁኔታ እንዳይተኛ ይቆጣጠራል
        if admin_states.get(user_id, {}).get('action') == 'add_product':
            route_admin_product_step(message, db, bot)
            return

        msg = f"⚙️ *የአስተዳዳሪ ፓነል*\n\n"
        msg += f"👥 ተጠቃሚዎች: {stats['total_users']}\n"
        msg += f"📦 ምርቶች: {stats['total_products']}\n"
        msg += f"📋 ትዕዛዞች: {stats['total_orders']}\n"
        msg += f"⏳ በመጠባበቅ: {stats['pending_orders']}\n"
        msg += f"💰 ገቢ: {format_currency(stats['total_revenue'])}\n"
        msg += f"📅 ዛሬ: {stats['today_orders']} ትዕዛዞች\n\n"
        msg += f"📌 ከታች ካሉት አዝራሮች ይምረጡ:"
        
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
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        category = call.data.split(':', 1)[1]
        if category not in {
            'women', 'men', 'kids', 'pajamas', 'shoes', 'accessories',
        }:
            bot.answer_callback_query(call.id, "❌ የተመረጠው ምድብ ትክክል አይደለም።")
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
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ አዲስ ምርት", callback_data="admin_add_product"),
            InlineKeyboardButton("📋 ምርቶች አሳይ", callback_data="admin_list_products"),
            InlineKeyboardButton("✏️ ምርት አስተካክል", callback_data="admin_edit_product"),
            InlineKeyboardButton("🗑️ ምርት ሰርዝ", callback_data="admin_delete_product"),
            InlineKeyboardButton("📊 ዝቅተኛ ክምችት", callback_data="admin_low_stock"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "📦 *የምርት አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
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
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📋 ሁሉንም ትዕዛዞች", callback_data="admin_all_orders"),
            InlineKeyboardButton("⏳ በመጠባበቅ", callback_data="admin_pending_orders"),
            InlineKeyboardButton("📦 በሂደት", callback_data="admin_processing_orders"),
            InlineKeyboardButton("🚚 የተላኩ", callback_data="admin_shipped_orders"),
            InlineKeyboardButton("✅ የተጠናቀቁ", callback_data="admin_completed_orders"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "📋 *የትዕዛዝ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
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
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👥 ሁሉንም ተጠቃሚዎች", callback_data="admin_all_users"),
            InlineKeyboardButton("📊 ንቁ ተጠቃሚዎች", callback_data="admin_active_users"),
            InlineKeyboardButton("📢 ማስታወቂያ ላክ", callback_data="admin_broadcast"),
            InlineKeyboardButton("👤 ተጠቃሚ ፈልግ", callback_data="admin_find_user"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "👥 *የተጠቃሚ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
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
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📊 የሽያጭ ሪፖርት", callback_data="admin_sales_report"),
            InlineKeyboardButton("🏆 ከፍተኛ ምርቶች", callback_data="admin_top_products"),
            InlineKeyboardButton("📈 ዕለታዊ ሪፖርት", callback_data="admin_daily_report"),
            InlineKeyboardButton("📊 የምድብ ሪፖርት", callback_data="admin_category_report"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "📊 *የሪፖርት ሜኑ*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
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
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ አዲስ ቅናሽ", callback_data="admin_add_discount"),
            InlineKeyboardButton("📋 ሁሉንም ቅናሾች", callback_data="admin_list_discounts"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "🏷️ *የቅናሽ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )

    @bot.message_handler(func=lambda m: m.text in ['⚙️ ቅንብሮች', '⚙️ Settings'])
    def manage_settings(message: Message):
        user_id = message.from_user.id
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        text = (
            "⚙️ ቅንብሮች\n\n"
            "የቦት እና የክፍያ ምስጢራዊ ውቅሮች በአካባቢ ተለዋዋጮች ይተዳደራሉ።"
            if get_user_lang(db, user_id) == 'am'
            else "⚙️ Settings\n\nBot and payment credentials are managed through environment configuration."
        )
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "🔙 ወደ አስተዳዳሪ ፓነል" if get_user_lang(db, user_id) == 'am' else "🔙 Admin Panel",
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
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        
        data = call.data
        lang = get_user_lang(db, user_id)
        
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
                "⚙️ ቅንብሮች\n\nየቦት እና የክፍያ ምስጢራዊ ውቅሮች በአካባቢ ተለዋዋጮች ይተዳደራሉ።"
                if lang == 'am'
                else "⚙️ Settings\n\nBot and payment credentials are managed through environment configuration."
            )
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                "🔙 ወደ አስተዳዳሪ ፓነል" if lang == 'am' else "🔙 Admin Panel",
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
        buttons = (
            ["📦 ምርቶች", "📋 ትዕዛዞች", "👥 ተጠቃሚዎች", "📊 ሪፖርቶች",
             "🏷️ ቅናሾች", "⚙️ ቅንብሮች", "🔙 ወደ መጀመሪያ"]
            if lang == 'am'
            else ["📦 Products", "📋 Orders", "👥 Users", "📊 Reports",
                  "🏷️ Discounts", "⚙️ Settings", "🔙 Main Menu"]
        )
        
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
        state = _ensure_add_product_state(user_id)
        state.update(step=1, data={})
        
        prompt = bot.send_message(
            _get_admin_chat_id(message),
            "📝 *አዲስ ምርት መጨመር*\n\n"
            "የምርቱን ስም በአማርኛ ያስገቡ:",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(prompt, process_add_product_name, db, bot)
    
    def process_add_product_name(message: Message, db: Database, bot: TeleBot):
        """የምርት ስም በአማርኛ ማስኬድ"""
        user_id = message.from_user.id
        state = _ensure_add_product_state(user_id)
        state['data']['name_am'] = message.text
        state['step'] = 2
        
        bot.send_message(
            message.chat.id,
            "📝 የምርቱን ስም በእንግሊዝኛ ያስገቡ:"
        )
        bot.register_next_step_handler(message, process_add_product_name_en, db, bot)
    
    def process_add_product_name_en(message: Message, db: Database, bot: TeleBot):
        """የምርት ስም በእንግሊዝኛ ማስኬድ"""
        user_id = message.from_user.id
        state = _ensure_add_product_state(user_id)
        state['data']['name_en'] = message.text
        state['step'] = 3
        
        bot.send_message(
            message.chat.id,
            "💰 የምርቱን ዋጋ በብር ያስገቡ:"
        )
        bot.register_next_step_handler(message, process_add_product_price, db, bot)
    
    def process_add_product_price(message: Message, db: Database, bot: TeleBot):
        """የምርት ዋጋ ማስኬድ"""
        user_id = message.from_user.id
        
        try:
            price = float(message.text)
            state = _ensure_add_product_state(user_id)
            state['data']['price'] = price
            state['step'] = 4
            
            bot.send_message(
                message.chat.id,
                "📏 የምርቱን መጠን (Size) ያስገቡ (S, M, L, XL, XXL):"
            )
            bot.register_next_step_handler(message, process_add_product_size, db, bot)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
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
            "📂 የምርቱን ምድብ ይምረጡ ወይም ብጁ ምድብ ይጻፉ:"
            if lang == 'am'
            else "📂 Choose a product category or type a custom category:",
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
                "❌ እባክዎ ምድብ ይምረጡ ወይም ይጻፉ။"
                if get_user_lang(db, user_id) == 'am'
                else "❌ Select a category or type a custom category.",
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
        
        try:
            stock = int(message.text)
            state = _ensure_add_product_state(user_id)
            state['data']['stock_quantity'] = stock
            state['step'] = 7
            
            bot.send_message(
                message.chat.id,
                "📸 የምርቱን ፎቶ ይላኩ:"
            )
            admin_uploading.add(user_id)
            bot.register_next_step_handler(message, process_add_product_image, db, bot)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
            )
            bot.register_next_step_handler(message, process_add_product_stock, db, bot)
    
    def process_add_product_image(message: Message, db: Database, bot: TeleBot):
        """የምርት ፎቶ ማስኬድ"""
        user_id = message.from_user.id
        
        if message.content_type != 'photo':
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ፎቶ ይላኩ!"
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
                "❌ የምርት መጨመር ሂደቱ ጊዜው አልፏል። እባክዎ /add እንደገና ይጀምሩ።",
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
            # ለአስተዳዳሪዎች ማሳወቅ
            notify_admins(
                bot,
                f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
                f"📦 {data['name_am']}\n"
                f"💰 ዋጋ: {data['price']:.2f} ETB\n"
                f"📏 መጠን: {data['size']}\n"
                f"📂 ምድብ: {data['category']}\n"
                f"📦 ክምችት: {data['stock_quantity']}\n"
                f"🆔 ID: {product_id}"
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ ምርቱ '{data['name_am']}' በተሳካ ሁኔታ ተጨምሯል!\n"
                f"🆔 የምርት ID: {product_id}"
            )
            
            db.log_activity(user_id, 'add_product', 
                          f"ምርት: {data['name_am']}, ID: {product_id}")
        else:
            bot.send_message(
                message.chat.id,
                "❌ ምርቱ መጨመር አልተቻለም!"
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
            "📋 ምንም ትዕዛዞች አልተገኙም." if lang == 'am' else "📋 No orders found.",
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
            (item.get('name_am') if lang == 'am' else item.get('name_en'))
            or item.get('name_am')
            or item.get('name')
            or 'Item'
        )
        item_lines.append(
            f"• {name} × {item.get('quantity', 0)}"
            f" · {format_currency(item.get('total_price', 0))}"
        )
    status = str(order.get('status') or 'Pending')
    status_label = {
        'pending': ('⏳ በመጠባበቅ', '⏳ Pending'),
        'processing': ('🔄 በሂደት', '🔄 Processing'),
        'shipped': ('🚚 ተልኳል', '🚚 Shipped'),
        'delivered': ('✔️ ተጠናቋል', '✔️ Completed'),
        'completed': ('✔️ ተጠናቋል', '✔️ Completed'),
        'cancelled': ('❌ ተሰርዟል', '❌ Cancelled'),
    }.get(status.strip().lower(), (status, status))
    labels = (
        ("📋 ትዕዛዝ", "👤 ደንበኛ", "📱 ስልክ", "📦 ምርቶች",
         "💰 ጠቅላላ", "📍 አድራሻ", "💳 ክፍያ")
        if lang == 'am'
        else ("📋 Order", "👤 Customer", "📱 Phone", "📦 Items",
              "💰 Total", "📍 Address", "💳 Payment")
    )
    text = (
        f"{labels[0]} #{order.get('order_number', order.get('id', 'N/A'))}\n"
        f"{labels[1]}: {order.get('customer_name') or 'Customer'}\n"
        f"{labels[2]}: {order.get('customer_phone') or '—'}\n"
        f"📌 {status_label[0 if lang == 'am' else 1]}\n"
        f"{labels[3]}:\n{chr(10).join(item_lines) if item_lines else '—'}\n"
        f"{labels[4]}: {format_currency(order.get('final_amount', 0))}\n"
        f"{labels[5]}: {order.get('shipping_address') or '—'}\n"
        f"{labels[6]}: {format_payment_method(order.get('payment_method'), lang)}"
    )
    keyboard = get_admin_order_actions_keyboard(
        order['id'],
        status=status,
        lang=lang,
    )
    return text, keyboard


def show_all_users(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ተጠቃሚዎች ማሳየት"""
    try:
        users = db.get_all_users(limit=20)
    except TypeError:
        users = db.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "👥 ምንም ተጠቃሚ አልተገኘም.")
        return []

    text = "\n".join(
        f"• {user.get('first_name', 'Unknown')} (@{user.get('username', 'n/a')})"
        for user in users[:10]
    )
    bot.send_message(message.chat.id, f"👥 ተጠቃሚዎች\n\n{text}")
    return users


def show_active_users(message: Message, db: Database, bot: TeleBot):
    """ንቁ ተጠቃሚዎችን ማሳየት"""
    try:
        users = db.get_active_users(days=7)
    except TypeError:
        users = db.get_active_users()
    if not users:
        bot.send_message(message.chat.id, "📊 ንቁ ተጠቃሚ አልተገኘም.")
        return []

    text = "\n".join(
        f"• {user.get('first_name', 'Unknown')} ({user.get('last_active', 'N/A')})"
        for user in users[:10]
    )
    bot.send_message(message.chat.id, f"📊 ንቁ ተጠቃሚዎች\n\n{text}")
    return users


def start_broadcast(message: Message, db: Database, bot: TeleBot):
    """ማስታወቂያ መላክ ሂደት መጀመር"""
    bot.send_message(message.chat.id, "📢 ማስታወቂያ ለመላክ መልእክት ያስገቡ.")
    return "broadcast started"


def start_find_user(message: Message, db: Database, bot: TeleBot):
    """ተጠቃሚ መፈለግ ሂደት መጀመር"""
    bot.send_message(message.chat.id, "👤 የተጠቃሚ መለያ ያስገቡ:")
    return "find user started"


def show_sales_report(message: Message, db: Database, bot: TeleBot):
    """የሽያጭ ሪፖርት ማሳየት"""
    report = db.get_sales_report(days=30)
    if not report:
        bot.send_message(message.chat.id, "📊 ምንም የሽያጭ ሪፖርት አልተገኘም.")
        return []

    text = "\n".join(
        f"• {row.get('sale_date', 'N/A')}: {row.get('total_sales', 0)} ETB"
        for row in report[:10]
    )
    bot.send_message(message.chat.id, f"📊 የሽያጭ ሪፖርት\n\n{text}")
    return report


def show_top_products(message: Message, db: Database, bot: TeleBot):
    """ከፍተኛ ምርቶችን ማሳየት"""
    products = db.get_top_products(limit=5)
    if not products:
        bot.send_message(message.chat.id, "🏆 ምንም ከፍተኛ ምርት አልተገኘም.")
        return []

    text = "\n".join(
        f"• {product.get('name_am', 'N/A')} ({product.get('total_sold', 0)} sold)"
        for product in products
    )
    bot.send_message(message.chat.id, f"🏆 ከፍተኛ ምርቶች\n\n{text}")
    return products


def show_daily_report(message: Message, db: Database, bot: TeleBot):
    """የዕለት ሪፖርት ማሳየት"""
    stats = db.get_daily_stats()
    text = (
        f"📈 አዲስ ተጠቃሚዎች: {stats.get('new_users', 0)}\n"
        f"📦 አዲስ ትዕዛዞች: {stats.get('new_orders', 0)}\n"
        f"💰 የዕለት ገቢ: {stats.get('daily_revenue', 0)} ETB"
    )
    bot.send_message(message.chat.id, f"📈 የዕለት ሪፖርት\n\n{text}")
    return stats


def show_category_report(message: Message, db: Database, bot: TeleBot):
    """የምድብ ሪፖርት ማሳየት"""
    stats = db.get_category_stats()
    if not stats:
        bot.send_message(message.chat.id, "📊 ምንም የምድብ ሪፖርት አልተገኘም.")
        return []

    text = "\n".join(
        f"• {row.get('category', 'N/A')}: {row.get('product_count', 0)} products"
        for row in stats
    )
    bot.send_message(message.chat.id, f"📊 የምድብ ሪፖርት\n\n{text}")
    return stats


def start_add_discount(message: Message, db: Database, bot: TeleBot):
    """አዲስ ቅናሽ መፍጠር ሂደት መጀመር"""
    bot.send_message(message.chat.id, "🏷️ የቅናሽ ኮድ ያስገቡ:")
    return "discount started"


def list_discounts(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ቅናሾች ማሳየት"""
    discounts = db.get_discounts() if hasattr(db, 'get_discounts') else []
    if not discounts:
        bot.send_message(message.chat.id, "🏷️ ምንም ቅናሽ አልተገኘም.")
        return []

    text = "\n".join(f"• {discount.get('code', 'N/A')} - {discount.get('discount_percent', 0)}%" for discount in discounts[:10])
    bot.send_message(message.chat.id, f"🏷️ ቅናሾች\n\n{text}")
    return discounts


def list_products(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ምርቶች ማሳየት"""
    products = db.get_products(limit=10)
    if not products:
        bot.send_message(message.chat.id, "📦 ምንም ምርት አልተገኘም.")
        return []

    text = "\n".join(f"• {product.get('name_am', 'N/A')} - {product.get('price', 0)} ETB" for product in products[:10])
    bot.send_message(message.chat.id, f"📦 ምርቶች\n\n{text}")
    return products


def start_edit_product(message: Message, db: Database, bot: TeleBot):
    """ምርት ማስተካከል ሂደት መጀመር"""
    bot.send_message(message.chat.id, "✏️ የምርት አይዲ ያስገቡ:")
    return "edit product started"


def start_delete_product(message: Message, db: Database, bot: TeleBot):
    """ምርት መሰረዝ ሂደት መጀመር"""
    prompt = bot.send_message(message.chat.id, "🗑️ የምርት አይዲ ያስገቡ:")
    bot.register_next_step_handler(prompt, process_delete_product, db, bot)
    return "delete product started"


def process_delete_product(
    message: Message,
    db: Database,
    bot: TeleBot,
    product_id_text: Optional[str] = None,
):
    """Validate and delete a product requested by an administrator."""
    if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
        _send_admin_message(bot, message, "⛔ ይህን ለማድረግ ፈቃድ የለዎትም!")
        return False

    value = product_id_text or (message.text or '').strip()
    try:
        product_id = int(value)
    except ValueError:
        _send_admin_message(bot, message, "❌ እባክዎ ትክክለኛ የምርት ID ያስገቡ።")
        return False

    if product_id <= 0 or not db.get_product(product_id):
        _send_admin_message(bot, message, "❌ ይህ ምርት አልተገኘም።")
        return False

    if not db.delete_product(product_id):
        _send_admin_message(bot, message, "❌ ምርቱን መሰረዝ አልተቻለም።")
        return False

    _send_admin_message(bot, message, f"✅ ምርት #{product_id} ተሰርዟል።")
    db.log_activity(message.from_user.id, 'delete_product', f'Product ID: {product_id}')
    return True


def show_low_stock(message: Message, db: Database, bot: TeleBot):
    """ዝቅተኛ ክምችት ያላቸውን ምርቶች ማሳየት"""
    products = db.get_low_stock_products(threshold=5)
    if not products:
        bot.send_message(message.chat.id, "📦 ዝቅተኛ ክምችት ያላቸው ምርቶች የሉም.")
        return []

    text = "\n".join(f"• {product.get('name_am', 'N/A')} ({product.get('stock_quantity', 0)})" for product in products)
    bot.send_message(message.chat.id, f"📦 ዝቅተኛ ክምችት\n\n{text}")
    return products


def show_admin_panel(message: Message, db: Database, bot: TeleBot):
    """Render the inline admin panel for commands and package-level callers."""
    user_id = message.from_user.id
    if not is_admin(user_id, config.bot.ADMIN_IDS):
        return bot.send_message(message.chat.id, "⛔ You are not authorized to use the admin panel.")
    lang = get_user_lang(db, user_id)
    return bot.send_message(
        message.chat.id,
        "⚙️ የአስተዳዳሪ ፓነል" if lang == 'am' else "⚙️ Admin Panel",
        reply_markup=get_admin_keyboard(lang),
    )


def show_stats(message: Message, db: Database, bot: TeleBot):
    """Show the admin dashboard summary for the /stats command."""
    if not is_admin(message.from_user.id, config.bot.ADMIN_IDS):
        return bot.send_message(message.chat.id, "⛔ You are not authorized to view statistics.")
    order_stats = db.get_order_stats()
    summary = order_stats.get('summary', {})
    pending = next(
        (value.get('count', 0) for key, value in order_stats.items() if key.lower() == 'pending'),
        0,
    )
    text = (
        f"👥 Users: {db.get_user_count()}\n"
        f"📦 Products: {db.get_product_count()}\n"
        f"📋 Orders: {summary.get('total_orders', 0)}\n"
        f"⏳ Pending: {pending}\n"
        f"💰 Revenue: {format_currency(summary.get('total_revenue', 0))}"
    )
    return bot.send_message(message.chat.id, text)