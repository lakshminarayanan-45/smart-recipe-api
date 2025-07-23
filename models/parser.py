import re
from fractions import Fraction
from word2number import w2n

def normalize(text):
    """Clean and convert unicode fractions to ASCII."""
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
    Extracts the numeric quantity and unit from a string like '1 1/2 cups'.
    Returns (amount: float, unit: str)
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
            # Try fraction first (e.g., 1/2, 3 1/4)
            if '/' in token or token.replace('.', '', 1).isdigit():
                frac = float(sum(Fraction(p) for p in token.split()))
                amount = frac
                matched = True
                continue
            # Try converting word-based number (e.g., one, two)
            if not matched:
                amount = w2n.word_to_num(token)
                matched = True
                continue
        except:
            # Everything after amount is considered unit
            if matched:
                unit_tokens = tokens[i:]
                break
            continue

    unit = ' '.join(unit_tokens).strip()
    return amount, unit
