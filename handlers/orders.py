# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false, reportArgumentType=false, reportOptionalSubscript=false, reportAttributeAccessIssue=false

"""
Hikma Online Shopping Bot - የትዕዛዝ እጅ አያያዝ
ይህ ፋይል ሁሉንም የትዕዛዝ እጅ አያያዞችን ይይዛል
"""

import logging
import json
import random
import string
import re
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, List

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from telebot.types import ReplyKeyboardRemove

from database import Database
from utils.helpers import (
    get_text, get_user_lang, format_currency, format_payment_method, generate_order_number,
)
from keyboards.inline import (
    get_order_keyboard, get_payment_keyboard, get_admin_order_actions_keyboard,
)
from keyboards.reply import get_address_menu
from services.notifications import notify_admins, send_order_confirmation

logger = logging.getLogger(__name__)

# ለትዕዛዝ ጊዜያዊ መረጃ
order_states = {}

show_cart = None
process_discount_code = None
handle_checkout = None
handle_payment = None
show_user_orders = None

show_cart = None
process_discount_code = None
handle_checkout = None
handle_payment = None
show_user_orders = None


def _cart_items(cart):
    items = cart.get('items') if cart else None
    return json.loads(items) if isinstance(items, str) else (items or [])


def register(bot: TeleBot, db: Database):
    """የትዕዛዝ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ጋሪ ማሳየት ====================
    
    @bot.message_handler(func=lambda m: m.text in ['🛒 ጋሪ', '🛒 Cart', 'ጋሪ 🛒', 'Cart 🛒'])
    def show_cart_command(message: Message):
        """የጋሪ ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        show_cart(message, db, bot)
    
    def show_cart(
        message: Message,
        db: Database,
        bot: TeleBot,
        message_id=None,
        user_id: Optional[int] = None,
    ):
        """ጋሪ ማሳየት"""
        user_id = user_id if user_id is not None else message.from_user.id
        lang = get_user_lang(db, user_id)
        
        cart = db.get_cart(user_id)
        
        items = _cart_items(cart)
        markup = InlineKeyboardMarkup(row_width=3)
        if not items:
            msg = (
                "🛒 ጋሪዎ ባዶ ነው። ምርት ለመመልከት ምድብ ይምረጡ."
                if lang == 'am'
                else "🛒 Your cart is empty. Choose a category to start browsing."
            )
            markup.row(
                InlineKeyboardButton("👕 የወንድ ልብሶች" if lang == 'am' else "👕 Men's Clothing", callback_data="category_Men"),
                InlineKeyboardButton("👗 የሴት ልብሶች" if lang == 'am' else "👗 Women's Clothing", callback_data="category_Women"),
            )
        else:
            subtotal = Decimal('0')
            lines = []
            for item in items:
                quantity = int(item.get('quantity', 0))
                price = Decimal(str(item.get('price', 0)))
                line_total = price * quantity
                subtotal += line_total
                product = db.get_product(item.get('product_id'))
                name = (
                    (product.get('name_am') if lang == 'am' else product.get('name_en'))
                    if product else item.get('name')
                ) or item.get('name') or ("ምርት" if lang == 'am' else "Product")
                lines.append(f"• {name} × {quantity} · {format_currency(line_total)}")
                markup.row(
                    InlineKeyboardButton("➖", callback_data=f"cart_dec_{item['product_id']}"),
                    InlineKeyboardButton(str(quantity), callback_data="browse_noop"),
                    InlineKeyboardButton("➕", callback_data=f"cart_inc_{item['product_id']}"),
                )
                markup.row(InlineKeyboardButton(
                    f"🗑️ {name} " + ("አስወግድ" if lang == 'am' else "Remove"),
                    callback_data=f"cart_remove_{item['product_id']}",
                ))

            final_amount = cart.get('final_amount')
            total = Decimal(str(subtotal if final_amount is None else final_amount))
            discount = Decimal(str(cart.get('discount_amount') or 0))
            title = "🛒 ጋሪዎ" if lang == 'am' else "🛒 Your Cart"
            msg = f"{title}\n\n" + '\n'.join(lines)
            msg += f"\n{'ጠቅላላ' if lang == 'am' else 'Subtotal'}: {format_currency(subtotal)}\n"
            if discount:
                msg += f"{'ቅናሽ' if lang == 'am' else 'Discount'}: −{format_currency(discount)}\n"
            msg += f"{'የሚከፈለው' if lang == 'am' else 'Total'}: {format_currency(total)}"
            markup.row(
                InlineKeyboardButton("🧹 ጋሪ አጽዳ" if lang == 'am' else "🧹 Clear Cart", callback_data="clear_cart"),
                InlineKeyboardButton("✅ አሁን ይዘዙ" if lang == 'am' else "✅ Checkout", callback_data="checkout"),
            )
            markup.row(
                InlineKeyboardButton("🏷️ ቅናሽ" if lang == 'am' else "🏷️ Discount", callback_data="apply_discount"),
                InlineKeyboardButton("🔙 ዋና ሜኑ" if lang == 'am' else "🔙 Main Menu", callback_data="main_menu"),
            )

        if message_id is not None:
            try:
                return bot.edit_message_text(
                    msg, message.chat.id, message_id, reply_markup=markup
                )
            except Exception:
                logger.exception("Could not update the cart message; sending a new summary")
        return bot.send_message(message.chat.id, msg, reply_markup=markup)

    globals()['show_cart'] = show_cart

    @bot.callback_query_handler(func=lambda call: call.data == 'view_cart')
    def handle_view_cart(call: CallbackQuery):
        show_cart(
            call.message, db, bot,
            message_id=call.message.message_id,
            user_id=call.from_user.id,
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith((
        'cart_inc_', 'cart_dec_', 'cart_remove_'
    )))
    def handle_cart_item_action(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        try:
            action, product_id_text = call.data.rsplit('_', 1)
            product_id = int(product_id_text)
        except ValueError:
            bot.answer_callback_query(call.id, get_text(lang, 'error'))
            return

        cart = db.get_cart(user_id)
        items = _cart_items(cart)
        item = next((entry for entry in items if entry.get('product_id') == product_id), None)
        if not item:
            bot.answer_callback_query(call.id, "Cart item no longer exists")
            show_cart(
                call.message, db, bot,
                message_id=call.message.message_id,
                user_id=user_id,
            )
            return

        quantity = int(item.get('quantity', 0))
        if action == 'cart_inc':
            product = db.get_product(product_id)
            if not product or quantity >= int(product.get('stock_quantity', 0)):
                bot.answer_callback_query(
                    call.id,
                    "Кምችት የለም" if lang == 'am' else "No more stock available",
                    show_alert=True,
                )
                return
            item['quantity'] = quantity + 1
        elif action == 'cart_dec':
            item['quantity'] = quantity - 1
            if item['quantity'] <= 0:
                items.remove(item)
        else:
            items.remove(item)

        if items:
            db.update_cart(user_id, items, cart.get('discount_code'))
        else:
            db.clear_cart(user_id)
        bot.answer_callback_query(call.id)
        show_cart(
            call.message, db, bot,
            message_id=call.message.message_id,
            user_id=user_id,
        )
    
    # ==================== ጋሪ ማጽዳት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'clear_cart')
    def handle_clear_cart(call: CallbackQuery):
        """ጋሪ ማጽዳት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        db.clear_cart(user_id)
        bot.answer_callback_query(call.id, "✅ ጋሪዎ ተጽድቷል!")
        
        show_cart(
            call.message, db, bot,
            message_id=call.message.message_id,
            user_id=user_id,
        )
    
    # ==================== ቅናሽ መተግበር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'apply_discount')
    def handle_apply_discount(call: CallbackQuery):
        """ቅናሽ መተግበር"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        msg = bot.send_message(
            call.message.chat.id,
            "🏷️ የቅናሽ ኮዱን ያስገቡ:"
        )
        bot.register_next_step_handler(msg, process_discount_code, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_discount_code(message: Message, db: Database, bot: TeleBot):
        """የቅናሽ ኮድ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        code = message.text.upper().strip()
        
        # ቅናሹን ማረጋገጥ
        discount = db.get_discount_by_code(code)
        
        if not discount:
            bot.send_message(
                message.chat.id,
                "❌ የቅናሽ ኮዱ ልክ አይደለም ወይም ጊዜው አልፏል!"
            )
            return
        
        # ተጠቃሚው ቅናሹን መጠቀም እንደሚችል ማረጋገጥ
        if discount['user_limit'] > 0:
            # ተጠቃሚው ስንት ጊዜ ተጠቅሟል ማረጋገጥ
            usage_count = db.execute(
                "SELECT COUNT(*) FROM discount_usage WHERE discount_id = %s AND user_id = %s",
                (discount['id'], user_id)
            ).fetchone()[0]
            
            if usage_count >= discount['user_limit']:
                bot.send_message(
                    message.chat.id,
                    "❌ ይህን ቅናሽ ከፍተኛውን ጊዜ ተጠቅመዋል!"
                )
                return
        
        # ቅናሽ መተግበር
        cart = db.get_cart(user_id)
        
        if not cart or not cart.get('items'):
            bot.send_message(
                message.chat.id,
                "❌ ጋሪዎ ባዶ ነው!"
            )
            return
        
        items = json.loads(cart['items']) if isinstance(cart['items'], str) else cart['items']
        total = sum(item['price'] * item['quantity'] for item in items)
        
        # ዝቅተኛ የትዕዛዝ መጠን ማረጋገጥ
        if discount['min_order_amount'] > 0 and total < discount['min_order_amount']:
            bot.send_message(
                message.chat.id,
                f"❌ ይህን ቅናሽ ለመጠቀም ቢያንስ {format_currency(discount['min_order_amount'])} መግዛት አለብዎት!"
            )
            return
        
        # ቅናሽ ማስላት
        discount_amount = total * (discount['discount_percent'] / 100)
        
        # ከፍተኛ ቅናሽ ማረጋገጥ
        if discount['max_discount_amount'] and discount_amount > discount['max_discount_amount']:
            discount_amount = discount['max_discount_amount']
        
        final_amount = total - discount_amount
        
        # ጋሪ ማዘመን
        db.update_cart(user_id, items, code)
        
        bot.send_message(
            message.chat.id,
            f"✅ ቅናሽ ተተግብሯል!\n\n"
            f"🏷️ ኮድ: {code}\n"
            f"📊 ቅናሽ: {discount['discount_percent']}%\n"
            f"💰 ቅናሽ መጠን: {format_currency(discount_amount)}\n"
            f"💰 የተጣራ: {format_currency(final_amount)}"
        )
        
        # ጋሪ ማሳየት
        show_cart(message, db, bot)

    globals()['process_discount_code'] = process_discount_code
    
    # ==================== ግዢ ማረጋገጥ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'checkout')
    def handle_checkout(call: CallbackQuery):
        """Begin the phone and delivery confirmation flow."""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        cart = db.get_cart(user_id)
        items = _cart_items(cart)
        if not items:
            bot.answer_callback_query(
                call.id,
                "❌ ጋሪዎ ባዶ ነው!" if lang == 'am' else "❌ Your cart is empty",
            )
            return
        subtotal = sum(
            (Decimal(str(item.get('price', 0))) * int(item.get('quantity', 0)) for item in items),
            Decimal('0'),
        )
        final_amount = cart.get('final_amount')
        total = Decimal(str(subtotal if final_amount is None else final_amount))
        order_states[user_id] = {
            'step': 'phone',
            'total': total,
            'subtotal': subtotal,
            'discount_amount': Decimal(str(cart.get('discount_amount') or 0)),
            'items': items,
            'discount_code': cart.get('discount_code'),
        }
        user = db.get_user(user_id) or {}
        saved_phone = user.get('phone')
        if saved_phone:
            order_states[user_id]['phone'] = saved_phone
            order_states[user_id]['step'] = 'phone_confirm'
            _send_phone_confirmation(call.message.chat.id, saved_phone, lang)
        else:
            _prompt_checkout_phone(call.message.chat.id, lang)
        bot.answer_callback_query(call.id)

    def _send_phone_confirmation(chat_id, phone, lang):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(
                "✅ አዎ፣ ይህን ተጠቀም" if lang == 'am' else "✅ Use this number",
                callback_data="checkout_phone_confirm",
            ),
            InlineKeyboardButton(
                "✏️ ቀይር" if lang == 'am' else "✏️ Change",
                callback_data="checkout_phone_edit",
            ),
        )
        markup.add(InlineKeyboardButton(
            "❌ ሰርዝ" if lang == 'am' else "❌ Cancel",
            callback_data="checkout_cancel",
        ))
        bot.send_message(
            chat_id,
            f"📱 {'የስልክ ቁጥርዎን ያረጋግጡ' if lang == 'am' else 'Confirm your phone number'}\n{phone}",
            reply_markup=markup,
        )

    def _prompt_checkout_phone(chat_id, lang):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "❌ ሰርዝ" if lang == 'am' else "❌ Cancel",
            callback_data="checkout_cancel",
        ))
        prompt = bot.send_message(
            chat_id,
            "📱 የስልክ ቁጥርዎን ያስገቡ:" if lang == 'am' else "📱 Enter your phone number:",
            reply_markup=markup,
        )
        bot.register_next_step_handler(prompt, process_checkout_phone, db, bot)

    def process_checkout_phone(message: Message, db: Database, bot: TeleBot):
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        state = order_states.get(user_id)
        phone = (message.text or '').strip()
        digits = re.sub(r'\D', '', phone)
        if not state or state.get('step') != 'phone' or not 9 <= len(digits) <= 15:
            bot.send_message(
                message.chat.id,
                "❌ ትክክለኛ ስልክ ያስገቡ።" if lang == 'am' else "❌ Enter a valid phone number.",
            )
            _prompt_checkout_phone(message.chat.id, lang)
            return
        state['phone'] = phone
        state['step'] = 'phone_confirm'
        db.update_user(user_id, phone=phone)
        _send_phone_confirmation(message.chat.id, phone, lang)

    @bot.callback_query_handler(func=lambda call: call.data == 'checkout_phone_edit')
    def handle_checkout_phone_edit(call):
        state = order_states.get(call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, "Checkout expired. Please start again.")
            return
        state['step'] = 'phone'
        _prompt_checkout_phone(call.message.chat.id, get_user_lang(db, call.from_user.id))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'checkout_phone_confirm')
    def handle_checkout_phone_confirm(call):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        state = order_states.get(user_id)
        if not state or state.get('step') != 'phone_confirm':
            bot.answer_callback_query(call.id, "Checkout expired. Please start again.")
            return
        state['step'] = 'address'
        _prompt_checkout_address(call.message.chat.id, lang)
        bot.answer_callback_query(call.id)

    def _prompt_checkout_address(chat_id, lang):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "❌ ሰርዝ" if lang == 'am' else "❌ Cancel",
            callback_data="checkout_cancel",
        ))
        prompt = bot.send_message(
            chat_id,
            "📍 የማድረሻ አድራሻ ይጻፉ ወይም የአካባቢ መረጃ ይላኩ:" if lang == 'am'
            else "📍 Enter your delivery address or share your location:",
            reply_markup=markup,
        )
        bot.register_next_step_handler(prompt, process_checkout_address, db, bot)

    def process_checkout_address(message: Message, db: Database, bot: TeleBot):
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        state = order_states.get(user_id)
        if not state or state.get('step') != 'address':
            return
        text = (message.text or '').strip()
        cancel_values = {'❌ ሰርዝ', '❌ Cancel'}
        if message.content_type == 'location' and message.location:
            address = f"{message.location.latitude}, {message.location.longitude}"
        elif text and text not in cancel_values:
            address = text
        else:
            order_states.pop(user_id, None)
            bot.send_message(
                message.chat.id,
                "Checkout cancelled." if lang == 'en' else "የግዢ ሂደቱ ተሰርዟል።",
            )
            return
        state['address'] = address
        state['step'] = 'address_confirm'
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("✅ አረጋግጥ" if lang == 'am' else "✅ Confirm", callback_data="checkout_address_confirm"),
            InlineKeyboardButton("✏️ ቀይር" if lang == 'am' else "✏️ Change", callback_data="checkout_address_edit"),
        )
        markup.add(InlineKeyboardButton(
            "❌ ሰርዝ" if lang == 'am' else "❌ Cancel",
            callback_data="checkout_cancel",
        ))
        bot.send_message(
            message.chat.id,
            f"📍 {'አድራሻውን ያረጋግጡ' if lang == 'am' else 'Confirm delivery address'}\n{address}",
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'checkout_address_edit')
    def handle_checkout_address_edit(call):
        state = order_states.get(call.from_user.id)
        if not state:
            bot.answer_callback_query(call.id, "Checkout expired. Please start again.")
            return
        state['step'] = 'address'
        _prompt_checkout_address(call.message.chat.id, get_user_lang(db, call.from_user.id))
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'checkout_address_confirm')
    def handle_checkout_address_confirm(call):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        state = order_states.get(user_id)
        if not state or state.get('step') != 'address_confirm':
            bot.answer_callback_query(call.id, "Checkout expired. Please start again.")
            return
        state['step'] = 'payment'
        bot.send_message(
            call.message.chat.id,
            "💳 የክፍያ ዘዴ ይምረጡ:" if lang == 'am' else "💳 Choose a payment method:",
            reply_markup=get_payment_keyboard(lang),
        )
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data == 'checkout_cancel')
    def handle_checkout_cancel(call):
        order_states.pop(call.from_user.id, None)
        bot.answer_callback_query(call.id, "Checkout cancelled")
        bot.send_message(
            call.message.chat.id,
            "የግዢ ሂደቱ ተሰርዟል።" if get_user_lang(db, call.from_user.id) == 'am' else "Checkout cancelled.",
        )
    
    # ==================== ክፍያ ማስኬድ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data in (
        'pay_chapa', 'pay_telebirr', 'pay_cash', 'pay_bank'
    ))
    def handle_payment(call: CallbackQuery):
        """የክፍያ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        payment_method = call.data.replace('pay_', '')
        state = order_states.get(user_id)
        
        if not state or state.get('step') != 'payment':
            bot.answer_callback_query(call.id, "❌ የግዢ ሂደት ተቋርጧል!")
            return
        
        # ትዕዛዝ መፍጠር
        order_number = generate_order_number()
        
        user = db.get_user(user_id) or {}
        order_data = {
            'order_number': order_number,
            'user_id': user_id,
            'total_amount': state['subtotal'],
            'subtotal_amount': state['subtotal'],
            'discount_amount': state['discount_amount'],
            'shipping_amount': 0,
            'tax_amount': 0,
            'final_amount': state['total'],
            'status': 'Pending',
            'payment_method': payment_method,
            'shipping_address': state['address'],
            'shipping_phone': state['phone'],
            'shipping_name': user.get('first_name'),
            'notes': f"ከቦት ትዕዛዝ - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        
        order_id = db.create_order(order_data)
        
        if not order_id:
            bot.send_message(
                call.message.chat.id,
                "❌ ትዕዛዙ መፍጠር አልተቻለም!"
            )
            return
        
        # የትዕዛዝ ዝርዝሮችን መጨመር
        for item in state['items']:
            db.add_order_item(
                order_id=order_id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
        
        # ቅናሽ ከተጠቀሙ
        if state.get('discount_code'):
            discount = db.get_discount_by_code(state['discount_code'])
            if discount:
                db.use_discount(discount['id'], user_id, order_id)
        
        # ጋሪ ማጽዳት
        db.clear_cart(user_id)
        
        # ማስታወቂያ
        order = db.get_order(order_id)
        items = db.get_order_items(order_id)
        
        # ለተጠቃሚ ማሳወቅ
        msg = f"✅ *ትዕዛዝዎ ተረጋግጧል!*\n\n"
        msg += f"🔢 *ትዕዛዝ ቁጥር:* {order_number}\n"
        msg += f"💰 *ጠቅላላ:* {format_currency(state['total'])}\n"
        msg += f"💳 *ክፍያ:* {format_payment_method(payment_method, lang)}\n\n"
        msg += f"📦 በቅርቡ እናገኝዎታለን! 🙏\n\n"
        msg += "📋 ትዕዛዝዎን ከታች ያለውን አዝራር በመጫን ይከታተሉ።" if lang == 'am' else "Use the button below to view your orders."
        order_keyboard = InlineKeyboardMarkup()
        order_keyboard.add(InlineKeyboardButton(
            "📋 ትዕዛዜን እይ" if lang == 'am' else "📋 View My Orders",
            callback_data="view_orders",
        ))
        
        bot.send_message(
            call.message.chat.id,
            msg,
            reply_markup=order_keyboard,
            parse_mode='Markdown'
        )
        
        # ለአስተዳዳሪ ማሳወቅ
        admin_msg = f"🆕 *አዲስ ትዕዛዝ!*\n\n"
        admin_msg += f"🔢 {order_number}\n"
        admin_msg += f"👤 ተጠቃሚ: {call.from_user.first_name} (@{call.from_user.username or 'Unknown'})\n"
        admin_msg += f"💰 {format_currency(state['total'])}\n"
        admin_msg += f"💳 {format_payment_method(payment_method, 'am')}\n"
        admin_msg += f"📍 {state['address'][:50]}...\n\n"
        admin_msg += f"📦 ምርቶች:\n"
        
        for item in items:
            product = db.get_product(item['product_id'])
            admin_msg += f"  • {product['name_am']} × {item['quantity']}\n"
        
        admin_msg += f"\n🔗 /order_{order_id}"
        
        notify_admins(bot, admin_msg)
        
        # ሁኔታን ማጽዳት
        order_states.pop(user_id, None)
        bot.answer_callback_query(call.id)

    globals()['handle_checkout'] = handle_checkout
    globals()['handle_payment'] = handle_payment
    
    # ==================== ትዕዛዞቼ ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📋 ትዕዛዞቼ', '📋 My Orders', 'ትዕዛዞቼ 📋', 'My Orders 📋'])
    def show_orders_command(message: Message):
        """የትዕዛዝ ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        show_user_orders(message, db, bot)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'view_orders')
    def handle_view_orders(call: CallbackQuery):
        show_user_orders(call.message, db, bot, user_id=call.from_user.id)
        bot.answer_callback_query(call.id)

    def show_user_orders(
        message: Message,
        db: Database,
        bot: TeleBot,
        user_id: Optional[int] = None,
    ):
        """የተጠቃሚ ትዕዛዞችን ማሳየት"""
        user_id = user_id if user_id is not None else message.from_user.id
        lang = get_user_lang(db, user_id)
        
        orders = db.get_user_orders(user_id, limit=10)
        
        if not orders:
            markup = InlineKeyboardMarkup(row_width=2)
            markup.row(
                InlineKeyboardButton("👕 የወንድ ልብሶች" if lang == 'am' else "👕 Men's Clothing", callback_data="category_Men"),
                InlineKeyboardButton("👗 የሴት ልብሶች" if lang == 'am' else "👗 Women's Clothing", callback_data="category_Women"),
            )
            return bot.send_message(
                message.chat.id,
                "📭 ገና ትዕዛዝ የለዎትም." if lang == 'am' else "📭 You haven't placed an order yet.",
                reply_markup=markup,
            )
        status_badges = {
            'Pending': ('⏳ በመጠባበቅ ላይ', '⏳ Pending'),
            'Processing': ('🔄 በሂደት ላይ', '🔄 Processing'),
            'Shipped': ('🚚 ተልኳል', '🚚 Shipped'),
            'Delivered': ('✅ ተረክቧል', '✅ Delivered'),
            'Cancelled': ('❌ ተሰርዟል', '❌ Cancelled'),
        }
        for order in orders[:10]:
            badge = status_badges.get(order['status'], ('📦 ' + order['status'], '📦 ' + order['status']))
            date = str(order.get('order_date') or '')[:10]
            count = order.get('item_count', 0)
            msg = (
                f"📋 {order['order_number']}\n"
                f"{badge[0] if lang == 'am' else badge[1]}\n"
                f"📅 {date} · {count} {'እቃ' if lang == 'am' else 'items'}\n"
                f"💰 {format_currency(order['final_amount'])}"
            )
            bot.send_message(
                message.chat.id,
                msg,
                reply_markup=get_order_keyboard(order['id'], order['status'], lang),
            )

    globals()['show_user_orders'] = show_user_orders
    
    # ==================== የትዕዛዝ ዝርዝር ====================
    
    @bot.callback_query_handler(func=lambda call: (
        call.data.startswith('order_') and call.data[6:].isdigit()
    ))
    def handle_order_detail(call: CallbackQuery):
        """የትዕዛዝ ዝርዝር ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        order_id = int(call.data[6:])
        order = db.get_order(order_id)
        
        if not order:
            bot.answer_callback_query(call.id, "❌ ትዕዛዙ አልተገኘም!")
            return
        
        # ተጠቃሚው የራሱ ትዕዛዝ መሆኑን ማረጋገጥ
        if order['user_id'] != user_id and user_id not in db.get_admin_ids():
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        
        items = db.get_order_items(order_id)
        
        msg = f"📋 *የትዕዛዝ ዝርዝር*\n\n"
        msg += f"🔢 *ቁጥር:* {order['order_number']}\n"
        msg += f"📅 *ቀን:* {order['order_date']}\n"
        msg += f"📦 *ሁኔታ:* {order['status']}\n"
        msg += f"💳 *ክፍያ:* {order['payment_method']} - {order['payment_status']}\n\n"
        
        msg += "*📦 ምርቶች:*\n"
        for item in items:
            product = db.get_product(item['product_id'])
            name = product['name_am'] if product else 'N/A'
            msg += f"  • {name} × {item['quantity']} = {format_currency(item['total_price'])}\n"
        
        msg += f"\n💰 *ጠቅላላ:* {format_currency(order['total_amount'])}\n"
        
        if order['discount_amount'] > 0:
            msg += f"🏷️ *ቅናሽ:* -{format_currency(order['discount_amount'])}\n"
        
        msg += f"💰 *የተጣራ:* {format_currency(order['final_amount'])}\n"
        
        if order['shipping_address']:
            msg += f"\n📍 *አድራሻ:* {order['shipping_address']}"
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(InlineKeyboardButton(
            "🔙 ወደ ትዕዛዞች" if lang == 'am' else "🔙 My Orders",
            callback_data="back_to_orders",
        ))
        from config import config
        if config.bot.ADMIN_USERNAME:
            markup.add(InlineKeyboardButton(
                "💬 አስተዳዳሪን ያግኙ" if lang == 'am' else "💬 Contact support",
                url=f"https://t.me/{config.bot.ADMIN_USERNAME}",
            ))
        
        bot.send_message(
            call.message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_orders')
    def handle_back_to_orders(call: CallbackQuery):
        """ወደ ትዕዛዞች መመለስ"""
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_user_orders(call.message, db, bot, user_id=call.from_user.id)
    
    # ==================== የአስተዳዳሪ ትዕዛዝ ማስተዳደር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_order_'))
    def handle_admin_order(call: CallbackQuery):
        """የአስተዳዳሪ ትዕዛዝ ማስተዳደር"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        if user_id not in db.get_admin_ids():
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        parts = call.data.split('_')
        if len(parts) < 4 or not parts[3].isdigit():
            bot.answer_callback_query(call.id, "Invalid order action", show_alert=True)
            return
        action = parts[2]
        order_id = int(parts[3])
        allowed_statuses = {
            'Processing': 'Processing',
            'Shipped': 'Shipped',
            'Delivered': 'Delivered',
            'Completed': 'Delivered',
            'Cancelled': 'Cancelled',
        }

        if action == 'status':
            new_status = parts[4] if len(parts) > 4 else None
            if new_status:
                status = allowed_statuses.get(new_status)
                if not status:
                    bot.answer_callback_query(call.id, "Invalid order status", show_alert=True)
                    return
                if not db.update_order_status(order_id, status):
                    bot.answer_callback_query(call.id, "Could not update order status", show_alert=True)
                    return

                order = db.get_order(order_id)
                if order:
                    order['status'] = status
                    order['items'] = db.get_order_items(order_id)
                    customer = db.get_user(order['user_id']) or {}
                    order['customer_name'] = (
                        order.get('shipping_name') or customer.get('first_name') or 'Customer'
                    )
                    order['customer_phone'] = (
                        order.get('shipping_phone') or customer.get('phone') or '—'
                    )
                    from handlers.admin import format_admin_order_card
                    text, keyboard = format_admin_order_card(order, lang)
                    try:
                        bot.edit_message_text(
                            text,
                            call.message.chat.id,
                            call.message.message_id,
                            reply_markup=keyboard,
                        )
                    except Exception:
                        logger.exception("Could not refresh admin order card after status update")
                        bot.send_message(call.message.chat.id, text, reply_markup=keyboard)

                    status_text = {
                        'Processing': ('🔄 በሂደት ላይ', '🔄 Processing'),
                        'Shipped': ('🚚 ተልኳል', '🚚 Shipped'),
                        'Delivered': ('✔️ ተጠናቋል', '✔️ Completed'),
                        'Cancelled': ('❌ ተሰርዟል', '❌ Cancelled'),
                    }[status][0 if get_user_lang(db, int(order['user_id'])) == 'am' else 1]
                    notification = (
                        f"📋 *የትዕዛዝ ሁኔታ ተዘምኗል!*\n\n"
                        f"🔢 {order['order_number']}\n📦 {status_text}\n\n"
                        "የትዕዛዝዎን ለማየት ከታች ያለውን ይጫኑ።"
                        if get_user_lang(db, int(order['user_id'])) == 'am'
                        else f"📋 *Your order status was updated.*\n\n"
                        f"🔢 {order['order_number']}\n📦 {status_text}\n\n"
                        "Use the button below to view your orders."
                    )
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(InlineKeyboardButton(
                        "📋 ትዕዛዞቼን እይ"
                        if get_user_lang(db, int(order['user_id'])) == 'am'
                        else "📋 View My Orders",
                        callback_data="view_orders",
                    ))
                    bot.send_message(order['user_id'], notification, reply_markup=keyboard, parse_mode='Markdown')
                bot.answer_callback_query(call.id, "✅ Status updated")
                return

            order = db.get_order(order_id)
            if not order:
                bot.answer_callback_query(call.id, "Order not found", show_alert=True)
                return
            order['items'] = db.get_order_items(order_id)
            customer = db.get_user(order['user_id']) or {}
            order['customer_name'] = order.get('shipping_name') or customer.get('first_name') or 'Customer'
            order['customer_phone'] = order.get('shipping_phone') or customer.get('phone') or '—'
            from handlers.admin import format_admin_order_card
            text, keyboard = format_admin_order_card(order, lang)
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
        elif action == 'view':
            order = db.get_order(order_id)
            if not order:
                bot.answer_callback_query(call.id, "❌ ትዕዛዙ አልተገኘም!")
                return
            order['items'] = db.get_order_items(order_id)
            customer = db.get_user(order['user_id']) or {}
            order['customer_name'] = order.get('shipping_name') or customer.get('first_name') or 'Customer'
            order['customer_phone'] = order.get('shipping_phone') or customer.get('phone') or '—'
            from handlers.admin import format_admin_order_card
            text, keyboard = format_admin_order_card(order, lang)
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=keyboard,
            )
        bot.answer_callback_query(call.id)