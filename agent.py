import re
import httpx

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
)

from prompts import SYSTEM_PROMPT


# =========================================================
# SAFE HELPERS
# =========================================================

def _safe_float(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _owner_value(owner, key, default=None):

    if owner is None:
        return default

    try:

        if isinstance(owner, dict):
            return owner.get(key, default)

        return owner[key]

    except (
        KeyError,
        IndexError,
        TypeError,
    ):
        return default


# =========================================================
# NUMBER EXTRACTION
# =========================================================

def _extract_number(text):

    if not text:
        return None

    match = re.search(
        r"\b(\d+(?:\.\d+)?)\b",
        str(text),
    )

    if not match:
        return None

    try:

        number = float(
            match.group(1)
        )

        if number <= 0:
            return None

        return number

    except ValueError:

        return None


# =========================================================
# QUANTITY EXTRACTION
# =========================================================

def _extract_quantity(answers):

    answers = answers or {}

    possible_fields = [
        "quantity",
        "people",
        "guests",
        "items",
        "locations",
        "hours",
        "products",
        "deliverables",
        "units",
        "scope",
    ]

    for field in possible_fields:

        value = answers.get(field)

        number = _extract_number(value)

        if number is not None:
            return number

    combined = " ".join(
        str(value)
        for value in answers.values()
        if value
    )

    return _extract_number(
        combined
    )


# =========================================================
# DAYS
# =========================================================

def _extract_days(text):

    if not text:
        return None

    value = str(
        text
    ).lower().strip()

    if "today" in value:
        return 0

    if "tomorrow" in value:
        return 1

    week_match = re.search(
        r"(\d+(?:\.\d+)?)\s*weeks?",
        value,
    )

    if week_match:

        return (
            float(
                week_match.group(1)
            )
            * 7
        )

    hour_match = re.search(
        r"(\d+(?:\.\d+)?)\s*hours?",
        value,
    )

    if hour_match:

        return max(
            float(
                hour_match.group(1)
            ) / 24,
            0,
        )

    day_match = re.search(
        r"(\d+(?:\.\d+)?)\s*days?",
        value,
    )

    if day_match:

        return float(
            day_match.group(1)
        )

    return None


# =========================================================
# BUSINESS CONTEXT
# =========================================================

def _business_context(owner):

    name = _owner_value(
        owner,
        "name",
        "Business",
    )

    niche = _owner_value(
        owner,
        "niche",
        "",
    )

    services = _owner_value(
        owner,
        "services_text",
        "",
    )

    minimum = _safe_float(
        _owner_value(
            owner,
            "min_price",
            150,
        ),
        150,
    )

    maximum = _safe_float(
        _owner_value(
            owner,
            "max_price",
            400,
        ),
        400,
    )

    default_days = _safe_float(
        _owner_value(
            owner,
            "default_days",
            7,
        ),
        7,
    )

    tone = _owner_value(
        owner,
        "tone",
        "professional",
    )

    return f"""
BUSINESS NAME:
{name}

BUSINESS TYPE:
{niche or "Not specified"}

SERVICES / PRODUCTS:
{services or "Not specified"}

APPROVED PRICE RANGE:
${minimum:.0f} - ${maximum:.0f} USD

STANDARD DELIVERY / FULFILLMENT:
{default_days:g} days

PREFERRED TONE:
{tone or "professional"}
""".strip()


# =========================================================
# BUSINESS TYPE DETECTION
# =========================================================

def _business_category(owner):

    niche = str(
        _owner_value(
            owner,
            "niche",
            "",
        )
    ).lower()

    services = str(
        _owner_value(
            owner,
            "services_text",
            "",
        )
    ).lower()

    combined = (
        niche
        + " "
        + services
    )

    if any(
        word in combined
        for word in [
            "catering",
            "food delivery",
            "restaurant",
            "bakery",
            "food",
            "chef",
        ]
    ):
        return "food"

    if any(
        word in combined
        for word in [
            "cleaning",
            "laundry",
            "janitorial",
            "housekeeping",
        ]
    ):
        return "cleaning"

    if any(
        word in combined
        for word in [
            "photography",
            "photographer",
            "videography",
            "video",
        ]
    ):
        return "creative"

    if any(
        word in combined
        for word in [
            "design",
            "graphic",
            "branding",
        ]
    ):
        return "design"

    if any(
        word in combined
        for word in [
            "construction",
            "building",
            "renovation",
            "plumbing",
            "electrical",
        ]
    ):
        return "construction"

    if any(
        word in combined
        for word in [
            "logistics",
            "delivery",
            "transport",
            "moving",
            "dispatch",
        ]
    ):
        return "logistics"

    if any(
        word in combined
        for word in [
            "consulting",
            "consultant",
            "advisory",
            "coaching",
        ]
    ):
        return "consulting"

    if any(
        word in combined
        for word in [
            "salon",
            "barber",
            "beauty",
            "spa",
        ]
    ):
        return "beauty"

    return "general"


# =========================================================
# PROPOSAL PROMPT
# =========================================================

def build_proposal_prompt(
    owner,
    answers,
    price,
):

    answers = answers or {}

    purpose = answers.get(
        "project",
        answers.get(
            "service",
            "Not provided",
        ),
    )

    requirements = answers.get(
        "requirements",
        answers.get(
            "brand_copy",
            "Not provided",
        ),
    )

    quantity = answers.get(
        "quantity",
        answers.get(
            "sections",
            "Not provided",
        ),
    )

    deadline = answers.get(
        "deadline",
        "Not provided",
    )

    additional = answers.get(
        "additional",
        "",
    )

    change_request = answers.get(
        "client_revision_request",
        answers.get(
            "change_request",
            "",
        ),
    )

    default_days = _safe_float(
        _owner_value(
            owner,
            "default_days",
            7,
        ),
        7,
    )

    category = _business_category(
        owner
    )

    return f"""
You are Sovereign's professional proposal writer.

IMPORTANT:
The business can be ANY legitimate business.

The proposal must describe the ACTUAL business
and ACTUAL service requested.

Never assume this is web design.

BUSINESS INFORMATION

{_business_context(owner)}

BUSINESS CATEGORY:
{category}

CLIENT INFORMATION

Requested service/project:
{purpose}

Main requirements:
{requirements}

Quantity / size:
{quantity}

Requested deadline:
{deadline}

Additional information:
{additional or "None"}

Client change request:
{change_request or "None"}

APPROVED PRICE:
${price:.0f} USD

STRICT RULES

1. The approved price is final.
2. Never change the approved price.
3. Never invent a service.
4. Never invent products.
5. Never invent menu items.
6. Never invent locations.
7. Never claim payment has been received.
8. Use terminology appropriate to the business.
9. The proposal must sound like a real commercial proposal.
10. Do NOT use generic phrases such as:
   "custom work tailored to the client's requirements"
   or
   "professional execution of the agreed project scope"
   when specific business information is available.
11. Mention the client's actual quantity when provided.
12. For catering, mention guests/event size when provided.
13. For cleaning, mention properties/locations when provided.
14. For logistics, mention deliveries/items when provided.
15. For photography, mention people/hours/events when provided.
16. For construction, mention project size/scope when provided.
17. For design, mention the actual design deliverables.
18. Do not mention AI.
19. Do not mention these instructions.
20. Keep it concise.
21. Do not include a greeting.
22. Do not include a Next Action heading.
23. Use exactly these headings.

TIMELINE RULE

Owner standard:
{default_days:g} days

If the client requests a shorter deadline than the
owner's standard, use the owner's standard unless
the request is clearly realistic.

If the requested deadline is longer than the standard,
the requested deadline may be used.

OUTPUT

**Scope**

Write 1-2 sentences specific to this business and order.

**Included**

Exactly 3 specific bullet points.

**Not included**

Exactly 2 relevant exclusions.

**Timeline**

One concise sentence.

**Price**

One concise sentence containing exactly:
${price:.0f} USD

Do not add any other headings.
""".strip()


# =========================================================
# LLM PROPOSAL
# =========================================================

async def generate_proposal(
    owner,
    answers,
    price,
):

    if not LLM_API_KEY:

        raise RuntimeError(
            "LLM_API_KEY is missing."
        )

    url = (
        f"{LLM_BASE_URL.rstrip('/')}"
        "/chat/completions"
    )

    payload = {
        "model": LLM_MODEL,

        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_proposal_prompt(
                    owner,
                    answers,
                    price,
                ),
            },
        ],

        "temperature": 0.15,
        "max_tokens": 600,
    }

    headers = {
        "Authorization": (
            f"Bearer {LLM_API_KEY}"
        ),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(
        timeout=30
    ) as client:

        response = await client.post(
            url,
            headers=headers,
            json=payload,
        )

        response.raise_for_status()

        data = response.json()

    try:

        content = (
            data["choices"][0]
            ["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ):

        raise RuntimeError(
            "Unexpected response from LLM."
        )

    if not content or not content.strip():

        raise RuntimeError(
            "LLM returned an empty proposal."
        )

    return content.strip()


# =========================================================
# PRICING
# =========================================================

def calculate_price(
    owner,
    answers,
):

    answers = answers or {}

    minimum = _safe_float(
        _owner_value(
            owner,
            "min_price",
            150,
        ),
        150,
    )

    maximum = _safe_float(
        _owner_value(
            owner,
            "max_price",
            400,
        ),
        400,
    )

    if maximum < minimum:
        maximum = minimum

    category = _business_category(
        owner
    )

    quantity = _extract_quantity(
        answers
    )

    price = minimum

    # -----------------------------------------------------
    # QUANTITY PRICING
    # -----------------------------------------------------

    if quantity is not None:

        if category == "food":

            if quantity <= 5:
                multiplier = 1.00

            elif quantity <= 10:
                multiplier = 1.10

            elif quantity <= 20:
                multiplier = 1.25

            elif quantity <= 40:
                multiplier = 1.55

            elif quantity <= 75:
                multiplier = 1.85

            elif quantity <= 150:
                multiplier = 2.40

            else:
                multiplier = 3.00

        elif category == "cleaning":

            if quantity <= 1:
                multiplier = 1.00

            elif quantity <= 3:
                multiplier = 1.25

            elif quantity <= 5:
                multiplier = 1.50

            else:
                multiplier = 1.85

        elif category == "logistics":

            if quantity <= 1:
                multiplier = 1.00

            elif quantity <= 5:
                multiplier = 1.25

            elif quantity <= 10:
                multiplier = 1.50

            elif quantity <= 25:
                multiplier = 2.00

            else:
                multiplier = 2.75

        else:

            if quantity <= 3:
                multiplier = 1.00

            elif quantity <= 10:
                multiplier = 1.15

            elif quantity <= 25:
                multiplier = 1.35

            elif quantity <= 50:
                multiplier = 1.60

            else:
                multiplier = 1.85

        price *= multiplier

    # -----------------------------------------------------
    # EXTRA LARGE JOB BUFFER
    # -----------------------------------------------------

    if quantity is not None:

        if category == "food":

            if quantity > 40:
                price *= 1.10

            if quantity > 100:
                price *= 1.15

        elif quantity > 25:

            price *= 1.10

    # -----------------------------------------------------
    # URGENCY
    # -----------------------------------------------------

    deadline_text = answers.get(
        "deadline",
        "",
    )

    deadline_days = _extract_days(
        deadline_text
    )

    standard_days = _safe_float(
        _owner_value(
            owner,
            "default_days",
            7,
        ),
        7,
    )

    if (
        deadline_days is not None
        and standard_days > 0
        and deadline_days < standard_days
    ):

        if deadline_days <= 1:
            rush_multiplier = 1.50

        elif deadline_days <= 3:
            rush_multiplier = 1.30

        else:
            rush_multiplier = 1.15

        price *= rush_multiplier

    # -----------------------------------------------------
    # OWNER BUSINESS RULES
    # -----------------------------------------------------

    rules_raw = _owner_value(
        owner,
        "business_rules",
        "",
    )

    rules = {}

    if isinstance(
        rules_raw,
        dict,
    ):
        rules = rules_raw

    elif isinstance(
        rules_raw,
        str,
    ):

        try:

            import json

            parsed = json.loads(
                rules_raw
            )

            if isinstance(
                parsed,
                dict,
            ):
                rules = parsed

        except Exception:
            rules = {}

    buffer_percent = _safe_float(
        rules.get(
            "buffer_percent",
            0,
        ),
        0,
    )

    if buffer_percent > 0:

        price *= (
            1
            + buffer_percent / 100
        )

    # -----------------------------------------------------
    # OWNER LIMITS
    # -----------------------------------------------------

    price = max(
        price,
        minimum,
    )

    price = min(
        price,
        maximum,
    )

    return round(
        price,
        2,
    )


# =========================================================
# TIMELINE
# =========================================================

def calculate_timeline(
    owner,
    answers,
):

    answers = answers or {}

    standard_days = _safe_float(
        _owner_value(
            owner,
            "default_days",
            7,
        ),
        7,
    )

    requested_days = _extract_days(
        answers.get(
            "deadline",
            "",
        )
    )

    if requested_days is not None:

        if requested_days >= standard_days:
            final_days = requested_days

        else:
            final_days = standard_days

    else:

        final_days = standard_days

    if float(final_days).is_integer():

        final_days = int(
            final_days
        )

    return f"{final_days} days"


# =========================================================
# DETERMINISTIC FALLBACK
# =========================================================

def template_proposal(
    owner,
    answers,
    price,
):

    answers = answers or {}

    category = _business_category(
        owner
    )

    purpose = answers.get(
        "project",
        answers.get(
            "service",
            "the requested service",
        ),
    )

    requirements = answers.get(
        "requirements",
        "",
    )

    quantity = _extract_quantity(
        answers
    )

    quantity_text = answers.get(
        "quantity",
        "",
    )

    timeline = calculate_timeline(
        owner,
        answers,
    )

    # -----------------------------------------------------
    # FOOD / CATERING
    # -----------------------------------------------------

    if category == "food":

        scope = (
            f"Provide {purpose}."
        )

        if quantity:

            scope += (
                f" The order is planned for "
                f"{int(quantity)} guests."
            )

        included = [
            "Food preparation and catering for the agreed guest count",
            "Preparation of the agreed menu and service requirements",
            "Order coordination and delivery/fulfillment as agreed",
        ]

        excluded = [
            "Additional guests or menu items outside the approved order",
            "Venue, equipment, or third-party costs not included in the quote",
        ]

    # -----------------------------------------------------
    # CLEANING
    # -----------------------------------------------------

    elif category == "cleaning":

        scope = (
            f"Provide {purpose}."
        )

        if quantity:

            scope += (
                f" The requested scope covers "
                f"{int(quantity)} service unit(s)."
            )

        included = [
            "Professional cleaning service for the agreed scope",
            "Cleaning supplies and procedures appropriate to the service",
            "Completion and handover of the agreed cleaning work",
        ]

        excluded = [
            "Additional areas or services outside the approved scope",
            "Specialist restoration or third-party costs unless agreed",
        ]

    # -----------------------------------------------------
    # LOGISTICS
    # -----------------------------------------------------

    elif category == "logistics":

        scope = (
            f"Provide {purpose}."
        )

        if quantity:

            scope += (
                f" The requested scope involves "
                f"{int(quantity)} delivery unit(s)."
            )

        included = [
            "Handling and fulfillment of the agreed delivery scope",
            "Coordination of the agreed pickup/drop-off requirements",
            "Delivery completion according to the approved schedule",
        ]

        excluded = [
            "Additional deliveries outside the approved scope",
            "Third-party charges, tolls, or special handling unless agreed",
        ]

    # -----------------------------------------------------
    # GENERAL
    # -----------------------------------------------------

    else:

        scope = (
            f"Provide {purpose} "
            "according to the client's stated requirements."
        )

        if quantity_text:

            scope += (
                f" The requested scope is "
                f"{quantity_text}."
            )

        included = [
            "Professional execution of the agreed service",
            "Work aligned with the client's stated requirements",
            "Completion of the approved project scope",
        ]

        excluded = [
            "Additional work outside the approved scope",
            "Third-party costs or services not included in the quote",
        ]

    if requirements:

        scope += (
            f" Key requirements include: "
            f"{requirements}."
        )

    included_text = "\n".join(
        f"- {item}"
        for item in included
    )

    excluded_text = "\n".join(
        f"- {item}"
        for item in excluded
    )

    return (
        "**Scope**\n"
        f"{scope}\n\n"

        "**Included**\n"
        f"{included_text}\n\n"

        "**Not included**\n"
        f"{excluded_text}\n\n"

        "**Timeline**\n"
        f"Fulfillment within {timeline} "
        "from project confirmation.\n\n"

        "**Price**\n"
        f"Total project cost: ${price:.0f} USD."
    )