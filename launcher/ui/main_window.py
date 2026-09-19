"""Главное окно лаунчера.

Всё содержимое окна — заголовки, кнопки, арт, цвет акцента — приходит из
``config.launcher`` (см. :mod:`launcher.config`), поэтому один и тот же
лаунчер обслуживает любой мод.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QEvent, QPropertyAnimation, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QDesktopServices,
    QFont,
    QIcon,
    QKeyEvent,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .. import REPO_URL, app_version
from ..config import LauncherConfig
from ..options import LaunchOption
from ..paths import find_asset
from ..runner import LaunchError, missing_required_files, option_is_available, perform
from ..updates import ReleaseInfo
from . import theme
from .update_check import UpdateChecker
from .widgets import OptionButton, TitleBarButton

LOGGER = logging.getLogger(__name__)

FADE_IN_MS = 260

#: ``COC_NO_UPDATE_CHECK=1`` отключает обращение к GitHub (офлайн-режим, тесты).
NO_UPDATE_CHECK_ENV = "COC_NO_UPDATE_CHECK"

BUNDLED_BACKGROUND = "background.jpg"
BUNDLED_ICON = ("icon.ico", "icon.png")


class LauncherWindow(QWidget):
    """Окно лаунчера со списком действий из конфига."""

    def __init__(self, config: LauncherConfig) -> None:
        super().__init__()
        self.config = config
        self.game_dir: Path = config.game_dir
        self.buttons: list[OptionButton] = []
        self.hidden_options: list[LaunchOption] = []
        self._backdrop: QPixmap | None = None
        self._drag_offset = None
        self.release_info: ReleaseInfo | None = None
        self._update_checker: UpdateChecker | None = None

        self.setWindowTitle(config.name)
        self.setWindowIcon(load_app_icon(config))
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(config.window.width)

        self._load_backdrop()
        self._build_ui()
        self._apply_size()
        self._center_on_screen()
        if config.warnings:
            LOGGER.warning("Конфигурация с замечаниями: %s", "; ".join(config.warnings))

    # ------------------------------------------------------------- оформление

    def _load_backdrop(self) -> None:
        """Фоновый арт: свой из конфига или встроенный."""
        path = find_asset(self.config.assets.background, self.game_dir, BUNDLED_BACKGROUND)
        if path is None:
            LOGGER.warning("Фоновый арт не найден — окно останется тёмным")
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            LOGGER.warning("Не удалось прочитать фоновый арт: %s", path)
            return
        LOGGER.info("Фон окна: %s", path)
        self._backdrop = pixmap

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        frame = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(frame, theme.WINDOW_RADIUS, theme.WINDOW_RADIUS)
        painter.setClipPath(path)

        painter.fillRect(self.rect(), theme.c("#0a0c10"))
        if self._backdrop is not None:
            painter.drawPixmap(0, 0, _cover_pixmap(self._backdrop, self.size()))

        painter.fillPath(path, QBrush(self._scrim_gradient()))
        painter.setClipping(False)
        painter.setPen(theme.c("#ffffff", 26))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

    def _scrim_gradient(self) -> QLinearGradient:
        """Затемнение поверх арта, чтобы текст и кнопки читались."""
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, theme.SCRIM_TOP)
        gradient.setColorAt(0.45, theme.SCRIM_MIDDLE)
        gradient.setColorAt(1.0, theme.SCRIM_BOTTOM)
        return gradient

    # ------------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._build_titlebar())
        layout.addWidget(self._build_hero())
        layout.addWidget(self._build_menu())

        self._status = QLabel(self.config.hint)
        self._status.setObjectName("status")
        self._status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._status.setWordWrap(True)
        self._status.setFixedHeight(theme.STATUS_HEIGHT)
        layout.addWidget(self._status)

        footer = QLabel(self.config.footer_text())
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        footer.setFixedHeight(theme.FOOTER_HEIGHT)
        layout.addWidget(footer)
        layout.addSpacing(theme.BOTTOM_MARGIN)

    def _build_titlebar(self) -> QWidget:
        bar = _TitleBar(self)

        app_icon = load_app_icon(self.config)
        if not app_icon.isNull():
            icon = QLabel()
            icon.setPixmap(app_icon.pixmap(16, 16))
            bar.layout().addWidget(icon)

        title = QLabel(f"{self.config.name} · v{app_version()}")
        title.setObjectName("windowTitle")
        _apply_letter_spacing(title, 1.0)
        bar.layout().addWidget(title)
        bar.layout().addStretch(1)

        minimize = TitleBarButton("minimize", bar)
        minimize.clicked.connect(self.showMinimized)
        bar.layout().addWidget(minimize)

        close = TitleBarButton("close", bar)
        close.clicked.connect(self.close)
        bar.layout().addWidget(close)
        return bar

    def _build_hero(self) -> QWidget:
        """Шапка окна: тексты из конфига, высота — тоже."""
        hero = QWidget()
        hero.setFixedHeight(self.config.window.hero_height)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(theme.CONTENT_MARGIN, 0, theme.CONTENT_MARGIN, 18)
        layout.setSpacing(3)
        layout.addStretch(1)

        for object_name, text, spacing in (
            ("heroKicker", self.config.hero.kicker, 4.0),
            ("heroTitle", self.config.hero.title, 1.6),
            ("heroSubtitle", self.config.hero.subtitle, 0.0),
        ):
            if not text:
                continue
            label = QLabel(text)
            label.setObjectName(object_name)
            if spacing:
                _apply_letter_spacing(label, spacing)
            layout.addWidget(label)
        return hero

    def _build_menu(self) -> QScrollArea:
        """Список кнопок из конфига; при нехватке места — прокрутка."""
        container = QWidget()
        menu = QVBoxLayout(container)
        menu.setContentsMargins(theme.CONTENT_MARGIN, 4, theme.CONTENT_MARGIN, 0)
        menu.setSpacing(theme.BUTTON_SPACING)

        for option in self.config.options:
            if option.hide_if_missing and not option_is_available(self.game_dir, option):
                LOGGER.info(
                    "Кнопка «%s» скрыта: нет %s",
                    option.title,
                    option.target or option.path,
                )
                self.hidden_options.append(option)
                continue
            button = OptionButton(option)
            button.clicked.connect(lambda _checked=False, opt=option: self._activate(opt))
            button.installEventFilter(self)
            self.buttons.append(button)
            menu.addWidget(button)

        if not self.buttons:
            empty = QLabel("Нет доступных кнопок — проверьте config.launcher")
            empty.setObjectName("status")
            empty.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            empty.setWordWrap(True)
            menu.addWidget(empty)

        menu.addStretch(1)

        area = QScrollArea()
        area.setWidget(container)
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        area.viewport().setAutoFillBackground(False)
        self._menu_area = area
        return area

    def _apply_size(self) -> None:
        """Высота окна под число кнопок, но не выше свободного места на экране."""
        hero_height = self.config.window.hero_height
        fixed = (
            theme.TITLEBAR_HEIGHT
            + hero_height
            + theme.STATUS_HEIGHT
            + theme.FOOTER_HEIGHT
            + theme.BOTTOM_MARGIN
        )
        needed = fixed + self._menu_height()
        available = self._available_height()
        height = max(theme.MIN_MENU_HEIGHT + fixed, min(needed, available))
        self._menu_area.setFixedHeight(max(theme.MIN_MENU_HEIGHT, height - fixed))
        self.setFixedSize(self.config.window.width, height)

    def _menu_height(self) -> int:
        count = max(1, len(self.buttons))
        return count * theme.BUTTON_HEIGHT + max(0, count - 1) * theme.BUTTON_SPACING + 8

    def _available_height(self) -> int:
        screen = QApplication.primaryScreen()
        if screen is None:
            return 900
        return max(420, screen.availableGeometry().height() - theme.SCREEN_MARGIN)

    # --------------------------------------------------------------- события

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Enter and isinstance(watched, OptionButton):
            self._set_status(watched.option.description or watched.option.title)
        return super().eventFilter(watched, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        if event.key() in {Qt.Key.Key_Down, Qt.Key.Key_Up}:
            self._focus_neighbour(down=event.key() == Qt.Key.Key_Down)
            return
        super().keyPressEvent(event)

    def _focus_neighbour(self, *, down: bool) -> None:
        if not self.buttons:
            return
        current = next((i for i, button in enumerate(self.buttons) if button.hasFocus()), -1)
        step = 1 if down else -1
        button = self.buttons[(current + step) % len(self.buttons)]
        button.setFocus()
        self._menu_area.ensureWidgetVisible(button)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._in_drag_zone(event):
            self._start_drag(event)
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)

    def _in_drag_zone(self, event) -> bool:
        return event.position().y() <= theme.TITLEBAR_HEIGHT

    def _start_drag(self, event) -> None:
        handle = self.windowHandle()
        if handle is not None and handle.startSystemMove():
            return
        self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geometry = self.frameGeometry()
        available = screen.availableGeometry()
        geometry.moveCenter(available.center())
        # не залезаем за верхний край: у высокого окна центр может уехать
        top = max(available.top() + 10, geometry.top())
        self.move(geometry.left(), top)

    # -------------------------------------------------------------- действия

    def _activate(self, option: LaunchOption) -> None:
        LOGGER.info("Нажата кнопка: %s (%s)", option.title, option.action)

        if option.is_update:
            self._open_release_page()
            return

        if option.is_run:
            missing = missing_required_files(self.game_dir, option.required_files)
            if missing:
                self._report_missing_files(option, missing)
                return

        try:
            perform(option, game_dir=self.game_dir)
        except LaunchError as exc:
            LOGGER.error("Действие «%s» не выполнено: %s", option.title, exc)
            self._set_status(str(exc).splitlines()[0], state="error")
            QMessageBox.critical(self, "Не получилось", str(exc))
            return

        self._set_status(f"{option.title}: готово", state="success")
        if not option.keep_open:
            self.close()

    def _report_missing_files(self, option: LaunchOption, missing: list[str]) -> None:
        files = "\n".join(f"  • {name}" for name in missing)
        LOGGER.error("Не хватает файлов для «%s»: %s", option.title, ", ".join(missing))
        self._set_status("Не хватает файлов сборки — смотрите список", state="error")
        QMessageBox.critical(
            self,
            "Не хватает файлов",
            f"Для «{option.title}» в папке игры нет:\n{files}\n\n"
            "Проверьте, что лаунчер лежит в корне сборки, а список "
            "required_files в config.launcher верен.",
        )

    def _open_release_page(self) -> None:
        """Кнопка обновления: открыть найденный релиз или страницу релизов."""
        if not self.config.update.enabled:
            QMessageBox.information(
                self,
                "Обновления выключены",
                "В config.launcher стоит update.enabled: false — "
                "проверка обновлений отключена автором сборки.",
            )
            return

        repo = self.config.update.repo
        if self.release_info is not None:
            url = self.release_info.url
        elif repo:
            url = f"https://github.com/{repo}/releases/latest"
        else:
            url = REPO_URL + "/releases/latest"

        LOGGER.info("Открываю страницу релизов: %s", url)
        if QDesktopServices.openUrl(url) or self._open_url_with_fallback(url):
            self._set_status("Открыл страницу релизов в браузере")
            return
        QMessageBox.information(self, "Обновление", f"Свежую версию можно скачать здесь:\n{url}")

    def _open_url_with_fallback(self, url) -> bool:
        from ..runner import open_url

        return open_url(url)

    # -------------------------------------------------------------- обновления

    def start_update_check(self) -> None:
        """Проверить обновления в фоне (можно отключить переменной окружения)."""
        if os.environ.get(NO_UPDATE_CHECK_ENV):
            LOGGER.info("Проверка обновлений отключена (%s)", NO_UPDATE_CHECK_ENV)
            return
        if not self.config.update.enabled or not self.config.update.repo:
            if any(option.is_update for option in self.config.options):
                LOGGER.info("Проверка обновлений не настроена в config.launcher")
            return

        checker = UpdateChecker(
            app_version(),
            self,
            repo=self.config.update.repo,
            timeout=self.config.update.timeout,
        )
        checker.release_found.connect(self._on_release_found)
        checker.finished.connect(checker.deleteLater)
        self._update_checker = checker
        checker.start()

    def _on_release_found(self, release: ReleaseInfo) -> None:
        self.release_info = release
        self._set_status(
            f"Доступна версия {release.version} — нажмите «ОБНОВЛЕНИЕ»", state="success"
        )

    def fade_in(self) -> None:
        """Плавное появление окна."""
        self.setWindowOpacity(0.0)
        animation = QPropertyAnimation(self, b"windowOpacity", self)
        animation.setDuration(FADE_IN_MS)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.finished.connect(lambda: self.setWindowOpacity(1.0))
        animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # -------------------------------------------------------------- статусбар

    def _set_status(self, text: str, *, state: str = "info") -> None:
        self._status.setText(text)
        self._status.setProperty("error", state == "error")
        self._status.setProperty("success", state == "success")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)


class _TitleBar(QWidget):
    """Полоса заголовка: за неё окно можно перетаскивать."""

    def __init__(self, window: LauncherWindow) -> None:
        super().__init__(window)
        self.setFixedHeight(theme.TITLEBAR_HEIGHT)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 8, 10, 0)
        layout.setSpacing(8)
        self._drag_offset = None

    def mousePressEvent(self, event) -> None:
        window = self.window()
        if event.button() == Qt.MouseButton.LeftButton:
            handle = window.windowHandle()
            if handle is not None and handle.startSystemMove():
                return
            self._drag_offset = event.globalPosition().toPoint() - window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_offset is not None:
            self.window().move(event.globalPosition().toPoint() - self._drag_offset)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)


def _apply_letter_spacing(label: QLabel, spacing: float) -> None:
    font = QFont(label.font())
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, spacing)
    label.setFont(font)


def _cover_pixmap(source: QPixmap, size) -> QPixmap:
    """Растянуть картинку на всё окно, сохранив пропорции (crop по краям)."""
    scaled = source.scaled(
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )
    x = max(0, (scaled.width() - size.width()) // 2)
    y = max(0, (scaled.height() - size.height()) // 2)
    return scaled.copy(x, y, size.width(), size.height())


def load_app_icon(config: LauncherConfig | None = None) -> QIcon:
    """Иконка приложения: своя из конфига, иначе встроенная (.ico, затем .png)."""
    if config is not None:
        path = find_asset(config.assets.icon, config.game_dir, *BUNDLED_ICON)
        if path is not None:
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon

    from ..paths import resource_path

    for name in BUNDLED_ICON:
        candidate = resource_path("assets", name)
        if candidate.exists():
            icon = QIcon(str(candidate))
            if not icon.isNull():
                return icon
    return QIcon()


def default_status() -> str:
    """Текст подсказки по умолчанию (когда конфиг её не задаёт)."""
    return "Выберите режим запуска"


__all__ = ["NO_UPDATE_CHECK_ENV", "LauncherWindow", "default_status", "load_app_icon"]
