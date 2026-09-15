"""Генерирует ресурс версии для .exe (build/version_info.txt).

Локально и в CI вызывается перед PyInstaller:

    python tools/make_version_info.py [--version 1.2.3] [--out build/version_info.txt]

Версия по умолчанию берётся из ``launcher.VERSION``; CI передаёт версию тега.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from launcher import APP_NAME, GAME_BUILD, REPO_URL, VERSION
from launcher.console import use_utf8_console

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={version_tuple},
    prodvers={version_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [StringStruct('CompanyName', 'stason172'),
         StringStruct('FileDescription', 'Лаунчер {game_build}'),
         StringStruct('FileVersion', '{version}'),
         StringStruct('InternalName', 'Launcher-CoC'),
         StringStruct('LegalCopyright', '{repo}'),
         StringStruct('OriginalFilename', 'Launcher-CoC.exe'),
         StringStruct('ProductName', '{app_name}'),
         StringStruct('ProductVersion', '{version}')])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def version_tuple(version: str) -> tuple[int, int, int, int]:
    """``"1.2"`` → ``(1, 2, 0, 0)`` — формат для FixedFileInfo."""
    numbers: list[int] = []
    for part in version.split(".")[:4]:
        digits = "".join(ch for ch in part if ch.isdigit())
        numbers.append(int(digits) if digits else 0)
    while len(numbers) < 4:
        numbers.append(0)
    return tuple(numbers[:4])  # type: ignore[return-value]


def render(version: str) -> str:
    return TEMPLATE.format(
        version=version,
        version_tuple=version_tuple(version),
        app_name=APP_NAME,
        game_build=GAME_BUILD,
        repo=REPO_URL,
    )


def main(argv: list[str] | None = None) -> int:
    use_utf8_console()
    parser = argparse.ArgumentParser(description="Ресурс версии для .exe")
    parser.add_argument("--version", default=VERSION, help="версия (по умолчанию из launcher)")
    parser.add_argument(
        "--out", type=Path, default=ROOT / "build" / "version_info.txt", help="куда писать"
    )
    args = parser.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(args.version), encoding="utf-8")
    print(f"Версия {args.version} → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
