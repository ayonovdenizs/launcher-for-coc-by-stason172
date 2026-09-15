"""Кастомные виджеты: кнопки меню и кнопки заголовка окна.

Кнопки рисуются вручную (QPainter), поэтому у них нет «системного» вида:
плавная подсветка при наведении анимируется свойством ``glow``.
"""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QAbstractButton

from ..options import LaunchOption
from . import theme

HOVER_DURATION_MS = 150


class HoverButton(QAbstractButton):
    """Кнопка с анимированной подсветкой при наведении."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._glow = 0.0
        self._hover_anim = QPropertyAnimation(self, b"glow", self)
        self._hover_anim.setDuration(HOVER_DURATION_MS)
        self._hover_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    # ------------------------------------------------------------ анимация

    def get_glow(self) -> float:
        return self._glow

    def set_glow(self, value: float) -> None:
        self._glow = float(value)
        self.update()

    glow = Property(float, get_glow, set_glow)

    def _animate_to(self, value: float) -> None:
        self._hover_anim.stop()
        self._hover_anim.setStartValue(self._glow)
        self._hover_anim.setEndValue(value)
        self._hover_anim.start()

    # --------------------------------------------------------------- события

    def enterEvent(self, event) -> None:
        self._animate_to(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._animate_to(0.0)
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self._animate_to(1.0)
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._animate_to(0.0)
        super().focusOutEvent(event)


def _draw_focus_ring(
    painter: QPainter, rect: QRectF, radius: float, color: str = theme.ACCENT_LIGHT
) -> None:
    pen = QPen(theme.c(color, 190), 1.4)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(rect, radius, radius)


class OptionButton(HoverButton):
    """Кнопка режима запуска: название, подпись и стрелка справа."""

    def __init__(self, option: LaunchOption, parent=None) -> None:
        super().__init__(parent)
        self.option = option
        self.setText(option.title)
        self.setToolTip(option.description)
        self.setMinimumHeight(theme.BUTTON_HEIGHT)
        self.setAccessibleName(option.title)

        self._title_font = QFont()
        self._title_font.setPointSizeF(10.5)
        self._title_font.setWeight(QFont.Weight.DemiBold)
        self._title_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.1)

        self._hint_font = QFont()
        self._hint_font.setPointSizeF(8.6)

    def sizeHint(self) -> QSize:
        return QSize(theme.WINDOW_WIDTH - 2 * theme.CONTENT_MARGIN, theme.BUTTON_HEIGHT)

    # ------------------------------------------------------------- отрисовка

    def _background_colors(self) -> tuple[QColor, QColor, QColor]:
        """(заливка, заливка при наведении, рамка)."""
        if self.option.accent:
            return (
                theme.c(theme.ACCENT_DARK, 235),
                theme.c(theme.ACCENT, 245),
                theme.c(theme.ACCENT_LIGHT, 210),
            )
        return theme.BUTTON_BG, theme.BUTTON_BG_HOVER, theme.BUTTON_BORDER

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        glow = self._glow
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = theme.BUTTON_RADIUS
        base, hover, border = self._background_colors()
        if self.isDown():
            fill = theme.lerp_color(
                theme.lerp_color(base, hover, glow), theme.BUTTON_BG_PRESSED, 0.45
            )
        else:
            fill = theme.lerp_color(base, hover, glow)

        # мягкое свечение вокруг акцентной кнопки — «выбранный» режим
        if self.option.accent:
            halo = QRectF(rect).adjusted(-3.5, -3.5, 3.5, 3.5)
            glow_color = theme.c(theme.ACCENT_LIGHT, int(28 + 34 * glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow_color)
            painter.drawRoundedRect(halo, radius + 3, radius + 3)

        gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        if self.option.accent:
            gradient.setColorAt(0.0, theme.lerp_color(fill.lighter(112), fill, 0.4))
            gradient.setColorAt(1.0, fill.darker(112))
        else:
            gradient.setColorAt(0.0, fill.lighter(108))
            gradient.setColorAt(1.0, fill)
        painter.setBrush(QBrush(gradient))
        pen_color = theme.lerp_color(
            border,
            theme.BUTTON_BORDER_HOVER if not self.option.accent else border,
            glow,
        )
        painter.setPen(QPen(pen_color, 1.0))
        painter.drawRoundedRect(rect, radius, radius)

        # акцентная полоса слева у обычных кнопок — «растёт» при наведении
        if not self.option.accent:
            bar_height = 14 + 22 * glow
            bar_width = 2.4
            bar_x = rect.left() + 1.5
            bar_y = rect.center().y() - bar_height / 2
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.c(theme.ACCENT_LIGHT, int(90 + 130 * glow)))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_width, bar_height), 1.2, 1.2)

        self._draw_text(painter, rect, glow)

        if self.hasFocus():
            ring_color = "#fff4e4" if self.option.accent else theme.ACCENT_LIGHT
            _draw_focus_ring(painter, rect, radius, ring_color)

    def _draw_text(self, painter: QPainter, rect: QRectF, glow: float) -> None:
        accent = self.option.accent
        text_left = rect.left() + 20
        chevron_x = rect.right() - 24 + 3.5 * glow

        painter.setFont(self._title_font)
        painter.setPen(theme.c("#fff7ea") if accent else theme.c(theme.TEXT, 240 if glow else 225))
        title_rect = QRectF(text_left, rect.top() + 11, chevron_x - text_left - 12, 20)
        painter.drawText(
            title_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.option.title,
        )

        painter.setFont(self._hint_font)
        painter.setPen(
            theme.c("#f6e2c2", 200)
            if accent
            else theme.lerp_color(theme.c(theme.TEXT_DIM), theme.c(theme.TEXT_MUTED), glow)
        )
        hint_rect = QRectF(text_left, rect.top() + 31, chevron_x - text_left - 12, 18)
        painter.drawText(
            hint_rect,
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            self.option.description,
        )

        self._draw_chevron(painter, chevron_x, rect.center().y(), glow, accent)

    def _draw_chevron(
        self, painter: QPainter, x: float, y: float, glow: float, accent: bool
    ) -> None:
        color = (
            theme.c("#fff4e4", int(185 + 60 * glow))
            if accent
            else theme.lerp_color(
                theme.c(theme.TEXT_DIM, 170), theme.c(theme.ACCENT_LIGHT, 255), glow
            )
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        arrow = QPolygonF(
            [QPointF(x, y - 6), QPointF(x + 6, y), QPointF(x, y + 6), QPointF(x + 3, y)]
        )
        painter.drawPolygon(arrow)


class TitleBarButton(HoverButton):
    """Кнопка в полосе заголовка: свернуть или закрыть."""

    WIDTH = 34
    HEIGHT = 26

    def __init__(self, kind: str, parent=None) -> None:
        super().__init__(parent)
        if kind not in {"minimize", "close"}:
            raise ValueError(f"Неизвестный тип кнопки заголовка: {kind}")
        self.kind = kind
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setToolTip("Свернуть" if kind == "minimize" else "Закрыть")
        self.setAccessibleName(self.toolTip())

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        rect = QRectF(self.rect())

        if self._glow > 0.01:
            hover_color = (
                theme.TITLEBAR_CLOSE_HOVER if self.kind == "close" else theme.TITLEBAR_BUTTON_HOVER
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(theme.lerp_color(theme.c(hover_color, 0), hover_color, self._glow))
            painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), 6, 6)

        if self.kind == "close" and self._glow > 0.5:
            glyph_color = theme.c("#ffffff", 245)
        elif self._glow > 0.5:
            glyph_color = theme.c("#ffffff", 235)
        else:
            glyph_color = theme.c(theme.TEXT_MUTED, 235)

        pen = QPen(glyph_color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        center = rect.center()
        if self.kind == "minimize":
            painter.drawLine(
                QPointF(center.x() - 5, center.y() + 4),
                QPointF(center.x() + 5, center.y() + 4),
            )
        else:
            offset = 4.5
            painter.drawLine(
                QPointF(center.x() - offset, center.y() - offset),
                QPointF(center.x() + offset, center.y() + offset),
            )
            painter.drawLine(
                QPointF(center.x() + offset, center.y() - offset),
                QPointF(center.x() - offset, center.y() + offset),
            )

        if self.hasFocus():
            _draw_focus_ring(painter, rect.adjusted(0.5, 0.5, -0.5, -0.5), 6)
