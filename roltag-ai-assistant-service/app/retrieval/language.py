from langdetect import DetectorFactory, LangDetectException, detect

# Confirmed required languages (see CLAUDE.md); any other detected language
# falls back to English rather than guessing an unsupported translation.
SUPPORTED_LANGUAGES = {
    "en": "English",
    "ru": "Russian",
    "he": "Hebrew",
}

DetectorFactory.seed = 0  # make langdetect deterministic across runs


def detect_language_name(text: str) -> str:
    try:
        code = detect(text)
    except LangDetectException:
        return SUPPORTED_LANGUAGES["en"]
    return SUPPORTED_LANGUAGES.get(code, SUPPORTED_LANGUAGES["en"])