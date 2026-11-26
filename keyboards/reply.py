# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - Reply ኪቦርዶች
ይህ ፋይል ሁሉንም የ Reply ኪቦርድ መፍጠሪያ ተግባራትን ይይዛል
"""

from typing import Optional
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from database import Database
from utils.helpers import get_text, get_user_lang
from config import config


def get_main_menu(user_id: int, db: Database) -> ReplyKeyboardMarkup:
    """ዋና ሜኑ መፍጠር"""
    lang = get_user_lang(db, user_id)

    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = [
        KeyboardButton("🛍️ ምርቶች" if lang == 'am' else "🛍️ Products"),
        KeyboardButton("🛒 ጋሪ" if lang == 'am' else "🛒 Cart"),
        KeyboardButton("📋 ትዕዛዞቼ" if lang == 'am' else "📋 My Orders"),
        KeyboardButton("❤️ ተወዳጆች" if lang == 'am' else "❤️ Wishlist"),
        KeyboardButton("👤 መገለጫ" if lang == 'am' else "👤 Profile"),
        KeyboardButton("📍 አድራሻ እና ስልክ" if lang == 'am' else "📍 Contact"),
    ]

    if user_id in config.bot.ADMIN_IDS:
        buttons.append(
            KeyboardButton("⚙️ አስተዳዳሪ" if lang == 'am' else "⚙️ Admin Panel")
        )

    markup.add(*buttons)
    return markup


def get_admin_menu(user_id: int, lang: str = 'am') -> ReplyKeyboardMarkup:
    """የአስተዳዳሪ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        KeyboardButton(get_text(lang, 'products')),
        KeyboardButton(get_text(lang, 'orders')),
        KeyboardButton(get_text(lang, 'users')),
        KeyboardButton(get_text(lang, 'reports')),
        KeyboardButton(get_text(lang, 'discounts')),
        KeyboardButton(get_text(lang, 'settings')),
        KeyboardButton(get_text(lang, 'back'))
    ]
    
    markup.add(*buttons)
    return markup


def get_language_menu() -> ReplyKeyboardMarkup:
    """የቋንቋ ምርጫ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🇪🇹 አማርኛ"),
        KeyboardButton("🇬🇧 English")
    )
    return markup


def get_contact_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የእውቂያ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        KeyboardButton(get_text(lang, 'share_contact'), request_contact=True),
        KeyboardButton(get_text(lang, 'back'))
    )
    return markup


def get_cancel_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የመሰረዝ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton(get_text(lang, 'cancel')))
    return markup


def get_remove_keyboard() -> ReplyKeyboardRemove:
    """ኪቦርዱን ለማስወገድ"""
    return ReplyKeyboardRemove()


def get_quantity_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የቁጥር ምርጫ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    markup.add(
        KeyboardButton("1"),
        KeyboardButton("2"),
        KeyboardButton("3"),
        KeyboardButton("4"),
        KeyboardButton("5"),
        KeyboardButton("10"),
        KeyboardButton(get_text(lang, 'cancel'))
    )
    return markup


def get_payment_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የክፍያ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("💳 " + get_text(lang, 'chapa')),
        KeyboardButton("📱 " + get_text(lang, 'telebirr')),
        KeyboardButton("💰 " + get_text(lang, 'cash')),
        KeyboardButton(get_text(lang, 'cancel'))
    )
    return markup


def get_address_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የአድራሻ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(
        KeyboardButton("📍 " + get_text(lang, 'share_location'), request_location=True),
        KeyboardButton("✏️ " + get_text(lang, 'enter_manually')),
        KeyboardButton(get_text(lang, 'cancel'))
    )
    return markup


def get_order_status_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የትዕዛዝ ሁኔታ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("⏳ " + get_text(lang, 'pending')),
        KeyboardButton("🔄 " + get_text(lang, 'processing')),
        KeyboardButton("🚚 " + get_text(lang, 'shipped')),
        KeyboardButton("✅ " + get_text(lang, 'delivered')),
        KeyboardButton("❌ " + get_text(lang, 'cancelled')),
        KeyboardButton(get_text(lang, 'back'))
    )
    return markup


def get_help_menu(lang: str = 'am') -> ReplyKeyboardMarkup:
    """የእርዳታ ሜኑ መፍጠር"""
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("❓ " + get_text(lang, 'faq')),
        KeyboardButton("📞 " + get_text(lang, 'contact_support')),
        KeyboardButton("🔙 " + get_text(lang, 'back'))
    )
    return markup