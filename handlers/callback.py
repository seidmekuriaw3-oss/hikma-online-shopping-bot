# -*- coding: utf-8 -*-
"""Handlers for customer callbacks that do not belong to a feature module."""

from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency


def show_wishlist(chat_id: int, user_id: int, db: Database, bot: TeleBot):
    lang = get_user_lang(db, user_id)
    products = db.execute(
        "SELECT p.* FROM wishlists w JOIN products p ON w.product_id = p.id "
        "WHERE w.user_id = %s ORDER BY w.created_at DESC",
        (user_id,),
    ).fetchall()
    markup = InlineKeyboardMarkup(row_width=1)
    if not products:
        markup.add(InlineKeyboardButton(
            "🛍️ ምርቶችን ያስሱ" if lang == 'am' else "🛍️ Browse Products",
            callback_data="browse_categories",
        ))
        text = "❤️ ተወዳጅ ምርቶች የሉም" if lang == 'am' else "❤️ Your wishlist is empty"
    else:
        text = "❤️ ተወዳጅ ምርቶች" if lang == 'am' else "❤️ Your Wishlist"
        for product in products[:20]:
            name = product.get('name_am') if lang == 'am' else product.get('name_en')
            markup.add(InlineKeyboardButton(
                f"{name or get_text(lang, 'product')} · {format_currency(product['price'])}",
                callback_data=f"product_view_{product['id']}",
            ))
    markup.add(InlineKeyboardButton(
        "🔙 ዋና ሜኑ" if lang == 'am' else "🔙 Main Menu",
        callback_data="main_menu",
    ))
    return bot.send_message(chat_id, text, reply_markup=markup)


def register(bot: TeleBot, db: Database):
    @bot.callback_query_handler(func=lambda call: call.data == 'show_discounts')
    def handle_show_discounts(call: CallbackQuery):
        lang = get_user_lang(db, call.from_user.id)
        discounts = db.get_all_discounts(active_only=True)
        if not discounts:
            bot.answer_callback_query(
                call.id,
                get_text(lang, 'no_active_discounts'),
            )
            return

        title = "🏷️ " + get_text(lang, 'active_discounts')
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
            response = "❤️ " + get_text(lang, 'removed_from_wishlist')
        else:
            db.execute(
                "INSERT INTO wishlists (user_id, product_id) VALUES (%s, %s)",
                (user_id, product_id),
            )
            response = "❤️ " + get_text(lang, 'added_to_wishlist')
        db.log_activity(user_id, 'wishlist', f'Product {product_id}')
        bot.answer_callback_query(call.id, response)

    @bot.callback_query_handler(func=lambda call: call.data == 'show_wishlist')
    def handle_show_wishlist(call: CallbackQuery):
        user_id = call.from_user.id
        show_wishlist(call.message.chat.id, user_id, db, bot)
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data in ('subscribe', 'unsubscribe'))
    def handle_subscription(call: CallbackQuery):
        subscribe = call.data == 'subscribe'
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        db.update_user(user_id, is_subscribed=int(subscribe))
        bot.answer_callback_query(
            call.id,
            ("✅ " + get_text(lang, 'subscribed'))
            if subscribe
            else ("🔕 " + get_text(lang, 'unsubscribed')),
        )

    @bot.callback_query_handler(func=lambda call: call.data == 'ignore')
    def handle_legacy_noop(call: CallbackQuery):
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_unknown_callback(call: CallbackQuery):
        bot.answer_callback_query(
            call.id,
            "❌ " + get_text(
                get_user_lang(db, call.from_user.id),
                'button_expired',
            ),
        )
