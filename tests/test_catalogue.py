import pytest
import yaml

from obscat import ObscatError
from obscat.catalogue import (
    CATALOGUE_FILE,
    MISSING_FILE,
    build_catalogue,
    load_entries,
)

DOE_NOTE = "Gyrokinetic simulations - W7-X and LHD.md"
SMITH_NOTE = "Fast solvers for α particles.md"


def read_frontmatter(path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    return yaml.safe_load(text.split("---\n")[1])


def test_load_entries_keeps_articles_papers_and_preprints(bib_file):
    assert list(load_entries(bib_file)) == [
        "doe2020gyro",
        "smith2019conf",
        "lee2021arxiv",
    ]


def test_load_entries_missing_file(tmp_path):
    with pytest.raises(ObscatError, match="does not exist"):
        load_entries(tmp_path / "nope.bib")


def test_build_creates_one_folder_per_entry(bib_file, articles_dir):
    entries, missing = build_catalogue(bib_file, articles_dir)
    assert set(entries) == {"doe2020gyro", "smith2019conf", "lee2021arxiv"}
    assert missing == list(entries)
    for key in entries:
        assert (articles_dir / key / f"{key}.bib").is_file()
    assert (articles_dir / "doe2020gyro" / DOE_NOTE).is_file()
    assert (articles_dir / "smith2019conf" / SMITH_NOTE).is_file()
    assert (articles_dir / "lee2021arxiv" / "A preprint.md").is_file()
    assert not (articles_dir / "knuth1984").exists()


def test_note_frontmatter_is_valid_yaml(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    assert read_frontmatter(articles_dir / "doe2020gyro" / DOE_NOTE) == {
        "title": "Gyrokinetic simulations: W7-X & LHD",
        "author": "DoeJane",
        "date": "2020-01",
        "bibentry": "doe2020gyro",
    }
    assert (
        read_frontmatter(articles_dir / "smith2019conf" / SMITH_NOTE)["date"]
        == "2019-11"
    )


def test_note_content(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    note = (articles_dir / "doe2020gyro" / DOE_NOTE).read_text(encoding="utf-8")
    assert (
        "#Articles/Author/DoeJane #Articles/Year/2020 "
        "#Articles/Journal/JournalofPlasmaPhysics"
    ) in note
    assert "Authors: [[DoeJane]], [[MüllerHans]]" in note
    assert "![[doe2020gyro_notes.md]]" in note
    assert "![[doe2020gyro.pdf.jpg]]" in note
    assert "![[doe2020gyro.pdf]]" in note
    assert "@article{doe2020gyro," in note


def test_booktitle_and_arxiv_used_as_venue(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    smith = (articles_dir / "smith2019conf" / SMITH_NOTE).read_text(encoding="utf-8")
    assert "#Articles/Journal/ProceedingsoftheAPSDPP" in smith
    lee = (articles_dir / "lee2021arxiv" / "A preprint.md").read_text(encoding="utf-8")
    assert "#Articles/Journal/arXiv" in lee


def test_full_path_links(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir, full_path=True)
    folder = articles_dir / "doe2020gyro"
    note = (folder / DOE_NOTE).read_text(encoding="utf-8")
    assert f"![[{folder}/doe2020gyro.pdf]]" in note
    table = (articles_dir / CATALOGUE_FILE).read_text(encoding="utf-8")
    assert f"(<{folder / DOE_NOTE}>)" in table


def test_html_link(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    doe = (articles_dir / "doe2020gyro" / "doe2020gyro.html").read_text()
    assert 'href="https://doi.org/10.1017/S0022377820000001"' in doe
    smith = (articles_dir / "smith2019conf" / "smith2019conf.html").read_text()
    assert 'href="https://example.org/paper/one"' in smith
    assert not (articles_dir / "lee2021arxiv" / "lee2021arxiv.html").exists()


def test_catalogue_table(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    lines = (articles_dir / CATALOGUE_FILE).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "| Article Name | First Author | Year | Journal |"
    assert lines[2] == (
        f"| [[{DOE_NOTE}]] | Doe, Jane | 2020 | Journal of Plasma Physics |"
    )
    assert len(lines) == 5


def test_missing_articles_lists_only_entries_without_pdf(bib_file, articles_dir):
    (articles_dir / "doe2020gyro").mkdir(parents=True)
    (articles_dir / "doe2020gyro" / "doe2020gyro.pdf").write_bytes(b"%PDF")
    _, missing = build_catalogue(bib_file, articles_dir)
    assert missing == ["smith2019conf", "lee2021arxiv"]
    text = (articles_dir / MISSING_FILE).read_text(encoding="utf-8")
    assert "doe2020gyro" not in text
    assert "- [smith2019conf](https://example.org/paper/one) | [Folder](<" in text
    assert "- lee2021arxiv | [Folder](<" in text


def test_existing_bib_and_html_are_not_overwritten(bib_file, articles_dir):
    folder = articles_dir / "doe2020gyro"
    folder.mkdir(parents=True)
    (folder / "doe2020gyro.bib").write_text("my edits")
    (folder / "doe2020gyro.html").write_text("my link")
    build_catalogue(bib_file, articles_dir)
    assert (folder / "doe2020gyro.bib").read_text() == "my edits"
    assert (folder / "doe2020gyro.html").read_text() == "my link"


def test_renamed_title_removes_old_note_but_keeps_user_notes(bib_file, articles_dir):
    folder = articles_dir / "doe2020gyro"
    folder.mkdir(parents=True)
    # A note generated by an older version: unquoted, invalid YAML title.
    old = folder / "Old title.md"
    old.write_text("---\ntitle: Old: title\nbibentry: doe2020gyro\n---\nbody")
    other = folder / "Other entry.md"
    other.write_text("---\nbibentry: someoneelse\n---\n")
    notes = folder / "doe2020gyro_notes.md"
    notes.write_text("my notes")

    build_catalogue(bib_file, articles_dir)

    assert not old.exists()
    assert other.exists()
    assert notes.read_text() == "my notes"
    assert (folder / DOE_NOTE).exists()


def test_build_is_idempotent(bib_file, articles_dir):
    build_catalogue(bib_file, articles_dir)
    first = {p: p.read_bytes() for p in articles_dir.rglob("*") if p.is_file()}
    build_catalogue(bib_file, articles_dir)
    second = {p: p.read_bytes() for p in articles_dir.rglob("*") if p.is_file()}
    assert first == second


def test_entry_without_title_uses_key(tmp_path, articles_dir):
    bib = tmp_path / "refs.bib"
    bib.write_text("@article{notitle, author={A, B}, journal={J}, year={2000}}")
    build_catalogue(bib, articles_dir)
    assert (articles_dir / "notitle" / "notitle.md").is_file()
