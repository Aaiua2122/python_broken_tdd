"""Order checkout.

The rules live in `src/shop/specs/checkout.md` - read it first.
Both functions below are stubs: their signature is final, the bodies are yours.
Do not change the constants: the tests rely on them.
"""

import re
import sys

from shop.money import percent_of

PROMO_CODES = {"WELCOME10": 10, "SUMMER15": 15, "VIP35": 35}
SUPPORTED_CITIES = ("msk", "spb")
MAX_DISCOUNT_PERCENT = 30
VAT_PERCENT = 20
SHIPPING_KOPEKS = 49_000
FREE_DELIVERY_FROM_KOPEKS = 500_000
TIER_DISCOUNTS = ((10, 5), (25, 10), (50, 15))


def _parse_integer(value: str) -> int | None:
    text = value.strip()
    if re.fullmatch(r"[+-]?\d(?:_?\d)*", text) is None:
        return None
    # Respect int()'s conversion limit without catching ValueError.
    digit_limit = sys.get_int_max_str_digits()
    digits = text.lstrip("+-").replace("_", "")
    if digit_limit and len(digits) > digit_limit:
        return None
    return int(text)


def _validate_line(item: dict[str, str], position: int) -> str | None:
    for key in ("sku", "qty", "unit_price_kopecks"):
        if key not in item:
            return f"Line {position}: missing key {key}"
    if item["sku"] == "":
        return f"Line {position}: SKU is empty"
    qty = _parse_integer(item["qty"])
    if qty is None or qty <= 0:
        return f"Line {position}: quantity must be a positive integer"
    price = _parse_integer(item["unit_price_kopecks"])
    if price is None or price < 0:
        return f"Line {position}: price must be a non-negative integer"
    return None


def validate_order(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> str | None:
    """Return a human readable reason why the order is invalid, or None if it is fine."""
    if not lines:
        return "Order is empty"
    seen: list[str] = []
    for position, item in enumerate(lines, start=1):
        reason = _validate_line(item, position)
        if reason is not None:
            return reason
        if item["sku"] in seen:
            return f"Line {position}: duplicate SKU"
        seen.append(item["sku"])
    if promo_code and promo_code not in PROMO_CODES:
        return "Unknown promo code"
    if shipping_city and shipping_city not in SUPPORTED_CITIES:
        return "Unsupported shipping city"
    return None


def calculate_order_total(
    lines: list[dict[str, str]],
    promo_code: str = "",
    shipping_city: str = "",
) -> int | None:
    """Return the order total in kopecks, or None if the order is invalid."""
    if validate_order(lines, promo_code, shipping_city) is not None:
        return None
    subtotal = sum(int(item["qty"]) * int(item["unit_price_kopecks"]) for item in lines)
    quantity = sum(int(item["qty"]) for item in lines)
    tier_discount = 0
    for threshold, percent in TIER_DISCOUNTS:
        if quantity >= threshold:
            tier_discount = percent
    discount_percent = min(max(tier_discount, PROMO_CODES.get(promo_code, 0)), MAX_DISCOUNT_PERCENT)
    discounted_subtotal = subtotal - percent_of(subtotal, discount_percent)
    shipping = (
        SHIPPING_KOPEKS if shipping_city and discounted_subtotal < FREE_DELIVERY_FROM_KOPEKS else 0
    )
    base = discounted_subtotal + shipping
    return base + percent_of(base, VAT_PERCENT)
