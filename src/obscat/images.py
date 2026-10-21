"""Render a preview collage of the first pages of each article's PDF.

The collage is written to ``<articles>/<key>/<key>.pdf.jpg`` in the vault (also
when the PDF itself lives outside the vault) and embedded in the note.
"""

import sys
from pathlib import Path

import pymupdf
from PIL import Image

MAX_COLLAGE_PAGES = 16
IMAGES_PER_ROW = 4
# 50 dpi keeps a 16 page collage around 0.5 MB while the pages stay recognisable.
DEFAULT_DPI = 50


def render_pages(pdf_path, max_pages=None, dpi=DEFAULT_DPI):
    """Render the first ``max_pages`` pages (all if ``None``) of a PDF to images."""
    with pymupdf.open(pdf_path) as doc:
        count = len(doc) if max_pages is None else min(len(doc), max_pages)
        images = []
        for page in doc.pages(0, count):
            pixmap = page.get_pixmap(dpi=dpi, alpha=False)
            images.append(
                Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
            )
        return images


def make_collage(images, images_per_row=IMAGES_PER_ROW):
    """Arrange images in a grid of ``images_per_row`` columns on white."""
    width = max(image.width for image in images)
    height = max(image.height for image in images)
    rows = -(-len(images) // images_per_row)

    collage = Image.new("RGB", (width * images_per_row, height * rows), "white")
    for index, image in enumerate(images):
        row, column = divmod(index, images_per_row)
        collage.paste(image, (column * width, row * height))
    return collage


def save_collage(pdf_path, collage_path, overwrite=False, dpi=DEFAULT_DPI):
    """Write the collage for a PDF; return whether it was written."""
    collage_path = Path(collage_path)
    if collage_path.exists() and not overwrite:
        return False

    pages = render_pages(pdf_path, MAX_COLLAGE_PAGES, dpi)
    if not pages:
        raise ValueError(f"{pdf_path} has no pages")
    collage_path.parent.mkdir(parents=True, exist_ok=True)
    make_collage(pages).save(collage_path)
    return True


def remove_frontpages(layout):
    """Delete the front page images written by older versions; return how many."""
    paths = list(layout.articles_dir.glob("*/*.pdf_frontpage.jpg"))
    for path in paths:
        path.unlink()
    return len(paths)


def render_collages(layout, overwrite=False, dpi=DEFAULT_DPI):
    """Render the collage of every article that has a PDF and a folder in the vault.

    A broken PDF is reported and skipped. Returns the keys that got a new collage
    and the keys that failed.
    """
    rendered, failed = [], []
    for key in layout.keys_with_pdf():
        if not layout.folder(key).is_dir():
            continue
        try:
            if save_collage(layout.pdf(key), layout.collage(key), overwrite, dpi):
                rendered.append(key)
        except Exception as error:
            print(f"Error processing {layout.pdf(key)}: {error}", file=sys.stderr)
            failed.append(key)
    return rendered, failed
