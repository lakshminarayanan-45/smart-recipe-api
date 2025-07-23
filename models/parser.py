import re
from fractions import Fraction

# Handle quantities like "1/2", "1 1/2", "0.5"
def parse_fraction(value):
    try:
        value = value.strip()
        if ' ' in value:
            parts = value.split()
            return float(sum(Fraction(part) for part in parts))
        return float(Fraction(value))
    except:
        return None

def normalize(text):
    text = text.lower().strip()
    text = re.sub(r'[\u200b\n\r\t]', ' ', text)

    # Replace common Unicode fractions with ASCII equivalents
    unicode_fractions = {
        '¼': '1/4', '½': '1/2', '¾': '3/4',
        '⅓': '1/3', '⅔': '2/3',
        '⅛': '1/8', '⅜': '3/8', '⅝': '5/8', '⅞': '7/8'
    }
    for k, v in unicode_fractions.items():
        text = text.replace(k, v)

    return text

# Identify if a line is an ingredient line based on simple rules
def is_ingredient_line(line):
    return any(char.isdigit() for char in line) and len(line.split()) < 10

# Extract amount, unit, ingredient from one line
def parse_ingredient_line(line):
    line = normalize(line)
    tokens = line.split()
    amount = 0
    unit = ""
    ingredient = ""

    for i, token in enumerate(tokens):
        try:
            amt = parse_fraction(token)
            if amt:
                amount = amt
                continue
        except:
            pass

        if not unit and token.isalpha():
            unit = token
        else:
            ingredient = ' '.join(tokens[i:])
            break

    return {
        "amount": amount,
        "unit": unit,
        "ingredient": ingredient.strip()
    }
