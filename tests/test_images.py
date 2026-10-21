from PIL import Image

from obscat.images import (
    collage_path,
    frontpage_path,
    make_collage,
    process_pdfs,
    render_pages,
    save_pdf_images,
)


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


def test_save_pdf_images(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "key.pdf", pages=5)
    written = save_pdf_images(pdf, dpi=72)
    assert written == [tmp_path / "key.pdf.jpg", tmp_path / "key.pdf_frontpage.jpg"]
    with Image.open(collage_path(pdf)) as collage:
        assert collage.size == (800, 600)
    with Image.open(frontpage_path(pdf)) as frontpage:
        assert frontpage.size == (200, 300)


def test_collage_is_limited_to_16_pages(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "long.pdf", pages=20)
    save_pdf_images(pdf, dpi=72)
    with Image.open(collage_path(pdf)) as collage:
        assert collage.size == (800, 1200)


def test_existing_images_are_skipped_unless_overwrite(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "key.pdf")
    save_pdf_images(pdf, dpi=72)
    assert save_pdf_images(pdf, dpi=72) == []
    assert len(save_pdf_images(pdf, overwrite=True, dpi=72)) == 2


def test_only_missing_image_is_rendered(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "key.pdf")
    save_pdf_images(pdf, dpi=72)
    frontpage_path(pdf).unlink()
    assert save_pdf_images(pdf, dpi=72) == [frontpage_path(pdf)]


def test_process_pdfs_recurses_and_survives_broken_pdfs(tmp_path, make_pdf, capsys):
    good = make_pdf(tmp_path / "a" / "a.pdf")
    broken = tmp_path / "b" / "b.pdf"
    broken.parent.mkdir()
    broken.write_bytes(b"not a pdf")

    rendered, failed = process_pdfs(tmp_path, dpi=72)

    assert rendered == [good]
    assert failed == [broken]
    assert "Error processing" in capsys.readouterr().err
    assert collage_path(good).exists()
