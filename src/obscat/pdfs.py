"""Links to the PDFs and moving them out of the vault."""

import filecmp
import re
import shutil

from obscat import ObscatError
from obscat.layout import Layout


def pdf_uri(layout, key):
    return layout.pdf(key).absolute().as_uri()


def pdf_property(layout, key):
    """The ``pdf`` property of a note: a file:// URL or a link inside the vault."""
    if layout.external_pdfs:
        return pdf_uri(layout, key)
    return f"[[{key}.pdf]]"


def pdf_markdown(layout, key, prefix=""):
    """How the note body shows the PDF: a link to open it, or the embedded PDF."""
    if layout.external_pdfs:
        return f"[Open PDF]({pdf_uri(layout, key)})"
    return f"![[{prefix}{key}.pdf]]"


def _relink_note(note, key, link):
    """Replace the embedded PDF in a note body by ``link``; return whether it did."""
    text = note.read_text(encoding="utf-8")
    embed = re.compile(rf"^!\[\[(?:[^\]]*/)?{re.escape(key)}\.pdf\]\]$", re.MULTILINE)
    updated, count = embed.subn(lambda _: link, text)
    if count:
        note.write_text(updated, encoding="utf-8")
    return bool(count)


def move_pdfs(articles_dir, pdf_dir):
    """Move ``<articles>/<key>/<key>.pdf`` to ``<pdf_dir>/<key>.pdf``.

    The embedded PDF in each note is replaced by a link to the new location. A PDF
    is not moved if a different file with the same name already exists in
    ``pdf_dir``. Returns the moved keys and the skipped keys.
    """
    vault, external = Layout(articles_dir), Layout(articles_dir, pdf_dir)
    if not external.pdf_dir.is_dir():
        raise ObscatError(f"PDF folder {external.pdf_dir} does not exist")

    moved, skipped = [], []
    for key in vault.keys_with_pdf():
        source, target = vault.pdf(key), external.pdf(key)
        if target.exists():
            if not filecmp.cmp(source, target, shallow=False):
                print(f"Skipping {key}: a different {target} already exists")
                skipped.append(key)
                continue
            source.unlink()
        else:
            shutil.move(source, target)
        note = vault.note(key)
        if note.exists() and not _relink_note(note, key, pdf_markdown(external, key)):
            print(f"Could not find the embedded PDF in {note.name}, link it yourself")
        moved.append(key)
    return moved, skipped
