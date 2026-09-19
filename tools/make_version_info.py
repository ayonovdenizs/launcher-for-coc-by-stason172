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

from launcher import APP_NAME, ORGANISATION, REPO_URL, VERSION
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
        [StringStruct('CompanyName', '{organisation}'),
         StringStruct('FileDescription', '{description}'),
         StringStruct('FileVersion', '{version}'),
         StringStruct('InternalName', '{exe_name}'),
         StringStruct('LegalCopyright', '{repo}'),
         StringStruct('OriginalFilename', '{exe_name}.exe'),
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


def description() -> str:
    """Описание файла для свойств .exe: название мода из config.launcher."""
    config_path = ROOT / "config.launcher"
    if config_path.exists():
        try:
            from launcher.config import read_config

            return f"Лаунчер: {read_config(config_path).name}"
        except Exception:
            pass
    return "Лаунчер мода"


def render(version: str, exe_name: str = "Launcher-CoC") -> str:
    """Содержимое ресурса версии для PyInstaller."""
    return TEMPLATE.format(
        version=version,
        version_tuple=version_tuple(version),
        app_name=APP_NAME,
        description=description(),
        exe_name=exe_name,
        organisation=ORGANISATION,
        repo=REPO_URL,
    )


def main(argv: list[str] | None = None) -> int:
    use_utf8_console()
    parser = argparse.ArgumentParser(description="Ресурс версии для .exe")
    parser.add_argument("--version", default=VERSION, help="версия (по умолчанию из launcher)")
    parser.add_argument(
        "--out", type=Path, default=ROOT / "build" / "version_info.txt", help="куда писать"
    )
    parser.add_argument(
        "--name",
        default="Launcher-CoC",
        help="имя .exe без расширения (для форков, меняющих имя сборки)",
    )
    args = parser.parse_args(argv)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(args.version, args.name), encoding="utf-8")
    print(f"Версия {args.version} → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
