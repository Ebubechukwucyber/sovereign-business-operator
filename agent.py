import httpx

from config import (
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
)

from prompts import SYSTEM_PROMPT


def build_proposal_prompt(
    owner,
    answers: dict,
    price: float,
) -> str:

    return f"""
Create a professional client business proposal for a landing-page project.

Studio:
{owner["name"]}

Client requirements:
- Page purpose: {answers.get("page_for", "Not provided")}
- Number of pages/sections: {answers.get("sections", "Not provided")}
- Deadline: {answers.get("deadline", "Not provided")}
- Existing copy/brand: {answers.get("brand_copy", "Not provided")}
- Client budget: {answers.get("budget", "Not provided")}

APPROVED PROJECT PRICE:
${price:.0f} USD

APPROVED DELIVERY TIME:
{owner["default_days"]} days

IMPORTANT RULES:

1. Never change the approved price.
2. Never change the approved delivery time.
3. Never claim payment has been received.
4. Never invent services.
5. Keep the proposal professional and commercially realistic.
6. Keep it under 150 words.
7. Do not include a greeting.
8. Do not include a "Next action" section.
9. Do not mention that AI was used.
10. Use proper grammar.

Use exactly these headings:

**Scope**

One or two concise sentences describing the project.

**Included**

Provide exactly 3 concise bullet points.

**Not included**

Provide exactly 2 concise bullet points.

**Timeline**

One concise sentence.

**Price**

One concise sentence containing the approved price.

IMPORTANT GRAMMAR RULE:

If the client says "4 sections", write:

"4-section landing page"

NOT:

"4 landing page"

Do not add any other sections.
"""


async def generate_proposal(
    owner,
    answers: dict,
    price: float,
) -> str:

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

        "temperature": 0.2,

        "max_tokens": 500,
    }

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
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

        content = data["choices"][0]["message"]["content"]

    except (KeyError, IndexError, TypeError):

        raise RuntimeError(
            "Unexpected response from LLM."
        )

    if not content:

        raise RuntimeError(
            "LLM returned an empty proposal."
        )

    return content.strip()


def calculate_price(
    owner,
    answers: dict,
) -> float:

    """
    Deterministic pricing.

    Base:
        $150 for a simple landing page.

    Extra:
        +$50 per additional major section.

    Rush:
        +40% when deadline is under 3 days.

    Finally:
        Respect owner's configured min/max price.
    """

    # -----------------------------------------------------
    # BASE PRICE
    # -----------------------------------------------------

    price = 150.0

    # -----------------------------------------------------
    # SECTION COUNT
    # -----------------------------------------------------

    sections_text = str(
        answers.get(
            "sections",
            "",
        )
    ).lower()

    section_count = None

    # Try to find a number.
    for word in (
        sections_text
        .replace(",", " ")
        .replace("-", " ")
        .split()
    ):

        try:

            number = int(word)

            if number > 0:

                section_count = number

                break

        except ValueError:

            continue

    # Extra sections.
    if section_count:

        extra_sections = max(
            section_count - 1,
            0,
        )

        price += (
            extra_sections * 50
        )

    # -----------------------------------------------------
    # RUSH PRICE
    # -----------------------------------------------------

    deadline = str(
        answers.get(
            "deadline",
            "",
        )
    ).lower()

    rush_terms = [
        "today",
        "tomorrow",
        "1 day",
        "2 days",
        "48 hours",
        "24 hours",
    ]

    is_rush = any(
        term in deadline
        for term in rush_terms
    )

    if is_rush:

        price *= 1.40

    # -----------------------------------------------------
    # OWNER PRICE LIMITS
    # -----------------------------------------------------

    try:

        minimum = float(
            owner["min_price"]
        )

    except (
        TypeError,
        ValueError,
    ):

        minimum = 150.0

    try:

        maximum = float(
            owner["max_price"]
        )

    except (
        TypeError,
        ValueError,
    ):

        maximum = 400.0

    # Minimum.
    price = max(
        price,
        minimum,
    )

    # Maximum.
    price = min(
        price,
        maximum,
    )

    return round(
        price,
        2,
    )


def template_proposal(
    owner,
    answers: dict,
    price: float,
) -> str:

    """
    Deterministic fallback if the LLM fails.
    This ensures the business flow still works.
    """

    purpose = answers.get(
        "page_for",
        "your business",
    )

    sections = answers.get(
        "sections",
        "requested",
    )

    # Make the grammar sensible.
    sections_text = str(
        sections
    ).strip()

    if sections_text:

        scope = (
            f"Design and develop a "
            f"{sections_text}-section landing page "
            f"for {purpose}."
        )

    else:

        scope = (
            f"Design and develop a professional "
            f"landing page for {purpose}."
        )

    return (
        "**Scope**\n"
        f"{scope}\n\n"

        "**Included**\n"
        "- Landing page structure and layout\n"
        "- Responsive desktop and mobile design\n"
        "- Content and section structure\n\n"

        "**Not included**\n"
        "- Domain and hosting costs\n"
        "- Logo or full brand identity development\n\n"

        "**Timeline**\n"
        f"{owner['default_days']} days.\n\n"

        "**Price**\n"
        f"${price:.0f} USD."
    )