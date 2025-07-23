def format_quantity(q):
    fractions = {
        0.25: "¼", 0.5: "½", 0.75: "¾"
    }
    rounded = round(q * 4) / 4
    whole = int(rounded)
    frac = rounded - whole
    if frac == 0:
        return str(whole)
    return f"{whole if whole else ''}{fractions.get(frac, round(frac, 2))}"
