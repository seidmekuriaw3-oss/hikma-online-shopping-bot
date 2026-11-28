from contextlib import contextmanager

from config import config
from keyboards.inline import get_start_keyboard
from web_storefront import create_app


class Result:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None


class Cursor:
    def __init__(self):
        self.statements = []
        self.row = None

    def execute(self, query, params=()):
        self.statements.append((query, params))
        if 'FROM products WHERE id' in query:
            self.row = {
                'id': 5, 'price': '12.50', 'stock_quantity': 3,
                'status': 'In Stock',
            }
        elif 'RETURNING id' in query:
            self.row = {'id': 81}

    def fetchone(self):
        return self.row


class DatabaseStub:
    def __init__(self):
        self.cursor_instance = Cursor()
        self.products = [{
            'id': 5, 'name_en': 'Cotton shirt', 'name_am': 'ሸሚዝ',
            'description_en': 'Soft cotton', 'description_am': '',
            'price': '12.50', 'category': 'Men', 'image_id': 'telegram-photo',
            'images': ['second-photo'], 'status': 'In Stock',
            'stock_quantity': 3, 'created_at': '2026-03-01',
        }]

    def get_products(self, **_kwargs):
        return list(self.products)

    def get_order_by_number(self, order_number):
        if order_number == 'HIK-260301-ABC123':
            return {
                'order_number': order_number, 'status': 'Pending',
                'order_date': '2026-03-01', 'shipping_phone': '+251911111111',
            }
        return None

    def execute(self, query, _params=()):
        if 'DISTINCT category' in query:
            return Result([{'category': 'Men'}])
        if 'regexp_replace' in query:
            return Result([{
                'order_number': 'HIK-260301-ABC123',
                'status': 'Pending',
                'order_date': '2026-03-01',
            }])
        if 'AS total_products' in query:
            return Result([{
                'total_products': 1, 'total_orders': 2,
                'pending_orders': 1, 'revenue': 37.5,
            }])
        return Result()

    @contextmanager
    def get_connection(self):
        yield type('Connection', (), {'cursor': lambda _self: self.cursor_instance})()


class BotStub:
    def __init__(self):
        self.messages = []

    def send_message(self, admin_id, message):
        self.messages.append((admin_id, message))


def test_catalog_keeps_legacy_and_gallery_images_and_filters():
    client = create_app(database=DatabaseStub(), admin_token='secret').test_client()

    response = client.get('/api/products?q=shirt&category=men')

    assert response.status_code == 200
    product = response.get_json()[0]
    assert product['images'] == [
        '/api/images/telegram-photo',
        '/api/images/second-photo',
    ]
    assert product['image_refs'] == ['telegram-photo', 'second-photo']


def test_admin_routes_require_token_and_return_metrics_after_auth():
    client = create_app(database=DatabaseStub(), admin_token='secret').test_client()

    denied = client.get('/api/admin/metrics')
    authorized = client.get(
        '/api/admin/metrics',
        headers={'Authorization': 'Bearer secret'},
    )

    assert denied.status_code == 401
    assert authorized.status_code == 200
    assert authorized.get_json()['revenue'] == 37.5


def test_checkout_rejects_invalid_contact_before_database_access():
    database = DatabaseStub()
    client = create_app(database=database, admin_token='secret').test_client()

    response = client.post('/api/orders', json={
        'name': 'Customer', 'phone': '123', 'city': 'Addis',
        'address': 'Bole', 'payment_method': 'cod',
        'items': [{'product_id': 5, 'quantity': 1}],
    })

    assert response.status_code == 400
    assert not database.cursor_instance.statements


def test_checkout_locks_inventory_and_notifies_admin():
    database = DatabaseStub()
    bot = BotStub()
    client = create_app(database=database, admin_token='secret', bot=bot).test_client()

    response = client.post('/api/orders', json={
        'name': 'Customer', 'phone': '+251911111111', 'city': 'Addis Ababa',
        'address': 'Bole', 'payment_method': 'telebirr',
        'items': [{'product_id': 5, 'quantity': 2}],
    })

    assert response.status_code == 201
    assert response.get_json()['total'] == 25
    statements = [query for query, _ in database.cursor_instance.statements]
    assert any('FOR UPDATE' in query for query in statements)
    assert any('INSERT INTO order_items' in query for query in statements)
    assert any('UPDATE products SET' in query for query in statements)


def test_order_tracking_accepts_phone_without_exposing_customer_details():
    client = create_app(database=DatabaseStub(), admin_token='secret').test_client()

    response = client.post('/api/orders/track', json={'phone': '+251911111111'})

    assert response.status_code == 200
    assert response.get_json() == {
        'order_number': 'HIK-260301-ABC123',
        'status': 'Pending',
        'order_date': '2026-03-01',
    }


def test_order_tracking_accepts_order_number_without_phone():
    client = create_app(database=DatabaseStub(), admin_token='secret').test_client()

    response = client.post(
        '/api/orders/track',
        json={'order_number': 'HIK-260301-ABC123'},
    )

    assert response.status_code == 200
    assert response.get_json()['status'] == 'Pending'


def test_bot_welcome_keyboard_has_web_app_button_when_configured(monkeypatch):
    monkeypatch.setattr(config.bot, 'WEB_APP_URL', 'https://shop.example')

    keyboard = get_start_keyboard('en')
    web_app_buttons = [
        button
        for row in keyboard.keyboard
        for button in row
        if button.web_app is not None
    ]

    assert len(web_app_buttons) == 1
    assert web_app_buttons[0].web_app.url == 'https://shop.example'
