"""Persistent user configuration: where the .bib file and the articles folder live."""

import os
from pathlib import Path

import yaml
from platformdirs import user_config_path

from obscat import ObscatError

KEYS = ("bib_file_path", "article_folder_path")


def config_path(path=None):
    """Return the config file to use.

    Priority: the ``path`` argument, the ``OBSCAT_CONFIG`` environment variable,
    then the platform's user config folder (e.g. ``~/.config/obscat/config.yml``).
    """
    if path is None:
        path = (
            os.environ.get("OBSCAT_CONFIG") or user_config_path("obscat") / "config.yml"
        )
    return Path(path).expanduser()


def load_config(path=None):
    """Load the config as a dict with all of ``KEYS``; missing values are ``None``."""
    path = config_path(path)
    config = dict.fromkeys(KEYS)
    if not path.exists():
        return config

    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ObscatError(f"Config file {path} is malformed")
    config.update({key: data.get(key) for key in KEYS})
    return config


def save_config(path=None, **values):
    """Update the config with the given non-``None`` values and return its path."""
    path = config_path(path)
    unknown = set(values) - set(KEYS)
    if unknown:
        raise ObscatError(f"Unknown config keys: {', '.join(sorted(unknown))}")

    config = load_config(path)
    for key, value in values.items():
        if value is not None:
            config[key] = str(Path(value).expanduser().resolve())

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path
