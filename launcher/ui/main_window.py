"""Главное окно лаунчера: безрамочное, с фоновым артом и анимациями."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QEvent,
    QPropertyAnimation,
    QRectF,
    Qt,
)
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
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from .. import GAME_BUILD, RELEASES_URL, app_version
from ..options import OPTIONS, LaunchOption
from ..paths import resource_path
from ..runner import LaunchError, launch
from ..updates import ReleaseInfo
from . import theme
from .update_check import UpdateChecker
from .widgets import OptionButton, TitleBarButton

LOGGER = logging.getLogger(__name__)

FADE_IN_MS = 260

#: ``COC_NO_UPDATE_CHECK=1`` отключает обращение к GitHub (офлайн-режим, тесты).
NO_UPDATE_CHECK_ENV = "COC_NO_UPDATE_CHECK"


class LauncherWindow(QWidget):
    """Окно лаунчера со списком режимов запуска."""

    def __init__(self, game_dir: Path) -> None:
        super().__init__()
        self.game_dir = game_dir
        self.buttons: list[OptionButton] = []
        self._backdrop: QPixmap | None = None
        self._scrim: QLinearGradient | None = None
        self._drag_offset = None
        self.release_info: ReleaseInfo | None = None
        self._update_checker: UpdateChecker | None = None

        self.setWindowTitle(f"{GAME_BUILD} — Лаунчер")
        self.setWindowIcon(load_app_icon())
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(theme.WINDOW_WIDTH, theme.WINDOW_HEIGHT)

        self._load_backdrop()
        self._build_ui()
        self._center_on_screen()

    # ------------------------------------------------------------- оформление

    def _load_backdrop(self) -> None:
        """Фоновый арт; если файла нет — окно просто остаётся тёмным."""
        path = resource_path("assets", "background.jpg")
        if not path.exists():
            LOGGER.warning("Фоновый арт не найден: %s", path)
            return
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            LOGGER.warning("Не удалось прочитать фоновый арт: %s", path)
            return
        self._backdrop = _cover_pixmap(pixmap, self.size())

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
            painter.drawPixmap(0, 0, self._backdrop)

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
        layout.addLayout(self._build_menu())

        self._status = QLabel("Выберите режим запуска")
        self._status.setObjectName("status")
        self._status.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._status.setWordWrap(True)
        self._status.setMinimumHeight(26)
        layout.addWidget(self._status)

        footer = QLabel(f"Лаунчер от ayden · версия {app_version()} · сборка {GAME_BUILD}")
        footer.setObjectName("footer")
        footer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(footer)
        layout.addSpacing(10)

    def _build_titlebar(self) -> QWidget:
        bar = _TitleBar(self)

        icon = QLabel()
        app_icon = load_app_icon()
        if not app_icon.isNull():
            icon.setPixmap(app_icon.pixmap(16, 16))
            bar.layout().addWidget(icon)

        title = QLabel(f"ЛАУНЧЕР CoC · v{app_version()}")
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
        hero = QWidget()
        hero.setFixedHeight(theme.HERO_HEIGHT)
        layout = QVBoxLayout(hero)
        layout.setContentsMargins(theme.CONTENT_MARGIN, 0, theme.CONTENT_MARGIN, 20)
        layout.setSpacing(3)
        layout.addStretch(1)

        kicker = QLabel("S.T.A.L.K.E.R.")
        kicker.setObjectName("heroKicker")
        _apply_letter_spacing(kicker, 4.0)
        layout.addWidget(kicker)

        title = QLabel("CALL OF CHERNOBYL")
        title.setObjectName("heroTitle")
        _apply_letter_spacing(title, 1.6)
        layout.addWidget(title)

        subtitle = QLabel(f"Сборка от stason172 · {GAME_BUILD}")
        subtitle.setObjectName("heroSubtitle")
        layout.addWidget(subtitle)
        return hero

    def _build_menu(self) -> QVBoxLayout:
        menu = QVBoxLayout()
        menu.setContentsMargins(theme.CONTENT_MARGIN, 4, theme.CONTENT_MARGIN, 0)
        menu.setSpacing(theme.BUTTON_SPACING)

        for option in OPTIONS:
            button = OptionButton(option)
            button.clicked.connect(lambda _checked=False, opt=option: self._activate(opt))
            button.installEventFilter(self)
            self.buttons.append(button)
            menu.addWidget(button)
            if option.accent:
                button.setFocus()
        return menu

    # --------------------------------------------------------------- события

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Enter and isinstance(watched, OptionButton):
            self._set_status(watched.option.description)
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
        self.buttons[(current + step) % len(self.buttons)].setFocus()

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
        geometry.moveCenter(screen.availableGeometry().center())
        self.move(geometry.topLeft())

    # -------------------------------------------------------------- действия

    def _activate(self, option: LaunchOption) -> None:
        if option.is_update:
            self._open_releases()
            return

        LOGGER.info("Выбран режим: %s", option.title)
        try:
            launch(self.game_dir, option)
        except LaunchError as exc:
            LOGGER.error("Не удалось запустить режим «%s»: %s", option.title, exc)
            self._set_status(str(exc).splitlines()[0], state="error")
            QMessageBox.critical(self, "Ошибка запуска", str(exc))
            return

        self._set_status(f"Запускаю: {option.title}…", state="success")
        if not option.keep_open:
            self.close()

    def _open_releases(self) -> None:
        url = self.release_info.url if self.release_info is not None else RELEASES_URL
        LOGGER.info("Открываю страницу релизов: %s", url)
        if QDesktopServices.openUrl(url):
            self._set_status("Открыл страницу релизов в браузере")
            return
        QMessageBox.information(
            self,
            "Обновление лаунчера",
            f"Свежую версию можно скачать здесь:\n{url}",
        )

    # -------------------------------------------------------------- статусбар

    def _set_status(self, text: str, *, state: str = "info") -> None:
        self._status.setText(text)
        self._status.setProperty("error", state == "error")
        self._status.setProperty("success", state == "success")
        self._status.style().unpolish(self._status)
        self._status.style().polish(self._status)

    def start_update_check(self) -> None:
        """Проверить обновления в фоне (можно отключить переменной окружения)."""
        if os.environ.get(NO_UPDATE_CHECK_ENV):
            LOGGER.info("Проверка обновлений отключена (%s)", NO_UPDATE_CHECK_ENV)
            return
        checker = UpdateChecker(app_version(), self)
        checker.release_found.connect(self._on_release_found)
        checker.finished.connect(checker.deleteLater)
        self._update_checker = checker
        checker.start()

    def _on_release_found(self, release: ReleaseInfo) -> None:
        self.release_info = release
        self._set_status(
            f"Доступна версия {release.version} — нажмите «ОБНОВЛЕНИЕ»",
            state="success",
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


class _TitleBar(QWidget):
    """Полоса заголовка: за неё окно можно перетаскивать."""

    def __init__(self, window: LauncherWindow) -> None:
        super().__init__(window)
        self.setFixedHeight(theme.TITLEBAR_HEIGHT)
        self.setCursor(Qt.CursorShape.ArrowCursor)
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


def load_app_icon() -> QIcon:
    """Иконка приложения: .ico для Windows, .png как запасной вариант."""
    for name in ("icon.ico", "icon.png"):
        path = resource_path("assets", name)
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return QIcon()
