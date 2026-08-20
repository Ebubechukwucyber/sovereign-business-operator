# Sovereign Business Operator

**AI-operated service business on Telegram — qualify, quote, collect USDC on Base, verify on-chain, deliver documents.**

[![Network](https://img.shields.io/badge/network-Base%20Mainnet-168AAD)](https://basescan.org)
[![Token](https://img.shields.io/badge/token-USDC-2A9D8F)](#payment--verification)
[![Interface](https://img.shields.io/badge/interface-Telegram-26A5E4)](https://telegram.org)
[![Status](https://img.shields.io/badge/status-mainnet%20ready-12233F)](#)

Sovereign Business Operator is a business-agnostic operating system for service studios. An owner configures niche, pricing, wallet, and brand once. Clients complete intake in Telegram, receive a professional proposal, pay in **USDC on Base**, and get receipts and invoices after the chain confirms the transfer.

> **Payment network:** Base mainnet (chain id `8453`) · Official Circle USDC  
> **Live demo:** Telegram bot (see repository description / landing page for the current link)

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
11. [Deploy for demo](#deploy-for-demo)
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
| Slow quoting | AI-assisted proposal + PDF |
| Payment disputes | On-chain USDC verification on Base |
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
   → AI pricing & proposals (within owner min/max)
   → SQLite job store
   → PDF generator (proposal / invoice / receipt)
   → payment_verifier.py
   → Base RPC (USDC Transfer events)
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

- Start project / continue intake (natural prompts)  
- **AI-assisted pricing** within owner min/max bounds  
- **Scoped proposals** (what’s needed vs out of scope)  
- Professional proposal PDF  
- **Payment** available as soon as the quote lands  
- One-tap copy wallet address  
- TX hash submission with validation  
- On-chain verification feedback  
- Receipt + invoice after confirmation  

### Owner

- Business profile (name, niche, services, tone)  
- Min / max price and default delivery window  
- USDC wallet on **Base mainnet**  
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
| AI | Configurable LLM endpoint (pricing + proposals) |
| Chain | **Base mainnet** (chain id 8453) |
| Token | USDC (6 decimals) — Circle native on Base |
| RPC | JSON-RPC over HTTPS |

---

## Repository structure

```text
sovereign-business-operator/
├── main.py                 # Bot wiring & handlers
├── config.py               # Env-driven configuration (Base mainnet defaults)
├── db.py                   # SQLite schema + job/payment APIs
├── ai.py                   # AI price estimate + proposal generation
├── pricing.py              # Deterministic pricing fallback
├── pdf_generator.py        # Proposal + invoice PDFs
├── payment_receipt.py      # Receipt PDF
├── payment_verifier.py     # Canonical on-chain verifier
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
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate

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
| `LLM_API_KEY` | Yes | Provider key for AI pricing & proposals |
| `LLM_BASE_URL` | Yes | OpenAI-compatible base URL |
| `LLM_MODEL` | Yes | Model name |
| `BASE_CHAIN_ID` | No | Default `8453` (Base mainnet) |
| `BASE_RPC_URL` | No | Default `https://mainnet.base.org` |
| `BASE_USDC_CONTRACT` | No | Default Circle USDC on Base: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| `BASE_CONFIRMATIONS` | No | Default `3` |
| `BASE_EXPLORER_URL` | No | Default `https://basescan.org` |
| `PAYMENT_NETWORK` | No | Client-facing label (default `Base`) |
| `PAYMENT_TOKEN` | No | Default `USDC` |
| `PAYMENT_MAX_AGE_SECONDS` | No | Max age of a TX (anti-replay) |
| `DATABASE_PATH` | No | SQLite path |


**Owner wallet:** configure a **Base mainnet** address that can receive USDC (bot → Payments). This is separate from the USDC token contract.

---

## Payment & verification

**Canonical module:** `payment_verifier.py`

Verification steps:

1. TX hash format  
2. Transaction exists and succeeded  
3. Correct network / chain id (`8453` on mainnet)  
4. ERC-20 `Transfer` to the configured studio wallet  
5. Token contract is USDC on Base  
6. Amount ≥ quoted amount  
7. Enough confirmations  
8. Time window (rejects ancient recycled transfers)  
9. Replay guard (hash already **confirmed** on another job → reject)

After success:

- Job → `PAID` / payment → `CONFIRMED`  
- Receipt PDF → client + owner  
- Invoice PDF → client + owner  

**Warning:** mainnet transfers are real value. Test with small amounts first.

---

## Owner operations

In Telegram (as `OWNER_TELEGRAM_ID`):

1. `/setup` — business name, niche, services, prices  
2. **Payments** — USDC receive wallet on Base  
3. Optional signature details for PDFs  
4. **Orders** → select a job → Mark Delivered / Close / resend docs  

---

## Deploy for demo

Keep the bot online without your laptop:

1. Push this repo to GitHub  
2. Create a **Background Worker** (Railway / Render / VPS)  
3. Start command: `python main.py`  
4. Add every env key in the host secrets UI  
5. Deploy  

`Procfile`:

```text
worker: python main.py
```

**Important:** only one process may poll the same bot token (stop local `python main.py` when cloud is running).

---

## Landing page

Static demo page: [`web/index.html`](web/index.html)

1. Replace `YOUR_BOT_USERNAME` with your bot  
2. Host with Netlify Drop, GitHub Pages, or Vercel  

---

## Security model

| Control | Behavior |
|---------|----------|
| Amount trust | Chain Transfer event only |
| Recipient | Must match owner-configured wallet |
| Token | Must match configured USDC contract on Base |
| Freshness | Rejects TX outside payment window |
| Replay | Confirmed hash cannot pay a second job |
| Secrets | Bot token / LLM keys only in env, never in repo |
| AI pricing | Suggestions clamped to owner min/max |

---

## Roadmap

- [x] Intake, pricing, proposal PDF  
- [x] AI pricing within owner bounds + scoped proposals  
- [x] Payment instructions + TX submission  
- [x] On-chain USDC verification (Base mainnet)  
- [x] Receipt + invoice generation  
- [x] Owner deliver / close / resend docs  
- [ ] Multi-owner hosted SaaS  
- [ ] Deliverable file upload from owner → client  

---

## Contributing

1. Keep payment verification in **`payment_verifier.py` only**  
2. Prefer env defaults over hard-coded secrets  
3. Never let the LLM confirm payment — only the chain verifier  
4. Document new job or payment states in `PROJECT_CONTEXT.md`  

---

## License

Specify your license of choice (MIT recommended for visibility).

---

**Sovereign Business Operator** — one Telegram bot, a full service-business loop, verifiable USDC settlement on Base.
