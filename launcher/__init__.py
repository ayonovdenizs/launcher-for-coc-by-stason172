"""Лаунчер сборки S.T.A.L.K.E.R. Call of Chernobyl от stason172.

Лаунчер универсальный: что показывать и что запускать, описывает файл
``config.launcher`` рядом с ним (см. :mod:`launcher.config`). Пакет содержит
логику — пути, разбор конфига, запуск игры, проверку обновлений,
логирование и интерфейс на PySide6.

Точка входа для пользователя — ``launcher_coc.py`` в корне репозитория
(в собранном виде — ``Launcher-CoC.exe``).
"""

from __future__ import annotations

import os

APP_NAME = "Launcher CoC"
APP_TITLE = "Лаунчер Call of Chernobyl"

ORGANISATION = "stason172"
AUTHOR = "ayden"
REPO_URL = "https://github.com/ayonovdenizs/launcher-for-coc-by-stason172"
RELEASES_URL = f"{REPO_URL}/releases/latest"

# Версия лаунчера. Бампните её вместе с записью в CHANGELOG.md,
# затем поставьте тег ``v<версия>`` — CI соберёт .exe и создаст релиз.
VERSION = "1.2.0"


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
    "ORGANISATION",
    "RELEASES_URL",
    "REPO_URL",
    "VERSION",
    "app_version",
]
