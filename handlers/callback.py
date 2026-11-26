# -*- coding: utf-8 -*-
"""Handlers for customer callbacks that do not belong to a feature module."""

from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency


def register(bot: TeleBot, db: Database):
    @bot.callback_query_handler(func=lambda call: call.data == 'show_discounts')
    def handle_show_discounts(call: CallbackQuery):
        lang = get_user_lang(db, call.from_user.id)
        discounts = db.get_all_discounts(active_only=True)
        if not discounts:
            bot.answer_callback_query(
                call.id,
                "በአሁኑ ጊዜ ቅናሽ የለም" if lang == 'am' else "No active discounts",
            )
            return

        title = "🏷️ ንቁ ቅናሾች" if lang == 'am' else "🏷️ Active Discounts"
        lines = [title, ""]
        for discount in discounts[:10]:
            lines.append(f"• {discount['code']} — {discount['discount_percent']}%")
            description = discount.get('description')
            if description:
                lines.append(str(description))
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(
            "🔙 ዋና ሜኑ" if lang == 'am' else "🔙 Main Menu",
            callback_data="main_menu",
        ))
        bot.send_message(call.message.chat.id, '\n'.join(lines), reply_markup=markup)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_wishlist_'))
    def handle_wishlist_toggle(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        try:
            product_id = int(call.data.rsplit('_', 1)[1])
        except ValueError:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        exists = db.execute(
            "SELECT 1 FROM wishlists WHERE user_id = %s AND product_id = %s",
            (user_id, product_id),
        ).fetchone()
        if exists:
            db.execute(
                "DELETE FROM wishlists WHERE user_id = %s AND product_id = %s",
                (user_id, product_id),
            )
            response = "❤️ ከተወዳጆች ተወግዷል" if lang == 'am' else "❤️ Removed from wishlist"
        else:
            db.execute(
                "INSERT INTO wishlists (user_id, product_id) VALUES (%s, %s)",
                (user_id, product_id),
            )
            response = "❤️ ወደ ተወዳጆች ተጨምሯል" if lang == 'am' else "❤️ Added to wishlist"
        db.log_activity(user_id, 'wishlist', f'Product {product_id}')
        bot.answer_callback_query(call.id, response)

    @bot.callback_query_handler(func=lambda call: call.data == 'show_wishlist')
    def handle_show_wishlist(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        products = db.execute(
            "SELECT p.* FROM wishlists w JOIN products p ON w.product_id = p.id "
            "WHERE w.user_id = %s ORDER BY w.created_at DESC",
            (user_id,),
        ).fetchall()
        markup = InlineKeyboardMarkup(row_width=1)
        if not products:
            markup.row(
                InlineKeyboardButton("👕 የወንድ ልብሶች" if lang == 'am' else "👕 Men's Clothing", callback_data="category_Men"),
                InlineKeyboardButton("👗 የሴት ልብሶች" if lang == 'am' else "👗 Women's Clothing", callback_data="category_Women"),
            )
            text = "❤️ ተወዳጅ ምርቶች የሉም" if lang == 'am' else "❤️ Your wishlist is empty"
        else:
            text = "❤️ ተወዳጅ ምርቶች" if lang == 'am' else "❤️ Your Wishlist"
            for product in products[:20]:
                name = product.get('name_am') if lang == 'am' else product.get('name_en')
                markup.add(InlineKeyboardButton(
                    f"{name or product.get('name_am')} · {format_currency(product['price'])}",
                    callback_data=f"product_view_{product['id']}",
                ))
        markup.add(InlineKeyboardButton(
            "🔙 ዋና ሜኑ" if lang == 'am' else "🔙 Main Menu",
            callback_data="main_menu",
        ))
        bot.send_message(call.message.chat.id, text, reply_markup=markup)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data in ('subscribe', 'unsubscribe'))
    def handle_subscription(call: CallbackQuery):
        subscribe = call.data == 'subscribe'
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        db.update_user(user_id, is_subscribed=int(subscribe))
        bot.answer_callback_query(
            call.id,
            ("✅ ተመዝግበዋል" if subscribe else "🔕 ምዝገባ ተቋርጧል")
            if lang == 'am'
            else ("✅ Subscribed" if subscribe else "🔕 Unsubscribed"),
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'ignore')
    def handle_legacy_noop(call: CallbackQuery):
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_unknown_callback(call: CallbackQuery):
        bot.answer_callback_query(
            call.id,
            "❌ ይህ አዝራር ጊዜው አልፏል። ሜኑውን እንደገና ይክፈቱ።"
            if get_user_lang(db, call.from_user.id) == 'am'
            else "❌ This button has expired. Please reopen the menu.",
        )
