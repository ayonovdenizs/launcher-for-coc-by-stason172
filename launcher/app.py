"""Сборка и запуск приложения лаунчера.

Импорты PySide6 выполняются лениво: команды ``--version`` и ``--help``
отвечают мгновенно и не требуют поднимать Qt.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from . import APP_NAME, ORGANISATION, app_version
from .console import use_utf8_console
from .paths import resolve_game_dir, setup_logging

if TYPE_CHECKING:  # pragma: no cover - только для аннотаций
    from PySide6.QtWidgets import QApplication

LOGGER = logging.getLogger(__name__)

CLI_HELP = """Лаунчер Call of Chernobyl (сборка от stason172)

Использование: Launcher-CoC.exe [--version] [--help]

Лаунчер работает рядом с игрой: положите его в корневую папку сборки
(туда, где лежит Stalker-CoC.exe) и запустите.

Переменные окружения:
  COC_NO_UPDATE_CHECK=1 — не проверять обновления через GitHub
"""


def create_application(argv: list[str]) -> QApplication:
    """QApplication с именем, иконкой и таблицей стилей."""
    from PySide6.QtWidgets import QApplication

    from .ui.main_window import load_app_icon
    from .ui.theme import STYLESHEET

    app = QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(app_version())
    app.setOrganizationName(ORGANISATION)
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(STYLESHEET)
    return app


def main(argv: list[str] | None = None) -> int:
    """Точка входа: логи, окно, цикл событий."""
    use_utf8_console()
    arguments = list(sys.argv if argv is None else argv)

    if "--version" in arguments:
        _write(f"{APP_NAME} {app_version()}")
        return 0

    if "--help" in arguments or "-h" in arguments:
        _write(CLI_HELP)
        return 0

    game_dir: Path = resolve_game_dir()
    log_path = setup_logging(game_dir)
    LOGGER.info("Запуск лаунчера %s", app_version())
    LOGGER.info("Каталог игры: %s", game_dir)
    LOGGER.debug("Файл лога: %s", log_path)

    from .ui import LauncherWindow

    app = create_application(arguments)
    window = LauncherWindow(game_dir)
    window.show()
    window.fade_in()
    window.start_update_check()
    return app.exec()


def _write(text: str) -> None:
    """Печать в консоль: у windowed-сборки потоков может не быть."""
    if sys.stdout is not None:
        print(text)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
