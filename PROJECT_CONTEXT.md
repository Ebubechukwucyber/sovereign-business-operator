# Sovereign Business Operator

> An AI-assisted, business-agnostic Telegram business operator that qualifies leads, creates quotes, manages jobs, accepts USDC payments, verifies payment transactions, and produces professional invoices and receipts.

**Project status:** Active development  
**Primary interface:** Telegram  
**Database:** SQLite  
**Language:** Python  
**Payment architecture:** Base -> Base Sepolia testnet first -> USDC  
**Current development goal:** Complete and test end-to-end payment verification and document generation.

---

# 1. Executive Summary

Sovereign Business Operator is a reusable AI-powered operating system for service businesses.

The system is intentionally **business-agnostic**. The owner configures:

- Business name/profile
- Niche
- Services
- Minimum and maximum pricing
- Default delivery time
- Communication tone
- Business rules
- Payment wallet
- Invoice/receipt signature details

Clients interact with the business through Telegram.

## Intended lifecycle

```text
CLIENT
   |
   v
Telegram conversation
   |
   v
Business intake / qualification
   |
   v
Job created in SQLite
   |
   v
Answers collected
   |
   v
Complexity / pricing analysis
   |
   v
Proposal generated
   |
   v
Quote sent to client
   |
   v
Payment instructions generated
   |
   v
Client sends USDC
   |
   v
Client submits transaction hash
   |
   v
Blockchain transaction verified
   |
   +-- Invalid --> Payment rejected
   |
   +-- Valid ----> Payment confirmed
                     |
                     v
                  Job marked PAID
                     |
                     v
              Receipt / invoice generated
                     |
                     v
                Document sent to client
```

The database and Telegram conversation foundation are implemented. The payment data model is also implemented. The next major task is completing and testing real Base Sepolia transaction verification.

---

# 2. Core Product Vision

The long-term goal is an autonomous or semi-autonomous business operator capable of handling repetitive operational work for service businesses.

The operator should eventually be able to:

1. Receive client requests.
2. Ask qualification questions.
3. Understand requested work.
4. Estimate complexity.
5. Apply business-specific pricing rules.
6. Generate quotes or proposals.
7. Request owner approval where required.
8. Accept cryptocurrency payments.
9. Verify transactions on-chain.
10. Generate professional financial documents.
11. Track jobs through their lifecycle.
12. Maintain an auditable operational history.

The architecture should remain modular so new capabilities can be added without rewriting the system.

---

# 3. Current Architecture

```text
sovereign-business-operator/
|
+-- main.py
|   Telegram application, handlers, conversations,
|   menus and application orchestration
|
+-- db.py
|   SQLite schema, migrations and database operations
|
+-- config.py
|   Configuration values such as DATABASE_PATH and credentials
|
+-- requirements.txt
|   Python dependencies
|
+-- .env
|   Local secrets (DO NOT COMMIT)
|
+-- .gitignore
|
+-- README.md
|
+-- PROJECT_CONTEXT.md
|   Continuation guide for engineers and LLMs
|
+-- data/
    SQLite database and generated application data
```

## Preferred future structure

```text
sovereign-business-operator/
|
+-- main.py
+-- config.py
+-- db.py
|
+-- handlers/
|   +-- owner.py
|   +-- client.py
|   +-- payment.py
|
+-- services/
|   +-- qualification.py
|   +-- pricing.py
|   +-- proposals.py
|   +-- payment_verification.py
|   +-- documents.py
|
+-- blockchain/
|   +-- base.py
|   +-- verifier.py
|
+-- documents/
|   +-- invoice.py
|   +-- receipt.py
|
+-- tests/
|
+-- data/
```

Do not perform a large refactor merely for aesthetics during hackathon development. Prioritize working features and refactor stable functionality later.

---

# 4. Technology Stack

## Backend

- Python
- python-telegram-bot
- SQLite

## Blockchain / Payments

- Base network
- Base Sepolia testnet during development
- USDC
- Transaction hash verification

## Documents

The application is intended to generate professional PDFs for:

- Payment invoices
- Payment receipts
- Potentially proposals in the future

Documents should include:

- Business name
- Client details
- Job/order ID
- Amount
- Currency/token
- Payment network
- Transaction hash
- Confirmation date
- Invoice/receipt number
- Signature name
- Signature title
- Optional signature image

---

# 5. Database Architecture

The application currently uses two primary tables:

```text
owners
jobs
```

## 5.1 owners

The `owners` table stores business operator configuration.

Primary key:

```text
telegram_id
```

Important fields:

| Field | Purpose |
|---|---|
| telegram_id | Telegram identity of owner |
| name | Owner/business name |
| niche | Business niche |
| services_text | Services offered |
| min_price | Minimum price |
| max_price | Maximum price |
| default_days | Default delivery period |
| tone | Communication tone |
| usdc_address | Payment wallet |
| setup_complete | Setup completion state |
| business_rules | JSON business configuration |
| signature_name | Name displayed on documents |
| signature_title | Signatory role/title |
| signature_image | Optional signature image path |
| created_at | Record creation time |
| updated_at | Last modification time |

### Business rules

`business_rules` is stored as JSON, allowing business-specific behavior without schema changes.

Example:

```json
{
  "pricing": {
    "enabled": true,
    "minimum": 150,
    "maximum": 400
  }
}
```

## 5.2 jobs

The `jobs` table represents both jobs and orders.

Compatibility helpers currently exist:

```python
create_order() -> create_job()
get_order() -> get_job()
```

The canonical concept going forward should be **job**.

Important fields:

### Client information

```text
client_telegram_id
client_name
```

### Job state

```text
status
paused
```

### Qualification

```text
answers
```

Stored as JSON.

### Quote

```text
quoted_price
currency
deadline
proposal_text
```

### Internal information

```text
notes
complexity
cushion_applied
internal_analysis
```

### Payment

```text
payment_status
payment_network
payment_token
payment_address
payment_tx_hash
payment_confirmed_at
payment_amount
```

### Documents

```text
receipt_file
invoice_file
```

---

# 6. Database Initialization and Migrations

`init_db()`:

1. Creates tables if they do not exist.
2. Ensures newer columns exist in older databases.

Migration support is handled by:

```python
_ensure_column(conn, table_name, column_name, definition)
```

The helper reads:

```sql
PRAGMA table_info(table_name)
```

It adds a column only when necessary.

When adding a field:

- Add it to `CREATE TABLE`.
- Add a migration with `_ensure_column`.
- Preserve existing data.
- Avoid forcing database deletion.

---

# 7. Job Lifecycle

Expected lifecycle:

```text
NEW
  |
  v
QUALIFYING
  |
  v
QUOTED
  |
  v
AWAITING PAYMENT
  |
  v
TX_SUBMITTED
  |
  v
VERIFYING
  |
  +--> REJECTED
  |
  v
CONFIRMED PAYMENT
  |
  v
PAID
  |
  v
WORK / DELIVERY
  |
  v
DELIVERED
  |
  v
CLOSED
```

`status` and `payment_status` are intentionally separate.

Example:

```text
Job status: PAID
Payment status: CONFIRMED
```

---

# 8. Payment State Machine

```text
UNPAID
  |
  v
AWAITING_PAYMENT
  |
  v
TX_SUBMITTED
  |
  v
VERIFYING
  |
  +--> REJECTED
  |
  v
CONFIRMED
```

## Critical rule

> A submitted transaction hash is not proof of payment.

The system must independently verify the blockchain transaction before confirmation.

---

# 9. Payment Verification Requirements

`confirm_payment(...)` must only be called after independent blockchain verification.

A valid transaction should satisfy:

1. Transaction exists.
2. Transaction executed successfully.
3. Transaction is on the expected network.
4. The transferred asset is the expected token.
5. The recipient matches the configured business wallet.
6. The amount is correct or sufficient.
7. The transaction has an acceptable confirmation state.

Desired flow:

```text
Client submits tx hash
        |
        v
set_payment_tx_hash()
        |
        v
mark_payment_pending()
        |
        v
verify_payment_transaction()
        |
        +--> invalid --> reject_payment()
        |
        v
valid
        |
        v
confirm_payment()
```

---

# 10. Current Base Payment Configuration

Development and testing target:

```text
Network: Base Sepolia
Token: USDC
```

The wallet configured during the latest development session was:

```text
0x17157C80278dC0Ba465c820C52695C64a92f53ef
```

## Current blocker

There is an unresolved issue with Base Sepolia wallet/testnet setup.

Development paused at this point.

Do not switch to mainnet merely to bypass testing.

Correct order:

```text
1. Fix Base Sepolia wallet setup
2. Obtain appropriate test funds/token setup
3. Send a test transaction
4. Capture transaction hash
5. Verify transaction programmatically
6. Confirm payment in database
7. Generate receipt
8. Send receipt to client
9. Test full end-to-end flow
10. Only then prepare for Base mainnet
```

---

# 11. Payment Functions Already Implemented

## Save payment instructions

```python
set_payment_details(
    job_id,
    payment_address="",
    payment_network="Base Sepolia",
    payment_token="USDC",
    payment_amount=0,
)
```

Sets:

```text
payment_status = AWAITING_PAYMENT
```

## Retrieve payment details

```python
get_payment_details(job_id)
```

## Save submitted transaction hash

```python
set_payment_tx_hash(job_id, tx_hash)
```

Sets:

```text
payment_status = TX_SUBMITTED
```

It does not confirm payment.

## Mark payment as verifying

```python
mark_payment_pending(job_id)
```

Sets:

```text
payment_status = VERIFYING
```

## Confirm payment

```python
confirm_payment(
    job_id,
    tx_hash,
    amount,
    payment_network="Base Sepolia",
    payment_token="USDC",
)
```

Sets:

```text
payment_status = CONFIRMED
status = PAID
```

Only call after blockchain validation.

## Reject payment

```python
reject_payment(job_id, reason="")
```

Preserves the submitted transaction hash and appends the rejection reason to notes.

## Check confirmation

```python
is_payment_confirmed(job_id)
```

Returns a boolean.

---

# 12. Receipt and Invoice Persistence

Database support exists for document paths.

```python
save_receipt_file(job_id, receipt_file)
save_invoice_file(job_id, invoice_file)
get_receipt_file(job_id)
get_invoice_file(job_id)
```

The next implementation task is connecting these functions to real PDF generation.

---

# 13. Owner Signature System

Owner signature fields:

```text
signature_name
signature_title
signature_image
```

Functions:

```python
save_owner_signature(...)
get_owner_signature(...)
```

The signature should be used in generated financial documents.

Example:

```text
Authorized by:

[Signature Image]

Name
Title
```

---

# 14. Pricing Architecture

Default pricing structure includes:

```python
DEFAULT_PRICING_RULES = {
    "enabled": True,
    "model": "base_plus_unit",
    "currency": "USD",
    "base_fee": 0,
    "unit": {
        "name": "unit",
        "price": 0,
    },
    "minimum": 150,
    "maximum": 400,
    "adjustments": [],
    "owner_approval": {
        "required": True,
        "required_above_maximum": True,
        "required_below_minimum": True,
        "required_for_manual_override": True,
    },
    "rounding": {
        "enabled": False,
        "nearest": 1,
    },
}
```

Rules are recursively merged using:

```python
merge_pricing_rules(defaults, overrides)
```

Functions include:

```python
get_default_pricing_rules()
get_pricing_rules(telegram_id)
save_pricing_rules(telegram_id, pricing_rules)
update_pricing_rule(telegram_id, key, value)
reset_pricing_rules(telegram_id)
```

---

# 15. Telegram Application

The application starts with:

```bash
python main.py
```

Latest successful startup output:

```text
Sovereign Business Operator is running...

Business-agnostic client intake enabled.

Base USDC payment system enabled.

Owner payment and signature controls enabled.
```

Warnings were produced by `python-telegram-bot` concerning `ConversationHandler`, `CallbackQueryHandler`, and `per_message=False`.

The application still started successfully.

Known conversation areas:

```text
owner_settings_conversation
owner_payment_signature_conversation
client_order_conversation
```

Do not spend hackathon time fixing warnings unless they cause broken behavior.

---

# 16. Owner Capabilities

The owner configuration system supports or is intended to support:

- Business name
- Niche
- Services
- Minimum price
- Maximum price
- Delivery days
- Tone
- Business rules
- Payment wallet
- Payment network
- Token configuration
- Signature name
- Signature title
- Signature image

The owner's Telegram ID is the primary identifier.

---

# 17. Client Flow

```text
/start
   |
   v
Start order/request
   |
   v
System creates job
   |
   v
System asks qualification questions
   |
   v
Answers saved
   |
   v
Pricing/complexity evaluated
   |
   v
Proposal generated
   |
   v
Quote presented
   |
   v
Client proceeds to payment
   |
   v
Wallet + amount shown
   |
   v
Client pays
   |
   v
Client submits tx hash
   |
   v
System verifies payment
   |
   v
Confirmation
   |
   v
Receipt sent
```

---

# 18. Immediate Next Steps

## Priority 1 - Resolve Base Sepolia setup

Current blocker:

> Base Sepolia wallet/test environment setup is not working correctly.

Resume from this exact point.

Do not redesign the database. The payment persistence structure is already in place.

## Priority 2 - Implement blockchain verifier

Preferred module:

```text
blockchain/verifier.py
```

Recommended interface:

```python
def verify_payment_transaction(
    tx_hash,
    expected_recipient,
    expected_amount,
    expected_token,
    expected_network,
):
    ...
```

Recommended return:

```python
{
    "valid": False,
    "reason": "",
    "tx_hash": "",
    "amount": 0,
    "recipient": "",
    "token": "",
    "network": "",
}
```

The verifier should:

1. Validate hash format.
2. Query a Base Sepolia RPC/provider.
3. Verify transaction success.
4. Inspect token transfer data/events.
5. Confirm recipient.
6. Confirm amount.
7. Confirm token contract.
8. Return a structured result.

Keep blockchain networking outside `db.py`.

## Priority 3 - Implement professional PDF generation

Preferred structure:

```text
documents/
    invoice.py
    receipt.py
```

Suggested functions:

```python
generate_invoice(job_id)
generate_receipt(job_id)
```

Requirements:

- Professional layout
- Good spacing
- Clear hierarchy
- Color accents
- Business identity
- Client name
- Job ID
- Amount
- Network
- Token
- Transaction hash
- Confirmation timestamp
- Signature information

Suggested storage:

```text
generated_documents/
    invoices/
    receipts/
```

After generation:

```python
save_receipt_file(job_id, path)
save_invoice_file(job_id, path)
```

## Priority 4 - Connect confirmation to receipt generation

Desired flow:

```python
verification = verify_payment_transaction(...)
```

If:

```python
verification["valid"] is True
```

Then:

```python
confirm_payment(...)
receipt_path = generate_receipt(job_id)
save_receipt_file(job_id, receipt_path)
```

Then send the PDF to the client through Telegram.

---

# 19. Recommended End-to-End Test

## Step 1 - Create a client job

Expected:

```text
status = NEW
payment_status = UNPAID
```

## Step 2 - Complete qualification

Expected:

```text
status = QUALIFYING
```

## Step 3 - Save proposal

Expected:

```text
status = QUOTED
quoted_price > 0
```

## Step 4 - Create payment instructions

Expected:

```text
payment_status = AWAITING_PAYMENT
payment_address populated
payment_amount populated
payment_network = Base Sepolia
payment_token = USDC
```

## Step 5

Send a real testnet transaction.

## Step 6

Submit the transaction hash.

Expected:

```text
payment_status = TX_SUBMITTED
```

## Step 7

Start verification.

Expected:

```text
payment_status = VERIFYING
```

## Step 8

Verify transaction.

Invalid:

```text
payment_status = REJECTED
```

Valid:

```text
payment_status = CONFIRMED
status = PAID
```

## Step 9

Generate receipt.

Expected:

```text
receipt_file populated
```

## Step 10

Send receipt through Telegram.

---

# 20. Technical Considerations

## UTC timestamps

Current implementation:

```python
datetime.utcnow().isoformat()
```

This is acceptable for the prototype. Future improvement: timezone-aware UTC timestamps.

## SQLite concurrency

SQLite is appropriate for the current hackathon prototype.

Future options:

- PostgreSQL
- SQLAlchemy
- Connection pooling
- Explicit transaction management

Do not migrate prematurely.

## Secrets

Never commit:

```text
.env
bot tokens
API keys
wallet private keys
RPC secrets
```

Wallet addresses are public. Private keys are not.

---

# 21. Suggested .gitignore

```gitignore
# Environment
.env
.venv/
venv/

# Python
__pycache__/
*.py[cod]

# Database
*.db
*.sqlite
*.sqlite3

# Generated files
generated_documents/
data/

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
```

---

# 22. Git Repository Setup

```bash
git init
git add .
git commit -m "Initial Sovereign Business Operator implementation"
```

Then:

```bash
git branch -M main
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Before pushing:

```bash
git status
```

Verify `.env`, private keys, and local databases are not staged.

---

# 23. Recommended Commit Strategy

Examples:

```text
feat: add SQLite job payment tracking
feat: add Base Sepolia payment workflow
feat: add owner payment wallet configuration
feat: add signature fields for financial documents
feat: add transaction hash submission flow
fix: preserve rejected payment audit details
docs: add project continuation guide
```

Avoid:

```text
update
changes
final
fix stuff
```

---

# 24. Engineering Principles for Continuation

## Principle 1 - Never confirm payment without verification

A transaction hash is not payment confirmation.

## Principle 2 - Separate responsibilities

`db.py` should:

- Read
- Write
- Update
- Query

Blockchain modules should:

- Call RPC providers
- Inspect transactions
- Validate transfers

Telegram handlers should:

- Receive user input
- Call services
- Present results

## Principle 3 - Preserve audit data

Do not delete transaction hashes when verification fails.

Keep:

- Hash
- Rejection reason
- Timestamps
- Relevant notes

## Principle 4 - Fail safely

If verification cannot be completed, do not confirm payment.

Prefer:

```text
VERIFYING
```

or:

```text
REJECTED
```

with a clear reason.

## Principle 5 - Test on Base Sepolia first

Do not use real money while verification is untested.

## Principle 6 - Keep the product business-agnostic

Do not hardcode assumptions about one profession.

Business-specific behavior should come from owner configuration and business rules.

---

# 25. Handoff Prompt for Another LLM

```text
You are taking over development of the Sovereign Business Operator project.

First, read README.md and PROJECT_CONTEXT.md completely.

Then inspect:

1. main.py
2. db.py
3. config.py
4. requirements.txt
5. .gitignore

Do not rewrite working functionality unnecessarily.

The application is a business-agnostic Telegram business operator built with Python and SQLite.

The current architecture includes:

- Owner business configuration
- Client qualification
- Job/order management
- Pricing rules
- Proposal persistence
- Base Sepolia / USDC payment data model
- Transaction hash submission
- Payment state tracking
- Owner wallet configuration
- Owner signature configuration
- Receipt/invoice file persistence

The current development blocker is Base Sepolia test wallet/testnet setup.

The next implementation goal after resolving that setup is:

1. Send a real test transaction.
2. Implement blockchain transaction verification.
3. Verify recipient, token, amount, network and transaction success.
4. Call confirm_payment() only after successful verification.
5. Generate a professional PDF receipt.
6. Save the receipt path in the database.
7. Send the receipt to the client through Telegram.
8. Test the complete flow end to end.

Important safety rule:

A submitted transaction hash must NEVER automatically mark a payment as confirmed.

Before changing code, explain:
- What the current code does.
- What you plan to change.
- Which files will be modified.

Then make the smallest safe change required.

Prefer modular services over adding large amounts of unrelated logic to main.py.
```

---

# 26. Exact Resume Point

The database and payment persistence layer are implemented.

The Telegram bot successfully starts.

The owner wallet configuration successfully saved a wallet address.

The active blocker is Base Sepolia testnet setup.

## Resume with

```text
Fix Base Sepolia wallet/testnet configuration.
```

## Then

```text
Implement real transaction verification.
```

## Then

```text
Generate and send a professional payment receipt after confirmed payment.
```

---

# 27. Definition of the Next Milestone

The next milestone is complete when:

```text
Client creates request
        |
        v
Client receives quote
        |
        v
Client receives Base Sepolia payment instructions
        |
        v
Client sends test USDC
        |
        v
Client submits transaction hash
        |
        v
System independently verifies transaction
        |
        v
Database marks payment CONFIRMED
        |
        v
Job becomes PAID
        |
        v
Professional PDF receipt generated
        |
        v
Receipt sent to client in Telegram
```

At that point, the project has a demonstrable end-to-end payment workflow suitable for a hackathon demonstration.

---

# 28. Final Status Snapshot

| Component | Status |
|---|---|
| SQLite database | Implemented |
| Owner configuration | Implemented |
| Business rules | Implemented |
| Pricing rule storage | Implemented |
| Jobs/orders | Implemented |
| Qualification answer storage | Implemented |
| Proposal persistence | Implemented |
| Job analysis storage | Implemented |
| Pause/resume | Implemented |
| Notes/status updates | Implemented |
| Payment data model | Implemented |
| Wallet storage | Implemented |
| Transaction hash storage | Implemented |
| Payment confirmation persistence | Implemented |
| Payment rejection persistence | Implemented |
| Base Sepolia test setup | Blocked / unresolved |
| Real blockchain verification | Next |
| Professional PDF receipt generation | Next |
| Professional PDF invoice generation | Pending |
| Automatic receipt delivery | Pending |
| Full end-to-end payment test | Pending |

---

# 29. Hackathon Priority

This is a hackathon project.

Priority:

```text
Working demo
    |
    v
Reliable core flow
    |
    v
Clean architecture
    |
    v
Additional polish
    |
    v
Future scalability
```

Do not introduce unnecessary infrastructure.

A working system with:

- Telegram intake
- Job management
- Quote/payment flow
- Real transaction verification
- Professional receipt generation

is more valuable at this stage than an overengineered architecture.

---

# Final Project Snapshot

**Project:** Sovereign Business Operator  
**Current phase:** Payment verification and financial document generation  
**Current test network:** Base Sepolia  
**Next blocker:** Wallet/testnet configuration  
**Next milestone:** Verified test payment -> confirmed job -> generated PDF receipt
