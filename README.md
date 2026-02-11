# “Buy from Reza” — Food Code Marketplace

This repository contains the **“Buy from Reza”** Telegram bot implemented in **Python 3** using **aiogram v3**.
The philosophy of the bot is simple: *“You can buy food from Reza.”* Users can sell their food codes or purchase codes from others, and the entire flow — registration, reservation, payment, admin approval, and rating — happens inside Telegram.

---

## Features

* Fast user registration via Telegram ID, optional email, and a mock OTP confirmation.
* Management of food-code sale listings with **Fernet encryption** and secure masked display.
* Reservation, payment receipt upload, admin review queue, and automatic code delivery after approval.
* Limits on concurrent reservations, daily active listings, and shortcuts for seller accounts.
* Two-way rating, dispute management, and daily reporting.
* Full in-Telegram admin panel for payment approval, settings management, ban/unban, and statistics.
* APScheduler-based timers for reservation expiry, listing expiration, and near-expiry warnings.

---

## Requirements

* Python 3.11+
* SQLite (default) or any SQLAlchemy-compatible database (configurable)
* Telegram account and bot token from [@BotFather](https://t.me/BotFather)

---

## Quick Start (Polling)

1. Clone the repository and enter the directory.

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create `.env` based on `.env.example`.
   To generate a Fernet key:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Put the output into the `FERNET_KEY` variable.

5. Run the application:

   ```bash
   python -m az_reza_bekhareh_bot.app
   ```

The bot will start in polling mode and become operational.

---

## Webhook Setup with FastAPI (Optional)

1. Set `WEBHOOK_URL` in `.env` to your public HTTPS address.

2. Inside your Python app use `create_fastapi_app` and run with uvicorn:

   ```python
   from az_reza_bekhareh_bot.app import build_dispatcher, create_fastapi_app
   from aiogram import Bot
   from aiogram.enums import ParseMode
   from az_reza_bekhareh_bot.config import settings

   bot = Bot(token=settings.bot_token, parse_mode=ParseMode.HTML)
   dp = build_dispatcher()
   app = create_fastapi_app(bot, dp)
   ```

   Then run:

   ```bash
   uvicorn my_module:app --host 0.0.0.0 --port 8080
   ```

3. If necessary, register the `/webhook` path via BotFather.

---

## Architecture & Modules

```
az_reza_bekhareh_bot/
├─ app.py                # entry point, builds Dispatcher & Scheduler, starts Polling/Webhook
├─ config.py             # settings management via Pydantic + ENV
├─ crypto.py             # Fernet encryption for food codes
├─ db.py                 # async SQLite connection & session manager
├─ models.py             # SQLAlchemy models and indexes
├─ middlewares/
│  └─ throttling.py      # user rate limiting
├─ keyboards/            # Inline and Reply keyboards
├─ handlers/             # command handlers and FSM flows
├─ services/             # business logic: reservation, payment, reporting, etc.
├─ scheduler/            # scheduled jobs for expiration & alerts
├─ messages/fa.py        # branded Persian messages
├─ tests/                # unit & flow tests using pytest-asyncio
├─ requirements.txt
└─ .env.example
```

---

## Roles

* **Regular user**: register, sell, buy, reserve, upload receipt, rate, open disputes.
* **Seller account (`seller_account`)**: similar to regular users but specially tracked in reports.
* **Admin**: access to `/admin` and management commands (`/ban`, `/unban`, `/set_ttl`, ...).

---

## Rules & Privacy

* Transferring codes may violate university regulations; responsibility lies entirely with the user.
* Stored data includes Telegram ID, name, university, optional email, listings, and transactions.
* Food codes are encrypted with Fernet and shown to buyers **only after admin approval**.
* The system never logs into any university portal and never asks for passwords or cookies.

---

## Tests

Run:

```bash
pytest
```

Test coverage includes:

* correct encryption and prevention of parallel reservations
* full flow: sell → reserve → pay → approve → rate
* reservation expiry and rejected payment scenarios
* lower-level services like statistics, disputes, and limits

---

## Scalability & Multiple Seller Accounts

* The `users` model includes `is_seller_account` so multiple sellers can be managed without hardcoding.
* Daily reports in `report_service` provide per-seller sales; external monitoring can be attached.
* Migrating to PostgreSQL or others only requires changing `DATABASE_URL`; SQLAlchemy handles the rest.
* The scheduler is independent from polling and can run on separate workers.

---

## Run Commands

* Normal: `python -m az_reza_bekhareh_bot.app`
* Webhook: `uvicorn your_module:app --host 0.0.0.0 --port 8080`

---

## License

This project is intended for educational purposes. Responsibility for real-world usage lies with the user.

