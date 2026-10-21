from PIL import Image

from obscat.images import (
    make_collage,
    remove_frontpages,
    render_collages,
    render_pages,
    save_collage,
)
from obscat.layout import Layout


def test_render_pages(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "a.pdf", pages=3)
    pages = render_pages(pdf, dpi=72)
    assert len(pages) == 3
    assert pages[0].size == (200, 300)
    assert len(render_pages(pdf, max_pages=2, dpi=72)) == 2


def test_make_collage_grid():
    images = [Image.new("RGB", (10, 20), "black") for _ in range(5)]
    collage = make_collage(images, images_per_row=4)
    assert collage.size == (40, 40)
    # The unused cells of the last row are white.
    assert collage.getpixel((35, 35)) == (255, 255, 255)
    assert collage.getpixel((5, 25)) == (0, 0, 0)


def test_save_collage(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "key.pdf", pages=5)
    collage = tmp_path / "vault" / "key.pdf.jpg"
    assert save_collage(pdf, collage, dpi=72)
    with Image.open(collage) as image:
        assert image.size == (800, 600)


def test_default_resolution_is_small(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "key.pdf", pages=1)
    save_collage(pdf, tmp_path / "key.pdf.jpg")
    with Image.open(tmp_path / "key.pdf.jpg") as image:
        # 200x300 pt pages at 50 dpi
        assert image.size == (4 * 139, 209)


def test_collage_is_limited_to_16_pages(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "long.pdf", pages=20)
    save_collage(pdf, tmp_path / "long.pdf.jpg", dpi=72)
    with Image.open(tmp_path / "long.pdf.jpg") as image:
        assert image.size == (800, 1200)


def test_existing_collage_is_skipped_unless_overwrite(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "key.pdf")
    collage = tmp_path / "key.pdf.jpg"
    assert save_collage(pdf, collage, dpi=72)
    assert not save_collage(pdf, collage, dpi=72)
    assert save_collage(pdf, collage, overwrite=True, dpi=72)


def test_render_collages_in_vault(articles_dir, make_pdf, capsys):
    layout = Layout(articles_dir)
    good = make_pdf(layout.pdf("good"))
    layout.folder("broken").mkdir(parents=True)
    layout.pdf("broken").write_bytes(b"not a pdf")
    make_pdf(layout.folder("good") / "other.pdf")  # not <key>.pdf, ignored

    rendered, failed = render_collages(layout, dpi=72)

    assert rendered == ["good"]
    assert failed == ["broken"]
    assert "Error processing" in capsys.readouterr().err
    assert layout.collage("good").exists()
    assert good.exists()


def test_render_collages_with_external_pdfs(tmp_path, articles_dir, make_pdf):
    layout = Layout(articles_dir, tmp_path / "papers")
    make_pdf(layout.pdf("a"))
    make_pdf(layout.pdf("no_note"))
    layout.folder("a").mkdir(parents=True)

    rendered, failed = render_collages(layout, dpi=72)

    assert rendered == ["a"]
    assert failed == []
    assert layout.collage("a").exists()
    assert not layout.folder("no_note").exists()


def test_remove_frontpages(articles_dir):
    (articles_dir / "a").mkdir(parents=True)
    (articles_dir / "a" / "a.pdf_frontpage.jpg").write_bytes(b"jpg")
    (articles_dir / "a" / "a.pdf.jpg").write_bytes(b"jpg")
    assert remove_frontpages(Layout(articles_dir)) == 1
    assert (articles_dir / "a" / "a.pdf.jpg").exists()
