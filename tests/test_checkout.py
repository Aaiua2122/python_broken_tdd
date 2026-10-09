"""Order checkout, part 2.

How to work through this file:

1. The single red test below is done for you - it shows what RED looks like.
2. Run `./scripts/check-part2.sh` and read the failure.
3. Write one assertion per rule from `src/shop/specs/checkout.md` into the empty
   tests: a failing test first, then the code that makes it pass.
4. Never edit a finished assertion, never `skip`, never weaken a test.

Run one test at a time while you work:

    uv run pytest tests/test_checkout.py -k tier -x
"""

import pytest

from shop.checkout import calculate_order_total, validate_order


def line(sku: str = "SKU-1", qty: str = "1", unit_price_kopecks: str = "10000") -> dict[str, str]:
    """Build one order line the way the warehouse export delivers it."""
    return {"sku": sku, "qty": qty, "unit_price_kopecks": unit_price_kopecks}


def test_smoke_single_line_without_delivery() -> None:
    """One line, no promo code, no delivery. Works out to 100.00 rub + 20% VAT."""
    assert validate_order([line()]) is None
    assert calculate_order_total([line()]) == 12_000


def test_empty_order_is_rejected() -> None:
    """Spec 3, rule 1: an order without lines cannot be processed."""
    result = validate_order([])
    assert isinstance(result, str)
    assert result != ""


def test_empty_sku_is_rejected() -> None:
    """Spec 3, rule 2: a blank article code is not allowed."""
    item = line(sku="")
    result = validate_order([item])
    assert isinstance(result, str)
    assert result != ""


def test_missing_line_key_is_rejected() -> None:
    """Spec 3, rule 3: every required key must be present."""
    item = line()
    del item["qty"]
    result = validate_order([item])
    assert isinstance(result, str)
    assert result != ""


def test_non_numeric_quantity_is_rejected() -> None:
    """Spec 3, rule 4: `qty` must be a whole number."""
    item = line(qty="abc")
    result = validate_order([item])
    assert isinstance(result, str)
    assert result != ""


def test_zero_quantity_is_rejected() -> None:
    """Spec 3, rule 5: `qty` must be greater than zero."""
    item = line(qty="0")
    result = validate_order([item])
    assert isinstance(result, str)
    assert result != ""


def test_non_numeric_price_is_rejected() -> None:
    """Spec 3, rule 6: `unit_price_kopecks` must be a whole number."""
    result = validate_order([line(unit_price_kopecks="abc")])
    assert isinstance(result, str)
    assert result != ""


def test_negative_price_is_rejected() -> None:
    """Spec 3, rule 7: a price may not be negative."""
    result = validate_order([line(unit_price_kopecks="-1")])
    assert isinstance(result, str)
    assert result != ""


def test_duplicate_sku_is_rejected() -> None:
    """Spec 3, rule 8: the same article may appear only once."""
    result = validate_order([line(), line()])
    assert isinstance(result, str)
    assert result != ""


def test_unknown_promo_code_is_rejected() -> None:
    """Spec 3, rule 9: only codes from PROMO_CODES exist."""
    result = validate_order([line()], promo_code="UNKNOWN")
    assert isinstance(result, str)
    assert result != ""


def test_unsupported_city_is_rejected() -> None:
    """Spec 3, rule 10: only cities from SUPPORTED_CITIES are served."""
    result = validate_order([line()], shipping_city="unknown")
    assert isinstance(result, str)
    assert result != ""


def test_valid_order_passes_validation() -> None:
    """Spec 3: a good order gets None back instead of a reason."""
    item = line(unit_price_kopecks="0")
    item["warehouse"] = "main"
    assert validate_order([item], promo_code="WELCOME10", shipping_city="msk") is None
    assert calculate_order_total([item]) == 0


def test_no_discount_below_first_tier() -> None:
    """Spec 4, steps 1-2: 9 units are below every threshold."""
    assert calculate_order_total([line(qty="9")]) == 108_000


def test_tier_discount_at_first_threshold() -> None:
    """Spec 4, steps 2-5: 10 units give 5%. Compare with example 2."""
    assert calculate_order_total([line(qty="10", unit_price_kopecks="1990")]) == 22_686


def test_tier_discount_at_highest_threshold() -> None:
    """Spec 4, steps 2-5: 50 units give 15%, not 5% + 10%."""
    assert (
        calculate_order_total([line(qty="50", unit_price_kopecks="1990")], "WELCOME10", "msk")
        == 160_290
    )


def test_promo_code_beats_tier_discount() -> None:
    """Spec 4, steps 3-4: the bigger percentage wins, the two do not add up."""
    assert calculate_order_total([line(qty="10")], promo_code="SUMMER15") == 102_000


def test_discount_is_capped_at_thirty_percent() -> None:
    """Spec 4, step 5: VIP35 gives 35%, but the cap is 30%. Compare with example 4."""
    assert calculate_order_total([line(qty="100")], "VIP35", "spb") == 840_000


def test_delivery_is_charged_for_small_order() -> None:
    """Spec 4, steps 7-10: a city adds SHIPPING_KOPEKS and VAT is charged on it."""
    assert calculate_order_total([line()], shipping_city="msk") == 70_800


def test_free_delivery_uses_discounted_subtotal() -> None:
    """Spec 4, step 7: the threshold is checked against the sum after the discount."""
    assert calculate_order_total([line(unit_price_kopecks="500000")], "WELCOME10", "msk") == 598_800


def test_vat_is_charged_on_the_discounted_sum() -> None:
    """Spec 4, steps 8-10: base = discounted subtotal + delivery."""
    assert calculate_order_total([line()], promo_code="WELCOME10") == 10_800


@pytest.mark.parametrize("key", ["sku", "qty", "unit_price_kopecks"])
def test_each_missing_key_rejects_order(key: str) -> None:
    item = line()
    del item[key]
    result = validate_order([line(sku="FIRST"), item])
    assert isinstance(result, str)
    assert result != ""
    assert calculate_order_total([line(sku="FIRST"), item]) is None


@pytest.mark.parametrize("value", ["", " ", "abc", "1.5", "1e2", "²", "+", "1__0", "_1", "1_"])
@pytest.mark.parametrize("key", ["qty", "unit_price_kopecks"])
def test_invalid_integer_strings_reject_order(key: str, value: str) -> None:
    item = line()
    item[key] = value
    result = validate_order([item])
    assert isinstance(result, str)
    assert result != ""
    assert calculate_order_total([item]) is None


@pytest.mark.parametrize("value", ["1", " +1 ", "01", "١", "１", "1_0"])
def test_integer_strings_accepted_by_int_are_valid(value: str) -> None:
    assert validate_order([line(qty=value, unit_price_kopecks=value)]) is None
    assert calculate_order_total([line(qty=value, unit_price_kopecks="0")]) == 0


@pytest.mark.parametrize(
    ("lines", "promo_code", "shipping_city"),
    [
        ([], "", ""),
        ([line(sku="")], "", ""),
        ([line(qty="-1")], "", ""),
        ([line(qty="0")], "", ""),
        ([line(unit_price_kopecks="-1")], "", ""),
        ([line(), line()], "", ""),
        ([line()], "UNKNOWN", ""),
        ([line()], "", "unknown"),
    ],
)
def test_invalid_order_has_no_total(
    lines: list[dict[str, str]], promo_code: str, shipping_city: str
) -> None:
    result = validate_order(lines, promo_code, shipping_city)
    assert isinstance(result, str)
    assert result != ""
    assert calculate_order_total(lines, promo_code, shipping_city) is None


@pytest.mark.parametrize(
    ("qty", "expected"),
    [
        ("9", 108_000),
        ("10", 114_000),
        ("24", 273_600),
        ("25", 270_000),
        ("49", 529_200),
        ("50", 510_000),
        ("51", 520_200),
    ],
)
def test_tier_boundaries(qty: str, expected: int) -> None:
    assert calculate_order_total([line(qty=qty)]) == expected


def test_tier_uses_total_quantity_across_lines() -> None:
    assert (
        calculate_order_total(
            [line(sku="A", qty="5"), line(sku="B", qty="5", unit_price_kopecks="20000")]
        )
        == 171_000
    )


@pytest.mark.parametrize("city", ["msk", "spb"])
@pytest.mark.parametrize(
    ("price", "expected"), [("499999", 658_799), ("500000", 600_000), ("500001", 600_001)]
)
def test_free_delivery_boundary(city: str, price: str, expected: int) -> None:
    assert calculate_order_total([line(unit_price_kopecks=price)], shipping_city=city) == expected


def test_discounted_sum_exactly_at_free_delivery_threshold() -> None:
    assert calculate_order_total([line(unit_price_kopecks="588235")], "SUMMER15", "spb") == 600_000


def test_discount_rounds_half_up_before_vat() -> None:
    assert calculate_order_total([line(unit_price_kopecks="5")], "WELCOME10") == 5


def test_vat_rounds_to_nearest_kopeck() -> None:
    assert calculate_order_total([line(unit_price_kopecks="3")]) == 4


def test_checkout_does_not_change_lines() -> None:
    lines = [line(), line(sku="SECOND", qty="9")]
    original = [item.copy() for item in lines]
    assert calculate_order_total(lines, "WELCOME10", "spb") == 166_800
    assert lines == original
