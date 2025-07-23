import spacy

# Dummy language detection from recipe name prefix or you can expand this
lang_code_map = {
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

def detect_language(recipe_name):
    # Simple heuristic: check prefix or use langdetect/spacy
    if recipe_name.startswith("ta:"):
        return "Tamil"
    elif recipe_name.startswith("hi:"):
        return "Hindi"
    return "English"

# Stub: Replace with actual translation if needed
def translate_to_english(text, lang):
    return text  # Assumes data is already in English or no translation needed

def normalize_header(text):
    return text.lower().strip().replace(" ", "_").replace("__", "_")

