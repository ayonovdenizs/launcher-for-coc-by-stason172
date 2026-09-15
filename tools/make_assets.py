"""Пересборка графики лаунчера из исходников (нужен Pillow).

Исходники лежат рядом:
* ``assets/icon_source.png`` — квадратный арт для иконки;
* ``assets/background.png`` — арт для фона окна.

Скрипт создаёт рабочие файлы, которые использует лаунчер и PyInstaller:

    python tools/make_assets.py

Результат: ``assets/icon.png``, ``assets/icon.ico`` (16…256 px) и
сжатый ``assets/background.jpg``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from launcher.console import use_utf8_console

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

ICON_SIZES = (16, 24, 32, 48, 64, 128, 256)
ICON_SIZE = 512
BACKGROUND_WIDTH = 700
BACKGROUND_QUALITY = 88


def build_icon(source: Path, out_png: Path, out_ico: Path) -> None:
    """Обрезать исходник по краю и собрать многоразмерный .ico."""
    icon = Image.open(source).convert("RGB")
    width, height = icon.size
    inset = int(width * 0.055)
    icon = icon.crop((inset, int(height * 0.045), width - inset, height - int(height * 0.05)))
    icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    icon.save(out_png, optimize=True)
    icon.save(out_ico, format="ICO", sizes=[(size, size) for size in ICON_SIZES])
    print(f"иконка: {out_png.name}, {out_ico.name}")


def build_background(source: Path, out_jpg: Path) -> None:
    """Ужать фоновый арт: JPEG весит в разы меньше PNG."""
    background = Image.open(source).convert("RGB")
    height = round(BACKGROUND_WIDTH * background.height / background.width)
    background.resize((BACKGROUND_WIDTH, height), Image.LANCZOS).save(
        out_jpg, quality=BACKGROUND_QUALITY, optimize=True, progressive=True
    )
    print(f"фон: {out_jpg.name} ({out_jpg.stat().st_size // 1024} КБ)")


def main() -> int:
    use_utf8_console()
    icon_source = ASSETS / "icon_source.png"
    background_source = ASSETS / "background.png"

    if icon_source.exists():
        build_icon(icon_source, ASSETS / "icon.png", ASSETS / "icon.ico")
    else:
        print(f"нет исходника иконки: {icon_source}", file=sys.stderr)

    if background_source.exists():
        build_background(background_source, ASSETS / "background.jpg")
    else:
        print(f"нет исходника фона: {background_source}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
