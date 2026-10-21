import pytest

from obscat.text import clean_tag, latex_to_text, month_number, safe_filename


@pytest.mark.parametrize(
    ("latex", "text"),
    [
        (r"{G}yrokinetic {S}imulations", "Gyrokinetic Simulations"),
        (r"M{\"u}ller", "Müller"),
        (r"A \textendash{} B", "A – B"),
        (r"Ber\hspace{0.167em}nd", "Bernd"),
        ("  lots   of\n space ", "lots of space"),
    ],
)
def test_latex_to_text(latex, text):
    assert latex_to_text(latex) == text


@pytest.mark.parametrize(
    ("title", "filename"),
    [
        (r"Gyrokinetics \& MHD: a review?", "Gyrokinetics and MHD - a review"),
        ("Tokamaks/Stellarators", "Tokamaks or Stellarators"),
        (r"{T}he [best] #1 code | ever^2", "The best 1 code ever2"),
        (r'Quoted "title" with * and <tags>', "Quoted title with and tags"),
        ("Trailing dots...", "Trailing dots"),
        ("", ""),
    ],
)
def test_safe_filename(title, filename):
    assert safe_filename(title) == filename


@pytest.mark.parametrize("char", list('*"\\/<>:|?#^[]'))
def test_safe_filename_removes_forbidden_characters(char):
    assert char not in safe_filename(f"a {char} b")


def test_safe_filename_is_truncated():
    assert len(safe_filename("word " * 100)) <= 150


@pytest.mark.parametrize(
    ("text", "tag"),
    [
        ("Doe, Jane", "DoeJane"),
        (r"M{\"u}ller, Hans", "MüllerHans"),
        ("J. Comput. Phys.", "JComputPhys"),
        ("Plasma Phys. Control. Fusion (UK)", "PlasmaPhysControlFusionUK"),
        ("Smith-Jones", "Smith-Jones"),
    ],
)
def test_clean_tag(text, tag):
    assert clean_tag(text) == tag


@pytest.mark.parametrize(
    ("month", "number"),
    [
        ("jan", 1),
        ("January", 1),
        ("sep.", 9),
        ("Sept", 9),
        ("12", 12),
        ("03", 3),
        ("13", None),
        ("ma", None),
        ("", None),
        ("spring", None),
    ],
)
def test_month_number(month, number):
    assert month_number(month) == number
