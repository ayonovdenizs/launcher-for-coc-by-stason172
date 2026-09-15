"""Настройка вывода в консоль.

Русский текст в ``print`` и в логах падает на Windows-консоли с кодировкой
cp866/cp1252 (``UnicodeEncodeError``). Поэтому перед любым выводом
переключаем потоки на UTF-8, а у windowed-сборки PyInstaller потоков может
не быть вовсе — это тоже нужно пережить.
"""

from __future__ import annotations

import sys


def use_utf8_console() -> None:
    """Перевести ``stdout``/``stderr`` в UTF-8, если это возможно."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):  # поток уже закрыт или не поддерживается
            continue


def console_text(value: object) -> str:
    """Строка, безопасная для вывода в любую консоль.

    Для windowed-сборки ``sys.stdout is None`` — тогда текст не нужен.
    """
    return "" if sys.stdout is None else str(value)
