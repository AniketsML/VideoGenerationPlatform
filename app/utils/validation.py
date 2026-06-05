from decimal import Decimal, InvalidOperation


def parse_money(value: str | int | float | None, *, field_name: str) -> str | None:
    if value is None or value == '':
        return None
    if isinstance(value, (int, float)):
        amount = Decimal(str(value))
    else:
        text = str(value).strip().replace(',', '').replace('₹', '')
        try:
            amount = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f'{field_name} must be numeric') from exc
    quantized = amount.quantize(Decimal('0.01'))
    if quantized == quantized.to_integral():
        formatted = f'₹{int(quantized):,}'
    else:
        formatted = f'₹{quantized:,.2f}'
    return formatted


def require_non_null(value: object, *, field_name: str) -> None:
    if value is None:
        raise ValueError(f'{field_name} is required')
    if isinstance(value, str) and not value.strip():
        raise ValueError(f'{field_name} is required')
