"""Сборка и запуск приложения лаунчера."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from . import APP_NAME, ORGANISATION, app_version
from .paths import resolve_game_dir, setup_logging
from .ui import LauncherWindow
from .ui.main_window import load_app_icon
from .ui.theme import STYLESHEET

LOGGER = logging.getLogger(__name__)

CLI_HELP = """Лаунчер Call of Chernobyl (сборка от stason172)

Использование: Launcher-CoC.exe [--version]

Лаунчер работает рядом с игрой: положите его в корневую папку сборки
(туда, где лежит Stalker-CoC.exe) и запустите.
"""


def create_application(argv: list[str]) -> QApplication:
    """QApplication с именем, иконкой и таблицей стилей."""
    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(app_version())
    app.setOrganizationName(ORGANISATION)
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(STYLESHEET)
    return app


def main(argv: list[str] | None = None) -> int:
    """Точка входа: настройка логов, окно, цикл событий."""
    arguments = list(sys.argv if argv is None else argv)

    if "--version" in arguments:
        # у windowed-сборки PyInstaller может не быть stdout
        if sys.stdout is not None:
            print(f"{APP_NAME} {app_version()}")
        return 0

    if "--help" in arguments or "-h" in arguments:
        if sys.stdout is not None:
            print(CLI_HELP)
        return 0

    game_dir: Path = resolve_game_dir()
    log_path = setup_logging(game_dir)
    LOGGER.info("Запуск лаунчера %s", app_version())
    LOGGER.info("Каталог игры: %s", game_dir)
    LOGGER.debug("Файл лога: %s", log_path)

    app = create_application(arguments)
    window = LauncherWindow(game_dir)
    window.show()
    window.fade_in()
    window.start_update_check()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
