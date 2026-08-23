# Sovereign Business Operator

<p align="center">
  <img src="docs/logo.png" alt="Sovereign Business Operator" width="220" />
</p>

<p align="center">
  <strong>AI business operator on Telegram</strong> — qualify, quote within owner rules, collect <strong>USDC on Base mainnet</strong>, verify on-chain, deliver documents, alert the owner.
</p>

<p align="center">
  <a href="https://basescan.org"><img src="https://img.shields.io/badge/network-Base%20Mainnet-0B1F3A" alt="Base" /></a>
  <img src="https://img.shields.io/badge/token-USDC-F4C430" alt="USDC" />
  <img src="https://img.shields.io/badge/interface-Telegram-26A5E4" alt="Telegram" />
  <img src="https://img.shields.io/badge/tenancy-multi--owner-1A8A9D" alt="Multi-owner" />
</p>

Sovereign is a **business-agnostic AI operator** for service studios. Owners configure niche, pricing bounds, wallet, signature, and notification email. Clients complete intake in Telegram, receive a professional proposal, pay in **USDC on Base (chain id 8453)**, and get receipts and invoices after the chain confirms the transfer.

> **Payment network:** Base **mainnet** only for production · Circle USDC  
> **Not** Base Sepolia testnet for live demos  
> **Landing:** [`web/index.html`](web/index.html) · **Architecture:** [`docs/architecture.png`](docs/architecture.png)

---

## Why this exists

| Pain | Sovereign |
|------|-----------|
| Unqualified leads in chat | Dynamic intake + refined answers |
| Inconsistent quoting | AI pricing clamped to owner min/max |
| Screenshot “proof of payment” | On-chain USDC verification on Base |
| Manual invoices | Auto receipt + invoice PDFs |
| One studio only | Multi-owner: each owner runs their business on one bot |

---

## Product lifecycle

```text
NEW → QUALIFYING → QUOTED → AWAITING_PAYMENT
    → TX_SUBMITTED → VERIFYING → PAID
    → DELIVERED → CLOSED
```

Payment is confirmed **only** after `payment_verifier.py` succeeds. The LLM never marks a job paid.

---

## Features

### Client
- Welcome uses the **selected business** name, niche, and services  
- Invite: `/start <slug>` or `https://t.me/<bot>?start=<slug>`  
- Dynamic follow-ups + answer refinement for PDFs  
- AI pricing (size, deadline tightness) inside min/max  
- Proposal PDF + one-tap copyable USDC address  
- TX hash → Base mainnet verify → receipt + invoice  

### Owner
- `/setup` for **any** Telegram user (their own business)  
- Public **slug** invite for clients  
- Orders isolated per business (`business_id`)  
- Export PDF, send file, mark delivered, resend docs  
- Email on paid (Resend) + Telegram notify to **that** owner  

### Trust
- Amount, token, recipient, confirmations, freshness, replay guard  
- Documents label **Base** / **USDC** (mainnet), not Sepolia  

---

## Multi-owner (v1)

| Concept | Implementation |
|---------|----------------|
| Business id | Owner’s Telegram user id |
| Invite | `owners.slug` → `/start slug` |
| Jobs | `jobs.business_id` |
| Isolation | Owner only sees/acts on own jobs |
| Demo fallback | Bare `/start` → env `OWNER_TELEGRAM_ID` |

Not yet: billing, web dashboard, multiple businesses per one Telegram account.

See [`docs/multi_tenant_day4_test.md`](docs/multi_tenant_day4_test.md).

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Interface | Telegram (`python-telegram-bot`) |
| Storage | SQLite + Railway volume recommended |
| Documents | ReportLab |
| AI | OpenAI-compatible API (e.g. Groq `openai/gpt-oss-20b`) |
| Chain | **Base mainnet** · Circle USDC |
| Email | Resend (optional SMTP fallback) |

---

## Quick start

```bash
git clone https://github.com/Ebubechukwucyber/sovereign-business-operator.git
cd sovereign-business-operator
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configure env (below), then:

```bash
python main.py
```

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | BotFather token |
| `OWNER_TELEGRAM_ID` | Yes | Default demo owner Telegram id |
| `TELEGRAM_BOT_USERNAME` | Recommended | Bot username (no `@`) for invite links |
| `LLM_API_KEY` | Recommended | Groq / OpenAI-compatible key |
| `LLM_BASE_URL` | Recommended | e.g. `https://api.groq.com/openai/v1` |
| `LLM_MODEL` | Recommended | e.g. `openai/gpt-oss-20b` |
| `DATABASE_PATH` | No | Use `/data/sovereign.db` with a volume |
| `BASE_CHAIN_ID` | No | Default **8453** (mainnet) |
| `BASE_RPC_URL` | No | Default `https://mainnet.base.org` |
| `BASE_USDC_CONTRACT` | No | Circle USDC on Base mainnet |
| `RESEND_API_KEY` | For email | Resend API key |
| `EMAIL_FROM` | For email | e.g. `onboarding@resend.dev` |
| `EMAIL_ENABLED` | No | Default true when configured |
| `OWNER_NOTIFY_EMAIL` | Recommended | Fallback inbox for paid alerts |

**Groq:** `llama-3.1-8b-instant` was deprecated (Aug 2026). Use a current model id such as `openai/gpt-oss-20b`.

---

## Payment & verification

Canonical module: **`payment_verifier.py`**

Checks include: TX format, success, **Base mainnet**, USDC contract, recipient wallet, amount ≥ quote, confirmations, time window, replay protection.

Receipts, invoices, and chat copy use network label **Base** and token **USDC**.

Mainnet = real value. Test with small amounts.

---

## Deploy (Railway)

1. Worker: `python main.py` (`Procfile`)  
2. Set all env vars  
3. Volume mount + `DATABASE_PATH=/data/sovereign.db`  
4. One process only (avoid getUpdates conflict)  

---

## Security

| Control | Behavior |
|---------|----------|
| Amount | From chain Transfer only |
| Recipient | Owner’s configured USDC wallet |
| Token | Configured USDC on Base mainnet |
| AI | Cannot confirm payment |
| Tenancy | Owners cannot open each other’s jobs |

---

## License

MIT (or your preferred license).

---

**Sovereign Business Operator** — AI commercial judgment, deterministic Base USDC settlement, multi-owner ready.
