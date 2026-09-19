"""Проверки путей, поиска ресурсов и логирования."""

from __future__ import annotations

import logging
from pathlib import Path

from launcher.paths import (
    ASSETS_DIR,
    LOG_FILENAME,
    find_asset,
    resolve_game_dir,
    resource_path,
    resource_root,
    setup_logging,
)

ROOT = Path(__file__).resolve().parent.parent


def test_resolve_game_dir_is_project_root() -> None:
    assert resolve_game_dir() == ROOT


def test_resource_path_points_into_assets() -> None:
    assert resource_root() == ROOT
    assert resource_path("assets", "icon.ico").name == "icon.ico"
    assert ASSETS_DIR == "assets"


def test_find_asset_prefers_config_path(tmp_path: Path) -> None:
    own = tmp_path / "art"
    own.mkdir()
    background = own / "фон.jpg"
    background.write_bytes(b"art")

    assert find_asset("art/фон.jpg", tmp_path, "background.jpg") == background


def test_find_asset_falls_back_to_bundled(tmp_path: Path) -> None:
    assert find_asset(None, tmp_path, "background.jpg") == ROOT / "assets" / "background.jpg"
    assert find_asset("нет-такого.jpg", tmp_path, "background.jpg") == (
        ROOT / "assets" / "background.jpg"
    )


def test_find_asset_returns_none_when_nothing_found(tmp_path: Path) -> None:
    assert find_asset("нет.jpg", tmp_path, "тоже-нет.jpg") is None


def test_find_asset_expands_environment(tmp_path: Path, monkeypatch) -> None:
    art_dir = tmp_path / "art"
    art_dir.mkdir()
    (art_dir / "bg.png").write_bytes(b"art")
    monkeypatch.setenv("TEST_ART_DIR", str(art_dir))

    assert find_asset("%TEST_ART_DIR%/bg.png", tmp_path, "background.jpg") == art_dir / "bg.png"


def test_setup_logging_writes_file(tmp_path: Path) -> None:
    log_path = setup_logging(tmp_path)

    assert log_path == tmp_path / LOG_FILENAME
    logging.getLogger("launcher.test").warning("проверка записи")
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert "проверка записи" in log_path.read_text(encoding="utf-8")


def test_setup_logging_survives_unwritable_dir(tmp_path: Path) -> None:
    blocked = tmp_path / "file-instead-of-dir"
    blocked.write_text("", encoding="utf-8")

    # пишем «в файл» — FileHandler бросит OSError, логирование остаётся в консоли
    assert setup_logging(blocked) is None
