from types import SimpleNamespace

from config import config
from handlers import admin, products, register_handlers, start
from keyboards.inline import get_product_keyboard, get_social_keyboard


class RecordingBot:
    def __init__(self):
        self.message_handlers = []
        self.callback_handlers = []
        self.replies = []
        self.next_steps = []

    def message_handler(self, **filters):
        def register(handler):
            self.message_handlers.append((filters, handler))
            return handler
        return register

    def callback_query_handler(self, **filters):
        def register(handler):
            self.callback_handlers.append((filters, handler))
            return handler
        return register

    def send_message(self, chat_id, text, **kwargs):
        return SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            from_user=SimpleNamespace(id=1),
            text=text,
        )

    def register_next_step_handler(self, message, handler, *args, **kwargs):
        self.next_steps.append((message, handler, args, kwargs))

    def reply_to(self, message, text, **kwargs):
        self.replies.append(text)


def test_admin_delete_command_deletes_only_existing_products(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [42])
    deleted = []
    db = SimpleNamespace(
        get_product=lambda product_id: {'id': product_id} if product_id == 7 else None,
        delete_product=lambda product_id: deleted.append(product_id) or True,
        log_activity=lambda *args: None,
    )
    bot = RecordingBot()
    admin.register(bot, db)
    delete_handler = next(
        handler
        for filters, handler in bot.message_handlers
        if filters.get('commands') == ['delete']
    )
    message = SimpleNamespace(
        text='/delete 7',
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=42),
    )

    delete_handler(message)

    assert deleted == [7]
    assert '7' in bot.replies[-1]


def test_admin_delete_command_rejects_non_numeric_id(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [42])
    db = SimpleNamespace(get_product=lambda product_id: {'id': product_id})
    bot = RecordingBot()
    admin.register(bot, db)
    delete_handler = next(
        handler
        for filters, handler in bot.message_handlers
        if filters.get('commands') == ['delete']
    )
    message = SimpleNamespace(
        text='/delete abc',
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=42),
    )

    delete_handler(message)

    assert bot.replies
    assert 'ትክክለኛ' in bot.replies[-1]


def test_add_command_registers_first_step_on_prompt(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [42])
    db = SimpleNamespace()
    bot = RecordingBot()
    admin.register(bot, db)
    add_handler = next(
        handler
        for filters, handler in bot.message_handlers
        if filters.get('commands') == ['add']
    )
    message = SimpleNamespace(
        text='/add',
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=42),
    )

    add_handler(message)

    prompt, next_handler, args, _ = bot.next_steps[-1]
    assert prompt is not message
    assert next_handler.__name__ == 'process_add_product_name'
    assert args == (db, bot)


def test_product_navigation_handler_does_not_consume_wishlist_callbacks():
    bot = RecordingBot()
    products.register(bot, SimpleNamespace())
    navigation_filter = next(
        filters['func']
        for filters, handler in bot.callback_handlers
        if handler.__name__ == 'handle_product_navigation'
    )

    assert navigation_filter(SimpleNamespace(data='product_nav_Men_1'))
    assert not navigation_filter(SimpleNamespace(data='product_wishlist_7'))


def test_language_reply_keyboard_switches_to_english(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [])
    updated = []
    db = SimpleNamespace(
        get_user_lang=lambda user_id: 'en',
        get_user=lambda user_id: {'first_name': 'Customer', 'is_subscribed': 1},
        update_user=lambda user_id, **kwargs: updated.append((user_id, kwargs)),
        log_activity=lambda *args: None,
    )
    bot = RecordingBot()
    start.register(bot, db)
    language_handler = next(
        handler
        for filters, handler in bot.message_handlers
        if filters.get('func')
        and filters['func'](SimpleNamespace(text='🇬🇧 English'))
    )
    message = SimpleNamespace(
        text='🇬🇧 English',
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=42),
    )

    language_handler(message)

    assert updated == [(42, {'lang': 'en'})]


def test_product_keyboard_has_previous_and_next_navigation():
    keyboard = get_product_keyboard(
        product_id=5,
        category='Men',
        index=1,
        total=3,
    )
    callback_data = [
        button.callback_data
        for row in keyboard.keyboard
        for button in row
        if button.callback_data
    ]

    assert 'product_nav_Men_0' in callback_data
    assert 'product_nav_Men_2' in callback_data


def test_social_keyboard_uses_configured_admin_username(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_USERNAME', 'hikma_admin')

    keyboard = get_social_keyboard('en')
    urls = [
        button.url
        for row in keyboard.keyboard
        for button in row
        if button.url
    ]

    assert urls == ['https://t.me/hikma_admin']


def test_commands_are_registered_before_the_text_fallback():
    bot = RecordingBot()
    register_handlers(bot, SimpleNamespace())
    catchall_index = next(
        index
        for index, (filters, _) in enumerate(bot.message_handlers)
        if filters.get('content_types') == ['text']
        and filters.get('func')
        and filters['func'](SimpleNamespace(text='ordinary message'))
    )
    command_indices = {
        command: next(
            index
            for index, (filters, _) in enumerate(bot.message_handlers)
            if command in filters.get('commands', [])
        )
        for command in ('start', 'add', 'delete')
    }

    assert all(index < catchall_index for index in command_indices.values())