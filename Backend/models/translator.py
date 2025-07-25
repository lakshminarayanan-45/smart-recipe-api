def detect_language(all_sheets, recipe_name):
    """
    Detect the Excel sheet and language-specific column for a given recipe name.

    Args:
        all_sheets (dict): Dictionary of {sheet_name: DataFrame} from pd.read_excel(..., sheet_name=None)
        recipe_name (str): Recipe name to search for

    Returns:
        Tuple: (sheet_name, language_column, language_code, matching_rows_df)
        Returns (None, None, None, None) if no match is found.
    """
    LANGUAGE_SUFFIX = {
        "TamilName": "ta", "tamilname": "ta",
        "hindiName": "hn", "malayalamName": "kl",
        "kannadaName": "kn", "teluguName": "te",
        "frenchName": "french", "spanishName": "spanish", "germanName": "german"
    }

    recipe_name_lower = recipe_name.lower().strip()

    for sheet_name, df in all_sheets.items():
        # Ensure columns are string for safe check
        columns = [str(col) for col in df.columns]

        # First search language-specific columns
        for lang_col, lang_code in LANGUAGE_SUFFIX.items():
            if lang_col in columns:
                match = df[df[lang_col].astype(str).str.lower().str.strip() == recipe_name_lower]
                if not match.empty:
                    return sheet_name, lang_col, lang_code, match

        # Fallback: search English 'name' or 'Name' columns
        for col in ["name", "Name"]:
            if col in columns:
                match = df[df[col].astype(str).str.lower().str.strip() == recipe_name_lower]
                if not match.empty:
                    return sheet_name, col, "en", match

    # No match found
    return None, None, None, None
