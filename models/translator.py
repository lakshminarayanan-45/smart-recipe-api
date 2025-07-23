# translator.py
from langdetect import detect

# List of supported language codes and their labels
LANG_CODE_MAP = {
    "ta": "Tamil",
    "hi": "Hindi",
    "en": "English",
    "ml": "Malayalam",
    "kn": "Kannada",
    "te": "Telugu",
    "bn": "Bengali",
    "gu": "Gujarati",
    "mr": "Marathi"
}

def detect_and_translate(text: str, detect_only=False, target_lang='en'):
    """
    Detects the language of the input text.
    If detect_only=True, returns only the detected language code.
    If detect_only=False, translates to target_lang (default: English).
    """
    if not text or not isinstance(text, str):
        return "en" if detect_only else text

    try:
        detected_lang = detect(text)
    except Exception:
        detected_lang = "en"

    if detect_only:
        return detected_lang.lower()

    # Stub for future translation logic (e.g., Google Translate)
    return text  # assuming pre-translated or multilingual column already exists


def normalize_column(col_name: str):
    """
    Normalize Excel column names by stripping and converting to lowercase
    """
    return col_name.lower().strip().replace(" ", "_").replace("__", "_")
