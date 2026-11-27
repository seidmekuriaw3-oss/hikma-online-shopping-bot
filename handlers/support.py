# -*- coding: utf-8 -*-
"""Help Center, FAQs, and in-bot customer support tickets."""

import logging
import re

from telebot import TeleBot
from telebot.apihelper import ApiException
from telebot.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from config import config
from database import Database
from utils.helpers import get_text, get_user_lang

logger = logging.getLogger(__name__)

awaiting_support_message = set()

_FAQ_KEYS = {
    'faq:order': 'faq_order_answer',
    'faq:payment': 'faq_payment_answer',
    'faq:delivery': 'faq_delivery_answer',
}
_MAIN_MENU_KEYWORDS = {'ወደ መጀመሪያ', 'ዋና ማውጫ', 'main menu'}
_CANCEL_KEYWORDS = {'ሰርዝ', 'cancel'}
_SUPPORT_USER_ID = re.compile(r'^User ID:\s*(\d+)\s*$', re.MULTILINE)


def clear_support_state(user_id: int) -> None:
    awaiting_support_message.discard(user_id)


def _normalize_keyword(text: str) -> str:
    return ''.join(character for character in text.casefold() if character.isalnum())


def _matches_keyword(text: str, keywords: set) -> bool:
    normalized = _normalize_keyword(text or '')
    return normalized in {_normalize_keyword(keyword) for keyword in keywords}


def _help_text(lang: str) -> str:
    contact_lines = []
    admin_username = config.bot.ADMIN_USERNAME.strip().lstrip('@')
    if admin_username:
        contact_lines.append(
            get_text(lang, 'help_admin_contact').format(
                admin_username=admin_username
            )
        )
    if config.bot.SUPPORT_PHONE:
        contact_lines.append(
            get_text(lang, 'help_support_phone').format(
                support_phone=config.bot.SUPPORT_PHONE
            )
        )
    return get_text(lang, 'help_text').format(
        support_contacts='\n'.join(contact_lines)
    ).rstrip()


def get_help_center_keyboard(lang: str) -> InlineKeyboardMarkup:
    markup = InlineKeyboardMarkup(row_width=2)
    markup.row(InlineKeyboardButton(
        get_text(lang, 'support_message_button'),
        callback_data='support:ask',
    ))
    markup.row(
        InlineKeyboardButton(
            get_text(lang, 'faq_order_button'),
            callback_data='faq:order',
        ),
        InlineKeyboardButton(
            get_text(lang, 'faq_payment_button'),
            callback_data='faq:payment',
        ),
    )
    delivery_button = InlineKeyboardButton(
        get_text(lang, 'faq_delivery_button'),
        callback_data='faq:delivery',
    )
    admin_username = config.bot.ADMIN_USERNAME.strip().lstrip('@')
    if admin_username:
        markup.row(
            delivery_button,
            InlineKeyboardButton(
                get_text(lang, 'direct_chat_button'),
                url=f'https://t.me/{admin_username}',
            ),
        )
    else:
        markup.row(delivery_button)
    return markup


def show_help_center(chat_id: int, user_id: int, db: Database, bot: TeleBot):
    lang = get_user_lang(db, user_id)
    return bot.send_message(
        chat_id,
        _help_text(lang),
        reply_markup=get_help_center_keyboard(lang),
    )


def _is_support_admin_reply(message: Message) -> bool:
    sender = getattr(message, 'from_user', None)
    if not sender or sender.id not in config.bot.ADMIN_IDS:
        return False
    replied_to = getattr(message, 'reply_to_message', None)
    if not replied_to or not getattr(
        getattr(replied_to, 'from_user', None),
        'is_bot',
        False,
    ):
        return False
    ticket_text = getattr(replied_to, 'text', None) or getattr(
        replied_to, 'caption', ''
    )
    return bool(_SUPPORT_USER_ID.search(ticket_text or ''))


def _ticket_content(message: Message) -> str:
    if message.content_type == 'photo':
        caption = (getattr(message, 'caption', None) or '').strip()
        return (
            f"Photo attachment\n{caption}"
            if caption
            else 'Photo attachment (no caption)'
        )
    return (message.text or '').strip()


def _support_ticket_text(message: Message, content: str) -> str:
    customer_name = ' '.join(
        part
        for part in (
            getattr(message.from_user, 'first_name', None),
            getattr(message.from_user, 'last_name', None),
        )
        if part
    )
    customer_name = ' '.join(customer_name.split()) or 'Unknown'
    username = getattr(message.from_user, 'username', None)
    username_line = f"\n@{username}" if username else ''
    return (
        f"{get_text('en', 'support_ticket_header')}\n"
        f"User ID: {message.from_user.id}\n\n"
        f"Customer Name: {customer_name}{username_line}\n\n"
        f"{get_text('en', 'support_ticket_message_label')}\n{content}"
    )


def _submit_ticket(message: Message, db: Database, bot: TeleBot) -> bool:
    user_id = message.from_user.id
    lang = get_user_lang(db, user_id)
    content = _ticket_content(message)
    ticket = _support_ticket_text(message, content)
    delivered = 0

    for admin_id in config.bot.ADMIN_IDS:
        try:
            bot.send_message(admin_id, ticket)
        except ApiException:
            logger.exception(
                "Could not deliver support ticket from user %s to admin %s",
                user_id,
                admin_id,
            )
            continue
        delivered += 1

        if message.content_type == 'photo':
            photo = message.photo[-1].file_id
            try:
                bot.send_photo(admin_id, photo)
            except ApiException:
                logger.exception(
                    "Could not deliver support photo from user %s to admin %s",
                    user_id,
                    admin_id,
                )

    if not delivered:
        bot.send_message(
            message.chat.id,
            get_text(lang, 'support_delivery_failed'),
            reply_markup=_support_cancel_keyboard(lang),
        )
        return False

    clear_support_state(user_id)
    db.log_activity(user_id, 'support_ticket', 'Support ticket submitted')
    bot.send_message(
        message.chat.id,
        get_text(lang, 'support_ticket_sent'),
        reply_markup=ReplyKeyboardRemove(),
    )
    return True


def _support_cancel_keyboard(lang: str) -> ReplyKeyboardMarkup:
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(KeyboardButton(get_text(lang, 'support_cancel_button')))
    return markup


def register(bot: TeleBot, db: Database):
    @bot.message_handler(commands=['cancel'])
    def cancel_support_command(message: Message):
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        was_awaiting = user_id in awaiting_support_message
        clear_support_state(user_id)
        response_key = (
            'support_cancelled'
            if was_awaiting
            else 'support_not_awaiting'
        )
        bot.send_message(
            message.chat.id,
            get_text(lang, response_key),
            reply_markup=ReplyKeyboardRemove(),
        )

    @bot.message_handler(
        func=lambda message: (
            getattr(getattr(message, 'from_user', None), 'id', None)
            in awaiting_support_message
            and _matches_keyword(
                message.text or '',
                _CANCEL_KEYWORDS,
            )
        ),
        content_types=['text'],
    )
    def cancel_support_text(message: Message):
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        clear_support_state(user_id)
        bot.send_message(
            message.chat.id,
            get_text(lang, 'support_cancelled'),
            reply_markup=ReplyKeyboardRemove(),
        )

    @bot.message_handler(
        func=lambda message: _is_support_admin_reply(message),
        content_types=['text'],
    )
    def relay_admin_reply(message: Message):
        replied_to = message.reply_to_message
        ticket_text = getattr(replied_to, 'text', None) or getattr(
            replied_to, 'caption', ''
        )
        match = _SUPPORT_USER_ID.search(ticket_text or '')
        if not match:
            return
        user_id = int(match.group(1))
        admin_text = (message.text or '').strip()
        lang = get_user_lang(db, user_id)
        bot.send_message(
            user_id,
            f"{get_text(lang, 'support_reply_header')}\n\n{admin_text}",
        )
        bot.send_message(
            message.chat.id,
            get_text(get_user_lang(db, message.from_user.id), 'support_admin_reply_sent'),
        )

    @bot.message_handler(
        func=lambda message: (
            getattr(getattr(message, 'from_user', None), 'id', None)
            in awaiting_support_message
            and not (message.text or '').lstrip().startswith('/')
            and not _matches_keyword(
                message.text or '',
                _CANCEL_KEYWORDS | _MAIN_MENU_KEYWORDS,
            )
        ),
        content_types=['text'],
    )
    def submit_text_ticket(message: Message):
        if not (message.text or '').strip():
            lang = get_user_lang(db, message.from_user.id)
            bot.send_message(
                message.chat.id,
                get_text(lang, 'support_prompt'),
                reply_markup=_support_cancel_keyboard(lang),
            )
            return
        _submit_ticket(message, db, bot)

    @bot.message_handler(
        func=lambda message: (
            getattr(getattr(message, 'from_user', None), 'id', None)
            in awaiting_support_message
        ),
        content_types=['photo'],
    )
    def submit_photo_ticket(message: Message):
        _submit_ticket(message, db, bot)

    @bot.callback_query_handler(
        func=lambda call: call.data in (
            'support:ask',
            'support:help_home',
            *_FAQ_KEYS.keys(),
        )
    )
    def handle_support_callbacks(call: CallbackQuery):
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        if call.data == 'support:ask':
            awaiting_support_message.add(user_id)
            bot.answer_callback_query(call.id)
            bot.send_message(
                call.message.chat.id,
                get_text(lang, 'support_prompt'),
                reply_markup=_support_cancel_keyboard(lang),
            )
            return

        if call.data == 'support:help_home':
            text = _help_text(lang)
            markup = get_help_center_keyboard(lang)
        else:
            text = get_text(lang, _FAQ_KEYS[call.data])
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton(
                get_text(lang, 'faq_back_button'),
                callback_data='support:help_home',
            ))
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup,
        )
        bot.answer_callback_query(call.id)
