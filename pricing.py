"""
Business-agnostic deterministic pricing engine.

The AI may extract facts from a client request, but it must NOT invent
commercial pricing.

All pricing authority comes from owner-configured rules.
"""

from __future__ import annotations

import math


# =========================================================
# DEFAULT PRICING RULES
# =========================================================

DEFAULT_PRICING_RULES = {
    "enabled": True,

    # Supported:
    # fixed
    # per_unit
    # base_plus_unit
    # hourly
    "model": "base_plus_unit",

    "currency": "USD",

    "base_fee": 0.0,

    "unit": {
        "name": "unit",
        "price": 0.0,
    },

    "minimum": 0.0,
    "maximum": 0.0,

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


# =========================================================
# HELPERS
# =========================================================

def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _integer(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _merge_dict(default, custom):
    if not isinstance(custom, dict):
        return dict(default)

    result = dict(default)

    for key, value in custom.items():

        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _merge_dict(
                result[key],
                value,
            )

        else:
            result[key] = value

    return result


def normalize_pricing_rules(rules=None):
    """
    Accepts either:

        {
            "pricing": {...}
        }

    or directly:

        {
            "model": "...",
            ...
        }
    """

    if not isinstance(rules, dict):
        rules = {}

    if "pricing" in rules:
        pricing = rules.get("pricing", {})
    else:
        pricing = rules

    if not isinstance(pricing, dict):
        pricing = {}

    return _merge_dict(
        DEFAULT_PRICING_RULES,
        pricing,
    )


# =========================================================
# CLIENT FACTS
# =========================================================

def normalize_client_facts(
    quantity=None,
    unit=None,
    hours=None,
    deadline_days=None,
    complexity=None,
):
    return {
        "quantity": _number(quantity, 0),
        "unit": str(unit).strip() if unit else "",
        "hours": _number(hours, 0),
        "deadline_days": _integer(deadline_days, 0),
        "complexity": (
            str(complexity).strip().lower()
            if complexity
            else ""
        ),
    }


# =========================================================
# CONDITIONS
# =========================================================

def _condition_matches(condition, facts):

    if not condition:
        return False

    condition = str(condition).strip().lower()

    quantity = facts.get("quantity", 0)
    hours = facts.get("hours", 0)
    deadline_days = facts.get("deadline_days", 0)
    complexity = facts.get("complexity", "")

    conditions = {
        "rush": (
            deadline_days > 0
            and deadline_days <= 3
        ),

        "quantity_gt_10": quantity > 10,
        "quantity_gt_20": quantity > 20,
        "quantity_gt_50": quantity > 50,

        "complexity_low": complexity == "low",
        "complexity_medium": complexity == "medium",
        "complexity_high": complexity == "high",

        "hours_gt_8": hours > 8,
    }

    return conditions.get(
        condition,
        False,
    )


# =========================================================
# ADJUSTMENTS
# =========================================================

def calculate_adjustments(
    subtotal,
    adjustments,
    facts,
):
    current = float(subtotal)

    applied = []

    if not isinstance(adjustments, list):
        return current, applied

    for adjustment in adjustments:

        if not isinstance(adjustment, dict):
            continue

        name = str(
            adjustment.get(
                "name",
                "Adjustment",
            )
        ).strip()

        adjustment_type = str(
            adjustment.get(
                "type",
                "percentage",
            )
        ).strip().lower()

        value = _number(
            adjustment.get("value", 0),
            0,
        )

        condition = adjustment.get(
            "condition",
            "",
        )

        if condition and not _condition_matches(
            condition,
            facts,
        ):
            continue

        before = current

        if adjustment_type == "percentage":

            current += (
                current
                * value
                / 100
            )

        elif adjustment_type == "fixed":

            current += value

        else:
            continue

        applied.append(
            {
                "name": name,
                "type": adjustment_type,
                "value": value,
                "before": round(before, 2),
                "after": round(current, 2),
            }
        )

    return current, applied


# =========================================================
# ROUNDING
# =========================================================

def round_price(price, rounding_rules):

    if not isinstance(rounding_rules, dict):
        return round(price, 2)

    if not bool(
        rounding_rules.get(
            "enabled",
            False,
        )
    ):
        return round(price, 2)

    nearest = _number(
        rounding_rules.get(
            "nearest",
            1,
        ),
        1,
    )

    if nearest <= 0:
        nearest = 1

    return round(
        math.ceil(price / nearest) * nearest,
        2,
    )


# =========================================================
# MAIN CALCULATOR
# =========================================================

def calculate_price(
    pricing_rules=None,
    quantity=None,
    unit=None,
    hours=None,
    deadline_days=None,
    complexity=None,
    manual_price=None,
):
    """
    Calculate price using ONLY owner-configured pricing rules.
    """

    rules = normalize_pricing_rules(
        pricing_rules
    )

    facts = normalize_client_facts(
        quantity=quantity,
        unit=unit,
        hours=hours,
        deadline_days=deadline_days,
        complexity=complexity,
    )

    currency = str(
        rules.get(
            "currency",
            "USD",
        )
    ).upper()

    model = str(
        rules.get(
            "model",
            "base_plus_unit",
        )
    ).lower()

    if not rules.get("enabled", True):

        return {
            "success": False,
            "requires_owner_input": True,
            "reason": "Pricing is not enabled.",
            "currency": currency,
            "price": None,
            "facts": facts,
        }

    base_fee = _number(
        rules.get(
            "base_fee",
            0,
        )
    )

    unit_config = rules.get(
        "unit",
        {},
    )

    if not isinstance(unit_config, dict):
        unit_config = {}

    unit_name = str(
        unit_config.get(
            "name",
            "unit",
        )
    )

    unit_price = _number(
        unit_config.get(
            "price",
            0,
        )
    )

    quantity_value = facts["quantity"]
    hours_value = facts["hours"]

    # =====================================================
    # FIXED
    # =====================================================

    if model == "fixed":

        if base_fee <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "The owner has not configured "
                    "a valid fixed price."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        subtotal = base_fee

    # =====================================================
    # PER UNIT
    # =====================================================

    elif model == "per_unit":

        if quantity_value <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "A valid quantity is required "
                    "for per-unit pricing."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        if unit_price <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "The owner has not configured "
                    "a valid unit price."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        subtotal = (
            quantity_value * unit_price
        )

    # =====================================================
    # BASE + UNIT
    # =====================================================

    elif model == "base_plus_unit":

        if quantity_value <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "A valid quantity is required "
                    "for base-plus-unit pricing."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        if unit_price <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "The owner has not configured "
                    "a valid unit price."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        subtotal = (
            base_fee
            + (
                quantity_value * unit_price
            )
        )

    # =====================================================
    # HOURLY
    # =====================================================

    elif model == "hourly":

        if hours_value <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "A valid number of hours "
                    "is required."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        if unit_price <= 0:

            return {
                "success": False,
                "requires_owner_input": True,
                "reason": (
                    "The owner has not configured "
                    "a valid hourly price."
                ),
                "currency": currency,
                "price": None,
                "facts": facts,
            }

        subtotal = (
            base_fee
            + (
                hours_value * unit_price
            )
        )

    else:

        return {
            "success": False,
            "requires_owner_input": True,
            "reason": (
                f"Unsupported pricing model: {model}"
            ),
            "currency": currency,
            "price": None,
            "facts": facts,
        }

    # =====================================================
    # ADJUSTMENTS
    # =====================================================

    adjusted_price, applied_adjustments = (
        calculate_adjustments(
            subtotal,
            rules.get(
                "adjustments",
                [],
            ),
            facts,
        )
    )

    # =====================================================
    # MIN / MAX
    # =====================================================

    minimum = _number(
        rules.get(
            "minimum",
            0,
        )
    )

    maximum = _number(
        rules.get(
            "maximum",
            0,
        )
    )

    price_before_limits = adjusted_price

    minimum_applied = False
    maximum_reached = False

    owner_approval = rules.get(
        "owner_approval",
        {},
    )

    if not isinstance(owner_approval, dict):
        owner_approval = {}

    owner_approval_required = bool(
        owner_approval.get(
            "required",
            True,
        )
    )

    if minimum > 0 and adjusted_price < minimum:

        adjusted_price = minimum
        minimum_applied = True

        if owner_approval.get(
            "required_below_minimum",
            True,
        ):
            owner_approval_required = True

    if maximum > 0 and adjusted_price > maximum:

        maximum_reached = True

        if owner_approval.get(
            "required_above_maximum",
            True,
        ):
            owner_approval_required = True

    # =====================================================
    # ROUND
    # =====================================================

    calculated_price = round_price(
        adjusted_price,
        rules.get(
            "rounding",
            {},
        ),
    )

    # =====================================================
    # MANUAL OVERRIDE
    # =====================================================

    override_used = False

    if manual_price is not None:

        manual_value = _number(
            manual_price,
            -1,
        )

        if manual_value >= 0:

            calculated_price = round(
                manual_value,
                2,
            )

            override_used = True

            if owner_approval.get(
                "required_for_manual_override",
                True,
            ):
                owner_approval_required = True

    # =====================================================
    # RESULT
    # =====================================================

    return {
        "success": True,
        "requires_owner_input": False,

        "owner_approval_required": (
            owner_approval_required
        ),

        "currency": currency,
        "model": model,
        "price": calculated_price,

        "subtotal": round(
            subtotal,
            2,
        ),

        "price_before_limits": round(
            price_before_limits,
            2,
        ),

        "minimum": minimum,
        "maximum": maximum,

        "minimum_applied": minimum_applied,
        "maximum_reached": maximum_reached,

        "manual_override": override_used,

        "facts": facts,

        "pricing_inputs": {
            "base_fee": base_fee,
            "unit_name": unit_name,
            "unit_price": unit_price,
        },

        "adjustments": applied_adjustments,

        "rules": rules,
    }


# =========================================================
# HUMAN READABLE BREAKDOWN
# =========================================================

def format_price_breakdown(result):

    if not result.get("success"):

        return result.get(
            "reason",
            "Unable to calculate price.",
        )

    currency = result.get(
        "currency",
        "USD",
    )

    price = result.get(
        "price",
        0,
    )

    lines = []

    lines.append(
        f"Pricing model: "
        f"{result.get('model', '')}"
    )

    inputs = result.get(
        "pricing_inputs",
        {},
    )

    base_fee = inputs.get(
        "base_fee",
        0,
    )

    unit_name = inputs.get(
        "unit_name",
        "unit",
    )

    unit_price = inputs.get(
        "unit_price",
        0,
    )

    facts = result.get(
        "facts",
        {},
    )

    quantity = facts.get(
        "quantity",
        0,
    )

    if base_fee:

        lines.append(
            f"Base fee: "
            f"{currency} {base_fee:,.2f}"
        )

    if quantity and unit_price:

        lines.append(
            f"{quantity:g} {unit_name} × "
            f"{currency} {unit_price:,.2f}"
        )

    for adjustment in result.get(
        "adjustments",
        [],
    ):

        lines.append(
            f"{adjustment['name']}: "
            f"{adjustment['type']} "
            f"{adjustment['value']:g}"
        )

    if result.get("minimum_applied"):

        lines.append(
            "Minimum project fee applied."
        )

    if result.get("maximum_reached"):

        lines.append(
            "Maximum configured quote reached."
        )

    lines.append(
        f"Final calculated price: "
        f"{currency} {price:,.2f}"
    )

    if result.get(
        "owner_approval_required"
    ):

        lines.append(
            "Owner approval required."
        )

    return "\n".join(lines)