"""Лаунчер сборки S.T.A.L.K.E.R. Call of Chernobyl от stason172.

Пакет с логикой лаунчера: пути, таблица режимов запуска, запуск игры,
настройка логирования и интерфейс на PySide6.

Точка входа для пользователя — ``launcher_coc.py`` в корне репозитория.
"""

from __future__ import annotations

import os

APP_NAME = "Launcher CoC"
APP_TITLE = "Лаунчер Call of Chernobyl"
GAME_BUILD = "CoC 1.4.22"
GAME_EXE = "Stalker-CoC.exe"

ORGANISATION = "stason172"
AUTHOR = "ayden"
REPO_URL = "https://github.com/ayonovdenizs/launcher-for-coc-by-stason172"
RELEASES_URL = f"{REPO_URL}/releases/latest"

# Версия лаунчера. Бампните её вместе с записью в CHANGELOG.md,
# затем поставьте тег ``v<версия>`` — CI соберёт .exe и создаст релиз.
VERSION = "1.1.0"


def app_version() -> str:
    """Версия приложения.

    CI может переопределить её переменной окружения ``COC_LAUNCHER_VERSION``
    (например, для сборок не из тега), иначе берётся значение из репозитория.
    """
    return os.environ.get("COC_LAUNCHER_VERSION") or VERSION


__all__ = [
    "APP_NAME",
    "APP_TITLE",
    "AUTHOR",
    "GAME_BUILD",
    "GAME_EXE",
    "ORGANISATION",
    "RELEASES_URL",
    "REPO_URL",
    "VERSION",
    "app_version",
]
