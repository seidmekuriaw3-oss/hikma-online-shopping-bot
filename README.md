# Hikma Online Shopping Bot

Hikma Online Shopping is a Telegram commerce bot for catalog browsing, orders, payments, and admin management.

Features
- Product catalog with categories and stock tracking
- Order workflow and status management
- Admin dashboard and reporting
- Payment integration hooks
- Telegram webhook and polling support

Quick start
1. Create and activate a virtual environment.
2. Install dependencies:

	pip install -r requirements.txt

3. Copy `.env.example` to `.env`, then set the required secrets and database values:

	`BOT_TOKEN`, `ADMIN_USERNAME`, `ADMIN_IDS`, `DATABASE_URL`, and `SECRET_KEY`

Set `BANK_NAME`, `BANK_ACCOUNT_HOLDER`, `BANK_ACCOUNT_NUMBER`, and
`BANK_BUSINESS_CODE` only if you want to offer bank-transfer payments.
Keep real credentials in `.env`; never commit that file.

Administrators can add products with `/add` and delete one with `/delete <id>`.

4. Start the bot:

	python main.py

Project layout
- main.py: application bootstrap
- handlers/: Telegram command and callback handlers
- models/: business entities and ORM models
- services/: external integrations
- database.py: PostgreSQL database access layer
- scheduler.py: background task scheduler
- webhook.py: Flask webhook endpoint for Telegram updates

Docker

Build and run with:

	docker build -t hikma-online-shopping-bot .
	docker run --env-file .env -p 8000:8000 hikma-online-shopping-bot

Testing

Run the test suite with:

	pytest -q
