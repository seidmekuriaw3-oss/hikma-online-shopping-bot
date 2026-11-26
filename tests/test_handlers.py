from types import SimpleNamespace

import psycopg2

from config import config
from handlers import (
    _DatabaseErrorReportingBot, admin, messages, orders, products,
    register_handlers, start, user,
)
from keyboards.inline import (
    get_admin_keyboard, get_admin_product_category_keyboard,
    get_main_keyboard, get_payment_keyboard, get_product_keyboard, get_social_keyboard,
    get_storefront_categories_keyboard,
)
from keyboards.reply import get_main_menu


class RecordingBot:
    def __init__(self):
        self.message_handlers = []
        self.callback_handlers = []
        self.replies = []
        self.messages = []
        self.message_options = []
        self.callback_answers = []
        self.next_steps = []
        self.cleared_step_chats = []
        self.photos = []
        self.edits = []
        self._next_message_id = 1

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
        self.messages.append((chat_id, text))
        self.message_options.append(kwargs)
        message_id = self._next_message_id
        self._next_message_id += 1
        return SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            from_user=SimpleNamespace(id=1),
            text=text,
            message_id=message_id,
            content_type='text',
        )

    def send_photo(self, chat_id, photo, **kwargs):
        self.photos.append((chat_id, photo, kwargs))
        message_id = self._next_message_id
        self._next_message_id += 1
        return SimpleNamespace(
            chat=SimpleNamespace(id=chat_id),
            from_user=SimpleNamespace(id=1),
            message_id=message_id,
            content_type='photo',
        )

    def edit_message_media(self, media, chat_id, message_id, **kwargs):
        self.edits.append(('media', media, chat_id, message_id, kwargs))

    def edit_message_caption(self, caption, chat_id, message_id, **kwargs):
        self.edits.append(('caption', caption, chat_id, message_id, kwargs))

    def edit_message_text(self, text, chat_id, message_id, **kwargs):
        self.edits.append(('text', text, chat_id, message_id, kwargs))

    def register_next_step_handler(self, message, handler, *args, **kwargs):
        self.next_steps.append((message, handler, args, kwargs))

    def clear_step_handler_by_chat_id(self, chat_id):
        self.cleared_step_chats.append(chat_id)

    def reply_to(self, message, text, **kwargs):
        self.replies.append(text)

    def answer_callback_query(self, callback_id, text='', **kwargs):
        self.callback_answers.append((callback_id, text, kwargs))


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
    assert '7' in bot.messages[-1][1]


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

    assert bot.messages
    assert 'ትክክለኛ' in bot.messages[-1][1]


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


def test_add_product_callback_tracks_fresh_admin_through_all_steps(monkeypatch):
    user_id = 42
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [user_id])
    monkeypatch.setattr(admin, 'admin_states', {})
    monkeypatch.setattr(admin, 'admin_uploading', set())
    monkeypatch.setattr(admin, 'notify_admins', lambda *args, **kwargs: None)
    created_products = []
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'am'},
        create_product=lambda product: created_products.append(product) or 77,
        log_activity=lambda *args: None,
    )
    bot = RecordingBot()
    admin.register(bot, db)

    callback_handler = next(
        handler
        for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='admin_add_product'))
    )
    callback = SimpleNamespace(
        id='callback-1',
        data='admin_add_product',
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=user_id),
            from_user=SimpleNamespace(id=999),
        ),
    )
    callback_handler(callback)

    assert user_id in admin.admin_states
    assert 999 not in admin.admin_states

    responses = [
        ('ሸሚዝ', 'text'),
        ('Shirt', 'text'),
        ('20', 'text'),
        ('M', 'text'),
        ('Men', 'text'),
        ('3', 'text'),
        (None, 'photo'),
    ]
    for index, (text, content_type) in enumerate(responses):
        _, handler, args, kwargs = bot.next_steps[index]
        message = SimpleNamespace(
            chat=SimpleNamespace(id=user_id),
            from_user=SimpleNamespace(id=user_id),
            text=text,
            content_type=content_type,
            photo=[SimpleNamespace(file_id='photo-id')] if content_type == 'photo' else [],
        )
        handler(message, *args, **kwargs)

    assert created_products == [{
        'name_am': 'ሸሚዝ',
        'name_en': 'Shirt',
        'price': 20.0,
        'size': 'M',
        'category': 'Men',
        'image_id': 'photo-id',
        'stock_quantity': 3,
        'status': 'In Stock',
    }]
    assert user_id not in admin.admin_states


def test_admin_add_product_category_can_be_selected_inline_end_to_end(monkeypatch):
    user_id = 42
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [user_id])
    monkeypatch.setattr(admin, 'admin_states', {})
    monkeypatch.setattr(admin, 'admin_uploading', set())
    monkeypatch.setattr(admin, 'notify_admins', lambda *args, **kwargs: None)
    created_products = []
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        create_product=lambda product: created_products.append(product) or 77,
        log_activity=lambda *args: None,
        get_user_count=lambda: 0,
        get_product_count=lambda: 1,
        get_order_stats=lambda: {'summary': {}},
        get_daily_stats=lambda: {},
    )
    bot = RecordingBot()
    admin.register(bot, db)

    add_handler = next(
        handler for filters, handler in bot.message_handlers
        if filters.get('commands') == ['add']
    )
    add_handler(SimpleNamespace(
        text='/add',
        from_user=SimpleNamespace(id=user_id),
        chat=SimpleNamespace(id=user_id),
    ))

    for index, (text, content_type) in enumerate((
        ('Dress', 'text'),
        ('Dress EN', 'text'),
        ('25', 'text'),
        ('M', 'text'),
    )):
        _, handler, args, kwargs = bot.next_steps[index]
        handler(SimpleNamespace(
            chat=SimpleNamespace(id=user_id),
            from_user=SimpleNamespace(id=user_id),
            text=text,
            content_type=content_type,
        ), *args, **kwargs)

    category_keyboard = bot.message_options[-1]['reply_markup']
    category_buttons = [
        button
        for row in category_keyboard.keyboard
        for button in row
    ]
    assert len(category_buttons) == 6
    assert any(button.callback_data == 'add_product_category:women' for button in category_buttons)

    select_category = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='add_product_category:women'))
    )
    select_category(SimpleNamespace(
        id='select-women',
        data='add_product_category:women',
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(chat=SimpleNamespace(id=user_id)),
    ))
    assert bot.cleared_step_chats == [user_id]
    assert admin.admin_states[user_id]['data']['category'] == 'women'

    _, stock_handler, args, kwargs = bot.next_steps[-1]
    stock_handler(SimpleNamespace(
        chat=SimpleNamespace(id=user_id),
        from_user=SimpleNamespace(id=user_id),
        text='3',
    ), *args, **kwargs)
    _, image_handler, args, kwargs = bot.next_steps[-1]
    image_handler(SimpleNamespace(
        chat=SimpleNamespace(id=user_id),
        from_user=SimpleNamespace(id=user_id),
        content_type='photo',
        photo=[SimpleNamespace(file_id='dress-photo')],
    ), *args, **kwargs)

    assert created_products[0]['category'] == 'women'
    assert created_products[0]['stock_quantity'] == 3


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


def test_main_menu_has_six_customer_actions_and_admin_only_button(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [42])
    db = SimpleNamespace(get_user=lambda _user_id: {'lang': 'en'})

    customer_menu = get_main_menu(7, db)
    admin_menu = get_main_menu(42, db)
    customer_rows = [[button['text'] for button in row] for row in customer_menu.keyboard]
    admin_rows = [[button['text'] for button in row] for row in admin_menu.keyboard]

    assert customer_rows == [
        ['🛍️ Products', '🛒 Cart'],
        ['📋 My Orders', '❤️ Wishlist'],
        ['👤 Profile', '📍 Contact'],
    ]
    assert admin_rows == customer_rows + [['⚙️ Admin Panel']]


def test_storefront_menu_opens_eight_category_carousel_with_legacy_aliases(monkeypatch):
    monkeypatch.setattr(admin, 'admin_states', {})
    catalog = [{
        'id': 5, 'name_am': 'ቀሚስ', 'name_en': 'Dress', 'price': 120,
        'size': 'M', 'stock_quantity': 2, 'image_id': 'photo-1',
        'category': 'Women',
    }]
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_product_category_counts=lambda: {
            'women': 1, 'men': 2, 'kids': 0, 'pajamas': 0,
            'shoes': 0, 'accessories': 0, 'new_arrivals': 3, 'hot_deals': 1,
        },
        get_products=lambda category=None, **_kwargs: catalog if category == 'women' else [],
        log_activity=lambda *_args: None,
    )
    bot = RecordingBot()
    register_handlers(bot, db)
    products_button_handler = next(
        handler for filters, handler in bot.message_handlers
        if filters.get('func')
        and filters['func'](SimpleNamespace(text='🛍️ Products'))
    )
    products_button_handler(SimpleNamespace(
        text='🛍️ Products',
        from_user=SimpleNamespace(id=701),
        chat=SimpleNamespace(id=701),
    ))

    assert 'reply_markup' in bot.message_options[-1], (
        products_button_handler.__name__, bot.messages,
    )
    keyboard = bot.message_options[-1]['reply_markup']
    category_buttons = [
        button
        for row in keyboard.keyboard
        for button in row
        if button.callback_data and button.callback_data.startswith('browse_cat:')
    ]
    assert len(category_buttons) == 8
    assert any(button.text == "👗 Women's Fashion (1)" for button in category_buttons)
    assert any(button.callback_data == 'browse_cat:new_arrivals:0' for button in category_buttons)
    assert any(button.callback_data == 'browse_cat:hot_deals:0' for button in category_buttons)

    category_handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='browse_cat:women:0'))
    )
    category_handler(SimpleNamespace(
        id='browse-women',
        data='browse_cat:women:0',
        from_user=SimpleNamespace(id=701),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=701),
            message_id=15,
            content_type='text',
            text='🛍️ Welcome to the Hikma store!\n\nChoose a category:',
        ),
    ))

    assert bot.photos[-1][1] == 'photo-1'
    assert 'Dress' in bot.photos[-1][2]['caption']
    product_keyboard = bot.photos[-1][2]['reply_markup']
    buttons = [
        button for row in product_keyboard.keyboard for button in row
    ]
    assert any(button.text == '🔙 Back to Categories' for button in buttons)
    assert any(button.callback_data == 'browse_categories' for button in buttons)

    categories_handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='browse_categories'))
    )
    categories_handler(SimpleNamespace(
        id='back-categories',
        data='browse_categories',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=42),
            message_id=88,
            content_type='photo',
        ),
    ))
    assert bot.edits[-1][0] == 'caption'
    assert any(
        button.callback_data == 'browse_cat:women:0'
        for row in bot.edits[-1][4]['reply_markup'].keyboard
        for button in row
    )


def test_storefront_category_keyboard_keeps_two_column_grid():
    keyboard = get_storefront_categories_keyboard(lang='am')
    category_rows = keyboard.keyboard[:4]

    assert all(len(row) == 2 for row in category_rows)
    assert [
        button.callback_data
        for row in category_rows
        for button in row
    ] == [
        'browse_cat:women:0', 'browse_cat:men:0',
        'browse_cat:kids:0', 'browse_cat:pajamas:0',
        'browse_cat:shoes:0', 'browse_cat:accessories:0',
        'browse_cat:new_arrivals:0', 'browse_cat:hot_deals:0',
    ]


def test_welcome_inline_products_button_opens_category_picker():
    keyboard = get_main_keyboard('en')
    products_button = next(
        button
        for row in keyboard.keyboard
        for button in row
        if button.callback_data == 'browse_categories'
    )
    assert products_button.text == '🛍️ Products'


def test_message_module_routes_new_products_and_wishlist_buttons():
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        log_activity=lambda *_args: None,
        get_product_category_counts=lambda: {},
        execute=lambda *_args: SimpleNamespace(fetchall=lambda: []),
    )
    bot = RecordingBot()
    messages.register(bot, db)
    catchall = next(
        handler for filters, handler in bot.message_handlers
        if filters.get('func')
        and filters['func'](SimpleNamespace(text='🛍️ Products'))
    )
    message = SimpleNamespace(
        text='🛍️ Products',
        from_user=SimpleNamespace(id=42),
        chat=SimpleNamespace(id=42),
    )
    catchall(message)
    assert 'Choose a category' in bot.messages[-1][1]
    assert any(
        button.callback_data == 'browse_cat:women:0'
        for row in bot.message_options[-1]['reply_markup'].keyboard
        for button in row
    )

    message.text = '❤️ Wishlist'
    catchall(message)
    assert 'Your wishlist is empty' in bot.messages[-1][1]
    assert any(
        button.callback_data == 'browse_categories'
        for row in bot.message_options[-1]['reply_markup'].keyboard
        for button in row
    )


def test_category_selection_sends_first_product_photo_card():
    catalog = [
        {
            'id': 5, 'name_am': 'ቀሚስ', 'name_en': 'Dress', 'price': 120,
            'size': 'M', 'stock_quantity': 2, 'image_id': 'photo-1',
            'category': 'Women',
        },
    ]
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_products=lambda **_kwargs: catalog,
    )
    bot = RecordingBot()
    products.register(bot, db)
    handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='category_Women'))
    )

    handler(SimpleNamespace(
        id='category-call',
        data='category_Women',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(id=42)),
    ))

    assert bot.photos[0][1] == 'photo-1'
    assert 'Dress' in bot.photos[0][2]['caption']
    assert '1 / 1' in bot.photos[0][2]['caption']


def test_category_card_falls_back_to_inline_text_when_photo_is_rejected():
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_products=lambda **_kwargs: [{
            'id': 5, 'name_en': 'Dress', 'price': 120,
            'size': 'M', 'stock_quantity': 2, 'image_id': 'invalid-photo',
            'category': 'Women',
        }],
    )
    bot = RecordingBot()
    bot.send_photo = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('bad file id'))
    products.register(bot, db)
    handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='category_Women'))
    )
    handler(SimpleNamespace(
        id='category-call',
        data='category_Women',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(id=42)),
    ))

    assert 'Dress' in bot.messages[-1][1]
    keyboard = bot.message_options[-1]['reply_markup']
    assert any(button.callback_data == 'product_cart_5' for row in keyboard.keyboard for button in row)


def test_browse_category_next_and_back_edit_the_product_card_in_place():
    catalog = [
        {'id': 1, 'name_am': 'አንድ', 'name_en': 'One', 'price': 1, 'size': 'S', 'stock_quantity': 1, 'image_id': 'one', 'category': 'Men'},
        {'id': 2, 'name_am': 'ሁለት', 'name_en': 'Two', 'price': 2, 'size': 'M', 'stock_quantity': 1, 'image_id': 'two', 'category': 'Men'},
    ]
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_products=lambda **_kwargs: catalog,
    )
    bot = RecordingBot()
    products.register(bot, db)
    handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='browse_cat:Men:1'))
    )
    for index, expected_photo in ((1, 'two'), (0, 'one')):
        call = SimpleNamespace(
            id=f'browse-{index}',
            data=f'browse_cat:Men:{index}',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(
                chat=SimpleNamespace(id=42),
                message_id=77,
                content_type='photo',
            ),
        )
        handler(call)
        edit = bot.edits[-1]
        assert edit[0] == 'media'
        assert edit[1].media == expected_photo
        assert edit[3] == 77
        callback_data = [
            button.callback_data
            for row in edit[4]['reply_markup'].keyboard
            for button in row
        ]
        assert f'browse_cat:Men:{1 - index}' in callback_data


def test_empty_hot_deals_returns_to_category_menu_gracefully():
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_product_category_counts=lambda: {'hot_deals': 0},
        get_products=lambda **_kwargs: [],
    )
    bot = RecordingBot()
    products.register(bot, db)
    handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='browse_cat:hot_deals:0'))
    )
    handler(SimpleNamespace(
        id='empty-deals',
        data='browse_cat:hot_deals:0',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=42),
            message_id=93,
            content_type='photo',
        ),
    ))

    assert bot.edits[-1][0] == 'caption'
    assert bot.callback_answers[-1][1] == 'No active deals right now. Choose another category.'
    assert any(
        button.callback_data == 'browse_cat:women:0'
        for row in bot.edits[-1][4]['reply_markup'].keyboard
        for button in row
    )


def test_product_command_supports_spaced_and_compact_ids():
    product = {
        'id': 8, 'name_en': 'Coat', 'price': 250, 'size': 'L',
        'stock_quantity': 1, 'image_id': 'coat-photo', 'category': 'Men',
    }
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_product=lambda product_id: product if product_id == 8 else None,
    )
    bot = RecordingBot()
    products.register(bot, db)
    product_command = next(
        handler for filters, handler in bot.message_handlers
        if filters.get('commands') == ['product']
    )
    for text in ('/product 8', '/product8'):
        product_command(SimpleNamespace(
            text=text,
            from_user=SimpleNamespace(id=42),
            chat=SimpleNamespace(id=42),
        ))

    assert [photo[1] for photo in bot.photos] == ['coat-photo', 'coat-photo']


def test_cart_quantity_callback_updates_cart_and_edits_summary():
    cart = {'items': [{'product_id': 9, 'name': 'Shirt', 'price': 25, 'quantity': 1}], 'final_amount': 25}
    updates = []
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_cart=lambda _user_id: cart,
        get_product=lambda _product_id: {'id': 9, 'name_en': 'Shirt', 'stock_quantity': 4},
        update_cart=lambda _user_id, items, discount_code=None: updates.append((items, discount_code)) or True,
        clear_cart=lambda _user_id: True,
    )
    bot = RecordingBot()
    orders.register(bot, db)
    handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='cart_inc_9'))
    )

    handler(SimpleNamespace(
        id='cart-call',
        data='cart_inc_9',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=42),
            message_id=81,
            from_user=SimpleNamespace(id=1),
        ),
    ))

    assert updates[0][0][0]['quantity'] == 2
    assert bot.edits[-1][0] == 'text'
    assert bot.edits[-1][3] == 81


def test_clear_cart_refresh_uses_the_callback_user_id():
    user_ids = []
    db = SimpleNamespace(
        get_user=lambda _user_id: {'lang': 'en'},
        get_cart=lambda user_id: user_ids.append(user_id) or {'items': []},
        clear_cart=lambda _user_id: True,
    )
    bot = RecordingBot()
    orders.register(bot, db)
    handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='clear_cart'))
    )
    handler(SimpleNamespace(
        id='clear-cart',
        data='clear_cart',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=42),
            message_id=81,
            from_user=SimpleNamespace(id=1),
        ),
    ))

    assert user_ids == [42]
    assert 'Your cart is empty' in bot.edits[-1][1]


def test_profile_has_direct_language_and_wishlist_actions():
    db = SimpleNamespace(
        get_user=lambda _user_id: {
            'first_name': 'Customer', 'lang': 'en', 'phone': '1234567890',
        },
        get_user_orders=lambda _user_id: [],
        get_cart=lambda _user_id: {'items': []},
        execute=lambda *_args: SimpleNamespace(fetchone=lambda: (3,)),
    )
    bot = RecordingBot()
    user.show_user_profile(
        SimpleNamespace(
            chat=SimpleNamespace(id=42),
            from_user=SimpleNamespace(id=42),
        ),
        db,
        bot,
    )

    profile_markup = bot.message_options[-1]['reply_markup']
    callback_data = [
        button.callback_data
        for row in profile_markup.keyboard
        for button in row
    ]
    assert 'change_language' in callback_data
    assert 'my_wishlist' in callback_data


def test_profile_language_button_opens_amharic_and_english_choices(monkeypatch):
    profile = {'first_name': 'Customer', 'lang': 'am'}
    updated = []
    db = SimpleNamespace(
        get_user=lambda _user_id: profile,
        get_user_orders=lambda _user_id: [],
        get_cart=lambda _user_id: {'items': []},
        execute=lambda *_args: SimpleNamespace(fetchone=lambda: (0,)),
        update_user=lambda _user_id, **kwargs: (profile.update(kwargs), updated.append(kwargs)),
        log_activity=lambda *_args: None,
    )
    bot = RecordingBot()
    user.register(bot, db)
    language_menu_handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='change_language'))
    )
    call = SimpleNamespace(
        id='language-menu',
        data='change_language',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(id=42)),
    )
    language_menu_handler(call)
    keyboard = bot.message_options[-1]['reply_markup']
    options = [
        button.callback_data
        for row in keyboard.keyboard
        for button in row
    ]
    assert 'set_lang_am' in options
    assert 'set_lang_en' in options
    change_handler = next(
        handler for filters, handler in bot.callback_handlers
        if filters['func'](SimpleNamespace(data='set_lang_en'))
    )
    change_handler(SimpleNamespace(
        id='language-choice',
        data='set_lang_en',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(id=42)),
    ))
    assert profile['lang'] == 'en'


def test_checkout_confirms_phone_and_address_before_payment():
    user_data = {'lang': 'en', 'phone': '1234567890', 'first_name': 'Customer'}
    db = SimpleNamespace(
        get_user=lambda _user_id: user_data,
        get_cart=lambda _user_id: {
            'items': [{'product_id': 3, 'price': 10, 'quantity': 1}],
            'final_amount': 10,
        },
        get_user_orders=lambda *_args, **_kwargs: [],
        update_user=lambda _user_id, **kwargs: user_data.update(kwargs),
    )
    monkeypatch_state = orders.order_states
    orders.order_states = {}
    bot = RecordingBot()
    orders.register(bot, db)
    try:
        checkout_handler = next(
            handler for filters, handler in bot.callback_handlers
            if filters['func'](SimpleNamespace(data='checkout'))
        )
        checkout_handler(SimpleNamespace(
            id='checkout',
            data='checkout',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        ))
        assert 'Confirm your phone number' in bot.messages[-1][1]

        edit_phone = next(
            handler for filters, handler in bot.callback_handlers
            if filters['func'](SimpleNamespace(data='checkout_phone_edit'))
        )
        edit_phone(SimpleNamespace(
            id='phone-edit',
            data='checkout_phone_edit',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        ))
        _, phone_handler, args, kwargs = bot.next_steps[-1]
        phone_handler(SimpleNamespace(
            chat=SimpleNamespace(id=42),
            from_user=SimpleNamespace(id=42),
            text='1234567891',
        ), *args, **kwargs)
        assert orders.order_states[42]['step'] == 'phone_confirm'

        confirm_phone = next(
            handler for filters, handler in bot.callback_handlers
            if filters['func'](SimpleNamespace(data='checkout_phone_confirm'))
        )
        confirm_phone(SimpleNamespace(
            id='phone-confirm',
            data='checkout_phone_confirm',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        ))
        _, address_handler, args, kwargs = bot.next_steps[-1]
        address_handler(SimpleNamespace(
            chat=SimpleNamespace(id=42),
            from_user=SimpleNamespace(id=42),
            content_type='text',
            text='12 Example Street',
        ), *args, **kwargs)
        assert 'Confirm delivery address' in bot.messages[-1][1]

        edit_address = next(
            handler for filters, handler in bot.callback_handlers
            if filters['func'](SimpleNamespace(data='checkout_address_edit'))
        )
        edit_address(SimpleNamespace(
            id='address-edit',
            data='checkout_address_edit',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        ))
        _, address_handler, args, kwargs = bot.next_steps[-1]
        address_handler(SimpleNamespace(
            chat=SimpleNamespace(id=42),
            from_user=SimpleNamespace(id=42),
            content_type='text',
            text='34 Updated Road',
        ), *args, **kwargs)
        assert orders.order_states[42]['address'] == '34 Updated Road'

        confirm_address = next(
            handler for filters, handler in bot.callback_handlers
            if filters['func'](SimpleNamespace(data='checkout_address_confirm'))
        )
        confirm_address(SimpleNamespace(
            id='address-confirm',
            data='checkout_address_confirm',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        ))
        assert orders.order_states[42]['step'] == 'payment'
        assert any(
            button.callback_data == 'pay_cash'
            for row in bot.message_options[-1]['reply_markup'].keyboard
            for button in row
        )
    finally:
        orders.order_states = monkeypatch_state


def test_customer_callback_prefixes_have_single_feature_owner():
    bot = RecordingBot()
    register_handlers(bot, SimpleNamespace())
    callback_data = (
        'category_Men', 'browse_categories', 'browse_cat:Men:1', 'product_cart_1',
        'product_wishlist_1', 'cart_inc_1', 'view_cart', 'checkout',
        'checkout_phone_confirm', 'checkout_address_confirm', 'view_orders',
        'order_1', 'view_profile', 'change_language', 'show_wishlist',
        'view_contact', 'main_menu', 'pay_cash', 'admin_add_product',
        'admin_order_view_1', 'admin_find_user', 'admin_toggle_ban_42',
        'add_product_category:women',
        'admin_all_orders', 'admin_pending_orders', 'admin_products',
        'admin_orders', 'admin_users', 'admin_reports', 'admin_discounts',
        'admin_settings',
    )
    for data in callback_data:
        matched_handlers = [
            handler
            for filters, handler in bot.callback_handlers
            if handler.__name__ != 'handle_unknown_callback'
            and filters.get('func')
            and filters['func'](SimpleNamespace(data=data))
        ]
        assert len(matched_handlers) == 1, (data, [handler.__name__ for handler in matched_handlers])


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
        for command in ('start', 'help', 'orders', 'admin', 'add', 'delete')
    }

    assert all(index < catchall_index for index in command_indices.values())
    slash_message = SimpleNamespace(text='/orders')
    assert not bot.message_handlers[catchall_index][0]['func'](slash_message)


def test_checkout_order_is_reachable_from_orders_command_and_inline_button(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [])
    order = {
        'id': 5, 'order_number': 'HIK202611260001', 'user_id': 42,
        'status': 'Pending', 'final_amount': 45000,
        'order_date': '2026-11-26', 'item_count': 1,
    }
    created = []
    db = SimpleNamespace(
        get_user=lambda user_id: {
            'user_id': user_id, 'lang': 'en', 'first_name': 'Customer',
            'phone': '1234567890',
        },
        get_admin_ids=lambda: [],
        create_order=lambda data: created.append(data) or 5,
        add_order_item=lambda **_kwargs: True,
        clear_cart=lambda _user_id: True,
        get_order=lambda _order_id: order,
        get_order_items=lambda _order_id: [],
        get_user_orders=lambda _user_id, limit=20: [order],
    )
    saved_states = orders.order_states
    orders.order_states = {
        42: {
            'step': 'payment',
            'total': 45000,
            'subtotal': 45000,
            'discount_amount': 0,
            'items': [{'product_id': 7, 'price': 45000, 'quantity': 1}],
            'discount_code': None,
            'phone': '1234567890',
            'address': '10 Example Street',
        },
    }
    bot = RecordingBot()
    register_handlers(bot, db)
    try:
        pay_handler = next(
            handler for filters, handler in bot.callback_handlers
            if handler.__name__ == 'handle_payment'
            and filters['func'](SimpleNamespace(data='pay_cash'))
        )
        pay_handler(SimpleNamespace(
            id='pay-order',
            data='pay_cash',
            from_user=SimpleNamespace(id=42, first_name='Customer', username='customer'),
            message=SimpleNamespace(chat=SimpleNamespace(id=42)),
        ))
        assert len(created) == 1
        confirmation = bot.messages[-1][1]
        assert confirmation.count('ETB') == 1
        assert any(
            button.callback_data == 'view_orders'
            for row in bot.message_options[-1]['reply_markup'].keyboard
            for button in row
        )

        before = len(bot.messages)
        orders_command = next(
            handler for filters, handler in bot.message_handlers
            if filters.get('commands') == ['orders']
        )
        orders_command(SimpleNamespace(
            text='/orders',
            from_user=SimpleNamespace(id=42),
            chat=SimpleNamespace(id=42),
        ))
        assert len(bot.messages) == before + 1
        assert 'HIK202611260001' in bot.messages[-1][1]

        view_handler = next(
            handler for filters, handler in bot.callback_handlers
            if filters['func'](SimpleNamespace(data='view_orders'))
        )
        view_handler(SimpleNamespace(
            id='view-orders',
            data='view_orders',
            from_user=SimpleNamespace(id=42),
            message=SimpleNamespace(
                chat=SimpleNamespace(id=42),
                message_id=70,
                from_user=SimpleNamespace(id=1),
            ),
        ))
        assert 'HIK202611260001' in bot.messages[-1][1]
    finally:
        orders.order_states = saved_states


def test_admin_order_filters_render_once_and_status_updates_notify_customer(monkeypatch):
    monkeypatch.setattr(config.bot, 'ADMIN_IDS', [42])
    order = {
        'id': 7, 'order_number': 'HIK202611260007', 'user_id': 99,
        'status': 'pending', 'final_amount': 45000,
        'total_amount': 45000, 'payment_method': 'cash_on_delivery',
        'customer_name': 'Customer', 'customer_phone': '1234567890',
        'shipping_name': 'Customer', 'shipping_phone': '1234567890',
        'shipping_address': '10 Example Street',
        'items': [{
            'name_am': 'ኮት', 'name_en': 'Coat', 'quantity': 1,
            'total_price': 45000,
        }],
    }
    status_queries = []

    def get_orders_by_status(status=None):
        status_queries.append(status)
        if status and status.lower() not in (order['status'].lower(), 'completed'):
            return []
        return [dict(order)]

    db = SimpleNamespace(
        get_user=lambda user_id: {
            'user_id': user_id, 'lang': 'en', 'first_name': 'Customer',
            'phone': '1234567890', 'username': 'customer',
        },
        get_admin_ids=lambda: [42],
        get_orders_by_status=get_orders_by_status,
        get_order=lambda _order_id: dict(order),
        get_order_items=lambda _order_id: order['items'],
        update_order_status=lambda _order_id, status: (order.update(status=status) or True),
    )
    bot = RecordingBot()
    register_handlers(bot, db)

    all_orders_handler = next(
        handler for filters, handler in bot.callback_handlers
        if handler.__name__ == 'handle_admin_callbacks'
        and filters['func'](SimpleNamespace(data='admin_all_orders'))
    )
    all_orders_handler(SimpleNamespace(
        id='all-orders',
        data='admin_all_orders',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(id=42), from_user=SimpleNamespace(id=1)),
    ))
    assert status_queries == [None]
    assert len(bot.messages) == 1
    card = bot.messages[0][1]
    assert all(value in card for value in (
        'HIK202611260007', 'Customer', '1234567890', 'Coat',
        '45,000.00 ETB', '10 Example Street', 'Cash on Delivery',
    ))
    assert card.count('ETB') == 2
    assert 'ETB ETB' not in card
    actions = bot.message_options[0]['reply_markup']
    assert any(
        button.callback_data == 'admin_order_status_7_Shipped'
        for row in actions.keyboard
        for button in row
    )

    pending_handler = next(
        handler for filters, handler in bot.callback_handlers
        if handler.__name__ == 'handle_admin_callbacks'
        and filters['func'](SimpleNamespace(data='admin_pending_orders'))
    )
    pending_handler(SimpleNamespace(
        id='pending-orders',
        data='admin_pending_orders',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(chat=SimpleNamespace(id=42), from_user=SimpleNamespace(id=1)),
    ))
    assert status_queries == [None, 'Pending']
    assert len(bot.messages) == 2

    status_handler = next(
        handler for filters, handler in bot.callback_handlers
        if handler.__name__ == 'handle_admin_order'
        and filters['func'](SimpleNamespace(data='admin_order_status_7_Shipped'))
    )
    status_handler(SimpleNamespace(
        id='ship-order',
        data='admin_order_status_7_Shipped',
        from_user=SimpleNamespace(id=42),
        message=SimpleNamespace(
            chat=SimpleNamespace(id=42),
            message_id=81,
            from_user=SimpleNamespace(id=1),
        ),
    ))
    assert order['status'] == 'Shipped'
    assert bot.messages[-1][0] == 99
    assert any(
        button.callback_data == 'view_orders'
        for row in bot.message_options[-1]['reply_markup'].keyboard
        for button in row
    )
    assert len(bot.edits) == 1


def test_payment_keyboard_uses_localized_readable_labels():
    keyboard = get_payment_keyboard('am')
    labels = [button.text for row in keyboard.keyboard for button in row]

    assert '💵 በጥሬ ገንዘብ (Cash on Delivery)' in labels
    assert '🏦 በባንክ ማስተላለፍ (Bank Transfer)' in labels
    assert '💳 Chapa' in labels
    assert '📱 Telebirr' in labels
    assert not any('_' in label for label in labels)


def test_admin_inline_keyboard_routes_to_registered_admin_features():
    bot = RecordingBot()
    register_handlers(bot, SimpleNamespace())
    keyboard = get_admin_keyboard('en')
    callback_data = [
        button.callback_data
        for row in keyboard.keyboard
        for button in row
        if button.callback_data
    ]
    for data in callback_data:
        matches = [
            handler for filters, handler in bot.callback_handlers
            if handler.__name__ != 'handle_unknown_callback'
            and filters.get('func')
            and filters['func'](SimpleNamespace(data=data))
        ]
        assert len(matches) == 1, (data, [handler.__name__ for handler in matches])


def test_postgres_handler_failure_sends_user_friendly_message():
    bot = RecordingBot()
    guarded_bot = _DatabaseErrorReportingBot(bot)

    @guarded_bot.message_handler()
    def fail(_message):
        raise psycopg2.OperationalError('database unavailable')

    message = SimpleNamespace(chat=SimpleNamespace(id=42))
    bot.message_handlers[-1][1](message)

    assert bot.messages
    assert 'try again later' in bot.messages[-1][1]


def test_postgres_callback_failure_shows_safe_alert():
    bot = RecordingBot()
    guarded_bot = _DatabaseErrorReportingBot(bot)

    @guarded_bot.callback_query_handler()
    def fail(_call):
        raise psycopg2.IntegrityError('database constraint detail')

    call = SimpleNamespace(id='callback-id', data='test')
    bot.callback_handlers[-1][1](call)

    assert bot.callback_answers
    _, text, options = bot.callback_answers[-1]
    assert 'database constraint detail' not in text
    assert options['show_alert'] is True


def test_postgres_next_step_failure_sends_user_friendly_message():
    bot = RecordingBot()
    guarded_bot = _DatabaseErrorReportingBot(bot)
    message = SimpleNamespace(chat=SimpleNamespace(id=42))

    def fail(_message):
        raise psycopg2.OperationalError('database unavailable')

    guarded_bot.register_next_step_handler(message, fail)
    _, next_step_handler, _, _ = bot.next_steps[-1]
    next_step_handler(message)

    assert bot.messages
    assert 'try again later' in bot.messages[-1][1]