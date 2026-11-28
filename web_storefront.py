import hmac
import logging
import os
import re
import secrets
from threading import Lock
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import quote

import requests
from flask import Flask, abort, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from config import config
from database import Database
from models.product import get_images

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / 'web'
UPLOAD_ROOT = Path(os.getenv('UPLOAD_DIR', str(WEB_ROOT / 'uploads'))).resolve()
ORDER_STATUSES = {'Pending', 'Confirmed', 'Shipped', 'Delivered'}
PAYMENT_METHODS = {'telebirr', 'cbe', 'cod'}
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}


def _json_value(value):
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _phone_digits(phone):
    return re.sub(r'\D', '', phone or '')


def _product_payload(product):
    item = dict(product)
    images = get_images(item)
    item['image_refs'] = images
    item['images'] = [
        image if image.startswith(('http://', 'https://', '/uploads/'))
        else f"/api/images/{quote(image, safe='')}"
        for image in images
    ]
    item['image_id'] = item['images'][0] if item['images'] else None
    return _json_value(item)


def create_app(database=None, admin_token=None, bot=None):
    app = Flask(__name__, static_folder=None)
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
    app.config['ADMIN_WEB_TOKEN'] = (
        admin_token if admin_token is not None
        else os.getenv('ADMIN_WEB_TOKEN', '')
    )
    app.extensions['hikma_database'] = database
    app.extensions['hikma_bot'] = bot
    database_lock = Lock()

    def get_db():
        db = app.extensions.get('hikma_database')
        if db is None:
            with database_lock:
                db = app.extensions.get('hikma_database')
                if db is None:
                    db = Database()
                    app.extensions['hikma_database'] = db
        return db

    def require_admin():
        expected = app.config['ADMIN_WEB_TOKEN']
        supplied = request.headers.get('Authorization', '')
        supplied = supplied.removeprefix('Bearer ').strip()
        if not expected or not supplied or not hmac.compare_digest(supplied, expected):
            return jsonify({'error': 'Admin authorization required'}), 401
        return None

    def admin_required(handler):
        from functools import wraps

        @wraps(handler)
        def guarded(*args, **kwargs):
            denied = require_admin()
            if denied is not None:
                return denied
            return handler(*args, **kwargs)

        return guarded

    @app.get('/api/health')
    def health():
        return jsonify({'status': 'ok'})

    @app.get('/api/config')
    def public_config():
        return jsonify({'support_username': config.bot.ADMIN_USERNAME})

    @app.get('/api/products')
    def products():
        db = get_db()
        if request.args.get('in_stock', 'true').lower() == 'true':
            rows = db.get_products(limit=300)
        else:
            result = db.execute(
                "SELECT * FROM products WHERE LOWER(status) IN ('in stock', 'out of stock') ORDER BY created_at DESC LIMIT 300"
            )
            rows = [dict(row) for row in result.fetchall()]
            for row in rows:
                row['images'] = get_images(row)
        query = request.args.get('q', '').strip().casefold()
        category = request.args.get('category', '').strip().casefold()
        in_stock = request.args.get('in_stock', 'true').lower() == 'true'
        if query:
            rows = [
                row for row in rows
                if query in ' '.join(str(row.get(key) or '') for key in (
                    'name_am', 'name_en', 'description_am', 'description_en',
                )).casefold()
            ]
        if category and category != 'all':
            rows = [row for row in rows if str(row.get('category') or '').casefold() == category]
        if in_stock:
            rows = [row for row in rows if int(row.get('stock_quantity') or 0) > 0]
        sort = request.args.get('sort', 'newest')
        if sort == 'price_asc':
            rows.sort(key=lambda row: Decimal(str(row.get('price') or 0)))
        elif sort == 'price_desc':
            rows.sort(key=lambda row: Decimal(str(row.get('price') or 0)), reverse=True)
        else:
            rows.sort(key=lambda row: str(row.get('created_at') or ''), reverse=True)
        return jsonify([_product_payload(row) for row in rows])

    @app.get('/api/categories')
    def categories():
        result = get_db().execute(
            "SELECT DISTINCT category FROM products WHERE category IS NOT NULL AND BTRIM(category) <> '' ORDER BY category"
        )
        return jsonify([row['category'] for row in result.fetchall()])

    @app.get('/api/images/<path:image_id>')
    def product_image(image_id):
        db = get_db()
        result = db.execute(
            "SELECT 1 FROM products WHERE image_id = %s OR images ? %s LIMIT 1",
            (image_id, image_id),
        )
        if not result.fetchone():
            abort(404)
        token = config.bot.TOKEN
        if not token:
            abort(404)
        try:
            response = requests.get(
                f"https://api.telegram.org/bot{token}/getFile",
                params={'file_id': image_id},
                timeout=8,
            )
            response.raise_for_status()
            file_path = response.json()['result']['file_path']
            image = requests.get(
                f"https://api.telegram.org/file/bot{token}/{file_path}",
                timeout=12,
            )
            image.raise_for_status()
        except (requests.RequestException, KeyError, ValueError):
            logger.exception('Could not retrieve Telegram product image')
            abort(502)
        return app.response_class(
            image.content,
            content_type=image.headers.get('Content-Type', 'application/octet-stream'),
            headers={'Cache-Control': 'public, max-age=3600'},
        )

    @app.get('/uploads/<path:filename>')
    def uploaded_image(filename):
        return send_from_directory(UPLOAD_ROOT, filename)

    @app.post('/api/orders')
    def create_order():
        payload = request.get_json(silent=True) or {}
        name = str(payload.get('name') or '').strip()
        phone = str(payload.get('phone') or '').strip()
        address = str(payload.get('address') or '').strip()
        city = str(payload.get('city') or '').strip()
        payment_method = str(payload.get('payment_method') or '').lower()
        items = payload.get('items')
        if not name or not phone or len(_phone_digits(phone)) < 9:
            return jsonify({'error': 'Enter a name and a valid phone number'}), 400
        if not address or not city:
            return jsonify({'error': 'Delivery address and city are required'}), 400
        if payment_method not in PAYMENT_METHODS:
            return jsonify({'error': 'Choose a supported payment method'}), 400
        if not isinstance(items, list) or not items or len(items) > 50:
            return jsonify({'error': 'Cart must contain between 1 and 50 items'}), 400

        quantities = {}
        try:
            for item in items:
                product_id = int(item['product_id'])
                quantity = int(item['quantity'])
                if product_id < 1 or quantity < 1 or quantity > 50:
                    raise ValueError
                quantities[product_id] = quantities.get(product_id, 0) + quantity
            if any(quantity > 50 for quantity in quantities.values()):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            return jsonify({'error': 'Cart contains an invalid product or quantity'}), 400

        db = get_db()
        order_number = f"HIK-{datetime.now(timezone.utc):%y%m%d}-{secrets.token_hex(8).upper()}"
        try:
            with db.get_connection() as connection:
                cursor = connection.cursor()
                lines = []
                subtotal = Decimal('0.00')
                for product_id, quantity in quantities.items():
                    cursor.execute(
                        "SELECT id, price, stock_quantity, status FROM products WHERE id = %s FOR UPDATE",
                        (product_id,),
                    )
                    product = cursor.fetchone()
                    if not product or str(product['status']).casefold() != 'in stock':
                        return jsonify({'error': 'A selected product is no longer available'}), 409
                    if int(product['stock_quantity'] or 0) < quantity:
                        return jsonify({'error': 'A selected product has insufficient stock'}), 409
                    price = Decimal(str(product['price']))
                    subtotal += price * quantity
                    lines.append((product_id, quantity, price))

                cursor.execute(
                    """
                    INSERT INTO orders (
                        order_number, total_amount, subtotal_amount, final_amount,
                        status, payment_method, shipping_address, shipping_city,
                        shipping_phone, shipping_name
                    ) VALUES (%s, %s, %s, %s, 'Pending', %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        order_number, subtotal, subtotal, subtotal, payment_method,
                        address, city, phone, name,
                    ),
                )
                order_id = cursor.fetchone()['id']
                for product_id, quantity, price in lines:
                    cursor.execute(
                        """
                        INSERT INTO order_items (
                            order_id, product_id, quantity, price_at_time, total_price
                        ) VALUES (%s, %s, %s, %s, %s)
                        """,
                        (order_id, product_id, quantity, price, price * quantity),
                    )
                    cursor.execute(
                        """
                        UPDATE products SET
                            stock_quantity = stock_quantity - %s,
                            status = CASE WHEN stock_quantity - %s <= 0
                                THEN 'Out of Stock' ELSE status END,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (quantity, quantity, product_id),
                    )
        except Exception:
            logger.exception('Could not create storefront order')
            raise

        _notify_new_order(app, order_number, name, phone, subtotal)
        return jsonify({
            'order_id': order_id,
            'order_number': order_number,
            'total': float(subtotal),
        }), 201

    @app.post('/api/orders/track')
    def track_order():
        payload = request.get_json(silent=True) or {}
        order_number = str(payload.get('order_number') or '').strip()
        phone = str(payload.get('phone') or '').strip()
        phone_value = _phone_digits(phone)
        if not order_number and not phone_value:
            return jsonify({'error': 'Enter an order number or checkout phone'}), 400
        db = get_db()
        if order_number:
            if order_number.isdecimal():
                if not phone:
                    return jsonify({'error': 'Provide the checkout phone with a numeric order ID'}), 400
                order_id = int(order_number)
                if order_id > 9223372036854775807:
                    return jsonify({'error': 'Order not found'}), 404
                result = db.execute('SELECT * FROM orders WHERE id = %s', (order_id,))
                order = result.fetchone()
            else:
                order = db.get_order_by_number(order_number)
            if order_number and phone and (
                not order
                or not hmac.compare_digest(
                    _phone_digits(order.get('shipping_phone')),
                    phone_value,
                )
            ):
                order = None
        else:
            if len(phone_value) < 9:
                return jsonify({'error': 'Enter a valid checkout phone number'}), 400
            result = db.execute(
                """
                SELECT * FROM orders
                WHERE regexp_replace(COALESCE(shipping_phone, ''), '[^0-9]', '', 'g') = %s
                ORDER BY order_date DESC LIMIT 1
                """,
                (phone_value,),
            )
            order = result.fetchone()
        if not order:
            return jsonify({'error': 'Order not found for that phone number'}), 404
        return jsonify(_json_value({
            'order_number': order.get('order_number'),
            'status': order.get('status'),
            'order_date': order.get('order_date'),
        }))

    @app.post('/api/support')
    def support_inquiry():
        payload = request.get_json(silent=True) or {}
        name = str(payload.get('name') or '').strip()
        phone = str(payload.get('phone') or '').strip()
        message = str(payload.get('message') or '').strip()
        if not name or not phone or not message or len(message) > 2000:
            return jsonify({'error': 'Name, phone and a message (up to 2000 characters) are required'}), 400
        result = get_db().execute(
            """
            INSERT INTO support_inquiries (name, phone, message)
            VALUES (%s, %s, %s) RETURNING id
            """,
            (name, phone, message),
        )
        row = result.fetchone()
        _notify_new_support_inquiry(app, name, phone, message)
        return jsonify({'id': row['id'], 'status': 'received'}), 201

    @app.post('/api/admin/session')
    def admin_session():
        payload = request.get_json(silent=True) or {}
        expected = app.config['ADMIN_WEB_TOKEN']
        supplied = str(payload.get('token') or '')
        if expected and supplied and hmac.compare_digest(supplied, expected):
            return jsonify({'authenticated': True})
        return jsonify({'error': 'Invalid admin token'}), 401

    @app.get('/api/admin/metrics')
    @admin_required
    def admin_metrics():
        result = get_db().execute(
            """
            SELECT
                (SELECT COUNT(*) FROM products WHERE LOWER(status) <> 'archived') AS total_products,
                (SELECT COUNT(*) FROM orders) AS total_orders,
                (SELECT COUNT(*) FROM orders WHERE LOWER(status) = 'pending') AS pending_orders,
                (SELECT COALESCE(SUM(final_amount), 0) FROM orders
                    WHERE LOWER(status) <> 'cancelled') AS revenue
            """
        )
        return jsonify(_json_value(dict(result.fetchone())))

    @app.get('/api/admin/products')
    @admin_required
    def admin_products():
        result = get_db().execute(
            "SELECT * FROM products WHERE LOWER(status) <> 'archived' ORDER BY created_at DESC LIMIT 500"
        )
        return jsonify([_product_payload(row) for row in result.fetchall()])

    @app.post('/api/admin/products')
    @admin_required
    def add_product():
        payload = request.get_json(silent=True) or {}
        error = _validate_product(payload)
        if error:
            return jsonify({'error': error}), 400
        product_id = get_db().create_product(payload)
        if not product_id:
            return jsonify({'error': 'Product could not be created'}), 500
        return jsonify({'id': product_id}), 201

    @app.patch('/api/admin/products/<int:product_id>')
    @admin_required
    def edit_product(product_id):
        payload = request.get_json(silent=True) or {}
        error = _validate_product(payload)
        if error:
            return jsonify({'error': error}), 400
        db = get_db()
        if not db.get_product(product_id) or not db.update_product(product_id, **payload):
            return jsonify({'error': 'Product could not be updated'}), 404
        return jsonify({'updated': True})

    @app.delete('/api/admin/products/<int:product_id>')
    @admin_required
    def remove_product(product_id):
        db = get_db()
        linked_orders = db.execute(
            'SELECT EXISTS (SELECT 1 FROM order_items WHERE product_id = %s) AS linked',
            (product_id,),
        ).fetchone()['linked']
        if linked_orders:
            if not db.update_product(product_id, status='Archived'):
                return jsonify({'error': 'Product could not be archived'}), 500
            return jsonify({'deleted': True})
        if not db.delete_product(product_id):
            return jsonify({'error': 'Product could not be deleted'}), 404
        return jsonify({'deleted': True})

    @app.post('/api/admin/uploads')
    @admin_required
    def upload_product_image():
        image = request.files.get('file')
        if image is None or image.mimetype not in ALLOWED_IMAGE_TYPES:
            return jsonify({'error': 'Choose a JPEG, PNG or WebP image'}), 400
        extension = secure_filename(image.filename or '').rsplit('.', 1)
        suffix = f".{extension[-1].lower()}" if len(extension) == 2 else ''
        if suffix not in {'.jpg', '.jpeg', '.png', '.webp'}:
            return jsonify({'error': 'Unsupported image file extension'}), 400
        matching_extensions = {
            'image/jpeg': {'.jpg', '.jpeg'},
            'image/png': {'.png'},
            'image/webp': {'.webp'},
        }
        if suffix not in matching_extensions[image.mimetype]:
            return jsonify({'error': 'Image content does not match its file type'}), 400
        signature = image.stream.read(12)
        image.stream.seek(0)
        valid_signature = (
            (image.mimetype == 'image/jpeg' and signature.startswith(b'\xff\xd8\xff'))
            or (image.mimetype == 'image/png' and signature.startswith(b'\x89PNG\r\n\x1a\n'))
            or (
                image.mimetype == 'image/webp'
                and signature.startswith(b'RIFF')
                and signature[8:12] == b'WEBP'
            )
        )
        if not valid_signature:
            return jsonify({'error': 'Image content does not match its file type'}), 400
        UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        filename = f"{secrets.token_hex(16)}{suffix}"
        image.save(UPLOAD_ROOT / filename)
        return jsonify({'url': f'/uploads/{filename}'}), 201

    @app.get('/api/admin/orders')
    @admin_required
    def admin_orders():
        orders = get_db().get_orders_by_status(limit=200)
        return jsonify(_json_value(orders))

    @app.patch('/api/admin/orders/<int:order_id>')
    @admin_required
    def change_order_status(order_id):
        payload = request.get_json(silent=True) or {}
        status = str(payload.get('status') or '').strip()
        if status not in ORDER_STATUSES:
            return jsonify({'error': 'Unsupported order status'}), 400
        if not get_db().update_order_status(order_id, status):
            return jsonify({'error': 'Order could not be updated'}), 404
        return jsonify({'updated': True})

    @app.get('/')
    @app.get('/admin')
    def storefront():
        index_file = WEB_ROOT / 'dist' / 'index.html'
        if not index_file.is_file():
            return jsonify({'error': 'Storefront build not found; run npm run build'}), 503
        return send_from_directory(index_file.parent, index_file.name)

    @app.get('/<path:asset_path>')
    def frontend_asset(asset_path):
        asset = WEB_ROOT / 'dist' / asset_path
        if asset.is_file():
            return send_from_directory(asset.parent, asset.name)
        if asset_path.startswith(('api/', 'uploads/')):
            abort(404)
        index_file = WEB_ROOT / 'dist' / 'index.html'
        if index_file.is_file():
            return send_from_directory(index_file.parent, index_file.name)
        abort(404)

    return app


def _validate_product(payload):
    if not str(payload.get('name_en') or '').strip():
        return 'English product name is required'
    if not str(payload.get('name_am') or '').strip():
        return 'Amharic product name is required'
    if not str(payload.get('category') or '').strip():
        return 'Category is required'
    try:
        price = Decimal(str(payload.get('price')))
        if not price.is_finite() or price < 0:
            return 'Price cannot be negative'
        if int(payload.get('stock_quantity', 0)) < 0:
            return 'Stock cannot be negative'
    except (ValueError, TypeError, ArithmeticError):
        return 'Enter a valid price and stock quantity'
    images = payload.get('images') or []
    if not isinstance(images, list) or len(images) > 10:
        return 'Provide up to 10 product images'
    if not images and not payload.get('image_id'):
        return 'At least one product image is required'
    return None


def _notify_new_order(app, order_number, name, phone, total):
    _notify_admins(
        app,
        f"New web order {order_number}\nCustomer: {name}\nPhone: {phone}\nTotal: {total} ETB",
        order_number,
    )


def _notify_new_support_inquiry(app, name, phone, message):
    _notify_admins(
        app,
        f"New storefront support inquiry\nCustomer: {name}\nPhone: {phone}\nMessage: {message}",
        'support inquiry',
    )


def _notify_admins(app, message, context):
    bot = app.extensions.get('hikma_bot')
    if bot is None and config.bot.TOKEN:
        try:
            from telebot import TeleBot

            bot = TeleBot(config.bot.TOKEN)
            app.extensions['hikma_bot'] = bot
        except Exception:
            logger.exception('Could not initialize Telegram order notifications')
            return
    if bot is None:
        logger.warning('Skipping Telegram notification for %s because no bot is configured', context)
        return
    for admin_id in config.bot.ADMIN_IDS:
        try:
            bot.send_message(admin_id, message)
        except Exception:
            logger.exception('Could not notify Telegram admin %s for %s', admin_id, context)


app = create_app()


if __name__ == '__main__':
    from waitress import serve

    serve(app, host='0.0.0.0', port=int(os.getenv('PORT', '8000')))
