"""Generate an article catalogue for Obsidian from a BibTeX file."""

__version__ = "0.2.0"


class ObscatError(Exception):
    """An error caused by user input, reported without a traceback."""
