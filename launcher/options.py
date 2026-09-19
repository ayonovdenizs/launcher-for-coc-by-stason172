"""Описание кнопки лаунчера и поддерживаемых действий.

Сами кнопки приходят из ``config.launcher`` (см. :mod:`launcher.config`),
здесь только структура данных и допустимые значения.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Запустить файл игры (exe, cmd, bat).
ACTION_RUN = "run"
#: Открыть ссылку в браузере.
ACTION_URL = "url"
#: Открыть папку или файл (сохранения, лог, конфиг движка).
ACTION_FOLDER = "folder"
#: Проверить свежий релиз через GitHub API.
ACTION_UPDATE = "update"

ACTION_TYPES = frozenset({ACTION_RUN, ACTION_URL, ACTION_FOLDER, ACTION_UPDATE})


@dataclass(frozen=True)
class LaunchOption:
    """Одна кнопка лаунчера."""

    key: str
    title: str
    description: str = ""
    action: str = ACTION_RUN
    #: файл для ``action="run"`` (относительно папки игры)
    target: str | None = None
    args: tuple[str, ...] = field(default_factory=tuple)
    #: ссылка для ``action="url"``
    url: str | None = None
    #: путь для ``action="folder"`` (``~`` и переменные окружения поддерживаются)
    path: str | None = None
    keep_open: bool = False
    accent: bool = False
    required_files: tuple[str, ...] = field(default_factory=tuple)
    hide_if_missing: bool = False

    @property
    def is_update(self) -> bool:
        """Кнопка проверки обновлений — файлы игры не запускаются."""
        return self.action == ACTION_UPDATE

    @property
    def is_run(self) -> bool:
        return self.action == ACTION_RUN
