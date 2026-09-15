"""Палитра, размеры и таблица стилей интерфейса."""

from __future__ import annotations

from PySide6.QtGui import QColor

# --------------------------------------------------------------------- размеры

WINDOW_WIDTH = 470
WINDOW_HEIGHT = 680
WINDOW_RADIUS = 14
TITLEBAR_HEIGHT = 42
HERO_HEIGHT = 170
CONTENT_MARGIN = 22
BUTTON_HEIGHT = 60
BUTTON_SPACING = 9
BUTTON_RADIUS = 10

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
ACCENT = "#c9821f"
ACCENT_LIGHT = "#e6a13c"
ACCENT_DARK = "#8f5a12"
DANGER = "#c0392b"

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

STYLESHEET = f"""
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

QToolTip {{
    background-color: #10131a;
    color: {TEXT};
    border: 1px solid #2c3038;
    padding: 4px 6px;
}}
"""
