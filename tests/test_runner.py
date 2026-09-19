"""Проверки действий лаунчера: запуск, ссылки, папки (без Qt и без окон)."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from launcher.config import parse_config
from launcher.options import ACTION_FOLDER, ACTION_RUN, ACTION_URL, LaunchOption
from launcher.runner import (
    LaunchError,
    build_command,
    missing_required_files,
    open_path,
    open_url,
    option_is_available,
    perform,
    resolve_target,
)


def option(**kwargs) -> LaunchOption:
    """Кнопка с разумными значениями по умолчанию."""
    data = {"key": "k", "title": "Кнопка", "action": ACTION_RUN, "target": "game.exe"}
    data.update(kwargs)
    return LaunchOption(**data)


# ------------------------------------------------------------ команда запуска


def test_build_command_for_exe(tmp_path: Path) -> None:
    target = tmp_path / "game.exe"
    assert build_command(target, ("-skip_reg", "-dbg")) == [
        str(target),
        "-skip_reg",
        "-dbg",
    ]


def test_build_command_wraps_cmd_scripts(tmp_path: Path) -> None:
    target = tmp_path / "fast.cmd"
    assert build_command(target) == ["cmd", "/c", str(target)]


def test_paths_from_config_are_relative_to_game_dir(tmp_path: Path) -> None:
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "xrEngine.exe").write_bytes(b"stub")
    target = resolve_target(tmp_path, option(target="bin/xrEngine.exe"))
    assert target == tmp_path / "bin" / "xrEngine.exe"


def test_missing_required_files_reports_all_gaps(tmp_path: Path) -> None:
    required = ("Stalker-CoC.exe", "gamedata", "fsgame.ltx")
    assert missing_required_files(tmp_path, required) == list(required)

    (tmp_path / "Stalker-CoC.exe").write_bytes(b"stub")
    (tmp_path / "gamedata").mkdir()
    assert missing_required_files(tmp_path, required) == ["fsgame.ltx"]


def test_missing_required_files_accepts_nested_path(tmp_path: Path) -> None:
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "xrEngine.exe").write_bytes(b"stub")
    assert missing_required_files(tmp_path, ("bin/xrEngine.exe",)) == []


# --------------------------------------------------------------- доступность


def test_option_is_available_for_existing_target(tmp_path: Path) -> None:
    (tmp_path / "game.exe").write_bytes(b"stub")
    assert option_is_available(tmp_path, option())
    assert not option_is_available(tmp_path, option(target="нет.exe"))


def test_option_is_available_for_folder(tmp_path: Path) -> None:
    (tmp_path / "savedgames").mkdir()
    folder = option(action=ACTION_FOLDER, target=None, path="savedgames")
    assert option_is_available(tmp_path, folder)
    assert not option_is_available(
        tmp_path, option(action=ACTION_FOLDER, target=None, path="нет-папки")
    )


def test_url_and_update_options_are_always_available(tmp_path: Path) -> None:
    assert option_is_available(tmp_path, option(action=ACTION_URL, target=None, url="https://a"))
    assert option_is_available(tmp_path, option(action="update", target=None))


# -------------------------------------------------------------------- запуск


def test_resolve_target_raises_for_unknown_file(tmp_path: Path) -> None:
    with pytest.raises(LaunchError) as error:
        resolve_target(tmp_path, option(target="нет.exe"))
    assert "нет.exe" in str(error.value)


def test_resolve_target_raises_without_target(tmp_path: Path) -> None:
    with pytest.raises(LaunchError, match="target"):
        resolve_target(tmp_path, option(target=None))


def test_perform_run_starts_process_in_game_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "game.exe").write_bytes(b"stub")
    started: dict[str, object] = {}

    def fake_popen(command, cwd=None):
        started["command"] = command
        started["cwd"] = cwd
        return SimpleNamespace(pid=1)

    monkeypatch.setattr("launcher.runner.subprocess.Popen", fake_popen)
    perform(option(args=("-skip_reg",)), game_dir=tmp_path)

    assert started["command"] == [str(tmp_path / "game.exe"), "-skip_reg"]
    assert started["cwd"] == tmp_path


def test_perform_run_wraps_os_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "game.exe").write_bytes(b"stub")

    def broken_popen(command, cwd=None):
        raise OSError("недостаточно прав")

    monkeypatch.setattr("launcher.runner.subprocess.Popen", broken_popen)
    with pytest.raises(LaunchError, match="недостаточно прав"):
        perform(option(), game_dir=tmp_path)


def test_perform_url_opens_browser(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    opened: list[str] = []
    monkeypatch.setattr("launcher.runner.open_url", lambda url: opened.append(url) or True)

    perform(option(action=ACTION_URL, target=None, url="https://vk.com/scoc174"), game_dir=tmp_path)
    assert opened == ["https://vk.com/scoc174"]


def test_perform_url_without_url_raises(tmp_path: Path) -> None:
    with pytest.raises(LaunchError, match="url"):
        perform(option(action=ACTION_URL, target=None), game_dir=tmp_path)


def test_perform_url_failure_is_reported(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("launcher.runner.open_url", lambda url: False)
    with pytest.raises(LaunchError, match="браузер"):
        perform(option(action=ACTION_URL, target=None, url="https://a"), game_dir=tmp_path)


def test_perform_folder_opens_existing_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "savedgames").mkdir()
    opened: list[Path] = []
    monkeypatch.setattr("launcher.runner.open_path", lambda path: opened.append(Path(path)) or True)

    perform(
        option(action=ACTION_FOLDER, target=None, path="savedgames"),
        game_dir=tmp_path,
    )
    assert opened == [tmp_path / "savedgames"]


def test_perform_folder_reports_missing_path(tmp_path: Path) -> None:
    with pytest.raises(LaunchError, match="не найден"):
        perform(option(action=ACTION_FOLDER, target=None, path="нет"), game_dir=tmp_path)


def test_perform_rejects_update_action(tmp_path: Path) -> None:
    """Проверку обновлений ведёт интерфейс, а не runner."""
    with pytest.raises(LaunchError, match="напрямую"):
        perform(option(action="update", target=None), game_dir=tmp_path)


def test_perform_expands_environment_in_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setenv("TEST_LOG_DIR", str(log_dir))

    opened: list[Path] = []
    monkeypatch.setattr("launcher.runner.open_path", lambda path: opened.append(Path(path)) or True)

    perform(option(action=ACTION_FOLDER, target=None, path="%TEST_LOG_DIR%"), game_dir=tmp_path)
    assert opened == [log_dir]


# ------------------------------------------------- системное открытие (моки)


def test_open_path_uses_explorer_on_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("launcher.runner.os.startfile", lambda p: calls.append(p), raising=False)

    assert open_path(tmp_path)
    assert calls == [str(tmp_path)]


def test_open_path_uses_xdg_open_on_linux(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(
        "launcher.runner.subprocess.Popen",
        lambda command, **kwargs: calls.append(command),
    )

    assert open_path(tmp_path)
    assert calls[0][0] == "xdg-open"


def test_open_path_reports_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args, **kwargs):
        raise OSError("нет проводника")

    monkeypatch.setattr("launcher.runner.subprocess.Popen", broken)
    assert open_path(tmp_path) is False


def test_open_url_uses_webbrowser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("launcher.runner.webbrowser.open", lambda url: True)
    assert open_url("https://example.com")


# ---------------------------------------------------------------- сквозной


def test_config_options_drive_runner(tmp_path: Path) -> None:
    """Кнопки из конфига должны «доезжать» до runner без ручной сборки."""
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "xrEngine.exe").write_bytes(b"stub")
    config = parse_config(
        {
            "game": {"executable": "bin/xrEngine.exe"},
            "options": [
                {"title": "Играть", "action": "run", "args": ["-nointro"]},
                {"title": "Сайт", "action": "url", "url": "https://example.com"},
            ],
        },
        game_dir=tmp_path,
    )

    play, site = config.options
    assert resolve_target(tmp_path, play) == tmp_path / "bin" / "xrEngine.exe"
    assert play.args == ("-nointro",)
    assert site.url == "https://example.com"
