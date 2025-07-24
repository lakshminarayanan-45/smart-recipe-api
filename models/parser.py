import re
from fractions import Fraction
from word2number import w2n

def normalize(text):
    """Clean input text and convert unicode fractions to ASCII equivalents."""
    text = text.lower().strip()
    text = re.sub(r'[\u200b\n\r\t]', ' ', text)

    unicode_fractions = {
        '¼': '1/4', '½': '1/2', '¾': '3/4',
        '⅓': '1/3', '⅔': '2/3',
        '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8'
    }
    for uf, ascii_eq in unicode_fractions.items():
        text = text.replace(uf, ascii_eq)

    return text

def extract_amount_and_unit(text):
    """
    Extract numeric amount and unit from ingredient amount string like "1 1/2 cups".
    Returns (float amount, string unit).
    """
    if not text or not isinstance(text, str):
        return 0.0, ""

    text = normalize(text)
    tokens = text.split()
    amount = 0.0
    unit_tokens = []
    matched = False

    for i, token in enumerate(tokens):
        try:
            # Handle fractions and decimals, possibly with spaces like "1 1/4"
            if '/' in token:
                parts = token.split()
                # Sum fractions in token separated by spaces - usually token is single, so just parse fraction
                frac = float(sum(Fraction(p) for p in token.split()))
                amount = frac
                matched = True
                continue
            # else try to convert as float or integer
            if token.replace('.', '', 1).isdigit():
                amount = float(token)
                matched = True
                continue
            # Try word numbers like 'one', 'two'
            if not matched:
                amount = w2n.word_to_num(token)
                matched = True
                continue
        except Exception:
            if matched:
                # The rest tokens after amount considered units
                unit_tokens = tokens[i:]
                break
            continue

    if not matched:
        # If no amount found, fallback 0 and whole text as unit
        return 0.0, text
    
    unit = ' '.join(unit_tokens).strip()
    return amount, unit
