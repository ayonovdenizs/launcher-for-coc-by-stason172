# -*- mode: python ; coding: utf-8 -*-
"""Спецификация PyInstaller: собирает Launcher-CoC.exe (onefile, без консоли).

Локально:
    pip install -r requirements-dev.txt
    python tools/make_version_info.py        # ресурс версии для .exe
    pyinstaller launcher.spec --noconfirm --clean

Версия берётся из ``launcher/__init__.py`` либо из переменной окружения
``COC_LAUNCHER_VERSION`` (её выставляет CI при сборке по тегу).
"""

import os
from pathlib import Path

ROOT = Path(SPECPATH)
VERSION_FILE = ROOT / "build" / "version_info.txt"

# Имя сборки. Форк может поменять его переменной окружения COC_EXE_NAME
# (workflow передаёт значение параметра exe-name).
EXE_NAME = os.environ.get("COC_EXE_NAME") or "Launcher-CoC"

# Отрезаем всё, что лаунчеру не нужно: интерфейс — обычные виджеты Qt,
# поэтому тяжёлые семейства (WebEngine, QML/Quick, 3D, мультимедиа) в .exe
# не попадают. QtOpenGL, QtSvg, QtXml оставлены намеренно: их подтягивают
# плагины платформы и форматов изображений.
EXCLUDED_QT = [
    "PySide6.Qt3DAnimation",
    "PySide6.Qt3DCore",
    "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput",
    "PySide6.Qt3DLogic",
    "PySide6.Qt3DRender",
    "PySide6.QtBluetooth",
    "PySide6.QtCharts",
    "PySide6.QtDataVisualization",
    "PySide6.QtDesigner",
    "PySide6.QtGraphs",
    "PySide6.QtHelp",
    "PySide6.QtLocation",
    "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets",
    "PySide6.QtNetworkAuth",
    "PySide6.QtNfc",
    "PySide6.QtPdf",
    "PySide6.QtPdfWidgets",
    "PySide6.QtPositioning",
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuick3D",
    "PySide6.QtQuickControls2",
    "PySide6.QtQuickWidgets",
    "PySide6.QtRemoteObjects",
    "PySide6.QtScxml",
    "PySide6.QtSensors",
    "PySide6.QtSerialPort",
    "PySide6.QtSpatialAudio",
    "PySide6.QtSql",
    "PySide6.QtStateMachine",
    "PySide6.QtTest",
    "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools",
    "PySide6.QtWebChannel",
    "PySide6.QtWebEngineCore",
    "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebSockets",
]

STDLIB_EXCLUDES = ["tkinter", "unittest", "pydoc", "doctest", "pdb", "test"]

a = Analysis(  # noqa: F821 - имена доступны внутри PyInstaller
    ["launcher_coc.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        ("assets/icon.ico", "assets"),
        ("assets/icon.png", "assets"),
        ("assets/background.jpg", "assets"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDED_QT + STDLIB_EXCLUDES,
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="assets/icon.ico",
    version=str(VERSION_FILE) if VERSION_FILE.exists() else None,
)
