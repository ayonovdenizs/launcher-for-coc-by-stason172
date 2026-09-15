"""Проверки сборки команды запуска и проверки файлов игры."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from launcher.options import GAME_EXE, MOD_MANAGER_EXE, OPTIONS_BY_KEY
from launcher.runner import (
    REQUIRED_FILES,
    LaunchError,
    build_command,
    launch,
    missing_required_files,
    resolve_target,
)


def test_build_command_for_exe(tmp_path: Path) -> None:
    target = tmp_path / GAME_EXE
    assert build_command(target, ("-skip_reg", "-dbg")) == [
        str(target),
        "-skip_reg",
        "-dbg",
    ]


def test_build_command_wraps_cmd_scripts(tmp_path: Path) -> None:
    target = tmp_path / "CoC_1.4_02coreCPU.cmd"
    assert build_command(target) == ["cmd", "/c", str(target)]


def test_missing_required_files_reports_all_gaps(tmp_path: Path) -> None:
    assert missing_required_files(tmp_path) == list(REQUIRED_FILES)

    for name in REQUIRED_FILES:
        path = tmp_path / name
        if path.suffix:  # .exe
            path.write_bytes(b"stub")
        else:  # папка gamedata
            path.mkdir(exist_ok=True)
    assert missing_required_files(tmp_path) == []


def test_resolve_target_raises_for_unknown_file(tmp_path: Path) -> None:
    option = OPTIONS_BY_KEY["mods"]
    with pytest.raises(LaunchError) as error:
        resolve_target(tmp_path, option)
    assert MOD_MANAGER_EXE in str(error.value)


def test_resolve_target_raises_for_update_option(tmp_path: Path) -> None:
    with pytest.raises(LaunchError):
        resolve_target(tmp_path, OPTIONS_BY_KEY["update"])


def test_launch_on_non_windows_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(LaunchError, match="Windows"):
        launch(Path("."), OPTIONS_BY_KEY["run"])


def test_launch_starts_process_in_game_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / GAME_EXE).write_bytes(b"stub")
    started: dict[str, object] = {}

    def fake_popen(command, cwd=None):
        started["command"] = command
        started["cwd"] = cwd
        return SimpleNamespace(pid=1)

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("launcher.runner.subprocess.Popen", fake_popen)

    launch(tmp_path, OPTIONS_BY_KEY["run"])

    assert started["command"] == [str(tmp_path / GAME_EXE), "-skip_reg"]
    assert started["cwd"] == tmp_path


def test_launch_wraps_os_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / GAME_EXE).write_bytes(b"stub")

    def broken_popen(command, cwd=None):
        raise OSError("недостаточно прав")

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("launcher.runner.subprocess.Popen", broken_popen)

    with pytest.raises(LaunchError, match="недостаточно прав"):
        launch(tmp_path, OPTIONS_BY_KEY["run"])
