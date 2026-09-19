"""Палитра, размеры и таблица стилей интерфейса.

Акцентный цвет приходит из ``config.launcher``: :func:`set_accent` пересчитывает
производные оттенки, а :func:`stylesheet` собирает QSS уже под текущую палитру.
"""

from __future__ import annotations

from PySide6.QtGui import QColor

# --------------------------------------------------------------------- размеры

DEFAULT_ACCENT = "#c9821f"
WINDOW_RADIUS = 14

TITLEBAR_HEIGHT = 42
CONTENT_MARGIN = 22
BUTTON_HEIGHT = 56
BUTTON_SPACING = 9
BUTTON_RADIUS = 10
STATUS_HEIGHT = 26
FOOTER_HEIGHT = 22
BOTTOM_MARGIN = 10
#: Отступ от краёв экрана, чтобы окно не упиралось в панель задач.
SCREEN_MARGIN = 70
MIN_MENU_HEIGHT = 120

FONT_STACK = '"Segoe UI", "Inter", "Roboto", "Noto Sans", "DejaVu Sans", sans-serif'


def c(hex_color: str, alpha: int = 255) -> QColor:
    """QColor из hex-строки с прозрачностью."""
    color = QColor(hex_color)
    color.setAlpha(alpha)
    return color


def lerp_color(start: QColor, end: QColor, t: float) -> QColor:
    """Линейная интерполяция двух цветов (``t`` от 0 до 1)."""
    t = max(0.0, min(1.0, t))
    return QColor(
        round(start.red() + (end.red() - start.red()) * t),
        round(start.green() + (end.green() - start.green()) * t),
        round(start.blue() + (end.blue() - start.blue()) * t),
        round(start.alpha() + (end.alpha() - start.alpha()) * t),
    )


# --------------------------------------------------------------------- палитра

TEXT = "#ecebe8"
TEXT_MUTED = "#9aa1ac"
TEXT_DIM = "#6b7280"

ACCENT = DEFAULT_ACCENT
ACCENT_LIGHT = "#e6a13c"
ACCENT_DARK = "#8f5a12"

SCRIM_TOP = c("#080a0d", 96)
SCRIM_MIDDLE = c("#080a0d", 158)
SCRIM_BOTTOM = c("#05070a", 214)

BUTTON_BG = c("#15181e", 196)
BUTTON_BG_HOVER = c("#2b313c", 225)
BUTTON_BG_PRESSED = c("#10131a", 230)
BUTTON_BORDER = c("#ffffff", 30)
BUTTON_BORDER_HOVER = c("#ffffff", 72)
BUTTON_BORDER_PRESSED = c("#ffffff", 20)

TITLEBAR_BUTTON_HOVER = c("#ffffff", 26)
TITLEBAR_CLOSE_HOVER = c("#c0392b", 210)


def set_accent(color: str) -> None:
    """Задать акцентный цвет (hex из ``config.launcher``).

    Светлый и тёмный оттенки выводятся автоматически, чтобы кнопки,
    подсветки и полосы смотрелись согласованно при любом цвете мода.
    """
    global ACCENT, ACCENT_LIGHT, ACCENT_DARK

    base = QColor(color)
    if not base.isValid():
        base = QColor(DEFAULT_ACCENT)
    ACCENT = base.name()
    ACCENT_LIGHT = base.lighter(128).name()
    ACCENT_DARK = base.darker(142).name()


def stylesheet() -> str:
    """Таблица стилей для текущей палитры."""
    return f"""
QWidget {{
    font-family: {FONT_STACK};
    color: {TEXT};
}}

QLabel {{
    background: transparent;
}}

QLabel#heroKicker {{
    color: {ACCENT_LIGHT};
    font-size: 10px;
    font-weight: 700;
}}

QLabel#heroTitle {{
    color: #f6f4f0;
    font-size: 25px;
    font-weight: 700;
}}

QLabel#heroSubtitle {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}

QLabel#windowTitle {{
    color: {TEXT_MUTED};
    font-size: 11px;
}}

QLabel#status {{
    color: {TEXT_MUTED};
    font-size: 11px;
    padding: 2px 6px;
}}

QLabel#status[error="true"] {{
    color: #e9857a;
}}

QLabel#status[success="true"] {{
    color: #a9d68a;
}}

QLabel#footer {{
    color: {TEXT_DIM};
    font-size: 10px;
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background: transparent;
    border: none;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: #ffffff33;
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT_LIGHT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
    height: 0px;
}}

QToolTip {{
    background-color: #10131a;
    color: {TEXT};
    border: 1px solid #2c3038;
    padding: 4px 6px;
}}
"""
