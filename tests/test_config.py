import pytest

from obscat import ObscatError
from obscat.config import config_path, load_config, save_config


def test_missing_config_gives_empty_values(isolated_config):
    assert not isolated_config.exists()
    assert load_config() == dict.fromkeys(
        ["bib_file_path", "article_folder_path", "pdf_folder_path"]
    )


def test_env_variable_selects_config(isolated_config):
    assert config_path() == isolated_config


def test_explicit_path_wins_over_env(tmp_path):
    assert config_path(tmp_path / "other.yml") == tmp_path / "other.yml"


def test_save_and_load_roundtrip(tmp_path, isolated_config):
    path = save_config(bib_file_path=tmp_path / "refs.bib")
    assert path == isolated_config
    assert load_config()["bib_file_path"] == str(tmp_path / "refs.bib")


def test_partial_update_keeps_other_values(tmp_path):
    save_config(bib_file_path=tmp_path / "refs.bib")
    save_config(article_folder_path=tmp_path / "articles")
    assert load_config() == {
        "bib_file_path": str(tmp_path / "refs.bib"),
        "article_folder_path": str(tmp_path / "articles"),
        "pdf_folder_path": None,
    }


def test_paths_are_stored_absolute(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    save_config(bib_file_path="refs.bib")
    assert load_config()["bib_file_path"] == str(tmp_path.resolve() / "refs.bib")


@pytest.mark.parametrize("content", ["", "{}", "bib_file_path: x.bib\n"])
def test_incomplete_config_fills_missing_keys(isolated_config, content):
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text(content)
    config = load_config()
    assert set(config) == {"bib_file_path", "article_folder_path", "pdf_folder_path"}
    assert config["article_folder_path"] is None


def test_malformed_config_raises(isolated_config):
    isolated_config.parent.mkdir(parents=True)
    isolated_config.write_text("- just\n- a list\n")
    with pytest.raises(ObscatError, match="malformed"):
        load_config()


def test_unknown_key_raises():
    with pytest.raises(ObscatError, match="Unknown config keys"):
        save_config(colour="blue")
