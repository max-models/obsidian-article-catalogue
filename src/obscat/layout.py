"""Where the files of an article live.

Everything except the PDF lives in ``<articles>/<key>/`` inside the vault. The PDF
is ``<pdfs>/<key>.pdf`` if a PDF folder outside the vault is configured (e.g. a
Nextcloud folder), otherwise ``<articles>/<key>/<key>.pdf``.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Layout:
    articles_dir: Path
    pdf_dir: Path | None = None

    def __post_init__(self):
        object.__setattr__(self, "articles_dir", Path(self.articles_dir))
        if self.pdf_dir is not None:
            object.__setattr__(self, "pdf_dir", Path(self.pdf_dir))

    @property
    def external_pdfs(self):
        return self.pdf_dir is not None

    def folder(self, key):
        return self.articles_dir / key

    def note(self, key):
        return self.folder(key) / f"@{key}.md"

    def pdf(self, key):
        if self.external_pdfs:
            return self.pdf_dir / f"{key}.pdf"
        return self.folder(key) / f"{key}.pdf"

    def collage(self, key):
        return self.folder(key) / f"{key}.pdf.jpg"

    def keys_with_pdf(self):
        """Return the keys of all PDFs in the PDF folder (or in the vault)."""
        if self.external_pdfs:
            pdfs = self.pdf_dir.glob("*.pdf")
        else:
            pdfs = self.articles_dir.glob("*/*.pdf")
        return sorted(pdf.stem for pdf in pdfs if pdf == self.pdf(pdf.stem))
