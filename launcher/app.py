"""Запуск лаунчера: разбор флагов, чтение конфига, окно.

Импорты PySide6 выполняются лениво: ``--version``, ``--check-config`` и
``--create-config`` работают без Qt и подходят для CI и проверки конфига.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import APP_NAME, ORGANISATION, app_version
from .config import (
    CONFIG_FILENAME,
    ConfigError,
    find_config,
    read_config,
    summarize,
    write_example_config,
)
from .console import use_utf8_console
from .paths import resolve_game_dir, setup_logging

LOGGER = logging.getLogger(__name__)

EXIT_OK = 0
EXIT_CONFIG_ERROR = 2

CLI_DESCRIPTION = f"""Лаунчер мода ({CONFIG_FILENAME})

Что показывать и что запускать, описывает файл {CONFIG_FILENAME} рядом
с лаунчером. Положите лаунчер в корневую папку игры и настройте конфиг."""

CLI_EPILOG = f"""примеры:
  Launcher.exe                        запустить лаунчер
  Launcher.exe --check-config         проверить {CONFIG_FILENAME} и выйти
  Launcher.exe --create-config        создать образец {CONFIG_FILENAME}
  Launcher.exe --config моя\\папка\\{CONFIG_FILENAME}

Переменные окружения:
  COC_NO_UPDATE_CHECK=1               не обращаться к GitHub за обновлениями
  COC_LAUNCHER_VERSION                версия для сборок не из тега
"""


def build_parser() -> argparse.ArgumentParser:
    """Парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=CLI_DESCRIPTION,
        epilog=CLI_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument("--version", action="store_true", help="показать версию и выйти")
    parser.add_argument(
        "--config",
        metavar="ФАЙЛ",
        default=None,
        help=f"путь к файлу настройки (по умолчанию {CONFIG_FILENAME} рядом с лаунчером)",
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="проверить настройки и выйти (без запуска интерфейса)",
    )
    parser.add_argument(
        "--create-config",
        nargs="?",
        const="",
        default=None,
        metavar="ФАЙЛ",
        help=f"создать образец {CONFIG_FILENAME} (по умолчанию рядом с лаунчером)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Точка входа лаунчера."""
    use_utf8_console()
    arguments = list(sys.argv if argv is None else argv)
    parser = build_parser()
    options, unknown = parser.parse_known_args(arguments[1:])
    _ = unknown  # аргументы Qt не мешают работе

    if options.version:
        _write(f"{APP_NAME} {app_version()}")
        return EXIT_OK

    game_dir = resolve_game_dir()

    if options.create_config is not None:
        return _create_config(game_dir, options.create_config)

    if options.check_config:
        return _check_config(game_dir, options.config)

    return _run_gui(game_dir, options.config)


def _create_config(game_dir: Path, target: str) -> int:
    """``--create-config``: положить образец рядом с лаунчером."""
    path = Path(target) if target else find_config(game_dir)
    if not path.is_absolute():
        path = game_dir / path
    try:
        write_example_config(path)
    except ConfigError as error:
        _write_error(error)
        return EXIT_CONFIG_ERROR
    _write(f"Создан образец: {path}\nЗаполните его и запустите лаунчер.")
    return EXIT_OK


def _check_config(game_dir: Path, explicit: str | None) -> int:
    """``--check-config``: проверить файл и напечатать сводку (для CI)."""
    path = find_config(game_dir, explicit)
    try:
        config = read_config(path, game_dir=game_dir)
    except ConfigError as error:
        _write_error(error)
        return EXIT_CONFIG_ERROR

    _write(summarize(config))
    _write("\nПроверка пройдена: конфигурация корректна.")
    return EXIT_OK


def _run_gui(game_dir: Path, explicit: str | None) -> int:
    """Обычный запуск: лог, конфиг, окно, цикл событий."""
    log_path = setup_logging(game_dir)
    LOGGER.info("Запуск лаунчера %s", app_version())
    LOGGER.info("Каталог игры: %s", game_dir)
    LOGGER.debug("Файл лога: %s", log_path)

    from .ui import LauncherWindow, theme
    from .ui.config_dialogs import load_config_interactive
    from .ui.main_window import load_app_icon

    app = create_application([])

    config = load_config_interactive(game_dir, explicit)
    if config is None:
        return EXIT_CONFIG_ERROR

    theme.set_accent(config.accent)
    app.setStyleSheet(theme.stylesheet())
    app.setWindowIcon(load_app_icon(config))

    window = LauncherWindow(config)
    window.show()
    window.fade_in()
    window.start_update_check()
    return app.exec()


def create_application(argv: list[str] | None = None):
    """QApplication с именем, иконкой и базовой таблицей стилей."""
    from PySide6.QtWidgets import QApplication

    from .ui import theme
    from .ui.main_window import load_app_icon

    app = QApplication(list(argv or []))
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(app_version())
    app.setOrganizationName(ORGANISATION)
    app.setWindowIcon(load_app_icon())
    app.setStyleSheet(theme.stylesheet())
    return app


def _write(text: str) -> None:
    """Печать в консоль: у windowed-сборки потоков может не быть."""
    if sys.stdout is not None:
        print(text)


def _write_error(error: ConfigError) -> None:
    """Ошибка конфига — в stderr (и в stdout, если stderr недоступен)."""
    text = f"Ошибка в файле настройки:\n\n{error.summary()}"
    if sys.stderr is not None:
        print(text, file=sys.stderr)
    else:  # pragma: no cover - windowed-сборка без консоли
        _write(text)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
