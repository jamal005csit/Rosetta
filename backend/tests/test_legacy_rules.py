from decimal import Decimal
from legacy_app.rules import (line_total, discounted_subtotal, vat_amount,
    round_to_nearest_05, order_total, exceeds_credit_limit)

def test_line_discount_tiers():
    assert line_total(5, Decimal("100")) == Decimal("500.00")
    assert line_total(10, Decimal("100")) == Decimal("950.00")   # 5%
    assert line_total(49, Decimal("10")) == Decimal("465.50")    # 5%
    assert line_total(50, Decimal("100")) == Decimal("4400.00")  # 12%

def test_vat_and_rounding():
    sub = discounted_subtotal([{"qty": 10, "price": Decimal("100")}])
    assert sub == Decimal("950.00")
    assert vat_amount(sub) == Decimal("133.00")
    assert round_to_nearest_05(Decimal("1083.02")) == Decimal("1083.00")
    assert round_to_nearest_05(Decimal("1083.03")) == Decimal("1083.05")

def test_order_total_and_credit():
    t = order_total([{"qty": 10, "price": Decimal("100")}])
    assert t == Decimal("1083.00")  # 950+133=1083 exact on 0.05 grid
    assert exceeds_credit_limit(Decimal("6000"), Decimal("5000")) is True
    assert exceeds_credit_limit(Decimal("100"), Decimal("5000")) is False