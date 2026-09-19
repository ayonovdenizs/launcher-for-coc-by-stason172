"""Превью интерфейса лаунчера в PNG (без запуска игры).

Полезно, когда нужно посмотреть на дизайн в headless-окружении или приложить
скриншот к pull request::

    python tools/preview_ui.py --out build/ui-preview.png --hover 2
    python tools/preview_ui.py --config examples/other-mod/config.launcher \
        --out build/ui-preview-other-mod.png

Файл рендерится в PNG поверх тёмного фона, имитирующего рабочий стол.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# headless: платформа offscreen подходит для рендера без дисплея
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication, QPoint
from PySide6.QtGui import QColor, QImage, QPainter

from launcher.config import ConfigError, load_config
from launcher.console import use_utf8_console
from launcher.ui import theme


def render(
    out_path: Path,
    config_path: Path,
    hover: int | None = None,
    game_dir: Path | None = None,
) -> Path:
    """Отрисовать окно лаунчера в ``out_path`` и вернуть путь."""
    from launcher.app import create_application
    from launcher.ui.main_window import LauncherWindow

    config_path = Path(config_path).resolve()
    game_dir = Path(game_dir).resolve() if game_dir else config_path.parent
    config = load_config(game_dir, config_path)

    application = create_application(["preview"])
    theme.set_accent(config.accent)
    application.setStyleSheet(theme.stylesheet())

    window = LauncherWindow(config)
    window.show()
    QCoreApplication.processEvents()

    if hover is not None and 0 <= hover < len(window.buttons):
        window.buttons[hover].set_glow(1.0)
        QCoreApplication.processEvents()

    image = QImage(window.size(), QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(QColor("#20242b"))  # фон «рабочего стола»
    painter = QPainter(image)
    window.render(painter, QPoint(0, 0))
    painter.end()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not image.save(str(out_path)):
        raise SystemExit(f"Не удалось сохранить {out_path}")
    del application, window
    return out_path


def main(argv: list[str] | None = None) -> int:
    use_utf8_console()
    parser = argparse.ArgumentParser(description="Скриншот окна лаунчера")
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config.launcher",
        help="файл настройки (по умолчанию config.launcher репозитория)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "build" / "ui-preview.png",
        help="куда сохранить PNG",
    )
    parser.add_argument(
        "--hover",
        type=int,
        default=None,
        help="номер кнопки (с 0), которую отрисовать в состоянии наведения",
    )
    parser.add_argument("--game-dir", type=Path, default=None, help="каталог игры для проверок")
    args = parser.parse_args(argv)

    try:
        out = render(args.out, args.config, args.hover, args.game_dir)
    except ConfigError as error:
        print(error.summary(), file=sys.stderr)
        return 2
    print(f"Готово: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
