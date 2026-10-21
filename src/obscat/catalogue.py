"""Generate Obsidian notes and an overview table from a BibTeX file.

For every article in the .bib file a folder ``<articles>/<key>/`` is created with:

- ``<title>.md``: the generated note (regenerated on every run),
- ``<key>.bib``: the BibTeX entry (only written once),
- ``<key>.html``: a link to the article online (only written once).

The PDF is expected at ``<articles>/<key>/<key>.pdf`` and your own notes at
``<articles>/<key>/<key>_notes.md``; neither is ever touched.
"""

import re
from pathlib import Path
from urllib.parse import unquote

import yaml
from pybtex.database import parse_file

from obscat import ObscatError
from obscat.text import clean_tag, latex_to_text, month_number, safe_filename

ARTICLE_TYPES = ("article", "inproceedings")
CATALOGUE_FILE = "article_catalogue.md"
MISSING_FILE = "Missing articles.md"

_BIBENTRY_RE = re.compile(r"^bibentry:\s*['\"]?(.*?)['\"]?\s*$", re.MULTILINE)


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
    return [latex_to_text(str(person)) for person in entry.persons.get("author", [])]


def entry_venue(entry):
    for field in ("journal", "booktitle"):
        if entry.fields.get(field):
            return latex_to_text(entry.fields[field])
    return "arXiv" if is_preprint(entry) else None


def entry_date(entry):
    """Return ``YYYY-MM``, ``YYYY`` or ``None``."""
    year = entry.fields.get("year", "").strip()
    if not year:
        return None
    month = month_number(entry.fields.get("month", ""))
    return f"{year}-{month:02d}" if month else year


def entry_url(entry):
    if url := entry.fields.get("url"):
        return unquote(url.replace("\\", ""))
    if doi := entry.fields.get("doi"):
        return f"https://doi.org/{doi}"
    return None


def note_filename(key, entry):
    return f"{safe_filename(entry.fields.get('title', '')) or key}.md"


def render_note(key, entry, folder, full_path=False):
    authors = entry_authors(entry)
    main_author = clean_tag(authors[0]) if authors else "UnknownAuthor"
    year = entry.fields.get("year", "").strip()
    venue = entry_venue(entry)

    frontmatter = {"title": entry_title(entry), "author": main_author}
    if date := entry_date(entry):
        frontmatter["date"] = date
    frontmatter["bibentry"] = key

    tags = [f"#Articles/Author/{main_author}"]
    if year:
        tags.append(f"#Articles/Year/{clean_tag(year)}")
    if venue:
        tags.append(f"#Articles/Journal/{clean_tag(venue)}")

    author_links = ", ".join(f"[[{clean_tag(author)}]]" for author in authors)
    prefix = f"{folder}/" if full_path else ""
    return "\n".join(
        [
            "---",
            yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False).strip(),
            "---",
            " ".join(tags),
            "",
            f"# {entry_title(entry)}",
            "",
            f"Authors: {author_links}",
            "",
            "## Notes",
            f"![[{prefix}{key}_notes.md]]",
            "",
            "## Summary",
            f"![[{prefix}{key}.pdf.jpg]]",
            "",
            "## Full pdf",
            f"![[{prefix}{key}.pdf]]",
            "",
            "## Citation",
            "```cpp",
            entry.to_string("bibtex").strip(),
            "```",
            "",
        ]
    )


def _remove_stale_notes(folder, key, keep):
    """Delete generated notes for ``key`` whose name changed (e.g. a new title)."""
    for path in folder.glob("*.md"):
        if path.name == keep:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.startswith("---\n"):
            continue
        frontmatter = text[4 : text.find("\n---", 4)]
        match = _BIBENTRY_RE.search(frontmatter)
        if match and match.group(1) == key:
            path.unlink()


def write_entry_files(key, entry, output_dir, full_path=False):
    """Write the files for one entry and return whether its PDF exists."""
    folder = Path(output_dir) / key
    folder.mkdir(parents=True, exist_ok=True)

    name = note_filename(key, entry)
    (folder / name).write_text(
        render_note(key, entry, folder, full_path), encoding="utf-8"
    )
    _remove_stale_notes(folder, key, keep=name)

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

    return (folder / f"{key}.pdf").exists()


def _cell(text):
    return text.replace("|", "\\|")


def write_missing_articles(entries, output_dir):
    lines = ["# Missing articles", ""]
    for key, entry in entries.items():
        folder = Path(output_dir) / key
        url = entry_url(entry)
        link = f"[{key}]({url})" if url else key
        lines.append(f"- {link} | [Folder](<{folder}>)")
    path = Path(output_dir) / MISSING_FILE
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_catalogue_table(entries, output_dir, full_path=False):
    lines = [
        "| Article Name | First Author | Year | Journal |",
        "|--------------|--------------|------|---------|",
    ]
    for key, entry in entries.items():
        name = note_filename(key, entry)
        title = _cell(entry_title(entry))
        if full_path:
            link = f"[{title}](<{Path(output_dir) / key / name}>)"
        else:
            link = f"[[{name}]]"
        authors = entry_authors(entry)
        main_author = _cell(authors[0]) if authors else "Unknown Author"
        year = entry.fields.get("year", "Unknown Year")
        venue = _cell(entry_venue(entry) or "Unknown Journal")
        lines.append(f"| {link} | {main_author} | {year} | {venue} |")
    path = Path(output_dir) / CATALOGUE_FILE
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_catalogue(bib_path, output_dir, full_path=False):
    """Generate all notes, the catalogue table and the list of missing PDFs.

    Returns the catalogued entries and the keys of the entries without a PDF.
    """
    entries = load_entries(bib_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        key
        for key, entry in entries.items()
        if not write_entry_files(key, entry, output_dir, full_path)
    ]
    write_missing_articles({key: entries[key] for key in missing}, output_dir)
    write_catalogue_table(entries, output_dir, full_path)
    return entries, missing
