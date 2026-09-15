"""Таблица режимов запуска, из которой строится меню лаунчера."""

from __future__ import annotations

from dataclasses import dataclass, field

from . import GAME_BUILD, GAME_EXE

FAST_LAUNCH_SCRIPT = "CoC_1.4_02coreCPU.cmd"
MOD_MANAGER_EXE = "Autorun.exe"
SETTINGS_EXE = "options.exe"

UPDATE_KEY = "update"


@dataclass(frozen=True)
class LaunchOption:
    """Описание одной кнопки лаунчера."""

    key: str
    title: str
    description: str
    target: str | None = None
    args: tuple[str, ...] = field(default_factory=tuple)
    keep_open: bool = False
    accent: bool = False

    @property
    def is_update(self) -> bool:
        """Кнопка проверки обновлений — не запускает файлы игры."""
        return self.key == UPDATE_KEY


OPTIONS: tuple[LaunchOption, ...] = (
    LaunchOption(
        key="run",
        title="ЗАПУСК",
        description=f"Обычный запуск {GAME_BUILD}",
        target=GAME_EXE,
        args=("-skip_reg",),
        accent=True,
    ),
    LaunchOption(
        key="debug",
        title="ЗАПУСК (ОТЛАДКА)",
        description="Запуск с отладкой и логом движка (-dbg)",
        target=GAME_EXE,
        args=("-skip_reg", "-dbg"),
    ),
    LaunchOption(
        key="fast",
        title="ФАСТ ЗАПУСК",
        description="Облегчённый режим для слабых ПК",
        target=FAST_LAUNCH_SCRIPT,
    ),
    LaunchOption(
        key="mods",
        title="МЕНЕДЖЕР МОДОВ",
        description="Менеджер модов от stason172",
        target=MOD_MANAGER_EXE,
        keep_open=True,
    ),
    LaunchOption(
        key="options",
        title="НАСТРОЙКИ",
        description="Графика и параметры игры",
        target=SETTINGS_EXE,
        keep_open=True,
    ),
    LaunchOption(
        key=UPDATE_KEY,
        title="ОБНОВЛЕНИЕ",
        description="Проверить свежую версию лаунчера",
    ),
)

OPTIONS_BY_KEY = {option.key: option for option in OPTIONS}
