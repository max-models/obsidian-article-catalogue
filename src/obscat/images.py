"""Render preview images for article PDFs.

For ``<key>.pdf`` two images are written next to it:

- ``<key>.pdf.jpg``: a collage of the first pages (embedded in the generated note),
- ``<key>.pdf_frontpage.jpg``: the first page.
"""

import sys
from pathlib import Path

import pymupdf
from PIL import Image

MAX_COLLAGE_PAGES = 16
IMAGES_PER_ROW = 4
DEFAULT_DPI = 150


def collage_path(pdf_path):
    return pdf_path.with_name(f"{pdf_path.name}.jpg")


def frontpage_path(pdf_path):
    return pdf_path.with_name(f"{pdf_path.name}_frontpage.jpg")


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


def save_pdf_images(pdf_path, overwrite=False, dpi=DEFAULT_DPI):
    """Write the collage and front page images for a PDF; return the written paths."""
    pdf_path = Path(pdf_path)
    collage, frontpage = collage_path(pdf_path), frontpage_path(pdf_path)
    todo = [path for path in (collage, frontpage) if overwrite or not path.exists()]
    if not todo:
        return []

    pages = render_pages(pdf_path, MAX_COLLAGE_PAGES, dpi)
    if not pages:
        raise ValueError(f"{pdf_path} has no pages")
    if collage in todo:
        make_collage(pages).save(collage)
    if frontpage in todo:
        pages[0].save(frontpage)
    return todo


def process_pdfs(input_dir, overwrite=False, dpi=DEFAULT_DPI):
    """Render images for every PDF below ``input_dir``.

    A broken PDF is reported and skipped. Returns the PDFs that got new images and
    the PDFs that failed.
    """
    rendered, failed = [], []
    for pdf_path in sorted(Path(input_dir).rglob("*.pdf")):
        try:
            if save_pdf_images(pdf_path, overwrite, dpi):
                rendered.append(pdf_path)
        except Exception as error:
            print(f"Error processing {pdf_path}: {error}", file=sys.stderr)
            failed.append(pdf_path)
    return rendered, failed
