"""
AI compatibility layer for Sovereign Business Operator.

Provides:

    calculate_price()
    generate_proposal()
    template_proposal()

The proposal PDF is handled separately by pdf_generator.py.
"""

import os
import json
import re
from typing import Any


# =========================================================
# SAFE HELPERS
# =========================================================

def clean_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def get_value(row, key, default=None):
    """
    Works with:

        sqlite3.Row
        dict
        normal objects
    """

    if row is None:
        return default

    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        pass

    try:
        return row.get(key, default)
    except AttributeError:
        pass

    try:
        return getattr(row, key)
    except AttributeError:
        return default


def get_business_rules(owner) -> dict:
    raw = get_value(
        owner,
        "business_rules",
        {},
    )

    if isinstance(raw, dict):
        return raw

    if not raw:
        return {}

    try:
        parsed = json.loads(raw)

        if isinstance(parsed, dict):
            return parsed

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        pass

    return {}


# =========================================================
# NUMBER EXTRACTION
# =========================================================

def extract_number(text: str):
    if not text:
        return None

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\b",
        str(text),
    )

    if not match:
        return None

    try:
        value = float(match.group(1))

        if value <= 0:
            return None

        return value

    except ValueError:
        return None


# =========================================================
# PRICE CALCULATION
# =========================================================

def calculate_price(
    owner,
    answers,
) -> float:
    """
    Calculate a project price from the business owner's
    configured pricing rules.

    The business owner's configured min/max range remains
    authoritative.
    """

    rules = get_business_rules(owner)

    minimum = safe_float(
        get_value(
            owner,
            "min_price",
            rules.get("min_price", 150),
        ),
        150,
    )

    maximum = safe_float(
        get_value(
            owner,
            "max_price",
            rules.get("max_price", 400),
        ),
        400,
    )

    if minimum <= 0:
        minimum = 150

    if maximum < minimum:
        maximum = minimum

    answers = answers or {}

    combined = " ".join(
        clean_text(value)
        for value in answers.values()
    ).lower()

    # -----------------------------------------------------
    # BASE
    # -----------------------------------------------------

    base_price = safe_float(
        rules.get(
            "base_price",
            minimum,
        ),
        minimum,
    )

    base_price = max(
        base_price,
        minimum,
    )

    base_price = min(
        base_price,
        maximum,
    )

    # -----------------------------------------------------
    # QUANTITY
    # -----------------------------------------------------

    quantity = extract_number(
        answers.get(
            "quantity",
            "",
        )
    )

    quantity_threshold = safe_float(
        rules.get(
            "large_quantity_threshold",
            20,
        ),
        20,
    )

    quantity_percent = safe_float(
        rules.get(
            "quantity_buffer_percent",
            0,
        ),
        0,
    )

    if (
        quantity is not None
        and quantity >= quantity_threshold
        and quantity_percent > 0
    ):

        base_price *= (
            1
            + quantity_percent / 100
        )

    # -----------------------------------------------------
    # RUSH
    # -----------------------------------------------------

    rush_terms = [
        "urgent",
        "asap",
        "immediately",
        "today",
        "tonight",
        "tomorrow",
        "24 hours",
        "48 hours",
        "as soon as possible",
    ]

    rush_percent = safe_float(
        rules.get(
            "rush_buffer_percent",
            0,
        ),
        0,
    )

    if (
        rush_percent > 0
        and any(
            term in combined
            for term in rush_terms
        )
    ):

        base_price *= (
            1
            + rush_percent / 100
        )

    # -----------------------------------------------------
    # COMPLEXITY
    # -----------------------------------------------------

    complexity_terms = [
        "complex",
        "complicated",
        "custom",
        "bulk",
        "multiple locations",
        "multiple teams",
        "multiple people",
        "advanced",
        "high volume",
        "end to end",
        "everything",
        "complete",
        "full package",
    ]

    complexity_hits = sum(
        1
        for term in complexity_terms
        if term in combined
    )

    complexity_percent = safe_float(
        rules.get(
            "complexity_buffer_percent",
            0,
        ),
        0,
    )

    if (
        complexity_hits > 0
        and complexity_percent > 0
    ):

        multiplier = min(
            complexity_hits,
            3,
        )

        base_price *= (
            1
            + (
                complexity_percent
                * multiplier
                / 100
            )
        )

    # -----------------------------------------------------
    # NORMAL BUFFER
    # -----------------------------------------------------

    buffer_percent = safe_float(
        rules.get(
            "buffer_percent",
            0,
        ),
        0,
    )

    if buffer_percent > 0:

        base_price *= (
            1
            + buffer_percent / 100
        )

    # -----------------------------------------------------
    # FINAL RANGE
    # -----------------------------------------------------

    base_price = max(
        base_price,
        minimum,
    )

    base_price = min(
        base_price,
        maximum,
    )

    return round(
        base_price,
        2,
    )


# =========================================================
# PROPOSAL HELPERS
# =========================================================

def proposal_value(
    answers,
    key,
    fallback="Not specified.",
):
    value = clean_text(
        answers.get(
            key,
            "",
        )
    )

    return value or fallback


def format_project_title(project):
    """
    Convert a raw client description into a cleaner proposal
    title without inventing information.
    """

    project = clean_text(project)

    if not project:
        return "Business Service Project"

    project = project.rstrip(". ")

    # Keep reasonable client wording.
    if len(project) <= 70:
        return project

    return (
        project[:67].rstrip()
        + "..."
    )


def looks_like_catering(answers, services=""):
    """
    Detect catering-related requests.

    This only changes wording where the client's actual
    request indicates catering/food/event service.
    """

    combined = " ".join(
        [
            clean_text(
                answers.get(
                    "project",
                    "",
                )
            ),
            clean_text(
                answers.get(
                    "requirements",
                    "",
                )
            ),
            clean_text(
                answers.get(
                    "quantity",
                    "",
                )
            ),
            clean_text(services),
        ]
    ).lower()

    catering_terms = [
        "catering",
        "cater",
        "birthday party",
        "party food",
        "event food",
        "food for",
        "buffet",
        "meal service",
        "food service",
    ]

    return any(
        term in combined
        for term in catering_terms
    )


# =========================================================
# TEMPLATE PROPOSAL
# =========================================================

def template_proposal(
    owner,
    answers,
    price,
):
    """
    Deterministic professional proposal.

    This is intentionally detailed enough to remain useful
    when no AI provider is available.
    """

    business_name = clean_text(
        get_value(
            owner,
            "name",
            "Sovereign Studio",
        )
    )

    services = clean_text(
        get_value(
            owner,
            "services_text",
            "",
        )
    )

    project = proposal_value(
        answers,
        "project",
        "Requested business service",
    )

    requirements = proposal_value(
        answers,
        "requirements",
        "The client's specific requirements will be confirmed before work begins.",
    )

    quantity = clean_text(
        answers.get(
            "quantity",
            "",
        )
    )

    deadline = clean_text(
        answers.get(
            "deadline",
            "",
        )
    )

    additional = clean_text(
        answers.get(
            "additional",
            "",
        )
    )

    revision = clean_text(
        answers.get(
            "client_revision_request",
            "",
        )
    )

    project_title = format_project_title(
        project
    )

    is_catering = looks_like_catering(
        answers,
        services,
    )

    lines = []

    # -----------------------------------------------------
    # TITLE
    # -----------------------------------------------------

    lines.extend(
        [
            project_title,
            "",
            "Executive Summary",
            (
                f"{business_name} is pleased to provide this "
                f"proposal for {project.rstrip('.')}."
            ),
            (
                "The proposal is based on the information "
                "provided by the client and is intended to "
                "define the initial project scope, delivery "
                "expectations and project investment."
            ),
            "",
        ]
    )

    # -----------------------------------------------------
    # SCOPE
    # -----------------------------------------------------

    lines.extend(
        [
            "Scope",
            (
                f"The requested service is: "
                f"{project.rstrip('.')}. "
                f"The work will be carried out according "
                f"to the agreed requirements and information "
                f"provided by the client."
            ),
            "",
            "Client Requirements",
            requirements,
        ]
    )

    # -----------------------------------------------------
    # CATERING-SPECIFIC WORDING
    # -----------------------------------------------------

    if is_catering:

        lines.extend(
            [
                "",
                "Event Service Details",
                (
                    "This proposal covers catering support "
                    "for the stated event or occasion."
                ),
                (
                    "Food selection, quantities, service "
                    "requirements and other event-specific "
                    "details will be based on the client's "
                    "confirmed requirements."
                ),
            ]
        )

        if quantity:
            lines.extend(
                [
                    "",
                    "Expected Quantity / Event Size",
                    quantity,
                ]
            )

    elif quantity:

        lines.extend(
            [
                "",
                "Project Size / Quantity",
                quantity,
            ]
        )

    # -----------------------------------------------------
    # INCLUDED
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Included",
            (
                "• Professional execution of the agreed "
                "project scope."
            ),
            (
                "• Work based on the requirements supplied "
                "by the client."
            ),
            (
                "• Reasonable coordination required to "
                "complete the agreed service."
            ),
            (
                "• Reasonable revisions where they remain "
                "within the approved scope."
            ),
        ]
    )

    # -----------------------------------------------------
    # TIMELINE
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Timeline",
        ]
    )

    if deadline:

        lines.append(
            f"Requested completion: {deadline}."
        )

        lines.append(
            "The final delivery schedule will be confirmed "
            "after the project details and payment requirements "
            "have been verified."
        )

    else:

        lines.append(
            "The delivery timeline will be confirmed after "
            "the project scope and required start conditions "
            "have been agreed."
        )

    # -----------------------------------------------------
    # ADDITIONAL INFORMATION
    # -----------------------------------------------------

    if additional:

        lines.extend(
            [
                "",
                "Additional Information",
                additional,
            ]
        )

    # -----------------------------------------------------
    # PRICE
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Investment",
            f"Total Project Investment: ${float(price):.2f} USD.",
            (
                "This investment is based on the currently "
                "approved project scope."
            ),
            (
                "Any material changes to the scope may require "
                "a revised quotation before additional work "
                "is undertaken."
            ),
        ]
    )

    # -----------------------------------------------------
    # NOT INCLUDED
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Not Included",
            (
                "• Work outside the agreed project scope."
            ),
            (
                "• Additional services not identified in "
                "the approved requirements."
            ),
            (
                "• Third-party costs unless specifically "
                "included in the agreement."
            ),
            (
                "• Additional work resulting from material "
                "changes requested after approval."
            ),
        ]
    )

    # -----------------------------------------------------
    # CLIENT RESPONSIBILITIES
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Client Responsibilities",
            (
                "• Provide accurate project information."
            ),
            (
                "• Provide required materials, information "
                "or access needed to perform the service."
            ),
            (
                "• Provide timely feedback and approvals."
            ),
            (
                "• Communicate any material changes to the "
                "agreed scope as early as possible."
            ),
        ]
    )

    # -----------------------------------------------------
    # PAYMENT
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Payment Terms",
            (
                f"The total project fee is "
                f"${float(price):.2f} USD."
            ),
            (
                "Work begins after the business has verified "
                "the required payment according to its approved "
                "payment process."
            ),
        ]
    )

    # -----------------------------------------------------
    # REVISION REQUEST
    # -----------------------------------------------------

    if revision:

        lines.extend(
            [
                "",
                "Client Requested Changes",
                revision,
            ]
        )

    # -----------------------------------------------------
    # NEXT STEPS
    # -----------------------------------------------------

    lines.extend(
        [
            "",
            "Next Steps",
            (
                "1. Review the proposal and confirm that the "
                "scope, timeline and investment accurately "
                "reflect the requested project."
            ),
            (
                "2. Complete the required payment process."
            ),
            (
                "3. The business verifies payment and confirms "
                "the project schedule."
            ),
            (
                "4. The project proceeds according to the "
                "approved scope."
            ),
            "",
            f"Prepared by {business_name}.",
        ]
    )

    return "\n".join(lines)


# =========================================================
# LLM HELPERS (config-driven, safe fallbacks)
# =========================================================

def _llm_config():
    """
    Prefer project config env vars; fall back to OPENAI_* names.
    """
    api_key = (
        os.getenv("LLM_API_KEY", "").strip()
        or os.getenv("OPENAI_API_KEY", "").strip()
    )
    base_url = (
        os.getenv("LLM_BASE_URL", "").strip()
        or "https://api.openai.com/v1"
    ).rstrip("/")
    model = (
        os.getenv("LLM_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
        or "llama-3.1-8b-instant"
    )
    return api_key, base_url, model


async def llm_chat(
    system: str,
    user: str,
    temperature: float = 0.3,
) -> str:
    """
    Minimal OpenAI-compatible chat completion via httpx.
    Returns empty string on any failure.
    """
    api_key, base_url, model = _llm_config()
    if not api_key:
        return ""

    try:
        import httpx
    except ImportError:
        return ""

    payload = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        choices = data.get("choices") or []
        if not choices:
            return ""

        message = choices[0].get("message") or {}
        return clean_text(message.get("content", ""))
    except Exception:
        return ""


def _owner_price_bounds(owner) -> tuple[float, float]:
    rules = get_business_rules(owner)
    minimum = safe_float(
        get_value(
            owner,
            "min_price",
            rules.get("min_price", 150),
        ),
        150,
    )
    maximum = safe_float(
        get_value(
            owner,
            "max_price",
            rules.get("max_price", 400),
        ),
        400,
    )
    if minimum <= 0:
        minimum = 150.0
    if maximum < minimum:
        maximum = minimum
    return minimum, maximum


def _clamp_price(value: float, minimum: float, maximum: float) -> float:
    return round(min(max(float(value), minimum), maximum), 2)


async def estimate_price_with_ai(owner, answers) -> dict | None:
    """
    AI suggests a price from requirements, then we clamp to
    owner min/max. Returns None on failure so callers keep
    using the deterministic rule engine.
    """
    minimum, maximum = _owner_price_bounds(owner)
    business_name = clean_text(
        get_value(owner, "name", "Studio")
    )
    niche = clean_text(get_value(owner, "niche", ""))
    services = clean_text(
        get_value(owner, "services_text", "")
    )
    answers = answers or {}

    answers_block = "\n".join(
        f"- {key}: {clean_text(value)}"
        for key, value in answers.items()
        if clean_text(value)
    ) or "- (no answers)"

    system = (
        "You are a commercial pricing assistant for a real "
        "service business. Recommend a fair project price "
        "based only on the client requirements and the "
        "services this business actually offers. "
        "Never invent services. Stay inside the given "
        "min/max bounds. Respond with JSON only."
    )

    user = f"""
Business: {business_name}
Niche: {niche or "not specified"}
Services this business offers:
{services or "not specified"}

Price bounds (USD):
minimum = {minimum}
maximum = {maximum}

Client requirements:
{answers_block}

Return ONLY valid JSON with these keys:
{{
  "price": number,
  "complexity": "LOW" | "MEDIUM" | "HIGH",
  "reasoning": "one or two short sentences",
  "in_scope": ["deliverable or work item", "..."],
  "out_of_scope": ["item not needed or not offered", "..."]
}}

Rules:
- price must be between {minimum} and {maximum}
- in_scope only from client need + offered services
- out_of_scope = not needed or not offered
- no markdown, no extra text outside JSON
"""

    raw = await llm_chat(system, user, temperature=0.2)
    if not raw:
        return None

    # Extract JSON object even if model wraps it
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None

    try:
        data = json.loads(match.group(0))
    except (TypeError, ValueError, json.JSONDecodeError):
        return None

    price = safe_float(data.get("price"), 0)
    if price <= 0:
        return None

    price = _clamp_price(price, minimum, maximum)

    complexity = clean_text(
        data.get("complexity", "MEDIUM")
    ).upper()
    if complexity not in ("LOW", "MEDIUM", "HIGH"):
        complexity = "MEDIUM"

    in_scope = data.get("in_scope") or []
    out_of_scope = data.get("out_of_scope") or []
    if not isinstance(in_scope, list):
        in_scope = [str(in_scope)]
    if not isinstance(out_of_scope, list):
        out_of_scope = [str(out_of_scope)]

    reasoning = clean_text(
        data.get("reasoning", "")
    ) or (
        f"AI estimate clamped to owner bounds "
        f"({minimum:.2f}–{maximum:.2f})."
    )

    return {
        "price": price,
        "complexity": complexity,
        "reasoning": reasoning,
        "in_scope": [clean_text(x) for x in in_scope if clean_text(x)],
        "out_of_scope": [
            clean_text(x) for x in out_of_scope if clean_text(x)
        ],
        "min_price": minimum,
        "max_price": maximum,
    }


# =========================================================
# OPTIONAL AI PROVIDER — PROPOSAL
# =========================================================

async def generate_proposal(
    owner,
    answers,
    price,
    analysis=None,
):
    """
    Generate a scoped, business-fit proposal via LLM.

    Falls back to template_proposal if no key / failure.
    Never changes the approved price.
    """

    analysis = analysis or {}

    business_name = clean_text(
        get_value(owner, "name", "Business")
    )
    niche = clean_text(get_value(owner, "niche", ""))
    services = clean_text(
        get_value(owner, "services_text", "")
    )

    project = proposal_value(
        answers, "project", "Not specified."
    )
    requirements = proposal_value(
        answers, "requirements", "Not specified."
    )
    quantity = proposal_value(
        answers, "quantity", "Not specified."
    )
    deadline = proposal_value(
        answers, "deadline", "Not specified."
    )
    additional = proposal_value(
        answers, "additional", "None provided."
    )
    revision = clean_text(
        answers.get("client_revision_request", "")
    )

    in_scope = analysis.get("in_scope") or []
    out_of_scope = analysis.get("out_of_scope") or []
    reasoning = clean_text(
        analysis.get("internal_analysis", "")
    )

    in_scope_text = (
        "\n".join(f"- {item}" for item in in_scope)
        if in_scope
        else "- (derive carefully from client needs + offered services)"
    )
    out_scope_text = (
        "\n".join(f"- {item}" for item in out_of_scope)
        if out_of_scope
        else "- Work outside the agreed scope"
    )

    system = (
        "You write professional service-business proposals. "
        "Scope tightly to what the client needs and what this "
        "business actually offers. Never invent capabilities, "
        "volumes, dates, or deliverables. Never change the price."
    )

    user = f"""
Create a polished client proposal.

BUSINESS
Name: {business_name}
Niche: {niche or "not specified"}
Services offered:
{services or "not specified"}

CLIENT REQUEST
Project: {project}
Requirements: {requirements}
Size / quantity: {quantity}
Deadline: {deadline}
Additional: {additional}
Revision notes: {revision or "None"}

PRICING GUIDANCE (internal — do not over-explain)
{reasoning or "Price set within owner commercial bounds."}

SUGGESTED IN-SCOPE
{in_scope_text}

SUGGESTED OUT-OF-SCOPE
{out_scope_text}

APPROVED INVESTMENT (exact — do not change)
${float(price):.2f} USD

RULES
1. Use only information above.
2. Optimize for a real business fit: include what is needed,
   exclude what is not needed or not offered.
3. Do not invent numbers, menus, tech stacks, team size, or dates.
4. If a detail is missing, say it will be confirmed — do not invent it.
5. Price must appear as exactly ${float(price):.2f} USD.
6. Professional, clear language a client can approve.

Use these headings exactly:

Executive Summary
Project Scope
Client Requirements
Included Services & Deliverables
Out of Scope
Why This Fits
Timeline
Project Investment
Client Responsibilities
Payment Terms
Next Steps

Return ONLY the proposal text.
"""

    text = await llm_chat(system, user, temperature=0.35)

    if not text:
        return template_proposal(owner, answers, price)

    return text