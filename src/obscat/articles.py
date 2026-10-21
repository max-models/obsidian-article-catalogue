"""Add a new article (PDF + BibTeX entry) to the catalogue."""

import re
import shutil
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

import pymupdf
from pybtex.database import BibliographyData, parse_file, parse_string

from obscat import ObscatError

# Crossref's recommended pattern, see https://www.crossref.org/blog/dois-and-matching-regular-expressions/
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:a-z0-9]+", re.IGNORECASE)
ARXIV_RE = re.compile(r"arxiv:\s*(\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)

USER_AGENT = "obscat (https://github.com/max-models/obsidian-article-catalogue)"


def _find_doi(text):
    match = DOI_RE.search(text)
    return match.group(0).rstrip(".,;)") if match else None


def detect_identifier(pdf_path):
    """Look for a DOI or arXiv id in a PDF.

    Returns ``("doi", doi)`` or ``("arxiv", arxiv_id)``. The PDF metadata is checked
    first, then the arXiv stamp, then any DOI on the first page.
    """
    with pymupdf.open(pdf_path) as doc:
        metadata = " ".join(value or "" for value in doc.metadata.values())
        first_page = doc[0].get_text() if len(doc) else ""

    if doi := _find_doi(metadata):
        return "doi", doi
    if match := ARXIV_RE.search(first_page):
        return "arxiv", match.group(1)
    if doi := _find_doi(first_page):
        return "doi", doi
    raise ObscatError(
        f"Could not find a DOI or arXiv id in {pdf_path}; "
        "pass --doi, --arxiv or --bibtex"
    )


def _http_get(url, accept):
    request = Request(url, headers={"Accept": accept, "User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8")
    except URLError as error:
        raise ObscatError(f"Could not fetch {url}: {error}") from error


def fetch_bibtex(doi=None, arxiv=None):
    """Download the BibTeX entry for a DOI (via doi.org) or an arXiv id."""
    if doi:
        return _http_get(f"https://doi.org/{quote(doi)}", "application/x-bibtex")
    if arxiv:
        return _http_get(f"https://arxiv.org/bibtex/{quote(arxiv)}", "text/plain")
    raise ValueError("Pass either doi or arxiv")


def parse_single_entry(bibtex):
    """Parse BibTeX text with exactly one entry and return ``(key, entry)``."""
    entries = parse_string(bibtex, bib_format="bibtex").entries
    if len(entries) != 1:
        raise ObscatError(f"Expected exactly one BibTeX entry, got {len(entries)}")
    return next(iter(entries.items()))


def _append_entry(bib_path, key, entry):
    existing = bib_path.read_text(encoding="utf-8") if bib_path.exists() else ""
    if not existing.strip():
        separator = ""
    elif existing.endswith("\n"):
        separator = "\n"
    else:
        separator = "\n\n"
    text = BibliographyData(entries={key: entry}).to_string("bibtex")
    bib_path.parent.mkdir(parents=True, exist_ok=True)
    with bib_path.open("a", encoding="utf-8") as file:
        file.write(separator + text)


def add_article(
    pdf_path,
    bib_path,
    articles_dir,
    *,
    bibtex=None,
    doi=None,
    arxiv=None,
    key=None,
    move=False,
):
    """Add a PDF to the catalogue and return its citation key.

    The BibTeX entry is taken from ``bibtex`` if given, otherwise downloaded using
    ``doi`` or ``arxiv``, otherwise downloaded using an identifier found in the PDF.
    The entry is appended to ``bib_path`` (optionally under a different ``key``) and
    the PDF is copied (or moved) to ``<articles_dir>/<key>/<key>.pdf``.
    """
    pdf_path, bib_path = Path(pdf_path), Path(bib_path)
    if not pdf_path.is_file():
        raise ObscatError(f"PDF {pdf_path} does not exist")

    if bibtex is None:
        if not (doi or arxiv):
            kind, identifier = detect_identifier(pdf_path)
            print(f"Found {kind} {identifier} in {pdf_path.name}")
            doi, arxiv = (identifier, None) if kind == "doi" else (None, identifier)
        bibtex = fetch_bibtex(doi=doi, arxiv=arxiv)

    entry_key, entry = parse_single_entry(bibtex)
    key = key or entry_key
    entry.key = key

    existing = parse_file(str(bib_path)).entries if bib_path.exists() else {}
    if key in existing:
        raise ObscatError(f"{bib_path} already contains an entry with key {key}")
    if new_doi := entry.fields.get("doi", "").lower():
        for other_key, other in existing.items():
            if other.fields.get("doi", "").lower() == new_doi:
                raise ObscatError(
                    f"{bib_path} already contains this DOI as {other_key}"
                )

    target = Path(articles_dir) / key / f"{key}.pdf"
    if target.exists():
        raise ObscatError(f"{target} already exists")

    _append_entry(bib_path, key, entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    if move:
        shutil.move(pdf_path, target)
    else:
        shutil.copy2(pdf_path, target)
    return key
