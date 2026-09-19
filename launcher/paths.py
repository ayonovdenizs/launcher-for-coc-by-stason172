"""Пути: где лежит игра, где ресурсы лаунчера и где писать лог."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

LOGGER = logging.getLogger(__name__)

ASSETS_DIR = "assets"
LOG_FILENAME = "launcher.log"


def resolve_game_dir() -> Path:
    """Каталог с игрой: рядом с самим лаунчером.

    Для сборки PyInstaller — рядом с ``.exe`` (а не во временной папке
    распаковки), иначе лаунчер искал бы игру в ``_MEIPASS``.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_root() -> Path:
    """Корень встроенных ресурсов (иконка, фоновый арт).

    В onefile-сборке PyInstaller ресурсы распакованы в ``sys._MEIPASS``,
    в обычном запуске — это корень репозитория.
    """
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle)
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Путь до ресурса, например ``resource_path("assets", "icon.ico")``."""
    return resource_root().joinpath(*parts)


def find_asset(
    value: str | None,
    base_dir: Path,
    *bundled_names: str,
) -> Path | None:
    """Найти ресурс: сначала путь из конфига, потом встроенный файл.

    :param value: значение из ``config.launcher`` (путь относительно файла
        конфига; ``~`` и переменные окружения поддерживаются). ``None`` —
        сразу берём встроенный файл.
    :param bundled_names: имена файлов в ``assets/`` внутри пакета/сборки.
    """
    if value:
        from .config import expand_path  # локальный импорт: без цикла модулей

        candidate = expand_path(str(value), Path(base_dir))
        if not candidate.is_absolute():
            candidate = Path(base_dir) / candidate
        if candidate.exists():
            return candidate
        LOGGER.warning("Файл из config.launcher не найден: %s", candidate)

    for name in bundled_names:
        candidate = resource_path(ASSETS_DIR, name)
        if candidate.exists():
            return candidate
    return None


def setup_logging(game_dir: Path) -> Path | None:
    """Логи в консоль и, если возможно, в ``launcher.log`` рядом с игрой.

    Возвращает путь до файла лога (``None``, если писать туда не получилось).
    """
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    log_path = game_dir / LOG_FILENAME
    try:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    except OSError as exc:  # папка только для чтения, нет прав и т.п.
        log_path = None
        print(f"Не удалось открыть {LOG_FILENAME}: {exc}", file=sys.stderr)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=handlers,
        force=True,
    )
    return log_path
