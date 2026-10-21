import pymupdf
import pytest

SAMPLE_BIB = r"""
@article{doe2020gyro,
  title = {{G}yrokinetic simulations: {W7-X} \& {LHD}},
  author = {Doe, Jane and M{\"u}ller, Hans},
  journal = {Journal of Plasma Physics},
  year = {2020},
  month = jan,
  doi = {10.1017/S0022377820000001},
}

@inproceedings{smith2019conf,
  title = {Fast solvers for $\alpha$ particles?},
  author = {Smith, John},
  booktitle = {Proceedings of the APS DPP},
  year = {2019},
  month = {11},
  url = {https://example.org/paper\%2Fone},
}

@misc{lee2021arxiv,
  title = {A preprint},
  author = {Lee, Ann},
  year = {2021},
  eprint = {2101.00001},
  archivePrefix = {arXiv},
}

@book{knuth1984,
  title = {The {\TeX}book},
  author = {Knuth, Donald},
  publisher = {Addison-Wesley},
  year = {1984},
}
"""


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    """Never read or write the real user config during tests."""
    path = tmp_path / "config" / "config.yml"
    monkeypatch.setenv("OBSCAT_CONFIG", str(path))
    return path


@pytest.fixture
def bib_file(tmp_path):
    path = tmp_path / "references.bib"
    path.write_text(SAMPLE_BIB, encoding="utf-8")
    return path


@pytest.fixture
def articles_dir(tmp_path):
    return tmp_path / "articles"


def _make_pdf(path, pages=3, text="Hello", metadata=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open()
    for number in range(pages):
        page = doc.new_page(width=200, height=300)
        page.insert_text((20, 40), f"{text} (page {number + 1})", fontsize=6)
    if metadata:
        doc.set_metadata(metadata)
    doc.save(path)
    doc.close()
    return path


@pytest.fixture
def make_pdf():
    """``make_pdf(path, pages=3, text="Hello", metadata=None)`` writes a small PDF."""
    return _make_pdf
