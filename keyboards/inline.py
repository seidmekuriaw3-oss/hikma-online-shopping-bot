# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - Inline ኪቦርዶች
ይህ ፋይል ሁሉንም የ Inline ኪቦርድ መፍጠሪያ ተግባራትን ይይዛል
"""

from typing import Dict, List, Optional
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import config
from utils.helpers import get_text, format_payment_method


_PRODUCT_CATEGORY_LABELS = {
    'women': ("👗 የሴቶች ፋሽን", "👗 Women's Fashion"),
    'men': ("👕 የወንዶች ፋሽን", "👕 Men's Fashion"),
    'kids': ("👶 የልጆች አልባሳት", "👶 Kids & Baby"),
    'pajamas': ("🛌 ፒጃማ እና የቤት ልብስ", "🛌 Pajamas & Loungewear"),
    'shoes': ("👟 ጫማዎች", "👟 Shoes & Footwear"),
    'accessories': ("👜 ቦርሳ እና መዋቢያ", "👜 Bags & Accessories"),
}

_STOREFRONT_CATEGORY_LABELS = {
    **_PRODUCT_CATEGORY_LABELS,
    'new_arrivals': ("✨ አዲስ የገቡ", "✨ New Arrivals"),
    'hot_deals': ("🔥 ቅናሽ ያላቸው", "🔥 Hot Deals"),
}


def get_main_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """Build the welcome keyboard around the storefront category menu."""
    markup = InlineKeyboardMarkup(row_width=2)

    markup.add(
        InlineKeyboardButton(
            "🛍️ ምርቶች" if lang == 'am' else "🛍️ Products",
            callback_data="browse_categories",
        ),
        InlineKeyboardButton(
            "🛒 ጋሪ" if lang == 'am' else "🛒 Cart",
            callback_data="view_cart",
        ),
    )
    markup.add(
        InlineKeyboardButton(
            "📋 ትዕዛዞቼ" if lang == 'am' else "📋 My Orders",
            callback_data="view_orders",
        ),
        InlineKeyboardButton(
            "❤️ ተወዳጆች" if lang == 'am' else "❤️ Wishlist",
            callback_data="show_wishlist",
        ),
    )
    markup.add(
        InlineKeyboardButton(
            "👤 መገለጫ" if lang == 'am' else "👤 Profile",
            callback_data="view_profile",
        ),
        InlineKeyboardButton(
            "📍 አድራሻ እና ስልክ" if lang == 'am' else "📍 Contact",
            callback_data="view_contact",
        ),
    )
    return markup


def get_storefront_categories_keyboard(
    counts: Optional[Dict[str, int]] = None,
    lang: str = 'am',
) -> InlineKeyboardMarkup:
    """Build the two-column category picker, including counts when supplied."""
    counts = counts or {}
    markup = InlineKeyboardMarkup(row_width=2)
    buttons = []
    for key, labels in _STOREFRONT_CATEGORY_LABELS.items():
        label = labels[0 if lang == 'am' else 1]
        if key in counts:
            label = f"{label} ({counts[key]})"
        buttons.append(InlineKeyboardButton(
            label,
            callback_data=f"browse_cat:{key}:0",
        ))
    markup.add(*buttons)
    markup.add(InlineKeyboardButton(
        "🔙 ዋና ሜኑ" if lang == 'am' else "🔙 Main Menu",
        callback_data="main_menu",
    ))
    return markup


def get_admin_product_category_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """Build the category picker used while creating a product."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(*[
        InlineKeyboardButton(
            labels[0 if lang == 'am' else 1],
            callback_data=f"add_product_category:{key}",
        )
        for key, labels in _PRODUCT_CATEGORY_LABELS.items()
    ])
    return markup


def get_start_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """Build the welcome message's quick-start actions."""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(
        InlineKeyboardButton(
            "🛍️ ሱቁን ይጎብኙ" if lang == 'am' else "🛍️ Browse Shop",
            callback_data="browse_categories",
        ),
        InlineKeyboardButton(
            "🌐 ቋንቋ" if lang == 'am' else "🌐 Language",
            callback_data="change_language",
        ),
    )
    return markup


def get_back_keyboard(callback_data: str = "main_menu", lang: str = 'am') -> InlineKeyboardMarkup:
    """የመመለሻ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data=callback_data
        )
    )
    return markup


def get_product_keyboard(product_id: int, category: str, index: int, total: int, 
                         in_stock: bool = True, lang: str = 'am') -> InlineKeyboardMarkup:
    """የምርት ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    # አሰሳ
    nav_buttons = []
    
    if index > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"product_nav_{category}_{index-1}"
            )
        )
    
    nav_buttons.append(
        InlineKeyboardButton(
            f"{index+1}/{total}",
            callback_data="ignore"
        )
    )
    
    if index < total - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=f"product_nav_{category}_{index+1}"
            )
        )
    
    markup.row(*nav_buttons)
    
    # ድርጊቶች
    if in_stock:
        markup.add(
            InlineKeyboardButton(
                "🛒 " + get_text(lang, 'buy'),
                callback_data=f"product_buy_{product_id}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "⭐ " + get_text(lang, 'review'),
            callback_data=f"product_review_{product_id}"
        ),
        InlineKeyboardButton(
            "❤️ " + get_text(lang, 'wishlist'),
            callback_data=f"product_wishlist_{product_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="main_menu"
        )
    )
    
    return markup


def get_browse_product_keyboard(
    product_id: int,
    category: str,
    index: int,
    total: int,
    lang: str = 'am',
    photo_index: int = 0,
    photo_count: int = 1,
) -> InlineKeyboardMarkup:
    """Build the compact keyboard used by category product cards."""
    markup = InlineKeyboardMarkup(row_width=2)
    back_label, next_label = (
        ("⬅️ ወደኋላ", "ቀጣይ ➡️") if lang == 'am' else ("⬅️ Back", "Next ➡️")
    )
    markup.row(
        InlineKeyboardButton(
            back_label,
            callback_data=f"browse_cat:{category}:{index - 1}" if index > 0 else "browse_noop",
        ),
        InlineKeyboardButton(
            next_label,
            callback_data=f"browse_cat:{category}:{index + 1}" if index < total - 1 else "browse_noop",
        ),
    )
    if photo_count > 1:
        markup.row(*get_product_photo_navigation(
            product_id,
            photo_index,
            photo_count,
            lang,
            view='browse',
        ))
    markup.row(
        InlineKeyboardButton(
            "🛒 ወደ ጋሪ ጨምር" if lang == 'am' else "🛒 Add to Cart",
            callback_data=f"product_cart_{product_id}",
        ),
        InlineKeyboardButton(
            "❤️ ተወዳጅ" if lang == 'am' else "❤️ Wishlist",
            callback_data=f"product_wishlist_{product_id}",
        ),
    )
    action_row = []
    if config.bot.ADMIN_USERNAME:
        action_row.append(
            InlineKeyboardButton(
                "💬 ቀጥታ ለመግዛት" if lang == 'am' else "💬 Buy Now",
                url=f"https://t.me/{config.bot.ADMIN_USERNAME}",
            )
        )
    action_row.append(
        InlineKeyboardButton(
            "🔙 ወደ ካታጎሪዎች" if lang == 'am' else "🔙 Back to Categories",
            callback_data="browse_categories",
        )
    )
    markup.row(*action_row)
    return markup


def get_product_photo_navigation(
    product_id: int,
    photo_index: int,
    photo_count: int,
    lang: str,
    view: str,
):
    """Build the photo gallery row shared by product-card layouts."""
    buttons = []
    if photo_index > 0:
        buttons.append(InlineKeyboardButton(
            "⬅️ ቀዳሚ" if lang == 'am' else "⬅️ Previous",
            callback_data=(
                f"product_image_{product_id}_{photo_index - 1}_{view}"
            ),
        ))
    buttons.append(InlineKeyboardButton(
        f"{photo_index + 1}/{photo_count}",
        callback_data="ignore",
    ))
    if photo_index < photo_count - 1:
        buttons.append(InlineKeyboardButton(
            "ቀጣይ ➡️" if lang == 'am' else "Next ➡️",
            callback_data=(
                f"product_image_{product_id}_{photo_index + 1}_{view}"
            ),
        ))
    return buttons


def get_rating_keyboard(product_id: int, lang: str = 'am') -> InlineKeyboardMarkup:
    """የደረጃ ምርጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=5)
    
    # ደረጃ 1-5
    buttons = []
    for i in range(1, 6):
        buttons.append(
            InlineKeyboardButton(
                f"⭐ {i}",
                callback_data=f"rate_{product_id}_{i}"
            )
        )
    
    markup.add(*buttons)
    
    markup.add(
        InlineKeyboardButton(
            "💬 " + get_text(lang, 'add_comment'),
            callback_data=f"review_comment_{product_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data=f"product_view_{product_id}"
        )
    )
    
    return markup


def get_order_keyboard(order_id: int, status: str, lang: str = 'am') -> InlineKeyboardMarkup:
    """የትዕዛዝ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "📋 ዝርዝር" if lang == 'am' else "📋 Details",
            callback_data=f"order_{order_id}"
        )
    )
    if config.bot.ADMIN_USERNAME:
        markup.add(InlineKeyboardButton(
            "💬 አስተዳዳሪን ያግኙ" if lang == 'am' else "💬 Contact support",
            url=f"https://t.me/{config.bot.ADMIN_USERNAME}",
        ))
    
    markup.add(
        InlineKeyboardButton(
            "🔙 ትዕዛዞቼ" if lang == 'am' else "🔙 My Orders",
            callback_data="back_to_orders"
        )
    )
    
    return markup


def get_admin_order_actions_keyboard(
    order_id: int,
    status: str = '',
    lang: str = 'am',
) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    labels = (
        (
            ("✅ አረጋግጥ", "Processing"),
            ("🚚 ተልኳል", "Shipped"),
            ("✔️ ተጠናቋል", "Delivered"),
            ("❌ ሰርዝ", "Cancelled"),
        )
        if lang == 'am'
        else (
            ("✅ Confirm", "Processing"),
            ("🚚 Shipped", "Shipped"),
            ("✔️ Completed", "Delivered"),
            ("❌ Cancel", "Cancelled"),
        )
    )
    for label, next_status in labels:
        if next_status.lower() != (status or '').strip().lower():
            markup.add(InlineKeyboardButton(
                label,
                callback_data=f"admin_order_status_{order_id}_{next_status}",
            ))
    markup.add(InlineKeyboardButton(
        "🔙 ወደ ትዕዛዞች" if lang == 'am' else "🔙 Back to Orders",
        callback_data="admin_back_to_orders",
    ))
    return markup


def get_payment_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የክፍያ ዘዴ ምርጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            format_payment_method('chapa', lang),
            callback_data="pay_chapa"
        ),
        InlineKeyboardButton(
            format_payment_method('telebirr', lang),
            callback_data="pay_telebirr"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            format_payment_method('cash_on_delivery', lang),
            callback_data="pay_cash"
        ),
        InlineKeyboardButton(
            format_payment_method('bank_transfer', lang),
            callback_data="pay_bank"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 ወደ ጋሪ" if lang == 'am' else "🔙 Back to Cart",
            callback_data="view_cart"
        ),
        InlineKeyboardButton(
            "❌ ሰርዝ" if lang == 'am' else "❌ Cancel",
            callback_data="checkout_cancel"
        )
    )
    
    return markup


def get_confirm_keyboard(action: str, lang: str = 'am') -> InlineKeyboardMarkup:
    """የማረጋገጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "✅ " + get_text(lang, 'confirm'),
            callback_data=f"confirm_{action}"
        ),
        InlineKeyboardButton(
            "❌ " + get_text(lang, 'cancel'),
            callback_data=f"cancel_{action}"
        )
    )
    
    return markup


def get_admin_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የአስተዳዳሪ Inline ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📦 " + get_text(lang, 'products'), callback_data="admin_products"),
        InlineKeyboardButton("📋 " + get_text(lang, 'orders'), callback_data="admin_orders"),
        InlineKeyboardButton("👥 " + get_text(lang, 'users'), callback_data="admin_users"),
        InlineKeyboardButton("📊 " + get_text(lang, 'reports'), callback_data="admin_reports"),
        InlineKeyboardButton("🏷️ " + get_text(lang, 'discounts'), callback_data="admin_discounts"),
        InlineKeyboardButton("⚙️ " + get_text(lang, 'settings'), callback_data="admin_settings"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="main_menu")
    )
    
    return markup


def get_pagination_keyboard(base_callback: str, current_page: int, total_pages: int, 
                           lang: str = 'am') -> InlineKeyboardMarkup:
    """የገጽ አሰሳ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=3)
    
    buttons = []
    
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"{base_callback}_{current_page-1}"
            )
        )
    
    buttons.append(
        InlineKeyboardButton(
            f"{current_page}/{total_pages}",
            callback_data="ignore"
        )
    )
    
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=f"{base_callback}_{current_page+1}"
            )
        )
    
    markup.row(*buttons)
    return markup


def get_filter_keyboard(filters: List[str], lang: str = 'am') -> InlineKeyboardMarkup:
    """የማጣሪያ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    for filter_name in filters:
        markup.add(
            InlineKeyboardButton(
                filter_name,
                callback_data=f"filter_{filter_name}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="main_menu"
        )
    )
    
    return markup


def get_social_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """Build social links using the configured Telegram admin account."""
    markup = InlineKeyboardMarkup(row_width=1)

    if config.bot.ADMIN_USERNAME:
        markup.add(
            InlineKeyboardButton(
                "📱 " + get_text(lang, 'telegram'),
                url=f"https://t.me/{config.bot.ADMIN_USERNAME}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="main_menu"
        )
    )
    
    return markup


def get_contact_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=1)
    if config.bot.ADMIN_USERNAME:
        markup.add(InlineKeyboardButton(
            "💬 አስተዳዳሪውን ያግኙ" if lang == 'am' else "💬 Chat with Admin",
            url=f"https://t.me/{config.bot.ADMIN_USERNAME}",
        ))
    markup.add(InlineKeyboardButton(
        "🔙 ዋና ሜኑ" if lang == 'am' else "🔙 Main Menu",
        callback_data="main_menu",
    ))
    return markup