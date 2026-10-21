import pytest
import yaml

from obscat import ObscatError
from obscat.catalogue import (
    BASE_FILE,
    build_catalogue,
    merge_properties,
    split_frontmatter,
)

KEYS = ["doe2020gyro", "smith2019conf", "lee2021arxiv", "knuth1984"]


def note_path(articles_dir, key):
    return articles_dir / key / f"@{key}.md"


def read_note(articles_dir, key):
    text = note_path(articles_dir, key).read_text(encoding="utf-8")
    return split_frontmatter(text, key)


def test_missing_bib_file(tmp_path, articles_dir):
    with pytest.raises(ObscatError, match="does not exist"):
        build_catalogue(tmp_path / "nope.bib", articles_dir)


def test_build_creates_one_note_per_entry(bib_file, articles_dir):
    entries, missing = build_catalogue(bib_file, articles_dir)
    assert list(entries) == KEYS
    assert missing == KEYS
    for key in KEYS:
        assert note_path(articles_dir, key).is_file()
        assert (articles_dir / key / f"{key}.bib").is_file()


def test_note_properties(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    properties, _ = read_note(articles_dir, "doe2020gyro")
    assert properties == {
        "title": "Gyrokinetic simulations: W7-X & LHD",
        "aliases": ["Gyrokinetic simulations: W7-X & LHD"],
        "authors": ["[[Jane Doe]]", "[[Hans Müller]]"],
        "year": 2020,
        "month": 1,
        "journal": "Journal of Plasma Physics",
        "doi": "10.1017/S0022377820000001",
        "url": "https://doi.org/10.1017/S0022377820000001",
        "citekey": "doe2020gyro",
        "type": "article",
        "has_pdf": False,
    }


def test_optional_properties_are_left_out(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    properties, _ = read_note(articles_dir, "lee2021arxiv")
    assert properties["journal"] == "arXiv"
    assert "month" not in properties
    assert "doi" not in properties
    assert "url" not in properties


def test_booktitle_is_used_as_journal(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    properties, _ = read_note(articles_dir, "smith2019conf")
    assert properties["journal"] == "Proceedings of the APS DPP"
    assert properties["month"] == 11
    assert properties["url"] == "https://example.org/paper/one"


def test_note_body(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    _, body = read_note(articles_dir, "doe2020gyro")
    assert body.startswith("# Gyrokinetic simulations: W7-X & LHD\n\n## Notes\n")
    assert "![[doe2020gyro.pdf.jpg]]" in body
    assert "![[doe2020gyro.pdf]]" in body
    assert "@article{doe2020gyro," in body


def test_full_path_embeds(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir, full_path=True)
    _, body = read_note(articles_dir, "doe2020gyro")
    assert f"![[{articles_dir / 'doe2020gyro'}/doe2020gyro.pdf]]" in body


def test_rebuild_keeps_body_and_user_properties(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    path = note_path(articles_dir, "doe2020gyro")
    properties, body = split_frontmatter(path.read_text(), path)
    properties["status"] = "read"
    properties["tags"] = ["gyrokinetics"]
    properties["has_pdf"] = True  # wrong on purpose, the build corrects it
    body = body.replace("## Notes\n", "## Notes\n\nVery good paper.\n")
    path.write_text("---\n" + yaml.safe_dump(properties) + "---\n" + body)

    build_catalogue(bib_file, articles_dir)

    properties, new_body = read_note(articles_dir, "doe2020gyro")
    assert new_body == body
    assert properties["status"] == "read"
    assert properties["tags"] == ["gyrokinetics"]
    assert properties["has_pdf"] is False
    assert list(properties)[:2] == ["title", "aliases"]


def test_rebuild_updates_changed_bib_fields(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    bib_file.write_text(
        bib_file.read_text()
        .replace("simulations:", "studies:")
        .replace("  doi = {10.1017/S0022377820000001},\n", "")
    )
    build_catalogue(bib_file, articles_dir)
    properties, _ = read_note(articles_dir, "doe2020gyro")
    assert properties["title"] == "Gyrokinetic studies: W7-X & LHD"
    assert properties["aliases"] == ["Gyrokinetic studies: W7-X & LHD"]
    assert "doi" not in properties


def test_has_pdf(bib_file, articles_dir):
    (articles_dir / "doe2020gyro").mkdir(parents=True)
    (articles_dir / "doe2020gyro" / "doe2020gyro.pdf").write_bytes(b"%PDF")
    _, missing = build_catalogue(bib_file, articles_dir)
    assert missing == ["smith2019conf", "lee2021arxiv", "knuth1984"]
    properties = read_note(articles_dir, "doe2020gyro")[0]
    assert properties["has_pdf"] is True
    assert properties["pdf"] == "[[doe2020gyro.pdf]]"
    assert "pdf" not in read_note(articles_dir, "smith2019conf")[0]


def test_external_pdf_folder(tmp_path, bib_file, articles_dir, make_pdf):
    papers = tmp_path / "papers"
    make_pdf(papers / "doe2020gyro.pdf")
    _, missing = build_catalogue(bib_file, articles_dir, pdf_dir=papers)
    assert missing == ["smith2019conf", "lee2021arxiv", "knuth1984"]
    properties, body = read_note(articles_dir, "doe2020gyro")
    uri = (papers / "doe2020gyro.pdf").as_uri()
    assert properties["pdf"] == uri
    assert f"[Open PDF]({uri})" in body
    assert "![[doe2020gyro.pdf]]" not in body
    assert "![[doe2020gyro.pdf.jpg]]" in body


def test_invalid_user_properties_are_not_overwritten(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    path = note_path(articles_dir, "doe2020gyro")
    path.write_text("---\ntitle: [unclosed\n---\nmy notes")
    with pytest.raises(ObscatError, match="Could not read the properties"):
        build_catalogue(bib_file, articles_dir)
    assert path.read_text() == "---\ntitle: [unclosed\n---\nmy notes"


def test_base_file_is_written_once(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    base = articles_dir / BASE_FILE
    content = yaml.safe_load(base.read_text())
    assert content["filters"] == {"and": ['file.hasProperty("citekey")']}
    assert [view["name"] for view in content["views"]] == [
        "All articles",
        "By journal",
        "Missing PDF",
    ]

    base.write_text("my customised views")
    build_catalogue(bib_file, articles_dir)
    assert base.read_text() == "my customised views"


def test_existing_bib_and_html_are_not_overwritten(bib_file, articles_dir):
    folder = articles_dir / "doe2020gyro"
    folder.mkdir(parents=True)
    (folder / "doe2020gyro.bib").write_text("my edits")
    (folder / "doe2020gyro.html").write_text("my link")
    build_catalogue(bib_file, articles_dir)
    assert (folder / "doe2020gyro.bib").read_text() == "my edits"
    assert (folder / "doe2020gyro.html").read_text() == "my link"


def test_build_is_idempotent(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    first = {p: p.read_bytes() for p in articles_dir.rglob("*") if p.is_file()}
    build_catalogue(bib_file, articles_dir)
    second = {p: p.read_bytes() for p in articles_dir.rglob("*") if p.is_file()}
    assert first == second


def test_migrates_old_layout(bib_file, articles_dir):
    folder = articles_dir / "doe2020gyro"
    folder.mkdir(parents=True)
    # A note generated by an older version: named after the title, invalid YAML.
    old_note = folder / "Gyrokinetic simulations - W7-X and LHD.md"
    old_note.write_text("---\ntitle: Old: title\nbibentry: doe2020gyro\n---\nbody")
    old_lowercase = folder / "Another old title.md"
    old_lowercase.write_text("---\nbibentry: DOE2020GYRO\n---\nbody")
    unrelated = folder / "Unrelated.md"
    unrelated.write_text("---\nbibentry: someoneelse\n---\n")
    user_notes = folder / "doe2020gyro_notes.md"
    user_notes.write_text("---\nstatus: read\n---\nMy notes with a [[link]].\n")
    (articles_dir / "article_catalogue.md").write_text("| Article Name | ... |\n")
    (articles_dir / "Missing articles.md").write_text("# Missing articles\n")

    build_catalogue(bib_file, articles_dir)

    assert not old_note.exists()
    assert not old_lowercase.exists()
    assert not user_notes.exists()
    assert unrelated.exists()
    assert not (articles_dir / "article_catalogue.md").exists()
    assert not (articles_dir / "Missing articles.md").exists()
    properties, body = read_note(articles_dir, "doe2020gyro")
    assert properties["status"] == "read"
    assert "## Notes\n\nMy notes with a [[link]].\n\n## Summary" in body


def test_legacy_files_with_other_content_are_kept(bib_file, articles_dir):
    articles_dir.mkdir()
    (articles_dir / "article_catalogue.md").write_text("my own file")
    build_catalogue(bib_file, articles_dir)
    assert (articles_dir / "article_catalogue.md").exists()


def test_entry_without_title(tmp_path, articles_dir):
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{notitle, author={A, B}, journal={J}, year={2000}}")
    build_catalogue(bib, articles_dir)
    properties, _ = read_note(articles_dir, "notitle")
    assert properties["title"] == "Unknown Title"


@pytest.mark.parametrize(
    ("text", "properties", "body"),
    [
        ("no frontmatter", {}, "no frontmatter"),
        ("---\n---\nbody", {}, "body"),
        ("---\na: 1\n---\nbody\n---\nmore", {"a": 1}, "body\n---\nmore"),
        ("---\na: 1\n---", {"a": 1}, ""),
    ],
)
def test_split_frontmatter(text, properties, body):
    assert split_frontmatter(text, "note.md") == (properties, body)


def test_merge_properties_keeps_user_aliases():
    existing = {"title": "Old", "aliases": ["Old", "Nickname"], "rating": 5}
    managed = {"title": "New", "citekey": "k", "doi": None}
    assert merge_properties(existing, managed) == {
        "title": "New",
        "aliases": ["New", "Nickname"],
        "citekey": "k",
        "rating": 5,
    }


def test_duplicate_fields_are_a_warning(tmp_path, articles_dir, capsys):
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{dup, title={T}, issn={1}, issn={1}, year={2000}}")
    entries, _ = build_catalogue(bib, articles_dir)
    assert list(entries) == ["dup"]
    assert "Warning: refs.bib: entry with key dup has a duplicate issn field" in (
        capsys.readouterr().err
    )


def test_books_get_a_note(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    properties, _ = read_note(articles_dir, "knuth1984")
    assert properties["type"] == "book"
    assert properties["title"] == "The TeXbook"
    assert "journal" not in properties
