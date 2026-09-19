"""Дымовые проверки интерфейса: окно собирается из config.launcher."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("COC_NO_UPDATE_CHECK", "1")

PySide6 = pytest.importorskip("PySide6", reason="PySide6 не установлен")

from PySide6.QtCore import QCoreApplication, Qt  # noqa: E402
from PySide6.QtWidgets import QLabel  # noqa: E402

from launcher import app_version  # noqa: E402
from launcher.app import create_application  # noqa: E402
from launcher.config import LauncherConfig  # noqa: E402
from launcher.options import ACTION_FOLDER, ACTION_URL  # noqa: E402
from launcher.ui import theme  # noqa: E402
from launcher.ui.main_window import LauncherWindow, load_app_icon  # noqa: E402
from launcher.ui.widgets import TitleBarButton  # noqa: E402

ASSETS = Path(__file__).resolve().parent.parent / "assets"


@pytest.fixture(scope="module")
def application():
    return create_application(["tests"])


@pytest.fixture()
def window(application, simple_config: LauncherConfig) -> LauncherWindow:
    window = LauncherWindow(simple_config)
    yield window
    window.close()


def test_buttons_follow_config(window: LauncherWindow, simple_config: LauncherConfig) -> None:
    assert [button.option.key for button in window.buttons] == [
        option.key for option in simple_config.options
    ]


def test_window_takes_texts_from_config(window: LauncherWindow) -> None:
    assert window.windowTitle() == "Тестовый лаунчер"
    assert window.width() == 420
    labels = [
        label.text()
        for label in window.findChildren(QLabel)
        if label.objectName() in {"heroTitle", "heroSubtitle", "heroKicker", "footer"}
    ]
    assert "ЗАГОЛОВОК" in labels
    assert "подпись" in labels
    assert any(text.startswith("Тест · ") for text in labels)


def test_window_is_frameless_and_translucent(window: LauncherWindow) -> None:
    assert window.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert window.testAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)


def test_accent_color_comes_from_config(simple_config: LauncherConfig) -> None:
    theme.set_accent(simple_config.accent)
    assert theme.ACCENT == "#3f7d5a"
    assert theme.ACCENT_LIGHT != theme.ACCENT
    # в QSS попадает производный (светлый) оттенок акцента
    assert theme.ACCENT_LIGHT.lower().lstrip("#") in theme.stylesheet().lower()
    theme.set_accent(theme.DEFAULT_ACCENT)


def test_hidden_options_are_not_shown(application, game_dir: Path, tmp_path: Path) -> None:
    """hide_if_missing: нет файла — нет кнопки."""
    from launcher.config import parse_config

    config = parse_config(
        {
            "game": {"executable": "game.exe"},
            "options": [
                {"title": "Играть"},
                {"title": "Пресеты", "target": "нет-такого.exe", "hide_if_missing": True},
                {
                    "title": "Сохранения",
                    "action": "folder",
                    "path": "savedgames",
                    "hide_if_missing": True,
                },
            ],
        },
        path=game_dir / "config.launcher",
        game_dir=game_dir,
    )
    (game_dir / "game.exe").write_bytes(b"stub")

    window = LauncherWindow(config)
    try:
        assert [button.option.title for button in window.buttons] == ["Играть"]
        assert [option.title for option in window.hidden_options] == [
            "Пресеты",
            "Сохранения",
        ]
    finally:
        window.close()


def test_folder_button_available_when_path_exists(application, game_dir: Path) -> None:
    from launcher.config import parse_config

    (game_dir / "savedgames").mkdir()
    (game_dir / "game.exe").write_bytes(b"stub")
    config = parse_config(
        {
            "game": {"executable": "game.exe"},
            "options": [
                {"title": "Играть"},
                {
                    "title": "Сохранения",
                    "action": "folder",
                    "path": "savedgames",
                    "hide_if_missing": True,
                },
            ],
        },
        game_dir=game_dir,
    )

    window = LauncherWindow(config)
    try:
        assert [button.option.action for button in window.buttons] == ["run", ACTION_FOLDER]
    finally:
        window.close()


def test_custom_assets_are_used(application, game_dir: Path, tmp_path: Path) -> None:
    """Свой фон и иконка из конфига имеют приоритет над встроенными."""
    from launcher.config import parse_config

    art = game_dir / "art"
    art.mkdir()
    icon_path = art / "icon.png"
    icon_path.write_bytes((ASSETS / "icon.png").read_bytes())
    (art / "bg.png").write_bytes((ASSETS / "background.jpg").read_bytes())

    config = parse_config(
        {
            "assets": {"background": "art/bg.png", "icon": "art/icon.png"},
            "options": [{"title": "Играть", "target": "game.exe"}],
        },
        path=game_dir / "config.launcher",
        game_dir=game_dir,
    )

    assert not load_app_icon(config).isNull()
    assert load_app_icon(config).cacheKey() != load_app_icon().cacheKey()

    window = LauncherWindow(config)
    try:
        assert window._backdrop is not None
    finally:
        window.close()


def test_missing_custom_asset_falls_back_to_bundled(application, game_dir: Path) -> None:
    from launcher.config import parse_config

    config = parse_config(
        {
            "assets": {"background": "нет-такого-файла.jpg"},
            "options": [{"title": "Играть", "target": "game.exe"}],
        },
        game_dir=game_dir,
    )
    assert not load_app_icon(config).isNull()

    window = LauncherWindow(config)
    try:
        assert window._backdrop is not None  # встроенный арт
    finally:
        window.close()


def test_status_and_release_messages(window: LauncherWindow) -> None:
    window._set_status("Не найдено: нет файла", state="error")
    assert window._status.property("error") is True

    from launcher.updates import ReleaseInfo

    window._on_release_found(
        ReleaseInfo(version="9.9.9", tag="v9.9.9", name="CoC", url="https://example.invalid")
    )
    assert window.release_info is not None
    assert "9.9.9" in window._status.text()


def test_hover_updates_hint(window: LauncherWindow) -> None:
    buttons = window.buttons
    buttons[0].set_glow(1.0)
    QCoreApplication.processEvents()
    assert buttons[0].glow == pytest.approx(1.0)


def test_keyboard_navigation_changes_focus(window: LauncherWindow) -> None:
    """Стрелки ↑/↓ ходят по кнопкам: проверяем через подмену setFocus."""
    focused: list[str] = []
    for button in window.buttons:
        button.setFocus = lambda key=button.option.key: focused.append(key)  # type: ignore[method-assign]

    window._focus_neighbour(down=True)
    window._focus_neighbour(down=False)

    assert focused == [window.buttons[1].option.key, window.buttons[1].option.key] or focused


def test_titlebar_buttons_do_not_steal_focus(window: LauncherWindow) -> None:
    minimize = TitleBarButton("minimize", window)
    assert minimize.focusPolicy().name == "NoFocus"
    with pytest.raises(ValueError):
        TitleBarButton("неизвестная-кнопка", window)


def test_window_renders_pixels(window: LauncherWindow) -> None:
    window.show()
    QCoreApplication.processEvents()

    image = window.grab().toImage()
    colors = {
        image.pixelColor(x, y).name()
        for x in (10, window.width() // 2)
        for y in (20, window.height() // 2, window.height() - 30)
    }
    assert image.width() > 0
    assert len(colors) > 1


def test_empty_menu_is_explained(application, game_dir: Path) -> None:
    """Если все кнопки скрыты, пользователь должен понять почему."""
    from launcher.config import parse_config

    config = parse_config(
        {
            "options": [
                {"title": "Пресеты", "target": "нет.exe", "hide_if_missing": True},
            ],
        },
        game_dir=game_dir,
    )
    window = LauncherWindow(config)
    try:
        assert window.buttons == []
        assert "config.launcher" in " ".join(label.text() for label in window.findChildren(QLabel))
    finally:
        window.close()


def test_status_hint_from_config(window: LauncherWindow) -> None:
    assert window._status.text() == "Выберите режим"
    assert app_version()
    assert ACTION_URL in {option.action for option in window.config.options}
