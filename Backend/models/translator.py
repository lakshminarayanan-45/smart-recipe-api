def detect_language(all_sheets, recipe_name):
    LANGUAGE_SUFFIX = {
        "TamilName": "ta", "tamilname": "ta",
        "hindiName": "hn", "malayalamName": "kl",
        "kannadaName": "kn", "teluguName": "te",
        "frenchName": "french", "spanishName": "spanish",
        "germanName": "german"
    }

    recipe_name_lower = recipe_name.lower().strip()

    for sheet_name, df in all_sheets.items():
        columns = [str(col) for col in df.columns]

        for lang_col, lang_code in LANGUAGE_SUFFIX.items():
            if lang_col in columns:
                match = df[df[lang_col].astype(str).str.lower().str.strip() == recipe_name_lower]
                if not match.empty:
                    return sheet_name, lang_col, lang_code, match

        for col in ["name", "Name"]:
            if col in columns:
                match = df[df[col].astype(str).str.lower().str.strip() == recipe_name_lower]
                if not match.empty:
                    return sheet_name, col, "en", match

    return None, None, None, None
