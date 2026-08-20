# Sovereign Business Operator

**AI-operated service business on Telegram — qualify, quote, collect USDC, verify on-chain, deliver documents.**

[![Network](https://img.shields.io/badge/network-Base%20Sepolia-168AAD)](https://sepolia.basescan.org)
[![Token](https://img.shields.io/badge/token-USDC-2A9D8F)](#payment--verification)
[![Interface](https://img.shields.io/badge/interface-Telegram-26A5E4)](https://telegram.org)
[![Status](https://img.shields.io/badge/status-hackathon%20demo-12233F)](#)

Sovereign Business Operator is a business-agnostic operating system for service studios. An owner configures niche, pricing, wallet, and brand once. Clients complete intake in Telegram, receive a professional proposal, pay in USDC, and get receipts and invoices after the chain confirms the transfer.

> **Demo network:** Base Sepolia (testnet). Mainnet is intentionally deferred until end-to-end behavior is stable.

---

## Table of contents

1. [Why this exists](#why-this-exists)
2. [System architecture](#system-architecture)
3. [Product lifecycle](#product-lifecycle)
4. [Features](#features)
5. [Tech stack](#tech-stack)
6. [Repository structure](#repository-structure)
7. [Quick start](#quick-start)
8. [Configuration](#configuration)
9. [Payment & verification](#payment--verification)
10. [Owner operations](#owner-operations)
11. [Deploy for demo (no laptop required)](#deploy-for-demo-no-laptop-required)
12. [Landing page](#landing-page)
13. [Security model](#security-model)
14. [Roadmap](#roadmap)
15. [Contributing](#contributing)

---

## Why this exists

Most freelancers and small studios still run sales in messy chat threads:

- No structured intake  
- Quotes live in screenshots  
- Payments are trusted by screenshot  
- Invoices are rebuilt by hand  

Sovereign collapses that into one Telegram operator:

| Pain | What Sovereign does |
|------|---------------------|
| Unqualified leads | Structured intake + job record |
| Slow quoting | AI / template proposal + PDF |
| Payment disputes | On-chain USDC verification |
| Admin overhead | Receipt + invoice auto-issued |
| Context switching | Owner controls the business from Telegram |

---

## System architecture

![System architecture](docs/architecture.png)

**Request path**

```text
Client (Telegram)
   → Telegram Bot API
   → handlers/client.py | handlers/owner.py
   → AI pricing & proposals
   → SQLite job store
   → PDF generator (proposal / invoice / receipt)
   → payment_verifier.py
   → Base Sepolia RPC (USDC Transfer events)
```

**Owner configuration** (wallet, pricing rules, signature) drives behavior without code changes per business.

---

## Product lifecycle

```text
NEW
  → QUALIFYING        intake answers saved
  → QUOTED            proposal PDF issued
  → AWAITING_PAYMENT  payment instructions shown
  → TX_SUBMITTED      client pastes hash
  → VERIFYING         on-chain checks
  → PAID / CONFIRMED  receipt + invoice sent
  → DELIVERED         owner marks complete
  → CLOSED            archive
```

Payment statuses are separate from job status (`UNPAID` → `AWAITING_PAYMENT` → `TX_SUBMITTED` → `VERIFYING` → `CONFIRMED` / `REJECTED`).

---

## Features

### Client

- Start project / continue intake  
- AI-assisted proposal generation  
- Professional proposal PDF  
- **Payment** available as soon as the quote lands  
- TX hash submission with validation  
- On-chain verification feedback  
- Receipt + invoice after confirmation  

### Owner

- Business profile (name, niche, services, tone)  
- Min / max price and default delivery window  
- USDC wallet configuration  
- Signature name / title for documents  
- Order list with pause / resume  
- **Mark delivered** (notifies client)  
- Close order  
- Re-send receipt / invoice  

### Trust layer

- Never trusts client-reported amount  
- Validates recipient wallet, USDC contract, success receipt  
- Confirmation depth check  
- Rejects stale transactions (time window)  
- Rejects confirmed-hash reuse across jobs  

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Interface | Telegram Bot API (`python-telegram-bot`) |
| Language | Python 3.11+ |
| Storage | SQLite |
| Documents | ReportLab PDFs |
| AI | Configurable LLM endpoint |
| Chain | Base Sepolia |
| Token | USDC (6 decimals) |
| RPC | JSON-RPC over HTTPS |

No heavy web frontend required for the operator itself. A static landing page is optional for demos.

---

## Repository structure

```text
sovereign-business-operator/
├── main.py                 # Bot wiring & handlers
├── config.py               # Env-driven configuration
├── db.py                   # SQLite schema + job/payment APIs
├── ai.py                   # Proposal generation
├── pricing.py              # Pricing engine
├── pdf_generator.py        # Proposal + invoice PDFs
├── payment_receipt.py      # Receipt PDF
├── payment_verifier.py     # Canonical on-chain verifier (use this)
├── handlers/
│   ├── client.py           # Client intake, quote, pay
│   └── owner.py            # Owner settings & order ops
├── web/
│   └── index.html          # Demo landing page
├── docs/
│   └── architecture.png    # Architecture diagram
├── Procfile                # Worker process for PaaS deploy
└── requirements.txt
```

---

## Quick start

### 1. Create a bot

Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.

### 2. Install

```bash
git clone https://github.com/Ebubechukwucyber/sovereign-business-operator.git
cd sovereign-business-operator

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment

Create `.env` in the project root (see [Configuration](#configuration)).

### 4. Run

```bash
python main.py
```

Open the bot in Telegram and send `/start`.

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | From BotFather |
| `OWNER_TELEGRAM_ID` | Yes | Numeric Telegram user id of the studio owner |
| `LLM_API_KEY` | Yes* | Provider key for proposal generation |
| `LLM_BASE_URL` | Yes* | OpenAI-compatible base URL |
| `LLM_MODEL` | Yes* | Model name |
| `BASE_SEPOLIA_RPC_URL` | No | Defaults to a public Base Sepolia RPC |
| `BASE_SEPOLIA_USDC_CONTRACT` | No | Defaults to official Base Sepolia USDC |
| `BASE_SEPOLIA_CONFIRMATIONS` | No | Minimum confirmations before accept |
| `PAYMENT_MAX_AGE_SECONDS` | No | Max age of a TX relative to “now” (anti-replay) |
| `DATABASE_PATH` | No | SQLite path |

\*Template proposals still work if the LLM is unavailable; quality is higher with a live model.

---

## Payment & verification

**Canonical module:** `payment_verifier.py`  
(`handlers/client.py` imports `verify_usdc_payment` from this file.)

Verification steps:

1. TX hash format  
2. Transaction exists and succeeded  
3. Correct network / chain id  
4. ERC-20 `Transfer` to the configured studio wallet  
5. Token contract is USDC  
6. Amount ≥ quoted amount  
7. Enough confirmations  
8. Time window (rejects ancient recycled transfers)  
9. Replay guard (hash already **confirmed** on another job → reject)

After success:

- Job → `PAID` / payment → `CONFIRMED`  
- Receipt PDF → client + owner  
- Invoice PDF → client + owner  
- Paths stored under `data/receipts/` and `data/invoices/`  

---

## Owner operations

In Telegram (as `OWNER_TELEGRAM_ID`):

1. Complete business setup (name, niche, services, prices)  
2. Set USDC receive wallet  
3. Optional signature details for PDFs  
4. Open **Orders** → select a job  

Paid jobs expose:

- **Mark Delivered** — status `DELIVERED`, client notified  
- **Close Order** — status `CLOSED`  
- **Receipt / Invoice** — re-send stored PDFs  

---

## Deploy for demo (no laptop required)

Keep the bot online for judges without running `python main.py` on your machine.

### Railway / Render (worker)

1. Push this repo to GitHub  
2. Create a **Background Worker** (not a static-only service)  
3. Start command: `python main.py`  
4. Add every `.env` key in the host secrets UI  
5. Deploy  

`Procfile` is included:

```text
worker: python main.py
```

### VPS

```bash
git pull
source .venv/bin/activate
pip install -r requirements.txt
# systemd or pm2 recommended so the process restarts on reboot
python main.py
```

---

## Landing page

Static demo page: [`web/index.html`](web/index.html)

1. Replace `YOUR_BOT_USERNAME` with your bot  
2. Host with Netlify Drop, GitHub Pages, or Vercel  

Judges get one URL: **landing → Open demo bot → full flow**.

---

## Security model

| Control | Behavior |
|---------|----------|
| Amount trust | Chain balance of the Transfer event only |
| Recipient | Must match owner-configured wallet |
| Token | Must match configured USDC contract |
| Freshness | Rejects TX outside payment window |
| Replay | Confirmed hash cannot pay a second job |
| Secrets | Bot token / LLM keys only in env, never in repo |

This is **testnet** infrastructure. Treat mainnet as a deliberate promotion after soak testing.

---

## Roadmap

- [x] Intake, pricing, proposal PDF  
- [x] Payment instructions + TX submission  
- [x] On-chain USDC verification  
- [x] Receipt + invoice generation  
- [x] Owner deliver / close / resend docs  
- [ ] Multi-owner hosted SaaS  
- [ ] Base mainnet profile (config switch)  
- [ ] Deliverable file upload from owner → client  

---

## Contributing

1. Keep payment verification in **`payment_verifier.py` only**  
2. Prefer env defaults over hard-coded secrets  
3. Test on Base Sepolia before any mainnet change  
4. Document new job or payment states in `PROJECT_CONTEXT.md`  

---

## License

Specify your license of choice (MIT recommended for hackathon visibility).

---

**Sovereign Business Operator** — one Telegram bot, a full service-business loop, verifiable settlement on Base.
