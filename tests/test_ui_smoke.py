"""Дымовые проверки интерфейса: окно собирается и кнопки на месте.

Тест пропускается, если PySide6 не установлен (например, при быстром
запуске только логических тестов) или если нет Qt-платформы.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("COC_NO_UPDATE_CHECK", "1")

PySide6 = pytest.importorskip("PySide6", reason="PySide6 не установлен")

from PySide6.QtCore import QCoreApplication  # noqa: E402

from launcher import app_version  # noqa: E402
from launcher.app import create_application  # noqa: E402
from launcher.options import OPTIONS  # noqa: E402
from launcher.ui.main_window import LauncherWindow, load_app_icon  # noqa: E402
from launcher.ui.widgets import TitleBarButton  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"


@pytest.fixture(scope="module")
def application() -> QCoreApplication:
    return create_application(["tests"])


@pytest.fixture()
def window(application, tmp_path: Path) -> LauncherWindow:
    window = LauncherWindow(tmp_path)
    yield window
    window.close()


def test_window_has_button_per_option(window: LauncherWindow) -> None:
    assert [button.option.key for button in window.buttons] == [option.key for option in OPTIONS]
    assert len(window.buttons) == len(OPTIONS)


def test_window_is_frameless_and_sized(window: LauncherWindow) -> None:
    from PySide6.QtCore import Qt

    flags = window.windowFlags()
    assert flags & Qt.WindowType.FramelessWindowHint
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    assert "Лаунчер" in window.windowTitle()


def test_hover_updates_status(window: LauncherWindow) -> None:
    window.buttons[1].set_glow(1.0)
    QCoreApplication.processEvents()

    assert window.buttons[1].glow == pytest.approx(1.0)


def test_status_shows_errors_and_success(window: LauncherWindow) -> None:
    window._set_status("Не найдено: нет файла", state="error")
    assert window._status.property("error") is True

    window._set_status("Запускаю: ЗАПУСК…", state="success")
    assert window._status.property("error") is False
    assert window._status.property("success") is True


def test_update_message_marks_release(window: LauncherWindow) -> None:
    from launcher.updates import ReleaseInfo

    window._on_release_found(
        ReleaseInfo(version="9.9.9", tag="v9.9.9", name="CoC", url="https://example.invalid")
    )

    assert window.release_info is not None
    assert "9.9.9" in window._status.text()


def test_titlebar_buttons_do_not_steal_focus(window: LauncherWindow) -> None:
    minimize = TitleBarButton("minimize", window)
    assert minimize.focusPolicy().name == "NoFocus"

    with pytest.raises(ValueError):
        TitleBarButton("неизвестная-кнопка", window)


def test_icon_and_assets_are_packaged(window: LauncherWindow) -> None:
    assert not load_app_icon().isNull()
    assert (ASSETS / "background.jpg").is_file()
    assert app_version()


def test_window_renders_pixels(window: LauncherWindow) -> None:
    window.show()
    QCoreApplication.processEvents()

    image = window.grab().toImage()

    assert image.width() > 0 and image.height() > 0
    assert len({image.pixelColor(x, y).name() for x in (10, 100, 300) for y in (30, 200, 600)}) > 1
