import re
from fractions import Fraction
from math import log

def parse_ingredient_line(text):
    items = [i.strip() for i in re.split(r",|\n", text) if i.strip()]
    results = []
    for item in items:
        item = item.replace("–", "-")
        match = re.match(
            r"(?P<qty>[\d\./\-]+)?\s*(?P<unit>[^\d\s\-]+)?\s*-?\s*(?P<name>.+)", item)
        if match:
            qty = match.group("qty")
            try:
                if qty and "-" in qty:
                    parts = re.findall(r"[\d\.]+", qty)
                    amount = sum(float(p) for p in parts) / len(parts)
                else:
                    amount = eval(qty) if qty else 1
            except Exception:
                amount = 1
            results.append({
                "amount": amount,
                "unit": match.group("unit").strip() if match.group("unit") else "",
                "name": match.group("name").strip(),
                "formattedAmount": format_fraction(amount)
            })
    return results

def format_fraction(amount):
    try:
        rounded = round(amount * 4) / 4
        frac = Fraction(rounded).limit_denominator(4)
        if frac.numerator % frac.denominator == 0:
            return str(frac.numerator // frac.denominator)
        if frac.numerator > frac.denominator:
            whole = frac.numerator // frac.denominator
            remainder = frac - whole
            return f"{whole} {format_simple_fraction(remainder)}"
        return format_simple_fraction(frac)
    except:
        return str(round(amount, 2)).rstrip("0").rstrip(".")

def format_simple_fraction(frac):
    frac_map = {
        Fraction(1, 4): "¼",
        Fraction(1, 2): "½",
        Fraction(3, 4): "¾"
    }
    return frac_map.get(frac, f"{frac.numerator}/{frac.denominator}")

def extract_amount_and_unit(text):
    match = re.match(
        r"(?P<qty>[\d\./\-]+)?\s*(?P<unit>[^\d\s\-]+)?\s*-?\s*(?P<name>.+)", text)
    if match:
        try:
            qty_str = match.group("qty")
            if qty_str and "-" in qty_str:
                parts = re.findall(r"[\d\.]+", qty_str)
                amount = sum(float(p) for p in parts) / len(parts)
            else:
                amount = eval(qty_str) if qty_str else 1
        except Exception:
            amount = 1
        unit = match.group("unit") if match.group("unit") else ""
        return amount, unit
    else:
        return 1, ""

def scale_cooking_time(original_time, new_servings, base=2):
    """
    Improved cooking time scaling using logarithmic scale and capped multipliers.
    """
    try:
        original_time = float(original_time)
    except Exception:
        return "N/A"

    if new_servings <= base or original_time <= 0:
        return round(original_time)

    try:
        scaled_time = original_time * (log(new_servings) / log(base))
    except Exception:
        # fallback linear scaling if log fails
        scaled_time = original_time * (new_servings / base)

    # Caps to avoid unrealistic high cooking times:
    max_multiplier = 1.7
    scaled_time = max(original_time, min(scaled_time, original_time * max_multiplier))

    # Minimum time threshold (optional)
    min_time = 5
    if scaled_time < min_time:
        scaled_time = min_time

    return round(scaled_time)
