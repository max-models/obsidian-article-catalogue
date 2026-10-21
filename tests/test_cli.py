import pytest

from obscat.catalogue import BASE_FILE
from obscat.cli import main
from obscat.config import load_config


def test_config_set_and_show(tmp_path, bib_file, articles_dir, capsys):
    assert main(["config", "-b", str(bib_file), "-a", str(articles_dir)]) == 0
    assert load_config() == {
        "bib_file_path": str(bib_file),
        "article_folder_path": str(articles_dir),
        "pdf_folder_path": None,
    }
    assert main(["config"]) == 0
    out = capsys.readouterr().out
    assert f"bib file:        {bib_file}" in out


def test_config_option_selects_file(tmp_path, bib_file):
    other = tmp_path / "other.yml"
    main(["--config", str(other), "config", "-b", str(bib_file)])
    assert load_config(other)["bib_file_path"] == str(bib_file)
    assert load_config()["bib_file_path"] is None


def test_build_uses_config(bib_file, articles_dir, capsys):
    main(["config", "-b", str(bib_file), "-a", str(articles_dir)])
    assert main(["build"]) == 0
    assert (articles_dir / "doe2020gyro" / "@doe2020gyro.md").exists()
    assert "Wrote 4 notes" in capsys.readouterr().out


def test_build_with_explicit_paths(bib_file, articles_dir):
    assert main(["build", "-b", str(bib_file), "-a", str(articles_dir)]) == 0
    assert (articles_dir / "doe2020gyro" / "@doe2020gyro.md").exists()


def test_build_without_paths_is_a_usage_error(capsys):
    with pytest.raises(SystemExit) as excinfo:
        main(["build"])
    assert excinfo.value.code == 2
    assert "--bib is required" in capsys.readouterr().err


def test_build_missing_bib_file_reports_error(tmp_path, articles_dir, capsys):
    assert (
        main(["build", "-b", str(tmp_path / "nope.bib"), "-a", str(articles_dir)]) == 1
    )
    assert "does not exist" in capsys.readouterr().err


def test_images(articles_dir, make_pdf, capsys):
    make_pdf(articles_dir / "key" / "key.pdf")
    assert main(["images", "-a", str(articles_dir), "--dpi", "72"]) == 0
    assert (articles_dir / "key" / "key.pdf.jpg").exists()
    assert "Rendered 1 previews" in capsys.readouterr().out


def test_images_with_broken_pdf_fails(articles_dir):
    (articles_dir / "key").mkdir(parents=True)
    (articles_dir / "key" / "key.pdf").write_bytes(b"broken")
    assert main(["images", "-a", str(articles_dir)]) == 1


def test_add_builds_catalogue(tmp_path, bib_file, articles_dir, make_pdf):
    entry = tmp_path / "entry.bib"
    entry.write_text("@article{new1, title={Brand new}, author={N, N}, year={2024}}")
    pdf = make_pdf(tmp_path / "paper.pdf")
    main(["config", "-b", str(bib_file), "-a", str(articles_dir)])

    assert main(["add", str(pdf), "--bibtex", str(entry)]) == 0

    folder = articles_dir / "new1"
    assert (folder / "new1.pdf").exists()
    assert (folder / "@new1.md").exists()
    assert (folder / "new1.pdf.jpg").exists()
    assert (articles_dir / BASE_FILE).exists()


def test_add_no_build(tmp_path, bib_file, articles_dir, make_pdf):
    entry = tmp_path / "entry.bib"
    entry.write_text("@article{new1, title={Brand new}, author={N, N}, year={2024}}")
    args = [
        "add",
        str(make_pdf(tmp_path / "p.pdf")),
        "--bibtex",
        str(entry),
        "--no-build",
    ]
    assert main([*args, "-b", str(bib_file), "-a", str(articles_dir)]) == 0
    assert not (articles_dir / "new1" / "@new1.md").exists()


def test_add_sources_are_mutually_exclusive(tmp_path):
    with pytest.raises(SystemExit):
        main(["add", "x.pdf", "--doi", "10.1/x", "--arxiv", "2101.00001"])


def test_external_pdf_folder(tmp_path, bib_file, articles_dir, make_pdf, capsys):
    papers = tmp_path / "Papers"
    papers.mkdir()
    entry = tmp_path / "entry.bib"
    entry.write_text("@article{new1, title={Brand new}, author={N, N}, year={2024}}")
    main(["config", "-b", str(bib_file), "-a", str(articles_dir), "-p", str(papers)])
    assert f"PDF folder:      {papers}" in capsys.readouterr().out

    assert (
        main(["add", str(make_pdf(tmp_path / "paper.pdf")), "--bibtex", str(entry)])
        == 0
    )

    assert (papers / "new1.pdf").exists()
    assert not (articles_dir / "new1" / "new1.pdf").exists()
    assert (articles_dir / "new1" / "new1.pdf.jpg").exists()
    note = (articles_dir / "new1" / "@new1.md").read_text()
    assert f"pdf: {(papers / 'new1.pdf').as_uri()}" in note
    assert f"[Open PDF]({(papers / 'new1.pdf').as_uri()})" in note

    assert main(["images"]) == 0
    assert "Rendered 0 previews" in capsys.readouterr().out


def test_move_pdfs_command(tmp_path, bib_file, articles_dir, make_pdf, capsys):
    papers = tmp_path / "Papers"
    papers.mkdir()
    make_pdf(articles_dir / "doe2020gyro" / "doe2020gyro.pdf")
    not_in_bib = make_pdf(articles_dir / "various" / "various.pdf")
    main(["config", "-b", str(bib_file), "-a", str(articles_dir)])
    main(["build"])
    (articles_dir / "doe2020gyro" / "doe2020gyro.pdf_frontpage.jpg").write_bytes(b"x")

    assert main(["move-pdfs", "-p", str(papers)]) == 0

    assert "Moved 1 PDFs" in capsys.readouterr().out
    assert (papers / "doe2020gyro.pdf").exists()
    assert not_in_bib.exists()
    note = (articles_dir / "doe2020gyro" / "@doe2020gyro.md").read_text()
    assert f"pdf: {(papers / 'doe2020gyro.pdf').as_uri()}" in note
    assert "has_pdf: true" in note

    main(["images", "-p", str(papers)])
    assert "Removed 1 unused front page images" in capsys.readouterr().out


def test_move_pdfs_requires_pdf_folder(bib_file, articles_dir, capsys):
    with pytest.raises(SystemExit):
        main(["move-pdfs", "-b", str(bib_file), "-a", str(articles_dir)])
    assert "--pdfs is required" in capsys.readouterr().err
