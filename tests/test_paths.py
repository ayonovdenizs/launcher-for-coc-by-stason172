"""Проверки путей и логирования."""

from __future__ import annotations

import logging
from pathlib import Path

from launcher.paths import (
    ASSETS_DIR,
    LOG_FILENAME,
    resolve_game_dir,
    resource_path,
    resource_root,
    setup_logging,
)


def test_resolve_game_dir_is_project_root() -> None:
    root = Path(__file__).resolve().parent.parent
    assert resolve_game_dir() == root


def test_resource_path_points_into_assets() -> None:
    assert resource_root() == Path(__file__).resolve().parent.parent
    assert resource_path("assets", "icon.ico").name == "icon.ico"
    assert ASSETS_DIR == "assets"


def test_setup_logging_writes_file(tmp_path: Path) -> None:
    log_path = setup_logging(tmp_path)

    assert log_path == tmp_path / LOG_FILENAME
    logging.getLogger("launcher.test").warning("проверка записи")
    for handler in logging.getLogger().handlers:
        handler.flush()

    content = log_path.read_text(encoding="utf-8")
    assert "проверка записи" in content


def test_setup_logging_survives_unwritable_dir(tmp_path: Path) -> None:
    blocked = tmp_path / "file-instead-of-dir"
    blocked.write_text("", encoding="utf-8")

    # пишем «в файл» — FileHandler бросит OSError, логирование остаётся в консоли
    assert setup_logging(blocked) is None
