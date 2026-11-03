# Product Requirements Document
# RPi Door Access RFID System

**Version:** 1.0  
**Date:** 2026-04-17  
**Status:** Production  

---

## 1. Overview

**Product name:** RPi Door Access RFID System  
**Deployment:** Parador Km1151, Uspallata, Mendoza — YPF Full fuel station  

This system controls physical access to truck-stop shower facilities (duchas) via RFID card validation. A Raspberry Pi serves as both the application server and database host. Staff at the front desk manage clients, companies, and RFID cards through a browser-based admin panel served locally on port 8000. Truckers receive a pre-loaded RFID card (ficha) and swipe it at the shower door; the system validates the card in real time, actuates a relay to unlock the door, deducts one credit, and logs the event. All hardware interaction — green/red LEDs, buzzer, and door relay — is driven by GPIO. A USB RFID reader at the desk allows staff to scan cards without leaving the admin panel.

---

## 2. Problem Statement

Parador Km1151 operates paid shower facilities for truckers passing through Uspallata. Prior to this system, access control was entirely manual: staff tracked usage on paper or by memory, with no reliable way to prevent unauthorized re-entry, audit usage, or manage prepaid access. Cards issued to clients had no enforced expiry or credit limit, and there was no central record of who accessed the facility or when.

The specific operational problems this system solves:

- No automated enforcement of prepaid access limits (credits).
- No expiry mechanism to prevent use of stale or revoked cards.
- No tamper-evident audit trail for dispute resolution.
- Manual card recovery was ad-hoc; cards left behind by clients had no structured re-issuance workflow.
- Staff had no real-time visibility into access events occurring at the door.

---

## 3. Goals and Non-Goals

### Goals

- Enforce RFID-based access control at the shower door: grant or deny entry based on card validity, status, expiry, and credit balance.
- Provide a web-based admin panel for staff to manage companies, clients, and RFID cards without technical knowledge.
- Support card scanning via USB RFID reader at the desk for fast card assignment.
- Log all access events permanently with timestamp, card ID, event type, and deny reason.
- Broadcast real-time access events to the admin panel via SSE.
- Provide a structured workflow for recovering and blanking abandoned cards.
- Run fully on-device (Raspberry Pi) with no external dependencies or cloud connectivity.
- Support development and testing on x86 hardware without requiring physical GPIO or RFID hardware.

### Non-Goals

- Payment processing. Transactions between staff and truckers are handled outside the system.
- Multi-user admin panel. A single operator account is sufficient for the deployment context.
- Cloud synchronization or remote monitoring (deferred to future versions).
- Multi-door or multi-zone access control.
- Mobile application.
- Card duplication detection or anti-passback logic.

---

## 4. Users and Roles

| Role | Description | Primary Interface |
|---|---|---|
| **Admin (Operador Full)** | Front-desk staff member. Creates and manages companies, clients, and cards. Hands out and recovers cards. Monitors live access events. | Admin panel at `http://<pi-ip>:8000` |
| **End User (Trucker)** | Presents an RFID card at the shower door. Has no interaction with the software directly. | Physical door reader (MFRC522 via SPI) |
| **System (RPi Daemon)** | The async polling loop running on the Raspberry Pi. Reads cards, validates them against the database, controls hardware outputs, and publishes events. | Internal — `rfid_polling_task` in `main.py` |

Authentication is single-user: one admin account configured via `SUPER_USER` and `SUPER_PASSWORD` environment variables. There is no self-registration or password reset flow.

---

## 5. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Web framework | FastAPI | 0.136.0 |
| ASGI server | Uvicorn | 0.44.0 |
| ORM | SQLAlchemy | 2.0.49 |
| Database | SQLite | (bundled) |
| Template engine | Jinja2 | 3.1.6 |
| Frontend reactivity | HTMX | 2.0 |
| Frontend interactivity | Alpine.js | latest (CDN) |
| CSS framework | Tailwind CSS | (via CDN/PostCSS) |
| Auth | JWT (HS256) via python-jose | 3.5.0 |
| Password hashing | passlib + bcrypt | 1.7.4 |
| Settings | pydantic-settings | 2.13.1 |
| GPIO control | gpiozero | 2.0.1 |
| RFID reader (SPI) | mfrc522 | 0.0.7 |
| SPI interface | spidev | 3.8 |
| Test framework | pytest + pytest-asyncio | 9.0.3 / 1.3.0 |
| HTTP test client | httpx | 0.28.1 |
| Runtime | Python | 3.x |
| Hardware | Raspberry Pi (any model with GPIO + SPI) | — |

---

## 6. Architecture Overview

The system uses a three-layer architecture:

```
┌─────────────────────────────────────────┐
│              API Layer                  │
│  FastAPI routers (auth, endpoints)      │
│  Jinja2 templates + HTMX fragments      │
│  SSE event stream (/sse/events)         │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│             Domain Layer                │
│  process_swipe() — validation logic     │
│  grant_access() / deny_access()         │
│  log_access() — writes AccessLogModel  │
│  broadcaster.publish() — SSE events     │
└───────────────┬─────────────────────────┘
                │
┌───────────────▼─────────────────────────┐
│          Infrastructure Layer           │
│  ┌──────────────┐  ┌───────────────┐   │
│  │  Database    │  │  Hardware     │   │
│  │  SQLite via  │  │  HardwareFactory  │
│  │  SQLAlchemy  │  │  (strategy)   │   │
│  └──────────────┘  └───────────────┘   │
└─────────────────────────────────────────┘
```

**Hardware strategy pattern:** At boot, `build_factory()` in `app/infrastructure/hardware/factory.py` detects the platform via `/proc/device-tree/model`. On a Raspberry Pi, it returns `GpioHardwareFactory`, which instantiates real `gpiozero` and `mfrc522` drivers. On any other platform (x86, CI), it returns `MockHardwareFactory`, which logs to stdout with no hardware side effects. All domain logic depends only on abstract interfaces (`LedIndicator`, `Buzzer`, `DoorRelay`, `RFIDReader`) defined in `interfaces.py`, making the switch transparent to the domain layer.

**RFID polling:** An `asyncio` background task (`rfid_polling_task`) polls the MFRC522 reader every 500ms via `reader.read_card()`. On card detection, it calls `process_swipe()` synchronously within a database session. GPIO operations (relay trigger, LED on/off, buzzer) are blocking but bounded in duration (≤5 seconds for door open). On error, the loop backs off to 2 seconds before retrying.

**Real-time events:** An in-process `broadcaster` object (async pub/sub) collects events from both the RFID polling loop and admin panel actions. The `/sse/events` endpoint streams these as Server-Sent Events to all authenticated browser clients. Events are rendered as HTML fragments via `_event_item.html` and injected into the dashboard sidebar by HTMX.

---

## 7. Data Model

### 7.1 Company (`companies`)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `name` | VARCHAR | NOT NULL |

The first record in this table is always "Particulares" (individual clients with no company affiliation).

### 7.2 User (`users`)

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `first_name` | VARCHAR | NOT NULL |
| `last_name` | VARCHAR | NOT NULL |
| `email` | VARCHAR | nullable |
| `company_id` | INTEGER | FK → `companies.id`, nullable |

### 7.3 Account (`accounts`)

The term "account" maps 1:1 to a physical RFID card or token. The card's hardware UID is the primary key.

| Column | Type | Constraints |
|---|---|---|
| `account_id` | VARCHAR | PK (RFID card UID) |
| `status` | VARCHAR | `"active"` or `"inactive"`, default `"active"` |
| `expiration_date` | DATETIME | NOT NULL (UTC) |
| `credits` | INTEGER | default 0 |
| `user_id` | INTEGER | FK → `users.id`, nullable |

A card with `user_id = NULL` is unassigned. Credits are consumed one per door open. When `user_id` is cleared by the "Blanquear" operation, the card becomes available for re-issue.

### 7.4 AccessLog (`access_logs`)

Immutable. Records are never deleted.

| Column | Type | Constraints |
|---|---|---|
| `id` | INTEGER | PK, autoincrement |
| `timestamp` | DATETIME | NOT NULL (UTC, set at insert) |
| `account_id` | VARCHAR | NOT NULL (no FK — preserves logs for deleted cards) |
| `event_type` | VARCHAR | `"grant"` or `"deny"` |
| `reason` | VARCHAR | nullable — populated on deny only |

---

## 8. Core Features

### 8.1 RFID Access Control

**Hardware polling loop:**  
Runs as an `asyncio` background task from application startup. Polls the MFRC522 SPI reader every 500ms. Errors in the loop are caught, logged to stdout, and the loop resumes after a 2-second backoff.

**Validation logic (`process_swipe`):**  
On card detection, the following checks run in order:

1. Card UID lookup in `accounts` table. If not found → deny, reason: `"Not Found"`.
2. `status == "active"` check. If inactive → deny, reason: `"Invalid Status"`.
3. Expiry check (`expiration_date >= utcnow()`). If expired → deny, reason: `"Expired"`.
4. Credits check (`credits > 0`). If zero → deny, reason: `"Out of Credits"`.
5. All checks pass → grant access.

**Grant path:**  
Buzzer beeps once (200ms). Green LED turns on. Door relay activates for 5 seconds (`active_high=False` — standard active-low relay module). Green LED turns off. One credit is deducted. Event logged as `"grant"`. SSE event published.

**Deny path:**  
- Reason `"Out of Credits"`: buzzer beeps 3 times (200ms each).
- All other deny reasons: buzzer beeps once (500ms).
- Red LED turns on for 1 second, then off. Event logged as `"deny"` with reason. SSE event published.

**Verbose mode:**  
Enabled via `VERBOSE=true` in `.env` or `--verbose` CLI flag. Prints detailed card lookup and result info to stdout. Idle polling prints a status line every 10 seconds (every 20 ticks × 500ms).

### 8.2 Admin Panel

**Authentication:**  
- Web UI login at `/login` with form POST to `/ui/login`.
- On success, a JWT (HS256, 60-minute expiry) is set as an HttpOnly, SameSite=Lax cookie (`access_token`).
- API endpoints use Bearer token auth via OAuth2 password flow at `/api/login`.
- Logout at `/ui/logout` clears the cookie and redirects to `/login`.
- Credentials are compared against `SUPER_USER` / `SUPER_PASSWORD` environment variables. Passwords are not stored in the database.

**Dashboard (`/`):**  
- Table of all accounts: card ID, assigned user, status, expiry date, credit balance.
- Per-row recharge button (HTMX inline form, no page reload).
- "Add Card" button opens a modal form (`_create_account_modal.html`).
- Live events sidebar: last ~20 events rendered as HTML fragments, updated via SSE.

**Company management:**  
- Create company (name only). "Particulares" is always company ID 1.

**User/client management:**  
- Create user: first name, last name, optional email, company (dropdown).
- Users are associated with one company.

**Card management:**  
- Add card to a user: scan via USB RFID reader (auto-fills card UID into form field) or type manually.
- Default on new card: 10 credits, expiry = now + 24 hours. Both fields are editable before submission.
- View all cards for a user.
- Edit card: status, expiry, credits.
- Delete card.
- Recharge credits: add an integer amount to existing balance.

**HTMX integration:**  
Account row creates and recharge responses return partial HTML fragments (`_account_row.html`) when the request carries an `HX-Request` header. Full-page responses are fallbacks for non-HTMX clients.

### 8.3 Card Recovery ("Recuperar tarjeta/llave")

A dedicated tab in the admin panel for processing cards left behind by clients after shower use.

**Workflow:**
1. Staff collects orphaned cards from the designated container.
2. Opens the "Recuperar tarjeta/llave" tab.
3. Scans cards one by one using the USB RFID reader. Each scan registers the card UID in a pending list.
4. After all cards are scanned, clicks "Blanquear."
5. The system sets `user_id = NULL` on every scanned account, dissociating the card from any previous user.
6. Cards are now unassigned and available for re-issue to new clients.

The blanquear operation does not delete cards from the database and does not affect access logs. It only clears the `user_id` foreign key.

### 8.4 Real-Time Events (SSE)

**Endpoint:** `GET /sse/events` (requires auth cookie).

The in-process `broadcaster` is an async pub/sub queue. Publishers are:
- `process_swipe()` domain function — publishes on every card read (grant or deny).
- Admin panel handlers — publish on `account_created` and `account_recharged`.

The stream also emits periodic `ping` keepalives to prevent proxy/browser timeout.

Each event is rendered server-side into an HTML fragment using `_event_item.html` and pushed as an SSE `data:` payload. The frontend (HTMX + Alpine.js) prepends each fragment to the events sidebar and trims the list to the last ~20 items.

Event types carried by the stream:

| Event name | Trigger |
|---|---|
| `swipe` | Card read (grant or deny) |
| `account_created` | New card added via admin panel |
| `account_recharged` | Credits added to a card |
| `ping` | Periodic keepalive |
| `ready` | Sent once on new subscriber connection |

### 8.5 Audit Log

All access events are written to `access_logs` at the time of the swipe, regardless of grant or deny outcome. Records are never updated or deleted. The log includes timestamp (UTC), card UID, event type, and deny reason where applicable.

The `account_id` column in `access_logs` is a plain string (no foreign key), ensuring that logs survive card deletion without orphan errors.

The admin panel displays recent events in the live sidebar. A full log view is available to staff for audit purposes.

### 8.6 Help Page (`/help`)

A static HTML page served at `/help` containing the full operator manual. Covers:
- How to create a new client and assign a card.
- How to recharge credits.
- How to interpret LED and buzzer signals.
- How to use the card recovery ("Recuperar tarjeta/llave") workflow.
- Explanation of deny reasons.

The page requires no authentication — it is intended to be accessible from any device on the local network without login friction.

---

## 9. User Stories

### 9.1 Happy Path — Trucker with known company

1. A trucker arrives at Parador Km1151 and requests shower access.
2. The operador opens the admin panel dashboard.
3. The operador finds or creates the trucker's company (e.g., a transport fleet operator).
4. The operador creates a new user record with the trucker's first and last name.
5. The operador clicks "Add Card," places a blank card on the USB RFID reader, and the card UID auto-fills in the form.
6. The operador confirms default values (10 credits, expiry = now + 24 hours) and submits.
7. The card is handed to the trucker.
8. The trucker swipes the card at the shower door.
9. The system validates: card found, status active, not expired, credits = 10.
10. Green LED turns on, buzzer beeps once, door unlocks for 5 seconds.
11. The trucker enters. Credits drop to 9. Event logged as `"grant"`.
12. The dashboard sidebar updates in real time showing the grant event.

### 9.2 "Particulares" Use Case — Individual client

1. A trucker with no company affiliation requests shower access and pays cash.
2. The operador opens the admin panel and selects the "Particulares" company (always company ID 1, always first in the list).
3. The operador creates a new user under "Particulares."
4. The operador scans a blank card via the USB RFID reader and assigns it with the default credit/expiry values.
5. The card is handed to the trucker.
6. After shower use, the trucker leaves the card in the designated container.

### 9.3 Card Recovery

1. The operador opens the "Recuperar tarjeta/llave" tab.
2. The operador scans all cards found in the container one by one. Each scan adds the UID to the pending list.
3. After scanning, the operador clicks "Blanquear."
4. All scanned cards have their `user_id` set to NULL. They are now unassigned.
5. The cards are returned to the ready-to-issue stock.

### 9.4 Credit Denial

1. A trucker's card has 0 credits remaining.
2. The trucker swipes the card at the door.
3. The system detects `credits <= 0`.
4. Red LED turns on, buzzer beeps 3 times (distinct pattern indicating out-of-credits).
5. Door does not open. Event logged as `"deny"`, reason `"Out of Credits"`.
6. The operador sees the denial in the live events sidebar.
7. The operador recharges the card (adds credits) via the dashboard.
8. The trucker swipes again — access is granted.

---

## 10. Business Rules

| Rule | Detail |
|---|---|
| Default credits on new card | 10 credits |
| Default expiry on new card | Current UTC time + 24 hours |
| Credit deduction per entry | 1 credit per successful door open |
| Credits cannot go negative | Deduction only occurs on grant; deny with 0 credits is logged but no deduction happens |
| Expiry check | `expiration_date` is compared against current UTC time at moment of swipe |
| Validation order | Not Found → Invalid Status → Expired → Out of Credits → Grant |
| Door open duration | 5 seconds (relay active-low, triggered by `GpioDoorRelay.trigger(5.0)`) |
| Green LED | On during door open (5 seconds), off when relay deactivates |
| Red LED | On for 1 second on deny, then off |
| Buzzer — grant | 1 beep, 200ms duration |
| Buzzer — deny (Out of Credits) | 3 beeps, 200ms duration each |
| Buzzer — deny (all other reasons) | 1 beep, 500ms duration |
| Deny reasons | `"Not Found"`, `"Invalid Status"`, `"Expired"`, `"Out of Credits"` |
| Access log permanence | Records in `access_logs` are never updated or deleted |
| Blanquear scope | Sets `user_id = NULL` on scanned accounts only; does not modify status, credits, or expiry |
| "Particulares" company | Always company ID 1; always the first entry in any company selection list |
| JWT expiry | 60 minutes; user must re-authenticate after expiry |
| SSE event buffer | Last ~20 events displayed in the dashboard sidebar |
| Timestamps | All timestamps stored and compared in UTC |

---

## 11. Hardware Specification

### Raspberry Pi GPIO Pin Assignments

| Signal | BCM Pin | gpiozero device | Notes |
|---|---|---|---|
| Door relay | GPIO 17 | `OutputDevice(17, active_high=False)` | Active-low relay module; `initial_value=False` (normally open) |
| Buzzer | GPIO 22 | `Buzzer(22)` | Active buzzer |
| Green LED | GPIO 27 | `LED(27)` | Indicates grant / door open |
| Red LED | GPIO 18 | `LED(18)` | Indicates deny |
| RFID RST | GPIO 25 | (mfrc522 internal) | MFRC522 reset pin, managed by `SimpleMFRC522` |

### RFID Reader — Door (SPI)

- **Module:** MFRC522
- **Interface:** SPI (hardware SPI on Raspberry Pi — MOSI, MISO, SCLK, SDA/CE0)
- **Library:** `mfrc522==0.0.7` (`SimpleMFRC522`)
- **Read method:** `read_no_block()` — non-blocking, returns `(id, text)` or `(None, None)` when no card present
- **Card UID:** Returned as integer, cast to string, stored as `account_id` VARCHAR

### RFID Reader — Desk (USB)

- A separate USB RFID reader is connected to the Raspberry Pi and appears as a HID keyboard device.
- When a card is placed on the reader, it types the card UID as a string followed by Enter into the focused input field.
- The admin panel's card assignment form has its card ID input field auto-focused, so the scan fills the field without any additional interaction.
- No software driver or special configuration is required for the USB reader.

### Relay Module

- Standard 5V relay module with active-low trigger input.
- Controls the electric door strike / bar (electromagnetic or motor-actuated, specifics are installation-dependent).
- Default state: relay open (door locked). Relay closes for 5 seconds on valid card swipe.

---

## 12. Future Considerations

These are directions that may be relevant as the deployment scales, but carry no commitment in the current version.

- **Cloud synchronization:** Periodic push of access logs to a remote server for off-site audit and reporting. Relevant if the station owner needs visibility from outside the local network.
- **Remote monitoring dashboard:** Read-only view of live events accessible over the internet, with appropriate authentication. Would require either a VPN setup or a reverse proxy with TLS.
- **Multi-location support:** A second Parador location would require either a shared central database or per-site deployments with a federation layer.
- **SMS/WhatsApp notifications:** Alert staff on unusual patterns, such as repeated deny events on a single card within a short window.
- **Credit purchase integration:** A self-service terminal or QR-code payment flow that automatically recharges a card after payment confirmation, removing the need for staff involvement for returning clients.
- **Time-based access windows:** Restricting card validity to specific hours of the day (e.g., shower facility operating hours) as a complement to expiry dates.
- **Offline resilience:** The current architecture is already fully offline-capable. Future work would focus on remote configuration sync that degrades gracefully on network loss.
