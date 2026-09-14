"""Современный лаунчер сборки S.T.A.L.K.E.R. Call of Chernobyl от stason172.

Написан на PySide6 (Qt 6). Перенесите файл в корневую папку игры —
рядом со ``Stalker-CoC.exe`` — и запустите:

    python launcher_coc.py
"""

from __future__ import annotations

import logging
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

APP_VERSION = "1.0.0"
GAME_BUILD = "CoC 1.4.22"
GAME_EXE = "Stalker-CoC.exe"

LOGGER = logging.getLogger("launcher")


@dataclass(frozen=True)
class LaunchOption:
    """Описание одной кнопки лаунчера."""

    key: str
    label: str
    description: str
    target: Optional[str] = None
    args: tuple[str, ...] = ()
    keep_open: bool = False
    accent: bool = False


OPTIONS: tuple[LaunchOption, ...] = (
    LaunchOption(
        key="run",
        label="ЗАПУСК",
        description="Запуск игры в обычном режиме",
        target=GAME_EXE,
        args=("-skip_reg",),
        accent=True,
    ),
    LaunchOption(
        key="debug",
        label="ЗАПУСК (отладка)",
        description="Запуск с отладкой и логированием",
        target=GAME_EXE,
        args=("-skip_reg", "-dbg"),
    ),
    LaunchOption(
        key="fast",
        label="ФАСТ ЗАПУСК",
        description="Облегчённый режим для слабых ПК",
        target="CoC_1.4_02coreCPU.cmd",
    ),
    LaunchOption(
        key="mods",
        label="МЕНЕДЖЕР МОДОВ",
        description="Менеджер модов от stason172",
        target="Autorun.exe",
        keep_open=True,
    ),
    LaunchOption(
        key="options",
        label="НАСТРОЙКИ",
        description="Настройки графики и игры",
        target="options.exe",
        keep_open=True,
    ),
    LaunchOption(
        key="update",
        label="ОБНОВЛЕНИЕ",
        description="Проверка обновлений лаунчера",
    ),
)

STYLESHEET = """
QWidget {
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
    font-size: 13px;
    color: #e8e6e3;
}
LauncherWindow {
    background-color: #14161a;
}
QLabel#title {
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    color: #f2f0ec;
}
QLabel#subtitle {
    color: #9aa0aa;
    font-size: 12px;
}
QLabel#status {
    color: #9aa0aa;
    font-size: 12px;
    padding: 4px 8px;
}
QLabel#footer {
    color: #5d636e;
    font-size: 11px;
}
QPushButton {
    background-color: #23262e;
    border: 1px solid #30343f;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    font-size: 13px;
}
QPushButton:hover {
    background-color: #2b2f3a;
    border-color: #3d4250;
}
QPushButton:pressed {
    background-color: #1e2128;
}
QPushButton[accent="true"] {
    background-color: #b8741d;
    border-color: #d98e2b;
    color: #fff8ee;
    font-weight: 600;
}
QPushButton[accent="true"]:hover {
    background-color: #d98e2b;
}
QPushButton[accent="true"]:pressed {
    background-color: #a2660f;
}
"""


def resolve_game_dir() -> Path:
    """Каталог с игрой: рядом с файлом лаунчера (или с собранным .exe)."""
    if getattr(sys, "frozen", False):  # сборка PyInstaller
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def setup_logging(game_dir: Path) -> None:
    """Логи в консоль и, по возможности, в ``launcher.log`` рядом с игрой."""
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    try:
        handlers.append(
            logging.FileHandler(game_dir / "launcher.log", encoding="utf-8")
        )
    except OSError:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(message)s",
        handlers=handlers,
    )


def build_command(target: Path, args: tuple[str, ...]) -> list[str]:
    """Команда запуска; .cmd/.bat скрипты прогоняем через интерпретатор."""
    if target.suffix.lower() in {".cmd", ".bat"}:
        return ["cmd", "/c", str(target), *args]
    return [str(target), *args]


class OptionButton(QPushButton):
    """Кнопка меню, сообщающая о наведении курсора."""

    def __init__(self, option: LaunchOption, hovered: Callable[[], None]) -> None:
        super().__init__(option.label)
        self._hovered = hovered
        self.setToolTip(option.description)
        if option.accent:
            self.setProperty("accent", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)

    def enterEvent(self, event) -> None:  # noqa: N802 (имя из Qt)
        self._hovered()
        super().enterEvent(event)


class LauncherWindow(QWidget):
    """Главное окно лаунчера."""

    def __init__(self, game_dir: Path) -> None:
        super().__init__()
        self.game_dir = game_dir
        self.setWindowTitle(f"Лаунчер {GAME_BUILD}")
        self.setFixedSize(420, 620)
        self._build_ui()
        self._center_on_screen()

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 16)
        layout.setSpacing(8)

        title = QLabel("CALL OF CHERNOBYL")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(title)

        subtitle = QLabel(f"Лаунчер сборки от stason172 · {GAME_BUILD}")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(subtitle)
        layout.addSpacing(12)

        for option in OPTIONS:
            button = OptionButton(
                option, lambda opt=option: self._set_status(opt.description)
            )
            button.clicked.connect(
                lambda _checked=False, opt=option: self._activate(opt)
            )
            layout.addWidget(button)

        layout.addStretch(1)

        self._status = QLabel("Выберите режим запуска")
        self._status.setObjectName("status")
        self._status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        footer = QLabel(f"Лаунчер от ayden · v{APP_VERSION}")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(footer)

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = self.frameGeometry()
        geometry.moveCenter(screen.availableGeometry().center())
        self.move(geometry.topLeft())

    def _set_status(self, text: str) -> None:
        self._status.setText(text)

    # -------------------------------------------------------------- actions

    def _activate(self, option: LaunchOption) -> None:
        if option.key == "update":
            QMessageBox.information(
                self,
                "Обновление",
                "Обновления пока в разработке. Следите за новостями!",
            )
            return

        if sys.platform != "win32":
            QMessageBox.critical(
                self,
                "Неподдерживаемая платформа",
                "Игра запускается только под Windows.",
            )
            return

        if option.target is None:
            return

        target = self.game_dir / option.target
        if not target.exists():
            QMessageBox.critical(
                self,
                "Файл не найден",
                (
                    f"Не удалось найти файл:\n{target}\n\n"
                    "Убедитесь, что лаунчер лежит в корневой папке игры."
                ),
            )
            return

        command = build_command(target, option.args)
        LOGGER.info("Запуск: %s", " ".join(command))
        try:
            subprocess.Popen(command, cwd=self.game_dir)
        except OSError as exc:
            LOGGER.exception("Не удалось запустить %s", target.name)
            QMessageBox.critical(
                self,
                "Ошибка запуска",
                f"Не удалось запустить {target.name}:\n{exc}",
            )
            return

        self._set_status(f"Запускаю: {option.label}…")
        if not option.keep_open:
            self.close()


def main() -> int:
    game_dir = resolve_game_dir()
    setup_logging(game_dir)
    LOGGER.info("Каталог игры: %s", game_dir)

    app = QApplication(sys.argv)
    app.setApplicationName("Launcher CoC")
    app.setApplicationVersion(APP_VERSION)
    app.setStyleSheet(STYLESHEET)

    window = LauncherWindow(game_dir)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
