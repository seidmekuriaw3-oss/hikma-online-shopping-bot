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
from utils.helpers import get_text, get_user_lang, format_currency
from keyboards.inline import (
    get_product_keyboard, get_rating_keyboard, get_browse_product_keyboard,
)
from services.notifications import notify_admins

logger = logging.getLogger(__name__)

add_to_cart = None

# ለምርት ጊዜያዊ መረጃ
product_cache = {}


def _product_caption(product: Dict, index: int, total: int, lang: str) -> str:
    name = product.get('name_am') if lang == 'am' else product.get('name_en')
    name = name or product.get('name_am') or product.get('name_en') or 'Product'
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
):
    """Send a product card or update the existing carousel message."""
    caption = _product_caption(product, index, total, lang)
    keyboard = get_browse_product_keyboard(product['id'], category, index, total, lang)
    image_id = product.get('image_id')

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
        return bot.send_message(
            message.chat.id,
            get_text(lang, 'no_products_in_category'),
        )
    return show_product_card(
        message.chat.id, products[0], 0, len(products), category, lang, bot
    )


def search_products(message: Message, query: str, db: Database, bot: TeleBot):
    """Search products for calls originating from the general text handler."""
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    products = db.search_products(query, limit=20)

    if not products:
        bot.send_message(message.chat.id, f"🔍 ለ '{query}' ምንም ምርት አልተገኘም")
        return []

    markup = InlineKeyboardMarkup(row_width=1)
    for product in products[:10]:
        name = product.get('name_am') if lang == 'am' else product.get('name_en')
        markup.add(InlineKeyboardButton(
            f"{name or product.get('name_am')} · {format_currency(product['price'])}",
            callback_data=f"product_view_{product['id']}",
        ))
    bot.send_message(message.chat.id, f"🔍 Search results for “{query}”", reply_markup=markup)
    return products


def register(bot: TeleBot, db: Database):
    """የምርት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ምርቶችን በምድብ ማሳየት ====================
    
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
            get_text(lang, 'added_to_cart').format(product['name_am'], quantity)
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
            "💬 አስተያየትዎን ይጻፉ (ካልፈለጉ 'skip' ይተይቡ):"
        )
        bot.register_next_step_handler(msg, process_review_comment, product_id, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_review_comment(message: Message, product_id: int, db: Database, bot: TeleBot):
        """የግምገማ አስተያየት ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        comment = None if message.text.lower() == 'skip' else message.text
        
        # ግምገማ ማዘመን
        success = db.add_review({
            'user_id': user_id,
            'product_id': product_id,
            'comment': comment
        })
        
        if success:
            bot.send_message(
                message.chat.id,
                "✅ አስተያየትዎ ተመዝግቧል! እናመሰግናለን! 🙏"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ አስተያየት መመዝገብ አልተቻለም!"
            )
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_product(chat_id: int, product: Dict, index: int, total: int, 
                     category: str, lang: str, db: Database, bot: TeleBot):
        """ምርት ማሳየት"""
        return show_product_card(
            chat_id, product, index, total, category, lang, bot
        )
    
    def show_product_detail(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        """የምርት ዝርዝር ማሳየት"""
        # የምርት ደረጃ
        rating = product.get('rating_avg', 0)
        rating_count = product.get('rating_count', 0)
        stars = "⭐" * round(rating) if rating else "☆"
        
        # ስም
        name = product['name_am'] if lang == 'am' else product['name_en']
        description = product.get('description_am', '') if lang == 'am' else product.get('description_en', '')
        
        # ሁኔታ
        status = "✅ በክምችት ላይ" if product['stock_quantity'] > 0 else "❌ ተሽጦ አልቋል"
        
        # መልዕክት
        msg = f"🔹 *{name}*\n\n"
        
        if description:
            msg += f"📝 {description}\n\n"
        
        msg += f"💰 *ዋጋ:* {format_currency(product['price'])}\n"
        
        if product.get('compare_price'):
            msg += f"~~{format_currency(product['compare_price'])}~~\n"
        
        msg += f"📏 *መጠን:* {product['size']}\n"
        msg += f"📦 *ሁኔታ:* {status}\n"
        msg += f"📊 *ክምችት:* {product['stock_quantity']}\n"
        
        if rating:
            msg += f"⭐ {stars} ({rating_count} {get_text(lang, 'reviews')})\n"
        
        # ኪቦርድ
        markup = InlineKeyboardMarkup(row_width=2)
        
        if product['stock_quantity'] > 0:
            markup.add(
                InlineKeyboardButton(
                    "🛒 ለመግዛት",
                    callback_data=f"product_buy_{product['id']}"
                )
            )
        
        markup.add(
            InlineKeyboardButton(
                "⭐ ግምገማ",
                callback_data=f"product_review_{product['id']}"
            ),
            InlineKeyboardButton(
                "❤️ ወደ ተመረጡ",
                callback_data=f"product_wishlist_{product['id']}"
            )
        )
        
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ ምርቶች",
                callback_data=f"category_{product['category']}"
            )
        )
        
        try:
            bot.send_photo(
                chat_id,
                product['image_id'],
                caption=msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"ምርት ማሳየት አልተቻለም: {e}")
            bot.send_message(
                chat_id,
                msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
    
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
                "🔍 ምን መፈለግ ይፈልጋሉ? በ /search ቀጥሎ ይጻፉ\n"
                "ለምሳሌ: /search ቀሚስ"
            )
            return
        
        # ምርቶችን መፈለግ
        products = db.search_products(query, limit=20)
        
        if not products:
            bot.send_message(
                message.chat.id,
                f"🔍 ለ '{query}' ምንም ምርት አልተገኘም"
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
            f"🔍 {'የፍለጋ ውጤቶች' if lang == 'am' else 'Search results'}",
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
                "❌ እባክዎ ትክክለኛ የምርት ID ያስገቡ!\n"
                "ለምሳሌ: /product 123"
            )
            return
        product_id = int(match.group(1))
        
        product = db.get_product(product_id)
        
        if not product:
            bot.send_message(
                message.chat.id,
                "❌ ምርቱ አልተገኘም!"
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
                "📂 የምድብ ስም ያስገቡ!\n"
                "ለምሳሌ: /category Men\n\n"
                "📌 የሚገኙ ምድቦች:\n"
                "• Men\n"
                "• Women\n"
                "• Accessories"
            )
            return
        
        show_category_products(message, category, db, bot)