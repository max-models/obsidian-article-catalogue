"""Turn BibTeX/LaTeX strings into text that is safe to use in Obsidian."""

import re

from pylatexenc.latex2text import LatexNodes2Text

_LATEX = LatexNodes2Text()

# Characters Obsidian does not allow in note names or links.
_FORBIDDEN_FILENAME_CHARS = set('*"\\/<>:|?#^[]')
_MAX_FILENAME_LENGTH = 150

_MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
)


def latex_to_text(text):
    """Convert LaTeX markup to plain unicode text with normalized whitespace."""
    return " ".join(_LATEX.latex_to_text(text).split())


def safe_filename(title):
    """Convert a (LaTeX) title into a name that is valid for an Obsidian note.

    Returns an empty string if nothing usable is left.
    """
    text = latex_to_text(title)
    text = text.replace("/", " or ").replace("&", " and ").replace(":", " -")
    text = "".join(char for char in text if char not in _FORBIDDEN_FILENAME_CHARS)
    text = " ".join(text.split())[:_MAX_FILENAME_LENGTH]
    return text.strip(" .")


def clean_tag(text):
    """Convert text into an Obsidian tag part (letters, digits, ``_`` and ``-``)."""
    return re.sub(r"[^\w-]", "", latex_to_text(text))


def month_number(month):
    """Parse a BibTeX month ("jan", "January", "1", "01") into 1-12, or ``None``."""
    month = month.strip().lower().rstrip(".")
    if month.isdigit():
        number = int(month)
        return number if 1 <= number <= 12 else None
    if len(month) >= 3:
        for number, name in enumerate(_MONTHS, start=1):
            if name.startswith(month):
                return number
    return None
