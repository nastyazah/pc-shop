import re
import unicodedata

# Має збігатися з char_filter "uk_normalize" в infra/opensearch/index_products.json
_APOSTROPHES = str.maketrans({"’": "'", "ʼ": "'", "`": "'", "´": "'", "′": "'"})
_LETTERS = str.maketrans({"ё": "е", "ы": "и", "э": "е", "ґ": "г"})


def fix_apostrophes(text: str) -> str:
    return text.translate(_APOSTROPHES)


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKC", text).lower()
    t = fix_apostrophes(t).translate(_LETTERS)
    return re.sub(r"\s+", " ", t).strip()


# Англійська розкладка -> українська (ЙЦУКЕН): "vfnthbyrf" -> "материнка"
_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,./"
_UK = "йцукенгшщзхїфівапролджєячсмитьбю."
_LAYOUT = str.maketrans(_EN, _UK)
_UNLAYOUT = str.maketrans(_UK, _EN)
LAYOUT_RE = re.compile(r"[a-z\[\];',./\d]{3,}")   # слово, набране англійською розкладкою
UK_LAYOUT_RE = re.compile(r"[йцукенгшщзхїфівапролджєячсмитьбю\d]{3,}")  # слово, набране українською


def fix_layout(token: str) -> str:
    """Англійська розкладка -> українська: "gkfnb" -> "плати"."""
    return token.translate(_LAYOUT)


def unfix_layout(token: str) -> str:
    """Українська розкладка -> англійська: "фігі" -> "asus"."""
    return token.translate(_UNLAYOUT)
