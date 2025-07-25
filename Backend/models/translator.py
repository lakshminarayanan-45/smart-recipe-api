def detect_language(all_sheets, recipe_name):
    LANGUAGE_SUFFIX = {
        "TamilName": "ta", "tamilname": "ta",
        "hindiName": "hn", "malayalamName": "kl", "kannadaName": "kn",
        "teluguName": "te", "frenchName": "french", "spanishName": "spanish", "germanName": "german"
    }

    for sheet_name, df in all_sheets.items():
        for lang_col, lang_code in LANGUAGE_SUFFIX.items():
            if lang_col in df.columns:
                match = df[df[lang_col].astype(str).str.lower().str.strip() == recipe_name.lower()]
                if not match.empty:
                    return sheet_name, lang_col, lang_code, match

        for col in ["name", "Name"]:
            if col in df.columns:
                match = df[df[col].astype(str).str.lower().str.strip() == recipe_name.lower()]
                if not match.empty:
                    return sheet_name, col, "en", match
    return None, None, None, None
