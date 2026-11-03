"""CairoTrade business rules. Unit-tested (AT-02). All money = Decimal."""
from decimal import Decimal, ROUND_HALF_UP

VAT_RATE = Decimal("0.14")
STEP = Decimal("0.05")

def line_discount_rate(qty: int) -> Decimal:
    if qty >= 50:
        return Decimal("0.12")
    if qty >= 10:
        return Decimal("0.05")
    return Decimal("0.00")

def line_total(qty: int, unit_price: Decimal) -> Decimal:
    gross = Decimal(str(unit_price)) * int(qty)
    net = gross * (Decimal("1") - line_discount_rate(int(qty)))
    return net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def discounted_subtotal(lines: list[dict]) -> Decimal:
    tot = sum((line_total(int(l["qty"]), Decimal(str(l["price"]))) for l in lines), Decimal("0"))
    return tot.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def vat_amount(subtotal: Decimal) -> Decimal:
    return (Decimal(str(subtotal)) * VAT_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def round_to_nearest_05(amount: Decimal) -> Decimal:
    a = Decimal(str(amount))
    steps = (a / STEP).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return (steps * STEP).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def order_total(lines: list[dict]) -> Decimal:
    sub = discounted_subtotal(lines)
    return round_to_nearest_05(sub + vat_amount(sub))

def exceeds_credit_limit(total: Decimal, limit: Decimal) -> bool:
    return Decimal(str(total)) > Decimal(str(limit))