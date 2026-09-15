"""Запуск игры: сборка командной строки, проверки и старт процесса."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

from .options import LaunchOption

LOGGER = logging.getLogger(__name__)

SCRIPT_SUFFIXES = {".cmd", ".bat"}

#: Минимальный набор файлов, без которого сборка точно не запустится.
REQUIRED_FILES: tuple[str, ...] = ("Stalker-CoC.exe", "gamedata")


class LaunchError(RuntimeError):
    """Понятная пользователю ошибка запуска."""


def build_command(target: Path, args: tuple[str, ...] = ()) -> list[str]:
    """Команда запуска; .cmd/.bat скрипты прогоняем через интерпретатор."""
    if target.suffix.lower() in SCRIPT_SUFFIXES:
        return ["cmd", "/c", str(target), *args]
    return [str(target), *args]


def missing_required_files(game_dir: Path) -> list[str]:
    """Каких обязательных файлов игры не хватает в ``game_dir``."""
    return [name for name in REQUIRED_FILES if not (game_dir / name).exists()]


def resolve_target(game_dir: Path, option: LaunchOption) -> Path:
    """Путь до файла, который запускает кнопка ``option``.

    :raises LaunchError: если файл не найден.
    """
    if option.target is None:
        raise LaunchError(f"Для режима «{option.title}» не задан файл запуска.")

    target = game_dir / option.target
    if not target.exists():
        raise LaunchError(
            f"Не найдено: {target}\n\nПроверьте, что лаунчер лежит в корневой папке игры."
        )
    return target


def launch(game_dir: Path, option: LaunchOption) -> Path:
    """Запустить режим ``option`` из каталога ``game_dir``.

    Возвращает путь до запущенного файла.
    """
    if sys.platform != "win32":
        raise LaunchError("Игра запускается только под Windows.")

    target = resolve_target(game_dir, option)
    command = build_command(target, option.args)
    LOGGER.info("Запуск: %s (cwd=%s)", " ".join(command), game_dir)
    try:
        subprocess.Popen(command, cwd=game_dir)
    except OSError as exc:
        LOGGER.exception("Не удалось запустить %s", target.name)
        raise LaunchError(f"Не удалось запустить {target.name}:\n{exc}") from exc
    return target
