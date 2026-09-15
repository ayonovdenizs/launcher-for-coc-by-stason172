"""Проверки вывода в консоль.

Русский текст в ``print`` ломал сборку на windows-runner: консоль там
в кодировке cp1252, и ``UnicodeEncodeError`` валил шаг «Ресурс версии».
Тесты запускают CLI в подпроцессе именно с такой кодировкой.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from launcher.console import use_utf8_console

ROOT = Path(__file__).resolve().parent.parent
WINDOWS_CONSOLE_ENCODING = "cp1252"


class FakeStream:
    """Поток с reconfigure(), как у настоящего sys.stdout."""

    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict] = []
        self._fail = fail

    def reconfigure(self, **kwargs) -> None:
        if self._fail:
            raise ValueError("поток закрыт")
        self.calls.append(kwargs)


def run_cli(*args: str, encoding: str = WINDOWS_CONSOLE_ENCODING) -> subprocess.CompletedProcess:
    """Запустить CLI репозитория с заданной кодировкой консоли."""
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        capture_output=True,
        timeout=120,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PYTHONIOENCODING": encoding,
            "PYTHONPATH": str(ROOT),
            "COC_NO_UPDATE_CHECK": "1",
        },
        check=False,
    )


def test_use_utf8_console_reconfigures_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    out, err = FakeStream(), FakeStream()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)

    use_utf8_console()

    assert out.calls == [{"encoding": "utf-8", "errors": "replace"}]
    assert err.calls == [{"encoding": "utf-8", "errors": "replace"}]


def test_use_utf8_console_survives_missing_streams(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)  # windowed-сборка PyInstaller
    monkeypatch.setattr(sys, "stderr", None)

    use_utf8_console()


def test_use_utf8_console_survives_closed_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", FakeStream(fail=True))
    monkeypatch.setattr(sys, "stderr", FakeStream(fail=True))

    use_utf8_console()


def test_version_flag_on_narrow_console() -> None:
    result = run_cli("launcher_coc.py", "--version")

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert "Launcher CoC" in result.stdout.decode("utf-8", "replace")


def test_help_flag_on_narrow_console() -> None:
    result = run_cli("launcher_coc.py", "--help")

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert "--version" in result.stdout.decode("utf-8", "replace")


def test_version_info_tool_on_narrow_console(tmp_path: Path) -> None:
    """Именно этот шаг падал на windows-runner при сборке .exe."""
    out = tmp_path / "version_info.txt"
    result = run_cli("tools/make_version_info.py", "--version", "9.9.9", "--out", str(out))

    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert "9.9.9" in out.read_text(encoding="utf-8")
