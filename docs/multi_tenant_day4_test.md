# Multi-tenant Day 4 — two-owner test

## Setup

1. Deploy latest `main` with volume + env vars.
2. Optional: `TELEGRAM_BOT_USERNAME=your_bot` on Railway.

## Owner A (Telegram account A)

1. `/setup` → complete (name, niche, prices, email).
2. Payments → set USDC wallet A.
3. Note invite slug from setup / owner home (`/start slug-a`).

## Owner B (Telegram account B)

1. `/setup` → different business name.
2. Payments → wallet B (can be same or different test wallet).
3. Note `/start slug-b`.

## Client tests

1. Open bot with `/start slug-a` → welcome shows **A** branding.
2. Place a small order under A.
3. Open bot with `/start slug-b` → welcome shows **B** branding.
4. Place an order under B.
5. **My projects** while in slug-a session should prefer A jobs (if `owner_id` in session).

## Isolation

| Check | Expected |
|-------|----------|
| Owner A → Orders | Only A jobs |
| Owner B → Orders | Only B jobs |
| Owner B opens A job id (if guessed) | "You don't have access" |
| Pay A job | Notify + email only to A |
| Owner A send file on B job | Blocked |
| Owner A resend receipt on B job | Blocked |

## Demo still works

Bare `/start` (no slug) still loads env `OWNER_TELEGRAM_ID` business for judges.
