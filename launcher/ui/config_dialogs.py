"""Диалоги запуска: что показать, если конфига нет или он сломан.

Режим строгий: без правильного ``config.launcher`` лаунчер не стартует.
Но вместо сухого «Error» автор мода получает путь до файла, причину с номером
строки, пример структуры и кнопки «Создать пример» / «Открыть файл».
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QWidget

from ..config import (
    CONFIG_FILENAME,
    ConfigError,
    LauncherConfig,
    example_config_text,
    find_config,
    read_config,
    write_example_config,
)
from ..runner import open_path

LOGGER = logging.getLogger(__name__)

CREATE_EXAMPLE = "Создать пример"
OPEN_FOLDER = "Открыть папку"
OPEN_FILE = "Открыть файл"
QUIT = "Выход"


def load_config_interactive(
    game_dir: Path,
    explicit: str | Path | None = None,
    parent: QWidget | None = None,
) -> LauncherConfig | None:
    """Загрузить конфиг, показывая диалоги при ошибках.

    Возвращает ``None``, если пользователь решил выйти: тогда лаунчер
    завершает работу, а причина уже написана в лог и показана в диалоге.
    """
    while True:
        path = find_config(game_dir, explicit)
        try:
            config = read_config(path, game_dir=game_dir)
        except ConfigError as error:
            LOGGER.error("config.launcher: %s", error.summary().replace("\n", " | "))
            if not _show_error(error, game_dir, parent):
                return None
            continue

        for warning in config.warnings:
            LOGGER.warning("config.launcher: %s", warning)
        return config


def _show_error(error: ConfigError, game_dir: Path, parent: QWidget | None) -> bool:
    """Показать ошибку конфига. ``True`` — попробовать загрузить файл снова."""
    missing_file = error.path is not None and not error.path.exists()

    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle("Проблема с config.launcher")
    box.setText(f"Не удалось прочитать настройки лаунчера.\n\n{error.location}")
    box.setInformativeText(error.message)
    details = []
    if error.snippet:
        details.append(error.snippet)
    if error.hint:
        details.append(f"Подсказка: {error.hint}")
    details.append("Ожидаемая структура файла:\n\n" + example_config_text())
    box.setDetailedText("\n\n".join(details))

    if missing_file:
        box.setInformativeText(
            f"{error.message}\n\nОжидаемый файл: {error.path}\n"
            "Лаунчер настраивается файлом config.launcher, который кладут рядом с ним."
        )
        create = box.addButton(CREATE_EXAMPLE, QMessageBox.ButtonRole.AcceptRole)
        folder = box.addButton(OPEN_FOLDER, QMessageBox.ButtonRole.ActionRole)
        box.addButton(QUIT, QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(create)
        box.exec()

        if box.clickedButton() is create:
            try:
                created = write_example_config(error.path or (game_dir / CONFIG_FILENAME))
            except ConfigError as write_error:
                QMessageBox.critical(parent, "Не получилось", write_error.summary())
                return False
            LOGGER.info("Создан образец конфигурации: %s", created)
            if not open_path(created):
                QMessageBox.information(
                    parent,
                    "Файл создан",
                    f"Заполните {created} и запустите лаунчер снова.",
                )
            return True
        if box.clickedButton() is folder:
            open_path(created_folder(error, game_dir))
        return False

    open_button = box.addButton(OPEN_FILE, QMessageBox.ButtonRole.ActionRole)
    box.addButton(QUIT, QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(open_button)
    box.exec()

    if box.clickedButton() is open_button and error.path is not None:
        open_path(error.path)
    return False


def created_folder(error: ConfigError, game_dir: Path) -> Path:
    """Папка, которую логично открыть автору мода при ошибке."""
    if error.path is not None:
        return error.path.parent
    return Path(game_dir)
