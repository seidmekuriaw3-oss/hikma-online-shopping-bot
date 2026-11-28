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

Start the Telegram bot, web storefront, and PostgreSQL together with:

	docker compose up --build

The storefront is available on port `8000`; its protected dashboard is at
`/admin`. Set a separate, strong `ADMIN_WEB_TOKEN` in `.env` before exposing
the dashboard. Product photos uploaded in the dashboard persist in the
`web_uploads` volume, and PostgreSQL data persists in `postgres_data`. Back up
both volumes before applying schema changes or replacing a deployment.

Web storefront development

The React/Vite storefront lives in `web/`; Flask serves its production build
and exposes the REST API while continuing to use the existing PostgreSQL
schema and Telegram bot. For local frontend development, start the bot/database
or web service, then run:

	cd web
	npm install
	npm run dev

The Vite server proxies `/api` and `/uploads` to `http://localhost:8000`.
Build and run frontend unit tests with:

	cd web
	npm run build
	npm test

The storefront uses `ADMIN_USERNAME` for its Telegram support link. Configure
it in `.env` to enable a direct link to the store owner. Customers can track
an order with its number/ID or the phone number used at checkout.
Set `WEB_APP_URL` to the public HTTPS storefront URL to show a Telegram
Mini App button in the bot's welcome keyboard.

For Railway, deploy the repository using the Dockerfile and set the service
start command to `python web_storefront.py` for the storefront service. Set
`DATABASE_URL`, `ADMIN_WEB_TOKEN`, `BOT_TOKEN`, `ADMIN_IDS`, and `ADMIN_USERNAME`
as Railway variables; run the Telegram bot as a separate service using the
same image with start command `python main.py`. Attach persistent storage at
`/app/web/uploads` for product photos.

Testing

Run the test suite with:

	pytest -q
