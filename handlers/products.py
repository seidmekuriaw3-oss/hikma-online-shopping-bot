# -*- coding: utf-8 -*-

"""
Hikma Online Shopping Bot - የምርት እጅ አያያዝ
ይህ ፋይል ሁሉንም የምርት እጅ አያያዞችን ይይዛል
"""

import logging
import json
import re
from typing import Optional, Dict, List
from datetime import datetime

from telebot import TeleBot
from telebot.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto,
)

from database import Database
from models.product import get_images
from utils.helpers import get_text, get_user_lang, format_currency
from keyboards.inline import (
    get_product_keyboard, get_rating_keyboard, get_browse_product_keyboard,
    get_storefront_categories_keyboard, get_product_photo_navigation,
)
from services.notifications import notify_admins

logger = logging.getLogger(__name__)

add_to_cart = None

# ለምርት ጊዜያዊ መረጃ
product_cache = {}


def _product_caption(product: Dict, index: int, total: int, lang: str) -> str:
    name = product.get('name_am') if lang == 'am' else product.get('name_en')
    name = name or get_text(lang, 'product')
    size = product.get('size') or ('ሁሉም መጠኖች' if lang == 'am' else 'One size')
    status_value = str(product.get('status') or 'In Stock').strip().lower()
    in_stock = product.get('stock_quantity', 0) > 0 and status_value not in {
        'sold out', 'out of stock', 'unavailable'
    }
    status = (
        ("✅ በክምችት ላይ" if in_stock else "❌ ተሽጦ አልቋል")
        if lang == 'am'
        else ("✅ In Stock" if in_stock else "❌ Sold Out")
    )
    position = f"{index + 1} / {total}"
    if lang == 'am':
        return (
            f"🛍️ {name}\n"
            f"💰 ዋጋ: {format_currency(product.get('price', 0))}\n"
            f"📏 መጠን: {size}\n"
            f"📦 ሁኔታ: {status}\n"
            f"🔢 {position}"
        )
    return (
        f"🛍️ {name}\n"
        f"💰 Price: {format_currency(product.get('price', 0))}\n"
        f"📏 Size: {size}\n"
        f"📦 Status: {status}\n"
        f"🔢 {position}"
    )


def show_product_card(
    chat_id: int,
    product: Dict,
    index: int,
    total: int,
    category: str,
    lang: str,
    bot: TeleBot,
    message_id: Optional[int] = None,
    is_photo_message: bool = False,
    photo_index: int = 0,
):
    """Send a product card or update the existing carousel message."""
    caption = _product_caption(product, index, total, lang)
    images = get_images(product)
    if images:
        photo_index = min(max(photo_index, 0), len(images) - 1)
    keyboard = get_browse_product_keyboard(
        product['id'],
        category,
        index,
        total,
        lang,
        photo_index=photo_index,
        photo_count=len(images),
    )
    image_id = images[photo_index] if images else None

    if message_id is not None:
        if image_id:
            try:
                bot.edit_message_media(
                    InputMediaPhoto(media=image_id, caption=caption),
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard,
                )
                return
            except Exception:
                logger.exception("Could not edit carousel photo; falling back to text")
        if is_photo_message:
            try:
                bot.edit_message_caption(
                    caption,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard,
                )
                return
            except Exception:
                logger.exception("Could not edit carousel caption; falling back to text")
        try:
            bot.edit_message_text(
                caption,
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=keyboard,
            )
            return
        except Exception:
            logger.exception("Could not edit carousel text; sending a new product card")

    if image_id:
        try:
            return bot.send_photo(chat_id, image_id, caption=caption, reply_markup=keyboard)
        except Exception:
            logger.exception("Product photo is unavailable; sending its text card")
    return bot.send_message(chat_id, caption, reply_markup=keyboard)


def show_category_products(message: Message, category: str, db: Database, bot: TeleBot):
    """Open the first visual product card for a category."""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    products = db.get_products(category=category, limit=20, offset=0)
    if not products:
        if category == 'hot_deals':
            return _render_category_menu(
                message.chat.id, lang, db, bot
            )
        return bot.send_message(
            message.chat.id,
            get_text(lang, 'no_products_in_category'),
        )
    return show_product_card(
        message.chat.id, products[0], 0, len(products), category, lang, bot
    )


def _category_menu_text(lang: str) -> str:
    if lang == 'am':
        return "🛍️ ወደ ሂክማ ሱቅ እንኳን ደህና መጡ!\n\nምድብ ይምረጡ፦"
    return "🛍️ Welcome to the Hikma store!\n\nChoose a category:"


def _render_category_menu(
    chat_id: int,
    lang: str,
    db: Database,
    bot: TeleBot,
    message_id: Optional[int] = None,
    is_photo_message: bool = False,
):
    count_method = getattr(db, 'get_product_category_counts', None)
    counts = count_method() if callable(count_method) else {}
    text = _category_menu_text(lang)
    keyboard = get_storefront_categories_keyboard(counts, lang)

    if message_id is not None:
        try:
            if is_photo_message:
                bot.edit_message_caption(
                    text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard,
                )
            else:
                bot.edit_message_text(
                    text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard,
                )
            return
        except Exception:
            logger.exception("Could not replace the current message with categories")
    return bot.send_message(chat_id, text, reply_markup=keyboard)


def show_category_menu(message: Message, db: Database, bot: TeleBot):
    """Display the storefront's category picker."""
    lang = get_user_lang(db, message.from_user.id)
    return _render_category_menu(message.chat.id, lang, db, bot)


def search_products(message: Message, query: str, db: Database, bot: TeleBot):
    """Search products for calls originating from the general text handler."""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    products = db.search_products(query, limit=20)

    if not products:
        bot.send_message(
            message.chat.id,
            "🔍 " + get_text(lang, 'search_no_results').format(query),
        )
        return []

    markup = InlineKeyboardMarkup(row_width=1)
    for product in products[:10]:
        name = product.get('name_am') if lang == 'am' else product.get('name_en')
        markup.add(InlineKeyboardButton(
            f"{name or get_text(lang, 'product')} · {format_currency(product['price'])}",
            callback_data=f"product_view_{product['id']}",
        ))
    bot.send_message(
        message.chat.id,
        f"🔍 {get_text(lang, 'search_results')}: “{query}”",
        reply_markup=markup,
    )
    return products


def register(bot: TeleBot, db: Database):
    """የምርት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ምርቶችን በምድብ ማሳየት ====================

    @bot.callback_query_handler(func=lambda call: call.data == 'browse_categories')
    def handle_browse_categories(call: CallbackQuery):
        lang = get_user_lang(db, call.from_user.id)
        _render_category_menu(
            call.message.chat.id,
            lang,
            db,
            bot,
            message_id=call.message.message_id,
            is_photo_message=getattr(call.message, 'content_type', None) == 'photo',
        )
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
    def handle_category_selection(call: CallbackQuery):
        """የምድብ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        category = call.data.replace('category_', '')
        lang = get_user_lang(db, user_id)
        
        # ምርቶችን ማግኘት
        products = db.get_products(category=category, limit=20, offset=0)
        
        if not products:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'no_products_in_category')
            )
            return
        
        show_product_card(
            call.message.chat.id, products[0], 0, len(products), category, lang, bot
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('browse_cat:'))
    def handle_browse_category(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        try:
            _, category, index_value = call.data.split(':', 2)
            index = int(index_value)
        except (ValueError, TypeError):
            bot.answer_callback_query(call.id, get_text(lang, 'no_more_products'))
            return

        products = db.get_products(category=category, limit=20, offset=0)
        if not products or not 0 <= index < len(products):
            if category == 'hot_deals' and not products:
                _render_category_menu(
                    call.message.chat.id,
                    lang,
                    db,
                    bot,
                    message_id=call.message.message_id,
                    is_photo_message=getattr(call.message, 'content_type', None) == 'photo',
                )
                bot.answer_callback_query(
                    call.id,
                    "አሁን ልዩ ቅናሽ የለም። ሌላ ምድብ ይምረጡ።"
                    if lang == 'am'
                    else "No active deals right now. Choose another category.",
                )
                return
            bot.answer_callback_query(call.id, get_text(lang, 'no_more_products'))
            return

        is_photo_message = getattr(call.message, 'content_type', None) == 'photo'
        is_category_menu = getattr(call.message, 'text', None) == _category_menu_text(lang)
        show_product_card(
            call.message.chat.id,
            products[index],
            index,
            len(products),
            category,
            lang,
            bot,
            message_id=(
                None
                if is_category_menu
                else call.message.message_id
            ),
            is_photo_message=is_photo_message,
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'browse_noop')
    def handle_browse_boundary(call: CallbackQuery):
        bot.answer_callback_query(call.id)
    
    # ==================== ምርት ማሳየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith((
        'product_view_', 'product_nav_', 'product_buy_', 'product_review_', 'product_cart_'
    )))
    def handle_product_navigation(call: CallbackQuery):
        """የምርት አሰሳ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        # መረጃውን መተንተን
        parts = call.data.split('_')
        action = parts[1]
        
        if action == 'view':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            
            if not product:
                bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
                return
            
            # የምርት እይታ መመዝገብ
            db.log_activity(user_id, 'view_product', f'ምርት ID: {product_id}')
            
            # ምርት ማሳየት
            show_product_detail(call.message.chat.id, product, lang, db, bot)
            bot.answer_callback_query(call.id)
        
        elif action == 'nav':
            # አሰሳ: product_nav_category_index
            category = parts[2]
            index = int(parts[3])
            
            products = db.get_products(category=category, limit=20, offset=0)
            
            if not products or index >= len(products):
                bot.answer_callback_query(call.id, get_text(lang, 'no_more_products'))
                return
            
            show_product_card(
                call.message.chat.id,
                products[index],
                index,
                len(products),
                category,
                lang,
                bot,
                message_id=call.message.message_id,
                is_photo_message=getattr(call.message, 'content_type', None) == 'photo',
            )
            bot.answer_callback_query(call.id)
        
        elif action == 'buy':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            
            if not product:
                bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
                return
            
            if product['stock_quantity'] <= 0:
                bot.answer_callback_query(call.id, get_text(lang, 'out_of_stock'))
                return
            
            # የቁጥር ምርጫ ማሳየት
            show_quantity_selector(call.message.chat.id, product, lang, db, bot)
            bot.answer_callback_query(call.id)
        
        elif action == 'review':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            
            if not product:
                bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
                return
            
            # ግምገማ ማሳየት
            show_reviews(call.message.chat.id, product, lang, db, bot)
            bot.answer_callback_query(call.id)

        elif action == 'cart':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            if not product or product.get('stock_quantity', 0) <= 0:
                bot.answer_callback_query(call.id, get_text(lang, 'out_of_stock'))
                return
            if add_to_cart(user_id, product_id, 1, db):
                bot.answer_callback_query(
                    call.id,
                    "✅ ወደ ጋሪ ተጨምሯል" if lang == 'am' else "✅ Added to cart",
                )
            else:
                bot.answer_callback_query(call.id, get_text(lang, 'error'))
    
    # ==================== የቁጥር ምርጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('qty_'))
    def handle_quantity_selection(call: CallbackQuery):
        """የቁጥር ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        parts = call.data.split('_')
        product_id = int(parts[1])
        quantity = int(parts[2])
        
        product = db.get_product(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        
        if quantity > product['stock_quantity']:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'not_enough_stock').format(product['stock_quantity'])
            )
            return
        
        # ወደ ጋሪ መጨመር
        if not add_to_cart(user_id, product_id, quantity, db):
            bot.answer_callback_query(
                call.id,
                get_text(lang, 'not_enough_stock').format(product['stock_quantity']),
            )
            return
        
        bot.answer_callback_query(
            call.id, 
            get_text(lang, 'added_to_cart').format(
                product.get('name_am' if lang == 'am' else 'name_en')
                or get_text(lang, 'product'),
                quantity,
            )
        )
        
        # የምርት ዝርዝር ማሳየት
        show_product_detail(call.message.chat.id, product, lang, db, bot)
    
    # ==================== ግምገማ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
    def handle_rating(call: CallbackQuery):
        """የደረጃ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        parts = call.data.split('_')
        product_id = int(parts[1])
        rating = int(parts[2])
        
        # ተጠቃሚው ይህን ምርት መግዛቱን ማረጋገጥ
        orders = db.get_user_orders(user_id)
        has_purchased = any(
            any(item['product_id'] == product_id for item in db.get_order_items(order['id']))
            for order in orders
        )
        
        if not has_purchased:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'must_purchase_to_review')
            )
            return
        
        # ግምገማ ማስቀመጥ
        success = db.add_review({
            'user_id': user_id,
            'product_id': product_id,
            'rating': rating,
            'is_verified': 1
        })
        
        if success:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'review_added').format(rating)
            )
            
            # ለአስተዳዳሪ ማሳወቅ
            product = db.get_product(product_id)
            notify_admins(
                bot,
                f"⭐ *አዲስ ግምገማ!*\n\n"
                f"📦 ምርት: {product['name_am']}\n"
                f"⭐ ደረጃ: {rating}/5\n"
                f"👤 ተጠቃሚ: {call.from_user.first_name}"
            )
        else:
            bot.answer_callback_query(call.id, get_text(lang, 'error'))
    
    # ==================== ግምገማ አስተያየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('review_comment_'))
    def handle_review_comment(call: CallbackQuery):
        """የግምገማ አስተያየት አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        product_id = int(call.data.split('_')[2])
        
        msg = bot.send_message(
            call.message.chat.id,
            "💬 " + get_text(lang, 'review_comment_prompt')
        )
        bot.register_next_step_handler(msg, process_review_comment, product_id, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_review_comment(message: Message, product_id: int, db: Database, bot: TeleBot):
        """የግምገማ አስተያየት ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        skip_values = ('skip', 'ዝለል') if lang == 'am' else ('skip',)
        comment = None if message.text.lower() in skip_values else message.text
        
        # ግምገማ ማዘመን
        success = db.add_review({
            'user_id': user_id,
            'product_id': product_id,
            'comment': comment
        })
        
        if success:
            bot.send_message(
                message.chat.id,
                "✅ " + get_text(lang, 'review_comment_saved')
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'review_comment_failed')
            )
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_product(chat_id: int, product: Dict, index: int, total: int, 
                     category: str, lang: str, db: Database, bot: TeleBot):
        """ምርት ማሳየት"""
        return show_product_card(
            chat_id, product, index, total, category, lang, bot
        )
    
    def show_product_detail(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        return show_product_detail_image(
            chat_id, product, lang, db, bot
        )

    def show_product_detail_image(
        chat_id: int,
        product: Dict,
        lang: str,
        db: Database,
        bot: TeleBot,
        message_id: Optional[int] = None,
        photo_index: int = 0,
    ):
        """የምርት ዝርዝር ማሳየት"""
        # የምርት ደረጃ
        rating = product.get('rating_avg', 0)
        rating_count = product.get('rating_count', 0)
        stars = "⭐" * round(rating) if rating else "☆"
        
        # ስም
        name = (
            product.get('name_am' if lang == 'am' else 'name_en')
            or get_text(lang, 'product')
        )
        description = product.get('description_am', '') if lang == 'am' else product.get('description_en', '')
        
        # ሁኔታ
        status = get_text(
            lang,
            'in_stock' if product['stock_quantity'] > 0 else 'out_of_stock',
        )
        
        # መልዕክት
        msg = f"🔹 *{name}*\n\n"
        
        if description:
            msg += f"📝 {description}\n\n"
        
        msg += f"💰 *{get_text(lang, 'price')}:* {format_currency(product['price'])}\n"
        
        if product.get('compare_price'):
            msg += f"~~{format_currency(product['compare_price'])}~~\n"
        
        msg += f"📏 *{get_text(lang, 'size')}:* {product.get('size') or '—'}\n"
        msg += f"📦 *{get_text(lang, 'status')}:* {status}\n"
        msg += f"📊 *{get_text(lang, 'stock')}:* {product['stock_quantity']}\n"
        
        if rating:
            msg += f"⭐ {stars} ({rating_count} {get_text(lang, 'reviews')})\n"
        
        # ኪቦርድ
        markup = InlineKeyboardMarkup(row_width=2)
        images = get_images(product)
        if images:
            photo_index = min(max(photo_index, 0), len(images) - 1)
        if len(images) > 1:
            markup.row(*get_product_photo_navigation(
                product['id'],
                photo_index,
                len(images),
                lang,
                view='detail',
            ))
        
        if product['stock_quantity'] > 0:
            markup.add(
                InlineKeyboardButton(
                    "🛒 " + get_text(lang, 'buy'),
                    callback_data=f"product_buy_{product['id']}"
                )
            )
        
        markup.add(
            InlineKeyboardButton(
                "⭐ " + get_text(lang, 'review'),
                callback_data=f"product_review_{product['id']}"
            ),
            InlineKeyboardButton(
                "❤️ " + get_text(lang, 'wishlist'),
                callback_data=f"product_wishlist_{product['id']}"
            )
        )
        
        markup.add(
            InlineKeyboardButton(
                "🔙 " + get_text(lang, 'products'),
                callback_data=f"category_{product['category']}"
            )
        )
        
        if message_id is not None and images:
            bot.edit_message_media(
                InputMediaPhoto(media=images[photo_index], caption=msg, parse_mode='Markdown'),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=markup,
            )
        elif images:
            try:
                bot.send_photo(
                    chat_id,
                    images[photo_index],
                    caption=msg,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error("Could not display product photo: %s", e)
                bot.send_message(
                    chat_id,
                    msg,
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
        else:
            bot.send_message(
                chat_id,
                msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith('product_image_')
    )
    def handle_product_image_navigation(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        try:
            _, _, product_id, photo_index, view = call.data.split('_', 4)
            product_id = int(product_id)
            photo_index = int(photo_index)
        except (TypeError, ValueError):
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        product = db.get_product(product_id)
        images = get_images(product or {})
        if not product or not 0 <= photo_index < len(images):
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        if view == 'detail':
            show_product_detail_image(
                call.message.chat.id,
                product,
                lang,
                db,
                bot,
                message_id=call.message.message_id,
                photo_index=photo_index,
            )
        elif view == 'browse':
            products = db.get_products(
                category=product.get('category'),
                limit=20,
                offset=0,
            )
            product_index = next(
                (
                    index for index, item in enumerate(products)
                    if item.get('id') == product_id
                ),
                0,
            )
            show_product_card(
                call.message.chat.id,
                product,
                product_index,
                max(len(products), 1),
                product.get('category', ''),
                lang,
                bot,
                message_id=call.message.message_id,
                is_photo_message=True,
                photo_index=photo_index,
            )
        else:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        bot.answer_callback_query(call.id)
    
    def show_quantity_selector(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        """የቁጥር ምርጫ ማሳየት"""
        max_qty = min(5, product['stock_quantity'])
        
        markup = InlineKeyboardMarkup(row_width=3)
        
        buttons = []
        for i in range(1, max_qty + 1):
            buttons.append(
                InlineKeyboardButton(
                    str(i),
                    callback_data=f"qty_{product['id']}_{i}"
                )
            )
        
        markup.add(*buttons)
        
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ ምርት",
                callback_data=f"product_view_{product['id']}"
            )
        )
        
        msg = f"🛒 *{product['name_am'] if lang == 'am' else product['name_en']}*\n\n"
        msg += f"💰 ዋጋ: {format_currency(product['price'])}\n"
        msg += f"📦 ክምችት: {product['stock_quantity']}\n\n"
        msg += f"📌 ብዛት ይምረጡ:"
        
        bot.send_message(
            chat_id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def show_reviews(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        """የምርት ግምገማዎችን ማሳየት"""
        reviews = db.get_product_reviews(product['id'], limit=10)
        
        msg = f"⭐ *ግምገማዎች ለ {product['name_am'] if lang == 'am' else product['name_en']}*\n\n"
        
        if not reviews:
            msg += get_text(lang, 'no_reviews_yet')
        else:
            for review in reviews[:5]:
                stars = "⭐" * review['rating']
                name = review.get('first_name', 'Anonymous')
                comment = review.get('comment', '')
                
                msg += f"{stars}\n"
                msg += f"👤 {name}\n"
                if comment:
                    msg += f"💬 {comment}\n"
                msg += f"📅 {review['created_at'][:10]}\n\n"
        
        # ግምገማ ለመስጠት ኪቦርድ
        markup = get_rating_keyboard(product['id'], lang)
        
        bot.send_message(
            chat_id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def add_to_cart(user_id: int, product_id: int, quantity: int, db: Database):
        """ምርት ወደ ጋሪ መጨመር"""
        product = db.get_product(product_id)
        
        if not product:
            return False
        
        # የአሁኑን ጋሪ ማግኘት
        cart = db.get_cart(user_id)
        items = cart['items'] if cart and cart.get('items') else []
        
        existing_item = next(
            (item for item in items if item['product_id'] == product_id),
            None,
        )
        current_quantity = int(existing_item.get('quantity', 0)) if existing_item else 0
        if quantity <= 0 or current_quantity + quantity > int(product.get('stock_quantity', 0)):
            return False

        if existing_item:
            existing_item['quantity'] = current_quantity + quantity
        else:
            items.append({
                'product_id': product_id,
                'name': product['name_am'],
                'price': product['price'],
                'quantity': quantity,
                'image_id': product['image_id']
            })
        
        # ጋሪ ማዘመን
        return db.update_cart(user_id, items)

    globals()['add_to_cart'] = add_to_cart
    
    # ==================== የምርት ፍለጋ ====================
    
    @bot.message_handler(commands=['search'])
    def search_command(message: Message):
        """የ /search ትዕዛዝ - ምርቶችን መፈለግ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        # የፍለጋ ጥያቄን ማግኘት
        query = message.text.replace('/search', '').strip()
        
        if not query:
            bot.send_message(
                message.chat.id,
                "🔍 " + get_text(lang, 'search_prompt') + "\n"
                + get_text(lang, 'search_prompt_example')
            )
            return
        
        # ምርቶችን መፈለግ
        products = db.search_products(query, limit=20)
        
        if not products:
            bot.send_message(
                message.chat.id,
                "🔍 " + get_text(lang, 'search_no_results').format(query)
            )
            return
        
        markup = InlineKeyboardMarkup(row_width=1)
        for product in products[:10]:
            name = product['name_am'] if lang == 'am' else product['name_en']
            markup.add(InlineKeyboardButton(
                f"{name} · {format_currency(product['price'])}",
                callback_data=f"product_view_{product['id']}",
            ))
        bot.send_message(
            message.chat.id,
            "🔍 " + get_text(lang, 'search_results'),
            reply_markup=markup,
        )
    
    # ==================== የምርት ዝርዝር በትዕዛዝ ====================
    
    def product_command(message: Message):
        """Open an exact product card for `/product 1` or `/product1`."""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        match = re.fullmatch(r'/product(?:@\w+)?\s*(\d+)', (message.text or '').strip())
        if not match:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_product_id')
            )
            return
        product_id = int(match.group(1))
        
        product = db.get_product(product_id)
        
        if not product:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'product_not_found')
            )
            return
        
        show_product_card(
            message.chat.id,
            product,
            0,
            1,
            product.get('category') or 'All',
            lang,
            bot,
        )

    bot.message_handler(commands=['product'])(product_command)
    bot.message_handler(regexp=r'^/product\d+(?:@\w+)?$')(product_command)
    
    # ==================== ምርቶች በምድብ ትዕዛዝ ====================
    
    @bot.message_handler(commands=['category'])
    def category_command(message: Message):
        """የ /category ትዕዛዝ - ምርቶችን በምድብ ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        category = message.text.replace('/category', '').strip()
        
        if not category:
            bot.send_message(
                message.chat.id,
                "📂 " + get_text(lang, 'category_name_prompt')
            )
            return
        
        show_category_products(message, category, db, bot)