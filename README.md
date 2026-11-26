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

	`BOT_TOKEN`, `ADMIN_IDS`, `POSTGRES_DB`, `POSTGRES_USER`,
	`POSTGRES_PASSWORD`, and `DATABASE_URL`. Set `ADMIN_USERNAME` to enable
	the admin contact button; production deployments also require `SECRET_KEY`.

Keep the PostgreSQL credentials in `DATABASE_URL` consistent with the three
`POSTGRES_*` values. Use a URL-safe password (letters, numbers, `-`, `_`) so
Docker Compose can safely build the container connection URL. The example
`DATABASE_URL` targets a PostgreSQL server running on the host at port 5433;
Docker Compose overrides it to connect to its `postgres` service.

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

Start the bot and PostgreSQL together with:

	docker compose up --build

The PostgreSQL data is persisted in the `postgres_data` volume. Back it up
before applying schema changes to an existing deployment.

Testing

Run the test suite with:

	pytest -q
