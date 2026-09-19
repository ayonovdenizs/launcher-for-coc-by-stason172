"""Действия лаунчера: запуск игры, открытие ссылок и папок.

Модуль не зависит от Qt — всё, что можно проверить юнит-тестами, живёт здесь,
а интерфейс только показывает результат.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

from .config import expand_path
from .options import ACTION_FOLDER, ACTION_RUN, ACTION_URL, LaunchOption

LOGGER = logging.getLogger(__name__)

SCRIPT_SUFFIXES = {".cmd", ".bat"}

#: Куда писать вывод системных команд открытия файлов.
_DEVNULL = subprocess.DEVNULL


class LaunchError(RuntimeError):
    """Понятная пользователю ошибка действия."""


def build_command(target: Path, args: tuple[str, ...] = ()) -> list[str]:
    """Команда запуска; .cmd/.bat скрипты прогоняем через интерпретатор."""
    if target.suffix.lower() in SCRIPT_SUFFIXES:
        return ["cmd", "/c", str(target), *args]
    return [str(target), *args]


def missing_required_files(game_dir: Path, required: tuple[str, ...] | list[str]) -> list[str]:
    """Каких обязательных файлов не хватает в ``game_dir``."""
    game_dir = Path(game_dir)
    return [name for name in required if not (game_dir / expand_path(name, game_dir)).exists()]


def resolve_target(game_dir: Path, option: LaunchOption) -> Path:
    """Путь до файла, который запускает кнопка.

    :raises LaunchError: если файл не найден.
    """
    if not option.target:
        raise LaunchError(f"Для кнопки «{option.title}» не задан файл запуска (target).")

    target = expand_path(option.target, Path(game_dir))
    if not target.exists():
        raise LaunchError(
            f"Не найдено: {target}\n\nПроверьте, что лаунчер лежит в корневой папке игры, "
            f'а поле "{option.target}" указано верно.'
        )
    return target


def option_is_available(game_dir: Path, option: LaunchOption) -> bool:
    """Существует ли то, на что указывает кнопка.

    Используется для ``hide_if_missing``: пустая кнопка в меню не нужна.
    """
    game_dir = Path(game_dir)
    if option.is_run:
        return bool(option.target) and expand_path(option.target, game_dir).exists()
    if option.action == ACTION_FOLDER:
        return bool(option.path) and expand_path(option.path, game_dir).exists()
    return True  # ссылки и проверка обновлений доступны всегда


def open_path(path: Path | str) -> bool:
    """Открыть папку или файл средствами системы.

    Возвращает ``True``, если команда запущена. Не бросает исключений —
    вызывающий код сам решает, что показать пользователю.
    """
    path = Path(path)
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # type: ignore[attr-defined]
            return True
        command = ["open", str(path)] if sys.platform == "darwin" else ["xdg-open", str(path)]
        subprocess.Popen(command, stdout=_DEVNULL, stderr=_DEVNULL)
        return True
    except OSError as exc:
        LOGGER.error("Не удалось открыть %s: %s", path, exc)
        return False


def open_url(url: str) -> bool:
    """Открыть ссылку в браузере по умолчанию."""
    try:
        return webbrowser.open(url)
    except webbrowser.Error as exc:  # pragma: no cover - зависит от системы
        LOGGER.error("Не удалось открыть ссылку %s: %s", url, exc)
        return False


def perform(option: LaunchOption, *, game_dir: Path) -> None:
    """Выполнить действие кнопки (кроме проверки обновлений).

    :raises LaunchError: если действие выполнить не удалось.
    """
    game_dir = Path(game_dir)

    if option.action == ACTION_RUN:
        target = resolve_target(game_dir, option)
        command = build_command(target, option.args)
        LOGGER.info("Запуск: %s (cwd=%s)", " ".join(command), game_dir)
        try:
            subprocess.Popen(command, cwd=game_dir)
        except OSError as exc:
            LOGGER.exception("Не удалось запустить %s", target.name)
            raise LaunchError(f"Не удалось запустить {target.name}:\n{exc}") from exc
        return

    if option.action == ACTION_URL:
        if not option.url:
            raise LaunchError(f"У кнопки «{option.title}» не задана ссылка (url).")
        LOGGER.info("Открываю ссылку: %s", option.url)
        if not open_url(option.url):
            raise LaunchError(
                f"Не удалось открыть ссылку:\n{option.url}\n\n"
                "Проверьте её вручную — браузер по умолчанию не ответил."
            )
        return

    if option.action == ACTION_FOLDER:
        if not option.path:
            raise LaunchError(f"У кнопки «{option.title}» не задан путь (path).")
        target_path = expand_path(option.path, game_dir)
        if not target_path.exists():
            raise LaunchError(
                f'Путь не найден:\n{target_path}\n\nПроверьте поле "path" в config.launcher.'
            )
        LOGGER.info("Открываю папку: %s", target_path)
        if not open_path(target_path):
            raise LaunchError(f"Не удалось открыть:\n{target_path}")
        return

    raise LaunchError(
        f'Кнопка «{option.title}» (действие "{option.action}") выполняется лаунчером напрямую.'
    )
