# Sovereign Business Operator

<p align="center">
  <img src="docs/logo.png" alt="Sovereign Business Operator" width="220" />
</p>

<p align="center">
  <strong>AI business operator on Telegram</strong> — qualify, quote within owner rules, collect USDC on Base, verify on-chain, deliver documents, alert the owner.
</p>

<p align="center">
  <a href="https://basescan.org"><img src="https://img.shields.io/badge/network-Base%20Mainnet-0B1F3A" alt="Base" /></a>
  <img src="https://img.shields.io/badge/token-USDC-F4C430" alt="USDC" />
  <img src="https://img.shields.io/badge/interface-Telegram-26A5E4" alt="Telegram" />
  <img src="https://img.shields.io/badge/status-mainnet%20ready-1A8A9D" alt="Status" />
</p>

Sovereign is a **business-agnostic AI operator** for service studios. The owner configures niche, pricing bounds, wallet, signature, and notification email once. Clients complete intake in Telegram, receive a professional proposal, pay in **USDC on Base**, and get receipts and invoices after the chain confirms the transfer. The owner is notified on Telegram and optionally by email (Resend).

> **Payment network:** Base mainnet (chain id `8453`) · Circle USDC  
> **Landing page:** [`web/index.html`](web/index.html)  
> **Architecture:** [`docs/architecture.png`](docs/architecture.png)

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
11. [Deploy](#deploy)
12. [Landing page](#landing-page)
13. [Security model](#security-model)
14. [Roadmap](#roadmap)
15. [License](#license)

---

## Why this exists

| Pain | What Sovereign does |
|------|---------------------|
| Unqualified leads in chat | Structured intake + dynamic follow-ups |
| Slow / inconsistent quoting | AI pricing clamped to owner min/max |
| Screenshot “proof of payment” | On-chain USDC verification on Base |
| Manual invoices | Auto receipt + invoice PDFs |
| Context switching | Full owner control inside Telegram |

---

## System architecture

![System architecture](docs/architecture.png)

```text
Client (Telegram)
  → Bot API → handlers (client / owner)
  → AI intake, pricing, proposals (LLM)
  → SQLite jobs + payment state
  → PDF engine (proposal / invoice / receipt / order export)
  → payment_verifier.py → Base RPC (USDC Transfer)
  → Owner: Telegram + optional Resend email
```

---

## Product lifecycle

```text
NEW → QUALIFYING → QUOTED → AWAITING_PAYMENT
    → TX_SUBMITTED → VERIFYING → PAID / CONFIRMED
    → DELIVERED → CLOSED
```

Payment is confirmed **only** after successful on-chain verification.

---

## Features

### Client
- Welcome uses the owner’s **business name, niche, and services**
- **Dynamic follow-up questions** from niche + answers so far
- **Answer refinement** for professional proposals (grammar / structure)
- **AI pricing** (size, deadline tightness, market sense) inside min/max
- Scoped **proposal PDF** + payment button
- One-tap **copyable** wallet address
- TX hash → on-chain verify → **receipt + invoice**

### Owner
- `/setup` — name, niche, services, prices, days, **notify email**
- Payments — Base USDC receive wallet
- Signature for documents
- Orders — pause/resume, mark delivered, close, resend docs
- **Export order PDF** / batch export
- **Send file** to the client on Telegram
- **Email alert** on paid orders (Resend) + Telegram notify
- Client **@username** on order detail when available

### Trust
- Amount, token, recipient, confirmations, time window, replay guard
- **LLM never confirms payment** — only `payment_verifier.py`

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Interface | Telegram (`python-telegram-bot`) |
| Language | Python 3.11+ |
| Storage | SQLite (use a Railway volume in production) |
| Documents | ReportLab |
| AI | OpenAI-compatible API (Groq: `openai/gpt-oss-20b`) |
| Chain | Base mainnet · USDC |
| Email | Resend API (optional SMTP fallback) |

---

## Repository structure

```text
sovereign-business-operator/
├── main.py
├── config.py
├── db.py
├── ai.py
├── pricing.py
├── pdf_generator.py
├── payment_receipt.py
├── payment_verifier.py
├── handlers/
│   ├── client.py
│   └── owner.py
├── web/
│   ├── index.html
│   └── logo.png
├── docs/
│   ├── architecture.png
│   └── logo.png
├── Procfile
└── requirements.txt
```

---

## Quick start

```bash
git clone https://github.com/Ebubechukwucyber/sovereign-business-operator.git
cd sovereign-business-operator
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` (see [Configuration](#configuration)), then:

```bash
python main.py
```

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | BotFather token |
| `OWNER_TELEGRAM_ID` | Yes | Owner numeric Telegram id |
| `LLM_API_KEY` | Recommended | Groq / OpenAI-compatible key |
| `LLM_BASE_URL` | Recommended | Default `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | Recommended | e.g. `openai/gpt-oss-20b` |
| `DATABASE_PATH` | No | Default `sovereign.db` — use `/data/sovereign.db` with a volume |
| `BASE_CHAIN_ID` | No | Default `8453` |
| `BASE_RPC_URL` | No | Default `https://mainnet.base.org` |
| `BASE_USDC_CONTRACT` | No |  on Base |
| `RESEND_API_KEY` | For email | Resend API key |
| `EMAIL_FROM` | For email | e.g. `onboarding@resend.dev` |
| `EMAIL_ENABLED` | No | Default true when key present |
| `OWNER_NOTIFY_EMAIL` | Recommended | Fallback inbox for paid-order alerts |

**Pricing tip:** set realistic owner min/max for the niche. Simple jobs bias toward the minimum.

**Groq note:** `llama-3.1-8b-instant` was deprecated (Aug 2026). Use `openai/gpt-oss-20b` (or another current Groq model id).

---

## Payment & verification

Canonical module: **`payment_verifier.py`**

1. TX hash format  
2. Success receipt  
3. Correct chain  
4. ERC-20 Transfer to studio wallet  
5. USDC contract  
6. Amount ≥ quote  
7. Confirmations  
8. Time window  
9. Replay protection  

Then: job → PAID · receipt + invoice · owner Telegram (+ email if configured).

Mainnet = real value. Test with small amounts.

---

## Owner operations

1. `/setup` — profile, prices, **email**  
2. **Payments** — Base USDC wallet  
3. **Signature** — PDF sign-off  
4. **Orders** — detail, export PDF, send file, deliver, close  

---

## Deploy

1. Push to GitHub  
2. Railway (or similar) **worker**: `python main.py`  
3. Set all env vars in the host UI  
4. Attach a **volume** at `/data` and set `DATABASE_PATH=/data/sovereign.db` so owner data survives deploys  
5. Only **one** process may poll the bot token  

`Procfile`:

```text
worker: python main.py
```

---

## Landing page

[`web/index.html`](web/index.html) + [`web/logo.png`](web/logo.png)

---

## Security model

| Control | Behavior |
|---------|----------|
| Amount | From chain Transfer only |
| Recipient | Must match owner wallet |
| Token | Configured USDC on Base |
| Freshness / replay | Time window + confirmed-hash guard |
| Secrets | Env only — never commit keys |
| AI | Clamped pricing; cannot mark paid |

---

## Roadmap

- [x] Intake, dynamic questions, answer refinement  
- [x] AI pricing within owner bounds + scoped proposals  
- [x] Base mainnet USDC verification  
- [x] Receipt + invoice PDFs  
- [x] Owner deliver / export / send file  
- [x] Owner email alerts (Resend)  
- [x] Landing page + brand logo  

---

## License

MIT .

---

**Sovereign Business Operator** — an AI agent, a full service-business loop, verifiable USDC settlement on Base.
