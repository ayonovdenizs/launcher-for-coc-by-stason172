"""Проверки упаковки: спецификация PyInstaller и ресурс версии.

Тесты не собирают .exe (это делает CI на Windows), но ловят опечатки в
списках исключений, забытые файлы в ``datas`` и нерабочий шаблон версии.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "launcher.spec"

sys.path.insert(0, str(ROOT / "tools"))

import make_version_info  # noqa: E402


def spec_tree() -> ast.Module:
    return ast.parse(SPEC.read_text(encoding="utf-8"))


def assigned_list(name: str) -> list[str]:
    """Вернуть литеральный список, присвоенный переменной ``name`` в spec."""
    for node in ast.walk(spec_tree()):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            return [element.value for element in node.value.elts]
    raise AssertionError(f"в launcher.spec нет списка {name}")


def spec_text() -> str:
    return SPEC.read_text(encoding="utf-8")


def test_entry_script_exists() -> None:
    assert '["launcher_coc.py"]' in spec_text()
    assert (ROOT / "launcher_coc.py").is_file()


def test_excluded_qt_modules_are_unique() -> None:
    excluded = assigned_list("EXCLUDED_QT")
    assert len(excluded) == len(set(excluded))
    assert all(name.startswith("PySide6.") for name in excluded)
    assert "PySide6.QtWebEngineCore" in excluded, "WebEngine весит больше всех"


def test_excluded_qt_modules_do_not_break_interface() -> None:
    excluded = set(assigned_list("EXCLUDED_QT"))
    for needed in ("PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"):
        assert needed not in excluded

    # QtOpenGL/QtSvg/QtXml нужны плагинам Qt — исключать их нельзя
    for plugin_dependency in ("PySide6.QtOpenGL", "PySide6.QtSvg", "PySide6.QtXml"):
        assert plugin_dependency not in excluded


def test_excluded_qt_modules_exist_in_pyside6() -> None:
    pytest.importorskip("PySide6", reason="PySide6 не установлен")
    unknown = [
        name for name in assigned_list("EXCLUDED_QT") if importlib.util.find_spec(name) is None
    ]
    assert unknown == [], f"таких модулей нет в PySide6: {unknown}"


def test_assets_are_declared_and_present() -> None:
    text = spec_text()
    for name in ("icon.ico", "icon.png", "background.jpg"):
        assert f"assets/{name}" in text, f"{name} не попадает в сборку"
        assert (ROOT / "assets" / name).is_file(), f"нет файла assets/{name}"


def test_exe_name_can_be_overridden_by_fork() -> None:
    """Имя сборки читается из окружения — форк назовёт её по-своему."""
    text = spec_text()
    assert "COC_EXE_NAME" in text
    assert "name=EXE_NAME" in text.replace(" ", "")


def test_config_launcher_is_not_bundled() -> None:
    """config.launcher лежит рядом с .exe и правится автором мода.

    Внутрь сборки его класть нельзя: тогда пользователь не смог бы
    отредактировать файл, а лаунчер требует его наличия.
    """
    text = spec_text()
    assert "config.launcher" not in text.split("datas=")[1].split("]")[0]


def test_icon_is_used_for_exe() -> None:
    assert 'icon="assets/icon.ico"' in spec_text().replace(" ", "")


def test_version_tuple_padding() -> None:
    assert make_version_info.version_tuple("1") == (1, 0, 0, 0)
    assert make_version_info.version_tuple("1.2") == (1, 2, 0, 0)
    assert make_version_info.version_tuple("1.2.3") == (1, 2, 3, 0)
    assert make_version_info.version_tuple("1.2.3.4.5") == (1, 2, 3, 4)
    assert make_version_info.version_tuple("1.2-beta") == (1, 2, 0, 0)


def test_version_resource_template_is_valid_python() -> None:
    """Пишем ресурс версии так, как это делает PyInstaller на Windows."""
    calls: list[str] = []

    def stub(name: str):
        def factory(*args, **kwargs):
            calls.append(name)
            return None

        return factory

    namespace = {
        name: stub(name)
        for name in (
            "VSVersionInfo",
            "FixedFileInfo",
            "StringFileInfo",
            "StringTable",
            "StringStruct",
            "VarFileInfo",
            "VarStruct",
        )
    }
    rendered = make_version_info.render("1.2.3")
    exec(compile(rendered, "version_info.txt", "exec"), namespace)

    assert "StringStruct" in calls
    assert "1.2.3" in rendered
