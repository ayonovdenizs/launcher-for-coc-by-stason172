"""Общие фикстуры тестов: конфиги и временная папка «игры»."""

from __future__ import annotations

from pathlib import Path

import pytest

from launcher.config import LauncherConfig, example_config_text, parse_config

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def game_dir(tmp_path: Path) -> Path:
    """Каталог «игры» с обязательными файлами из тестового конфига."""
    (tmp_path / "gamedata").mkdir()
    (tmp_path / "Stalker-CoC.exe").write_bytes(b"stub")
    return tmp_path


@pytest.fixture()
def simple_config(game_dir: Path) -> LauncherConfig:
    """Минимальная валидная конфигурация: две кнопки запуска и ссылка."""
    payload = {
        "name": "Тестовый лаунчер",
        "hint": "Выберите режим",
        "footer": "Тест · {version}",
        "accent": "#3f7d5a",
        "hero": {"kicker": "KICKER", "title": "ЗАГОЛОВОК", "subtitle": "подпись"},
        "window": {"width": 420, "hero_height": 120},
        "game": {
            "executable": "Stalker-CoC.exe",
            "required_files": ["Stalker-CoC.exe", "gamedata"],
        },
        "update": {"enabled": True, "repo": "owner/repo"},
        "options": [
            {
                "key": "run",
                "title": "ЗАПУСК",
                "description": "Обычный запуск",
                "action": "run",
                "args": ["-skip_reg"],
                "accent": True,
            },
            {
                "key": "site",
                "title": "САЙТ",
                "description": "Новости",
                "action": "url",
                "url": "https://example.com",
            },
        ],
    }
    return parse_config(payload, path=game_dir / "config.launcher", game_dir=game_dir)


@pytest.fixture()
def config_file(tmp_path: Path, game_dir: Path) -> Path:
    """Файл config.launcher с валидным содержимым (для CLI-тестов)."""
    path = game_dir / "config.launcher"
    path.write_text(example_config_text(), encoding="utf-8")
    return path
