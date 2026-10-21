import pytest
from pybtex.database import parse_file

from obscat import ObscatError, articles
from obscat.articles import add_article, detect_identifier, parse_single_entry

NEW_ENTRY = r"""
@article{New_2023,
  title = {A new article},
  author = {New, Nina},
  journal = {Nuclear Fusion},
  year = {2023},
  doi = {10.1088/1741-4326/new},
}
"""


@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace HTTP requests with a canned BibTeX response and record the URLs."""
    urls = []

    def http_get(url, accept):
        urls.append(url)
        return NEW_ENTRY

    monkeypatch.setattr(articles, "_http_get", http_get)
    return urls


@pytest.mark.parametrize(
    ("text", "metadata", "expected"),
    [
        (
            "Published at https://doi.org/10.1017/S00223778.",
            None,
            ("doi", "10.1017/S00223778"),
        ),
        (
            "arXiv:2101.00001v2 [physics.plasm-ph] 1 Jan 2021",
            None,
            ("arxiv", "2101.00001"),
        ),
        ("arXiv:2101.00001 and doi 10.1/x", None, ("arxiv", "2101.00001")),
        (
            "arXiv:2101.00001",
            {"subject": "doi:10.1063/5.0001"},
            ("doi", "10.1063/5.0001"),
        ),
    ],
)
def test_detect_identifier(tmp_path, make_pdf, text, metadata, expected):
    pdf = make_pdf(tmp_path / "a.pdf", pages=1, text=text, metadata=metadata)
    assert detect_identifier(pdf) == expected


def test_detect_identifier_fails_without_identifier(tmp_path, make_pdf):
    pdf = make_pdf(tmp_path / "a.pdf", text="nothing here")
    with pytest.raises(ObscatError, match="Could not find"):
        detect_identifier(pdf)


def test_parse_single_entry():
    key, entry = parse_single_entry(NEW_ENTRY)
    assert key == "New_2023"
    assert entry.fields["journal"] == "Nuclear Fusion"


@pytest.mark.parametrize("bibtex", ["", NEW_ENTRY + NEW_ENTRY.replace("New_2023", "x")])
def test_parse_single_entry_rejects_zero_or_many(bibtex):
    with pytest.raises(ObscatError, match="exactly one"):
        parse_single_entry(bibtex)


def test_add_with_bibtex(tmp_path, bib_file, articles_dir, make_pdf):
    pdf = make_pdf(tmp_path / "download.pdf")
    key = add_article(pdf, bib_file, articles_dir, bibtex=NEW_ENTRY)

    assert key == "New_2023"
    assert (articles_dir / key / f"{key}.pdf").read_bytes() == pdf.read_bytes()
    assert pdf.exists()
    entries = parse_file(str(bib_file)).entries
    assert list(entries)[-1] == "New_2023"
    assert len(entries) == 5


def test_add_keeps_existing_bib_text(tmp_path, bib_file, articles_dir, make_pdf):
    original = bib_file.read_text()
    add_article(make_pdf(tmp_path / "a.pdf"), bib_file, articles_dir, bibtex=NEW_ENTRY)
    assert bib_file.read_text().startswith(original + "\n@article{New_2023,")


def test_add_to_new_bib_file(tmp_path, articles_dir, make_pdf):
    bib = tmp_path / "new" / "refs.bib"
    add_article(make_pdf(tmp_path / "a.pdf"), bib, articles_dir, bibtex=NEW_ENTRY)
    assert list(parse_file(str(bib)).entries) == ["New_2023"]


def test_add_with_custom_key_and_move(tmp_path, bib_file, articles_dir, make_pdf):
    pdf = make_pdf(tmp_path / "a.pdf")
    key = add_article(
        pdf, bib_file, articles_dir, bibtex=NEW_ENTRY, key="new2023", move=True
    )
    assert key == "new2023"
    assert not pdf.exists()
    assert (articles_dir / "new2023" / "new2023.pdf").exists()
    assert "new2023" in parse_file(str(bib_file)).entries
    assert "@article{new2023," in bib_file.read_text()


def test_add_fetches_doi(tmp_path, bib_file, articles_dir, make_pdf, fake_fetch):
    add_article(make_pdf(tmp_path / "a.pdf"), bib_file, articles_dir, doi="10.1/abc")
    assert fake_fetch == ["https://doi.org/10.1/abc"]


def test_add_fetches_arxiv(tmp_path, bib_file, articles_dir, make_pdf, fake_fetch):
    add_article(
        make_pdf(tmp_path / "a.pdf"), bib_file, articles_dir, arxiv="2101.00001"
    )
    assert fake_fetch == ["https://arxiv.org/bibtex/2101.00001"]


def test_add_detects_identifier(tmp_path, bib_file, articles_dir, make_pdf, fake_fetch):
    pdf = make_pdf(tmp_path / "a.pdf", text="arXiv:2302.12345v1 [cs.LG]")
    add_article(pdf, bib_file, articles_dir)
    assert fake_fetch == ["https://arxiv.org/bibtex/2302.12345"]


def test_add_rejects_duplicate_key(tmp_path, bib_file, articles_dir, make_pdf):
    original = bib_file.read_text()
    with pytest.raises(ObscatError, match="already contains an entry with key"):
        add_article(
            make_pdf(tmp_path / "a.pdf"),
            bib_file,
            articles_dir,
            bibtex=NEW_ENTRY,
            key="DOE2020GYRO",
        )
    assert bib_file.read_text() == original
    assert not articles_dir.exists()


def test_add_rejects_duplicate_doi(tmp_path, bib_file, articles_dir, make_pdf):
    duplicate = NEW_ENTRY.replace("10.1088/1741-4326/new", "10.1017/s0022377820000001")
    with pytest.raises(ObscatError, match="already contains this DOI as doe2020gyro"):
        add_article(
            make_pdf(tmp_path / "a.pdf"), bib_file, articles_dir, bibtex=duplicate
        )


def test_add_refuses_to_overwrite_pdf(tmp_path, bib_file, articles_dir, make_pdf):
    make_pdf(articles_dir / "New_2023" / "New_2023.pdf")
    with pytest.raises(ObscatError, match="already exists"):
        add_article(
            make_pdf(tmp_path / "a.pdf"), bib_file, articles_dir, bibtex=NEW_ENTRY
        )


def test_add_missing_pdf(tmp_path, bib_file, articles_dir):
    with pytest.raises(ObscatError, match="does not exist"):
        add_article(tmp_path / "nope.pdf", bib_file, articles_dir, bibtex=NEW_ENTRY)


def test_add_to_external_pdf_folder(tmp_path, bib_file, articles_dir, make_pdf):
    papers = tmp_path / "papers"
    key = add_article(
        make_pdf(tmp_path / "a.pdf"),
        bib_file,
        articles_dir,
        bibtex=NEW_ENTRY,
        pdf_dir=papers,
    )
    assert (papers / f"{key}.pdf").exists()
    assert not articles_dir.exists()
