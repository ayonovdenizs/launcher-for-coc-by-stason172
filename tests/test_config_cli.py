"""Флаги командной строки: --version, --check-config, --create-config.

Запускаются в подпроцессе — так же, как это делает автор мода и CI.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from launcher.config import CONFIG_FILENAME, example_config_text

ROOT = Path(__file__).resolve().parent.parent
ENTRY = ROOT / "launcher_coc.py"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Запустить лаунчер с аргументами (без Qt: только текстовые режимы)."""
    return subprocess.run(
        [sys.executable, str(ENTRY), *args],
        cwd=str(cwd or ROOT),
        capture_output=True,
        timeout=120,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONPATH": str(ROOT),
            "COC_NO_UPDATE_CHECK": "1",
        },
        check=False,
    )


def test_version_flag() -> None:
    result = run_cli("--version")
    assert result.returncode == 0
    assert "Launcher" in result.stdout.decode("utf-8")


def test_help_mentions_config_flags() -> None:
    result = run_cli("--help")
    text = result.stdout.decode("utf-8")

    assert result.returncode == 0
    assert "--check-config" in text
    assert "--create-config" in text
    assert CONFIG_FILENAME in text


def test_check_config_of_repository_file() -> None:
    """Наш config.launcher обязан проходить проверку — это ловит CI."""
    result = run_cli("--check-config")
    text = result.stdout.decode("utf-8")

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert "Проверка пройдена" in text
    assert "Кнопок:" in text


def test_check_config_of_other_mod_example() -> None:
    result = run_cli("--check-config", "--config", "examples/other-mod/config.launcher")
    text = result.stdout.decode("utf-8")

    assert result.returncode == 0, result.stderr.decode("utf-8")
    assert "Северный ветер" in text


def test_check_config_reports_error_with_location(tmp_path: Path) -> None:
    broken = tmp_path / CONFIG_FILENAME
    broken.write_text(
        '{\n  "options": [\n    {"title": "A", "action": "url"}\n  ]\n}', encoding="utf-8"
    )

    result = run_cli("--check-config", "--config", str(broken))
    error_text = result.stderr.decode("utf-8")

    assert result.returncode == 2
    assert str(broken) in error_text
    assert "url" in error_text


def test_check_config_reports_missing_file(tmp_path: Path) -> None:
    result = run_cli("--check-config", "--config", str(tmp_path / "нет.launcher"))
    error_text = result.stderr.decode("utf-8")

    assert result.returncode == 2
    assert "не найден" in error_text
    assert "--create-config" in error_text


def test_create_config_writes_example(tmp_path: Path) -> None:
    target = tmp_path / "мой-мод.launcher"
    result = run_cli("--create-config", str(target))

    assert result.returncode == 0
    assert target.exists()
    assert target.read_text(encoding="utf-8") == example_config_text()


def test_created_config_passes_check(tmp_path: Path) -> None:
    """Что создали — то и проверяется: образец обязан быть валидным."""
    target = tmp_path / CONFIG_FILENAME
    run_cli("--create-config", str(target))
    result = run_cli("--check-config", "--config", str(target))

    assert result.returncode == 0, result.stderr.decode("utf-8")


def test_create_config_refuses_to_overwrite(tmp_path: Path) -> None:
    target = tmp_path / CONFIG_FILENAME
    target.write_text("{}", encoding="utf-8")

    result = run_cli("--create-config", str(target))

    assert result.returncode == 2
    assert "существует" in result.stderr.decode("utf-8")


@pytest.mark.parametrize("relative", ["config.launcher", "examples/other-mod/config.launcher"])
def test_repository_configs_summarize_actions(relative: str) -> None:
    result = run_cli("--check-config", "--config", relative)
    text = result.stdout.decode("utf-8")

    assert result.returncode == 0
    assert "run →" in text
    assert "url →" in text
    assert "folder →" in text
