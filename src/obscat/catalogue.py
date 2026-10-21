"""Generate one Obsidian note per article from a BibTeX file.

For every article in the .bib file a folder ``<articles>/<key>/`` is created with:

- ``@<key>.md``: the note for the article. Its body is written once and then
  left alone, so you can write your notes in it. On every build only the
  properties that come from the .bib file are updated; properties you add
  yourself are kept.
- ``<key>.bib``: the BibTeX entry (only written once),
- ``<key>.html``: a link to the article online (only written once),
- ``<key>.pdf.jpg``: a preview of the first pages (see ``obscat.images``).

Where the PDF lives is described by ``obscat.layout``. ``<articles>/Articles.base``
(written once) lists all articles and the ones without a PDF.
"""

import re
from pathlib import Path
from urllib.parse import unquote

import yaml
from pybtex.database import parse_file

from obscat import ObscatError
from obscat.layout import Layout
from obscat.pdfs import pdf_markdown, pdf_property
from obscat.text import latex_to_text, month_number, safe_filename

ARTICLE_TYPES = ("article", "inproceedings")
BASE_FILE = "Articles.base"

# Properties that are set from the .bib file on every build, in this order.
MANAGED_PROPERTIES = (
    "title",
    "aliases",
    "authors",
    "year",
    "month",
    "journal",
    "doi",
    "url",
    "citekey",
    "pdf",
    "has_pdf",
)

BASE = """\
filters:
  and:
    - file.hasProperty("citekey")
properties:
  file.name:
    displayName: Note
  note.title:
    displayName: Title
  note.authors:
    displayName: Authors
  note.year:
    displayName: Year
  note.journal:
    displayName: Journal
  note.pdf:
    displayName: PDF
  note.has_pdf:
    displayName: Has PDF
  note.url:
    displayName: Link
views:
  - type: table
    name: All articles
    order:
      - file.name
      - title
      - authors
      - year
      - journal
      - pdf
  - type: table
    name: By journal
    groupBy:
      property: note.journal
      direction: ASC
    order:
      - file.name
      - title
      - authors
      - year
  - type: table
    name: Missing PDF
    filters:
      and:
        - has_pdf == false
    order:
      - file.name
      - title
      - year
      - url
"""

# Files written by obscat before notes were named after the citation key.
_LEGACY_FILES = {
    "article_catalogue.md": "| Article Name |",
    "Missing articles.md": "# Missing articles",
}
_LEGACY_NOTE_RE = re.compile(r"^bibentry:\s*['\"]?(.*?)['\"]?\s*$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(
    r"\A---\n(.*?)^---[ \t]*(?:\n|\Z)", re.DOTALL | re.MULTILINE
)


def is_preprint(entry):
    fields = ("archiveprefix", "eprinttype", "publisher", "howpublished", "url")
    return "arxiv" in " ".join(entry.fields.get(f, "") for f in fields).lower()


def is_catalogued(entry):
    """Articles, conference papers and preprints are catalogued; books etc. are not."""
    return entry.type in ARTICLE_TYPES or (
        entry.type in ("misc", "unpublished") and is_preprint(entry)
    )


def load_entries(bib_path):
    """Return the catalogued entries of a .bib file, keyed by citation key."""
    bib_path = Path(bib_path)
    if not bib_path.is_file():
        raise ObscatError(f"BibTeX file {bib_path} does not exist")
    data = parse_file(str(bib_path), bib_format="bibtex")
    return {key: entry for key, entry in data.entries.items() if is_catalogued(entry)}


def entry_title(entry):
    return latex_to_text(entry.fields.get("title", "")) or "Unknown Title"


def entry_authors(entry):
    """Return the authors as "First Last" names."""
    names = []
    for person in entry.persons.get("author", []):
        parts = (
            person.first_names
            + person.middle_names
            + person.prelast_names
            + person.last_names
            + person.lineage_names
        )
        names.append(latex_to_text(" ".join(parts)))
    return names


def entry_venue(entry):
    for field in ("journal", "booktitle"):
        if entry.fields.get(field):
            return latex_to_text(entry.fields[field])
    return "arXiv" if is_preprint(entry) else None


def entry_url(entry):
    if url := entry.fields.get("url"):
        return unquote(url.replace("\\", ""))
    if doi := entry.fields.get("doi"):
        return f"https://doi.org/{doi}"
    return None


def entry_properties(key, entry, layout):
    """Return the properties set from the .bib file; ``None`` means "remove"."""
    has_pdf = layout.pdf(key).exists()
    year = entry.fields.get("year", "").strip()
    authors = [safe_filename(name) for name in entry_authors(entry)]
    return {
        "title": entry_title(entry),
        "authors": [f"[[{name}]]" for name in authors if name] or None,
        "year": int(year) if year.isdigit() else year or None,
        "month": month_number(entry.fields.get("month", "")),
        "journal": entry_venue(entry),
        "doi": entry.fields.get("doi") or None,
        "url": entry_url(entry),
        "citekey": key,
        "pdf": pdf_property(layout, key) if has_pdf else None,
        "has_pdf": has_pdf,
    }


def split_frontmatter(text, path):
    """Split a note into its properties and its body."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        properties = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as error:
        raise ObscatError(
            f"Could not read the properties of {path}: {error}"
        ) from error
    if not isinstance(properties, dict):
        raise ObscatError(f"The properties of {path} are not a mapping")
    return properties, text[match.end() :]


def join_frontmatter(properties, body):
    dumped = yaml.safe_dump(
        properties, allow_unicode=True, sort_keys=False, width=1_000_000
    )
    return f"---\n{dumped}---\n{body}"


def merge_properties(existing, managed):
    """Update ``existing`` with ``managed``, keeping the user's own properties."""
    title = managed["title"]
    aliases = existing.get("aliases") or []
    if isinstance(aliases, str):
        aliases = [aliases]
    old_title = existing.get("title")

    merged = {}
    for name in MANAGED_PROPERTIES:
        if name == "aliases":
            merged["aliases"] = [title] + [
                alias for alias in aliases if alias not in (title, old_title)
            ]
        elif managed.get(name) is not None:
            merged[name] = managed[name]
    for name, value in existing.items():
        if name not in MANAGED_PROPERTIES:
            merged[name] = value
    return merged


def render_body(key, entry, layout, full_path=False, notes=""):
    prefix = f"{layout.folder(key)}/" if full_path else ""
    lines = [f"# {entry_title(entry)}", "", "## Notes", ""]
    if notes:
        lines += [notes, ""]
    lines += [
        "## Summary",
        "",
        f"![[{prefix}{key}.pdf.jpg]]",
        "",
        "## Full pdf",
        "",
        pdf_markdown(layout, key, prefix),
        "",
        "## Citation",
        "",
        "```cpp",
        entry.to_string("bibtex").strip(),
        "```",
        "",
    ]
    return "\n".join(lines)


def _remove_legacy_notes(folder, key, keep):
    """Delete notes generated by older versions (named after the title)."""
    for path in folder.glob("*.md"):
        if path.name == keep:
            continue
        match = _FRONTMATTER_RE.match(
            path.read_text(encoding="utf-8", errors="replace")
        )
        legacy = match and _LEGACY_NOTE_RE.search(match.group(1))
        if legacy and legacy.group(1) == key:
            path.unlink()


def _create_note(path, key, entry, properties, layout, full_path):
    """Write a new note, moving in the contents of an old ``<key>_notes.md``."""
    folder = path.parent
    notes_path = folder / f"{key}_notes.md"
    notes_properties, notes = {}, ""
    if notes_path.exists():
        text = notes_path.read_text(encoding="utf-8")
        notes_properties, notes = split_frontmatter(text, notes_path)

    body = render_body(key, entry, layout, full_path, notes.strip())
    text = join_frontmatter(merge_properties(notes_properties, properties), body)
    path.write_text(text, encoding="utf-8")

    if notes_path.exists():
        notes_path.unlink()
        print(f"Moved {notes_path.name} into {path.name}")
    _remove_legacy_notes(folder, key, keep=path.name)


def _update_note(path, properties):
    """Update the properties of an existing note; the body is left alone."""
    text = path.read_text(encoding="utf-8")
    existing, body = split_frontmatter(text, path)
    updated = join_frontmatter(merge_properties(existing, properties), body)
    if updated != text:
        path.write_text(updated, encoding="utf-8")


def write_entry_files(key, entry, layout, full_path=False):
    """Create or update the files for one entry and return whether its PDF exists."""
    folder = layout.folder(key)
    folder.mkdir(parents=True, exist_ok=True)

    path = layout.note(key)
    properties = entry_properties(key, entry, layout)
    if path.exists():
        _update_note(path, properties)
    else:
        _create_note(path, key, entry, properties, layout, full_path)

    html_path = folder / f"{key}.html"
    url = entry_url(entry)
    if url and not html_path.exists():
        html_path.write_text(
            f'<html><body><a href="{url}">Link to Resource</a></body></html>\n',
            encoding="utf-8",
        )

    bib_path = folder / f"{key}.bib"
    if not bib_path.exists():
        bib_path.write_text(entry.to_string("bibtex"), encoding="utf-8")

    return properties["has_pdf"]


def _remove_legacy_files(output_dir):
    for name, start in _LEGACY_FILES.items():
        path = output_dir / name
        if path.exists() and path.read_text(encoding="utf-8").startswith(start):
            path.unlink()
            print(f"Removed {name}, use {BASE_FILE} instead")


def build_catalogue(bib_path, output_dir, full_path=False, pdf_dir=None):
    """Create or update all notes and write ``Articles.base`` if it does not exist.

    PDFs are looked for in ``pdf_dir`` if given, otherwise in the vault. Returns the
    catalogued entries and the keys of the entries without a PDF.
    """
    entries = load_entries(bib_path)
    layout = Layout(output_dir, pdf_dir)
    output_dir = layout.articles_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        key
        for key, entry in entries.items()
        if not write_entry_files(key, entry, layout, full_path)
    ]

    base_path = output_dir / BASE_FILE
    if not base_path.exists():
        base_path.write_text(BASE, encoding="utf-8")
    _remove_legacy_files(output_dir)
    return entries, missing
