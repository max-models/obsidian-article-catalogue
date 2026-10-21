import pytest

from obscat import ObscatError
from obscat.catalogue import build_catalogue
from obscat.layout import Layout
from obscat.pdfs import move_pdfs, pdf_markdown, pdf_property


@pytest.fixture
def pdf_dir(tmp_path):
    path = tmp_path / "Nextcloud Papers"
    path.mkdir()
    return path


def test_layout_in_vault(articles_dir):
    layout = Layout(articles_dir)
    assert layout.pdf("k") == articles_dir / "k" / "k.pdf"
    assert layout.collage("k") == articles_dir / "k" / "k.pdf.jpg"
    assert layout.note("k") == articles_dir / "k" / "@k.md"
    assert pdf_property(layout, "k") == "[[k.pdf]]"
    assert pdf_markdown(layout, "k") == "![[k.pdf]]"


def test_layout_with_external_pdfs(articles_dir, pdf_dir):
    layout = Layout(articles_dir, pdf_dir)
    assert layout.pdf("k") == pdf_dir / "k.pdf"
    assert layout.collage("k") == articles_dir / "k" / "k.pdf.jpg"
    uri = pdf_dir.absolute().as_uri() + "/k.pdf"
    assert "%20" in uri
    assert pdf_property(layout, "k") == uri
    assert pdf_markdown(layout, "k") == f"[Open PDF]({uri})"


def test_keys_with_pdf(articles_dir, pdf_dir, make_pdf):
    make_pdf(articles_dir / "a" / "a.pdf")
    make_pdf(articles_dir / "a" / "supplement.pdf")
    make_pdf(pdf_dir / "b.pdf")
    assert Layout(articles_dir).keys_with_pdf() == ["a"]
    assert Layout(articles_dir, pdf_dir).keys_with_pdf() == ["b"]


def test_move_pdfs(bib_file, articles_dir, pdf_dir, make_pdf):
    pdf = make_pdf(articles_dir / "doe2020gyro" / "doe2020gyro.pdf")
    content = pdf.read_bytes()
    build_catalogue(bib_file, articles_dir)
    note = articles_dir / "doe2020gyro" / "@doe2020gyro.md"
    assert "![[doe2020gyro.pdf]]" in note.read_text()

    moved, skipped = move_pdfs(articles_dir, pdf_dir)

    assert moved == ["doe2020gyro"]
    assert skipped == []
    assert not pdf.exists()
    assert (pdf_dir / "doe2020gyro.pdf").read_bytes() == content
    layout = Layout(articles_dir, pdf_dir)
    text = note.read_text()
    assert "![[doe2020gyro.pdf]]" not in text
    assert pdf_markdown(layout, "doe2020gyro") in text


def test_move_pdfs_removes_identical_copy(articles_dir, pdf_dir, make_pdf):
    original = make_pdf(pdf_dir / "a.pdf")
    vault_copy = articles_dir / "a" / "a.pdf"
    vault_copy.parent.mkdir(parents=True)
    vault_copy.write_bytes(original.read_bytes())
    assert move_pdfs(articles_dir, pdf_dir) == (["a"], [])
    assert not vault_copy.exists()


def test_move_pdfs_skips_conflicts(articles_dir, pdf_dir, make_pdf, capsys):
    make_pdf(pdf_dir / "a.pdf", text="one version")
    vault_copy = make_pdf(articles_dir / "a" / "a.pdf", text="another version")
    assert move_pdfs(articles_dir, pdf_dir) == ([], ["a"])
    assert vault_copy.exists()
    assert "a different" in capsys.readouterr().out


def test_move_pdfs_reports_edited_notes(articles_dir, pdf_dir, make_pdf, capsys):
    make_pdf(articles_dir / "a" / "a.pdf")
    (articles_dir / "a" / "@a.md").write_text("I removed the embed")
    move_pdfs(articles_dir, pdf_dir)
    assert "link it yourself" in capsys.readouterr().out
    assert (articles_dir / "a" / "@a.md").read_text() == "I removed the embed"


def test_move_pdfs_needs_existing_folder(tmp_path, articles_dir):
    with pytest.raises(ObscatError, match="does not exist"):
        move_pdfs(articles_dir, tmp_path / "nope")


def test_move_pdfs_only_given_keys(articles_dir, pdf_dir, make_pdf):
    make_pdf(articles_dir / "a" / "a.pdf")
    other = make_pdf(articles_dir / "b" / "b.pdf")
    assert move_pdfs(articles_dir, pdf_dir, keys={"a"}) == (["a"], [])
    assert other.exists()
