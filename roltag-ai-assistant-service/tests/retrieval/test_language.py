from app.retrieval.language import detect_language_name


def test_detects_english():
    assert detect_language_name("How do I replace the imaging oil in the press?") == "English"


def test_detects_russian():
    assert detect_language_name("Как заменить чернила в принтере?") == "Russian"


def test_detects_hebrew():
    assert detect_language_name("איך מחליפים דיו במדפסת?") == "Hebrew"


def test_unsupported_language_falls_back_to_english():
    # French is not in SUPPORTED_LANGUAGES, so it should fall back rather
    # than silently answering in a language we've never validated output for.
    assert detect_language_name("Comment remplacer l'encre de l'imprimante ?") == "English"


def test_empty_string_falls_back_to_english():
    # langdetect raises LangDetectException on empty/unparseable input.
    assert detect_language_name("") == "English"
