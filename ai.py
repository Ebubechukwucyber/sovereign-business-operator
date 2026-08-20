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
# OPTIONAL AI PROVIDER
# =========================================================

async def generate_proposal(
    owner,
    answers,
    price,
):
    """
    Generate a professional proposal using OpenAI.

    If no provider is configured or the provider fails,
    return the deterministic proposal template.
    """

    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:

        return template_proposal(
            owner,
            answers,
            price,
        )

    try:

        from openai import AsyncOpenAI

    except ImportError:

        return template_proposal(
            owner,
            answers,
            price,
        )

    business_name = clean_text(
        get_value(
            owner,
            "name",
            "Business",
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
        "Not specified.",
    )

    requirements = proposal_value(
        answers,
        "requirements",
        "Not specified.",
    )

    quantity = proposal_value(
        answers,
        "quantity",
        "Not specified.",
    )

    deadline = proposal_value(
        answers,
        "deadline",
        "Not specified.",
    )

    additional = proposal_value(
        answers,
        "additional",
        "None provided.",
    )

    revision = clean_text(
        answers.get(
            "client_revision_request",
            "",
        )
    )

    prompt = f"""
You are a professional business proposal writer.

Create a polished proposal for a real client.

BUSINESS INFORMATION
Business name:
{business_name}

Services offered by the business:
{services}

CLIENT PROJECT INFORMATION
Project/service requested:
{project}

Main requirements:
{requirements}

Quantity / project size:
{quantity}

Requested deadline:
{deadline}

Additional information:
{additional}

Client revision request:
{revision or "None"}

APPROVED PROJECT INVESTMENT
${float(price):.2f} USD

IMPORTANT RULES

1. Use ONLY information provided above.
2. Do NOT invent guest numbers, menu items, food types,
   venues, locations, equipment, staffing, delivery charges,
   technical specifications, materials, dates or deliverables.
3. Do not assume something simply because it is common for
   this type of project.
4. If an important detail was not provided, describe it as
   something to be confirmed rather than inventing it.
5. The approved project investment is exactly:
   ${float(price):.2f} USD.
6. Never change the price.
7. Never create a different currency.
8. Do not describe optional services as included.
9. Make the proposal specific to the client's actual request.
10. Do not simply repeat the client's first sentence in every
    section.
11. Write in professional business language.
12. Keep the proposal clear enough for a client to approve.

PROPOSAL STRUCTURE

Use these exact headings:

Executive Summary

Project Scope

Client Requirements

Included Services & Deliverables

Timeline

Project Investment

Exclusions

Client Responsibilities

Payment Terms

Next Steps

CONTENT GUIDANCE

Executive Summary:
Briefly explain what the client is asking the business to
provide and the purpose of the proposal.

Project Scope:
Translate the client's request into a clear description of
the work. Do not invent details.

Client Requirements:
Summarize the actual requirements supplied by the client.

Included Services & Deliverables:
Describe only what can reasonably be included from the supplied
information. If a specific deliverable has not been confirmed,
say it will be confirmed rather than inventing it.

Timeline:
Use the requested deadline exactly when supplied. Do not
invent a different date. If the client gave a relative timeline,
preserve it accurately.

Project Investment:
State exactly:
${float(price):.2f} USD

Exclusions:
State that work outside the agreed scope and unapproved
additional services are excluded.

Client Responsibilities:
Explain that the client must provide accurate information,
requirements, approvals and other necessary information.

Payment Terms:
State that work begins after payment has been verified through
the business's approved payment process.

Next Steps:
Tell the client to review, approve, complete payment and then
proceed with the project.

Return ONLY the proposal text.
"""

    try:

        client = AsyncOpenAI(
            api_key=api_key
        )

        response = await client.responses.create(
            model=os.getenv(
                "OPENAI_MODEL",
                "gpt-5-mini",
            ),
            input=prompt,
        )

        text = clean_text(
            getattr(
                response,
                "output_text",
                "",
            )
        )

        if not text:

            return template_proposal(
                owner,
                answers,
                price,
            )

        return text

    except Exception:

        return template_proposal(
            owner,
            answers,
            price,
        )