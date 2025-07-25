import re
from fractions import Fraction
from math import log

def parse_ingredient_line(text):
    """
    Parse raw ingredient text into structured ingredients with amount, unit, and name.
    Handles quantities with fractions, ranges, and missing data safely.

    Args:
        text (str): raw multiline string or comma-separated ingredients.

    Returns:
        list of dicts with keys: amount (float), unit (str), name (str), formattedAmount (str)
    """
    items = [i.strip() for i in re.split(r",|\n", text) if i.strip()]
    results = []
    for item in items:
        item = item.replace("–", "-")
        # Match optional quantity, optional unit, and name (rest of string)
        match = re.match(
            r"(?P<qty>[\d\./\-]+)?\s*(?P<unit>[^\d\s\-]+)?\s*-?\s*(?P<name>.+)", item)
        if match:
            qty = match.group("qty")
            try:
                if qty and "-" in qty:
                    # If a range like "1-2", average it
                    parts = re.findall(r"[\d\.]+", qty)
                    amount = sum(float(p) for p in parts) / len(parts) if parts else 1
                else:
                    amount = eval(qty) if qty else 1
            except Exception:
                amount = 1  # Safe fallback quantity
            results.append({
                "amount": amount,
                "unit": match.group("unit").strip() if match.group("unit") else "",
                "name": match.group("name").strip(),
                "formattedAmount": format_fraction(amount)
            })
    return results

def format_fraction(amount):
    """
    Format a float quantity into a nicely readable string with fractions.
    Examples: 1.5 => "1 1/2", 0.75 => "¾", 2.0 => "2"
    """
    try:
        rounded = round(amount * 4) / 4  # round to nearest quarter
        frac = Fraction(rounded).limit_denominator(4)
        if frac.numerator % frac.denominator == 0:
            # Whole number
            return str(frac.numerator // frac.denominator)
        if frac.numerator > frac.denominator:
            # Mixed fraction
            whole = frac.numerator // frac.denominator
            remainder = frac - whole
            return f"{whole} {format_simple_fraction(remainder)}"
        return format_simple_fraction(frac)
    except:
        # Fallback formatting
        return str(round(amount, 2)).rstrip("0").rstrip(".")

def format_simple_fraction(frac):
    """
    Convert simple fractions to unicode fraction characters for better readability.
    """
    frac_map = {
        Fraction(1, 4): "¼",
        Fraction(1, 2): "½",
        Fraction(3, 4): "¾"
    }
    return frac_map.get(frac, f"{frac.numerator}/{frac.denominator}")

def extract_amount_and_unit(text):
    """
    Extract numeric amount and unit from an ingredient string.
    Returns amount (float) and unit (string).
    """
    match = re.match(
        r"(?P<qty>[\d\./\-]+)?\s*(?P<unit>[^\d\s\-]+)?\s*-?\s*(?P<name>.+)", text)
    if match:
        try:
            qty_str = match.group("qty")
            if qty_str and "-" in qty_str:
                parts = re.findall(r"[\d\.]+", qty_str)
                amount = sum(float(p) for p in parts) / len(parts) if parts else 1
            else:
                amount = eval(qty_str) if qty_str else 1
        except Exception:
            amount = 1  # Fallback default
        unit = match.group("unit") if match.group("unit") else ""
        return amount, unit
    else:
        return 1, ""  # Default amount and no unit

def scale_cooking_time(original_time, new_servings, base=2):
    """
    Scale cooking time based on servings using logarithmic scaling,
    capped between original time and 1.7 times the original time,
    to avoid unrealistic long cooking times.

    Args:
        original_time (float, int, str): original cook time in minutes
        new_servings (int): new number of servings
        base (int): base servings count from original recipe

    Returns:
        int or str: scaled cooking time rounded to nearest min, or "N/A" if invalid
    """
    try:
        original_time = float(original_time)
    except (ValueError, TypeError):
        return "N/A"

    if new_servings <= base or original_time <= 0:
        return round(original_time)

    try:
        scaled_time = original_time * (log(new_servings) / log(base))
    except Exception:
        # fall back to simple linear scaling if error
        scaled_time = original_time * (new_servings / base)

    # Clamp to no less than original, no more than 1.7x original
    max_multiplier = 1.7
    scaled_time = max(original_time, min(scaled_time, original_time * max_multiplier))

    # Set a minimum reasonable cooking time (optional)
    min_time = 5
    if scaled_time < min_time:
        scaled_time = min_time

    return round(scaled_time)
