"""Чтение и разбор ``config.launcher`` — файла настройки лаунчера.

Формат — JSON с комментариями (``//``, ``/* */``) и висячими запятыми:
разбор идёт на стандартной библиотеке, без внешних зависимостей, а автор мода
может документировать поля прямо в файле.

Файл лежит рядом с лаунчером (в корне игры). Всё, что видит пользователь —
заголовки, кнопки, арт, цвет акцента, проверяемые файлы, репозиторий
обновлений, — задаётся здесь, код править не нужно.

Ошибки разбора и проверки поднимаются как :class:`ConfigError` с путём файла,
номером строки и подсказкой — их показывают в диалоге при запуске и в
``--check-config``.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shlex
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from . import REPO_URL, app_version
from .options import (
    ACTION_FOLDER,
    ACTION_RUN,
    ACTION_TYPES,
    ACTION_UPDATE,
    ACTION_URL,
    LaunchOption,
)

LOGGER = logging.getLogger(__name__)

CONFIG_FILENAME = "config.launcher"
BACKUP_SUFFIX = ".bak"

DEFAULT_WIDTH = 470
MIN_WIDTH, MAX_WIDTH = 340, 1100
DEFAULT_HERO_HEIGHT = 150
MIN_HERO_HEIGHT, MAX_HERO_HEIGHT = 0, 420
DEFAULT_UPDATE_TIMEOUT = 6.0
ACCENT_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")

#: Поля верхнего уровня, которые понимает лаунчер.
KNOWN_TOP_LEVEL = (
    "name",
    "hint",
    "footer",
    "accent",
    "window",
    "hero",
    "assets",
    "game",
    "update",
    "options",
)


class ConfigError(Exception):
    """Понятная автору мода ошибка в ``config.launcher``."""

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        line: int | None = None,
        column: int | None = None,
        hint: str | None = None,
        snippet: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.path = Path(path) if path is not None else None
        self.line = line
        self.column = column
        self.hint = hint
        self.snippet = snippet

    @property
    def location(self) -> str:
        """``файл:строка:столбец`` — для логов и диалогов."""
        parts = [str(self.path) if self.path else CONFIG_FILENAME]
        if self.line is not None:
            parts.append(str(self.line))
            if self.column is not None:
                parts.append(str(self.column))
        return ":".join(parts)

    def summary(self) -> str:
        """Многострочное описание для диалога/консоли."""
        lines = [f"{self.location}\n{self.message}"]
        if self.snippet:
            lines.append(self.snippet)
        if self.hint:
            lines.append(f"Подсказка: {self.hint}")
        return "\n\n".join(lines)

    def __str__(self) -> str:  # pragma: no cover - тривиально
        return self.summary()


# ------------------------------------------------------------------ настройки


@dataclass(frozen=True)
class HeroConfig:
    """Заголовок в верхней части окна."""

    kicker: str = ""
    title: str = ""
    subtitle: str = ""


@dataclass(frozen=True)
class WindowConfig:
    """Размеры окна."""

    width: int = DEFAULT_WIDTH
    hero_height: int = DEFAULT_HERO_HEIGHT


@dataclass(frozen=True)
class AssetsConfig:
    """Пути к графике; ``None`` — использовать встроенную."""

    background: str | None = None
    icon: str | None = None


@dataclass(frozen=True)
class GameConfig:
    """Что запускаем и какие файлы считаем обязательными."""

    executable: str | None = None
    required_files: tuple[str, ...] = ()


@dataclass(frozen=True)
class UpdateConfig:
    """Проверка обновлений через GitHub API."""

    enabled: bool = True
    repo: str | None = None
    timeout: float = DEFAULT_UPDATE_TIMEOUT


@dataclass(frozen=True)
class LauncherConfig:
    """Полная конфигурация лаунчера."""

    game_dir: Path
    path: Path | None = None
    name: str = "Лаунчер"
    hint: str = "Выберите режим запуска"
    footer: str = "Версия {version}"
    accent: str = "#c9821f"
    hero: HeroConfig = field(default_factory=HeroConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    assets: AssetsConfig = field(default_factory=AssetsConfig)
    game: GameConfig = field(default_factory=GameConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    options: tuple[LaunchOption, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_default_config(self) -> bool:
        """Конфиг без файла (например, значения по умолчанию для тестов)."""
        return self.path is None

    def option_by_key(self, key: str) -> LaunchOption | None:
        return next((option for option in self.options if option.key == key), None)

    def footer_text(self) -> str:
        """Подпись внизу окна с подставленной версией лаунчера."""
        try:
            return self.footer.format(version=app_version(), name=self.name)
        except (KeyError, IndexError, ValueError):
            return self.footer


# ------------------------------------------------------------- JSON с комментами


def strip_jsonc(text: str, *, path: Path | None = None) -> str:
    """Убрать комментарии из JSONC, сохранив нумерацию строк.

    Поддерживаются ``//`` и ``/* */``; строки в кавычках не трогаются,
    а переводы строк внутри блочных комментариев сохраняются, чтобы номера
    строк в сообщениях об ошибках совпадали с файлом.
    """
    out: list[str] = []
    index, length = 0, len(text)
    in_string = False

    while index < length:
        char = text[index]

        if in_string:
            out.append(char)
            if char == "\\" and index + 1 < length:
                out.append(text[index + 1])
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue

        if char == "/" and index + 1 < length and text[index + 1] == "/":
            while index < length and text[index] not in "\r\n":
                index += 1
            continue

        if char == "/" and index + 1 < length and text[index + 1] == "*":
            end = text.find("*/", index + 2)
            if end == -1:
                line = text.count("\n", 0, index) + 1
                raise ConfigError(
                    "Не закрыт блочный комментарий /* ... */",
                    path=path,
                    line=line,
                    hint="Закройте комментарий символами */.",
                )
            out.append("\n" * text.count("\n", index, end))
            index = end + 2
            continue

        out.append(char)
        index += 1

    return "".join(out)


def strip_trailing_commas(text: str) -> str:
    """Убрать висячие запятые перед ``}`` и ``]`` (вне строк)."""
    chars = list(text)
    index, length = 0, len(text)
    in_string = False

    while index < length:
        char = text[index]
        if in_string:
            if char == "\\":
                index += 2
                continue
            if char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            index += 1
            continue
        if char == ",":
            lookahead = index + 1
            while lookahead < length and text[lookahead] in " \t\r\n":
                lookahead += 1
            if lookahead < length and text[lookahead] in "}]":
                chars[index] = " "
        index += 1

    return "".join(chars)


def snippet_at(text: str, line: int, column: int, width: int = 78) -> str:
    """Фрагмент строки с указателем на проблемное место."""
    lines = text.splitlines()
    if not 1 <= line <= len(lines):
        return ""
    source = lines[line - 1]
    start = max(0, column - 1 - 30)
    fragment = source[start : start + width]
    caret = " " * max(0, column - 1 - start) + "^"
    return f"  {fragment}\n  {caret}"


def loads_jsonc(text: str, *, path: Path | None = None) -> Any:
    """Разобрать JSONC-текст, поднимая :class:`ConfigError` вместо JSONDecodeError."""
    prepared = strip_trailing_commas(strip_jsonc(text, path=path))
    try:
        return json.loads(prepared)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Синтаксическая ошибка JSON: {exc.msg}",
            path=path,
            line=exc.lineno,
            column=exc.colno,
            snippet=snippet_at(text, exc.lineno, exc.colno),
            hint="Проверьте кавычки, запятые и скобки рядом с указанным местом.",
        ) from exc


# ------------------------------------------------------------------- утилиты


#: ``%LOCALAPPDATA%`` — так переменные пишут в Windows-конфигах.
_VAR_PATTERN = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")


def expand_env(value: str) -> str:
    """Подставить переменные окружения: и ``%VAR%``, и ``$VAR``."""
    with_percent = _VAR_PATTERN.sub(
        lambda match: os.environ.get(match.group(1), match.group(0)), value
    )
    return os.path.expandvars(with_percent)


def expand_path(value: str, base: Path) -> Path:
    """Развернуть путь из конфига: ``~``, переменные окружения, база — папка игры."""
    expanded = os.path.expanduser(expand_env(str(value)))
    path = Path(expanded)
    return path if path.is_absolute() else base / path


#: Транслитерация для ключей кнопок: «ЗАПУСК» → ``zapusk``.
TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "c",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify(text: str, fallback: str) -> str:
    """``"ФАСТ ЗАПУСК"`` → ``"fast-zapusk"`` — читаемый ключ кнопки."""
    transliterated = "".join(TRANSLIT.get(char, char) for char in text.lower())
    slug = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
    return slug or fallback


def _typename(value: Any) -> str:
    if isinstance(value, bool):
        return "логическое значение"
    if isinstance(value, int):
        return "число"
    if isinstance(value, float):
        return "число"
    if isinstance(value, str):
        return "строка"
    if isinstance(value, list):
        return "список"
    if isinstance(value, dict):
        return "объект"
    return type(value).__name__


def _error(message: str, *, path: Path | None, hint: str | None = None) -> ConfigError:
    return ConfigError(message, path=path, hint=hint)


def _mapping(raw: Any, field_name: str, *, path: Path | None) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise _error(
            f'Поле "{field_name}" должно быть объектом {{...}}, а не {_typename(raw)}.',
            path=path,
        )
    return raw


def _string(value: Any, field_name: str, *, path: Path | None, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise _error(
            f'Поле "{field_name}" должно быть строкой, а не {_typename(value)}.',
            path=path,
        )
    return value


def _flag(value: Any, field_name: str, *, path: Path | None, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise _error(
            f'Поле "{field_name}" должно быть true или false, а не {_typename(value)}.',
            path=path,
        )
    return value


def _integer(
    value: Any,
    field_name: str,
    *,
    path: Path | None,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None:
        return default
    # bool — подкласс int, но как размер окна это явная ошибка
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(
            f'Поле "{field_name}" должно быть целым числом, а не {_typename(value)}.',
            path=path,
        )
    if not minimum <= value <= maximum:
        raise _error(
            f'Поле "{field_name}" должно быть от {minimum} до {maximum}, а указано {value}.',
            path=path,
        )
    return value


def _number(
    value: Any, field_name: str, *, path: Path | None, default: float, minimum: float
) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise _error(
            f'Поле "{field_name}" должно быть числом, а не {_typename(value)}.',
            path=path,
        )
    if value < minimum:
        raise _error(
            f'Поле "{field_name}" не может быть меньше {minimum}.',
            path=path,
        )
    return float(value)


def _string_list(value: Any, field_name: str, *, path: Path | None) -> tuple[str, ...]:
    """Список строк: ``["a", "b"]`` или одна строка ``"a b"``."""
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(part for part in shlex.split(value) if part)
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        raise _error(
            f'Поле "{field_name}" должно быть списком строк, а не {_typename(value)}.',
            path=path,
        )
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise _error(
                f'Поле "{field_name}" должно содержать только строки, а не {_typename(item)}.',
                path=path,
            )
        result.append(item)
    return tuple(result)


def _warn_unknown(
    raw: Mapping[str, Any],
    known: Sequence[str],
    *,
    where: str,
    warnings: list[str],
) -> None:
    unknown = [key for key in raw if key not in known]
    if unknown:
        warnings.append(
            f"{where}: неизвестные поля {', '.join(sorted(unknown))} — они проигнорированы"
        )


# ------------------------------------------------------------------- разбор


def _parse_hero(raw: Any, *, name: str, path: Path | None, warnings: list[str]) -> HeroConfig:
    if raw is None:
        return HeroConfig(title=name)
    mapping = _mapping(raw, "hero", path=path)
    _warn_unknown(mapping, ("kicker", "title", "subtitle"), where="hero", warnings=warnings)
    return HeroConfig(
        kicker=_string(mapping.get("kicker"), "hero.kicker", path=path),
        title=_string(mapping.get("title"), "hero.title", path=path, default=name),
        subtitle=_string(mapping.get("subtitle"), "hero.subtitle", path=path),
    )


def _parse_window(raw: Any, *, path: Path | None, warnings: list[str]) -> WindowConfig:
    if raw is None:
        return WindowConfig()
    mapping = _mapping(raw, "window", path=path)
    _warn_unknown(mapping, ("width", "hero_height"), where="window", warnings=warnings)
    return WindowConfig(
        width=_integer(
            mapping.get("width"),
            "window.width",
            path=path,
            default=DEFAULT_WIDTH,
            minimum=MIN_WIDTH,
            maximum=MAX_WIDTH,
        ),
        hero_height=_integer(
            mapping.get("hero_height"),
            "window.hero_height",
            path=path,
            default=DEFAULT_HERO_HEIGHT,
            minimum=MIN_HERO_HEIGHT,
            maximum=MAX_HERO_HEIGHT,
        ),
    )


def _parse_assets(raw: Any, *, path: Path | None, warnings: list[str]) -> AssetsConfig:
    if raw is None:
        return AssetsConfig()
    mapping = _mapping(raw, "assets", path=path)
    _warn_unknown(mapping, ("background", "icon"), where="assets", warnings=warnings)
    return AssetsConfig(
        background=_string(mapping.get("background"), "assets.background", path=path) or None,
        icon=_string(mapping.get("icon"), "assets.icon", path=path) or None,
    )


def _parse_game(raw: Any, *, path: Path | None, warnings: list[str]) -> GameConfig:
    if raw is None:
        return GameConfig()
    mapping = _mapping(raw, "game", path=path)
    _warn_unknown(mapping, ("executable", "required_files"), where="game", warnings=warnings)
    return GameConfig(
        executable=_string(mapping.get("executable"), "game.executable", path=path) or None,
        required_files=_string_list(
            mapping.get("required_files"), "game.required_files", path=path
        ),
    )


def _parse_update(raw: Any, *, path: Path | None, warnings: list[str]) -> UpdateConfig:
    if raw is None:
        return UpdateConfig()
    mapping = _mapping(raw, "update", path=path)
    _warn_unknown(mapping, ("enabled", "repo", "timeout"), where="update", warnings=warnings)
    repo = _string(mapping.get("repo"), "update.repo", path=path) or None
    if repo is not None and not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        raise _error(
            f'Поле "update.repo" должно выглядеть как "владелец/репозиторий", а указано "{repo}".',
            path=path,
            hint=f"Например: {REPO_URL.removeprefix('https://github.com/')}",
        )
    return UpdateConfig(
        enabled=_flag(mapping.get("enabled"), "update.enabled", path=path, default=True),
        repo=repo,
        timeout=_number(
            mapping.get("timeout"),
            "update.timeout",
            path=path,
            default=DEFAULT_UPDATE_TIMEOUT,
            minimum=1.0,
        ),
    )


def _parse_option(
    raw: Any,
    index: int,
    *,
    game: GameConfig,
    update: UpdateConfig,
    path: Path | None,
    warnings: list[str],
) -> LaunchOption:
    where = f"options[{index}]"
    mapping = _mapping(raw, where, path=path)
    title = _string(mapping.get("title"), f"{where}.title", path=path).strip()
    if not title:
        raise _error(
            f'У кнопки {where} не задан "title" — это надпись на кнопке.',
            path=path,
        )

    key = _string(mapping.get("key"), f"{where}.key", path=path).strip()
    if not key:
        key = slugify(title, f"option-{index + 1}")

    action = _string(mapping.get("action"), f"{where}.action", path=path, default=ACTION_RUN)
    if action not in ACTION_TYPES:
        raise _error(
            f'У кнопки «{title}» неизвестное действие "{action}".',
            path=path,
            hint=f"Доступны: {', '.join(sorted(ACTION_TYPES))}.",
        )

    _warn_unknown(
        mapping,
        (
            "key",
            "title",
            "description",
            "action",
            "target",
            "args",
            "url",
            "path",
            "keep_open",
            "accent",
            "required_files",
            "hide_if_missing",
        ),
        where=f"options[{index}] («{title}»)",
        warnings=warnings,
    )

    target = _string(mapping.get("target"), f"{where}.target", path=path) or None
    url = _string(mapping.get("url"), f"{where}.url", path=path) or None
    folder = _string(mapping.get("path"), f"{where}.path", path=path) or None
    args = _string_list(mapping.get("args"), f"{where}.args", path=path)

    if action == ACTION_RUN:
        if target is None:
            target = game.executable
        if target is None:
            raise _error(
                f'У кнопки «{title}» не задано, что запускать: поле "target".',
                path=path,
                hint='Либо задайте "game.executable" — тогда "target" можно не писать.',
            )
    elif action == ACTION_URL:
        if not url:
            raise _error(
                f'У кнопки «{title}» действие "url", но не заполнено поле "url".',
                path=path,
                hint='Пример: "url": "https://vk.com/scoc174"',
            )
        if not url.startswith(("http://", "https://")):
            raise _error(
                f'Поле "url" у кнопки «{title}» должно начинаться с http:// или https://.',
                path=path,
            )
    elif action == ACTION_FOLDER:
        if not folder:
            raise _error(
                f'У кнопки «{title}» действие "folder", но не заполнено поле "path".',
                path=path,
                hint='Пример: "path": "savedgames" — папка внутри игры.',
            )
    elif action == ACTION_UPDATE and not update.repo:
        raise _error(
            f"Кнопка «{title}» проверяет обновления, но не указан репозиторий.",
            path=path,
            hint='Добавьте "update": {"repo": "владелец/репозиторий"} — '
            "оттуда лаунчер возьмёт свежий релиз.",
        )

    required = _string_list(mapping.get("required_files"), f"{where}.required_files", path=path)
    if not required and action == ACTION_RUN:
        required = game.required_files

    default_keep_open = action != ACTION_RUN
    return LaunchOption(
        key=key,
        title=title,
        description=_string(mapping.get("description"), f"{where}.description", path=path),
        action=action,
        target=target,
        args=args,
        url=url,
        path=folder,
        keep_open=_flag(
            mapping.get("keep_open"), f"{where}.keep_open", path=path, default=default_keep_open
        ),
        accent=_flag(mapping.get("accent"), f"{where}.accent", path=path, default=False),
        required_files=required,
        hide_if_missing=_flag(
            mapping.get("hide_if_missing"),
            f"{where}.hide_if_missing",
            path=path,
            default=False,
        ),
    )


def _parse_options(
    raw: Any,
    *,
    game: GameConfig,
    update: UpdateConfig,
    path: Path | None,
    warnings: list[str],
) -> tuple[LaunchOption, ...]:
    if raw is None:
        raise _error(
            'В конфиге нет списка "options" — лаунчеру нечего показывать.',
            path=path,
            hint=f"Скопируйте образец: --create-config, либо примеры в {CONFIG_FILENAME}.",
        )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        raise _error(
            f'Поле "options" должно быть списком кнопок [...], а не {_typename(raw)}.',
            path=path,
        )
    if not raw:
        raise _error(
            'Список "options" пуст — нужна хотя бы одна кнопка.',
            path=path,
        )

    options: list[LaunchOption] = []
    seen: dict[str, str] = {}
    for index, item in enumerate(raw):
        option = _parse_option(item, index, game=game, update=update, path=path, warnings=warnings)
        if option.key in seen:
            raise _error(
                f'Ключ кнопки "{option.key}" повторяется '
                f"(«{seen[option.key]}» и «{option.title}»).",
                path=path,
                hint='"key" должен быть уникальным — задайте его вручную.',
            )
        seen[option.key] = option.title
        options.append(option)

    accents = [option.title for option in options if option.accent]
    if len(accents) > 1:
        warnings.append(
            "выделено акцентом несколько кнопок ("
            + ", ".join(f"«{title}»" for title in accents)
            + "); обычно accent: true ставится одной кнопке запуска"
        )
    return tuple(options)


def parse_config(
    payload: Any, *, path: Path | None = None, game_dir: Path | None = None
) -> LauncherConfig:
    """Проверить разобранный JSON и собрать :class:`LauncherConfig`."""
    warnings: list[str] = []
    mapping = _mapping(payload, "config", path=path)
    _warn_unknown(mapping, KNOWN_TOP_LEVEL, where="config", warnings=warnings)

    name = _string(mapping.get("name"), "name", path=path, default="Лаунчер").strip()
    if not name:
        name = "Лаунчер"

    accent = _string(mapping.get("accent"), "accent", path=path, default="#c9821f").strip()
    if not ACCENT_PATTERN.fullmatch(accent):
        raise _error(
            f'Поле "accent" должно быть цветом вида "#c9821f", а указано "{accent}".',
            path=path,
            hint="Подойдёт любой hex-цвет из трёх или шести цифр.",
        )

    update = _parse_update(mapping.get("update"), path=path, warnings=warnings)
    game = _parse_game(mapping.get("game"), path=path, warnings=warnings)

    if not update.enabled and any(
        isinstance(item, Mapping) and item.get("action") == ACTION_UPDATE
        for item in mapping.get("options") or []
    ):
        warnings.append(
            "проверка обновлений выключена (update.enabled: false), "
            'но кнопка с действием "update" осталась'
        )

    return LauncherConfig(
        game_dir=Path(game_dir) if game_dir is not None else Path.cwd(),
        path=Path(path) if path is not None else None,
        name=name,
        hint=_string(mapping.get("hint"), "hint", path=path, default="Выберите режим запуска"),
        footer=_string(mapping.get("footer"), "footer", path=path, default="Версия {version}"),
        accent=accent,
        hero=_parse_hero(mapping.get("hero"), name=name, path=path, warnings=warnings),
        window=_parse_window(mapping.get("window"), path=path, warnings=warnings),
        assets=_parse_assets(mapping.get("assets"), path=path, warnings=warnings),
        game=game,
        update=update,
        options=_parse_options(
            mapping.get("options"), game=game, update=update, path=path, warnings=warnings
        ),
        warnings=tuple(warnings),
    )


# -------------------------------------------------------------- файл на диске


def find_config(game_dir: Path, explicit: Path | str | None = None) -> Path:
    """Путь к конфигу: явно указанный или ``config.launcher`` рядом с лаунчером.

    Относительный путь из ``--config`` считается от текущего каталога
    (обычное поведение командной строки), а не от папки игры.
    """
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = Path.cwd() / path
        return path
    return Path(game_dir) / CONFIG_FILENAME


def read_config(path: Path, *, game_dir: Path | None = None) -> LauncherConfig:
    """Прочитать и проверить ``config.launcher``.

    :raises ConfigError: файла нет, он не читается или в нём ошибка.
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(
            f"Файл настройки не найден: {path}",
            path=path,
            hint=(
                "Лаунчер настраивается файлом config.launcher — положите его рядом "
                "с лаунчером (в корне игры). Готовый образец: --create-config."
            ),
        )
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise ConfigError(
            f"Не удалось прочитать файл: {exc}",
            path=path,
            hint="Файл должен быть в кодировке UTF-8 и доступен на чтение.",
        ) from exc

    payload = loads_jsonc(text, path=path)
    return parse_config(payload, path=path, game_dir=game_dir or path.parent)


def load_config(game_dir: Path, explicit: Path | str | None = None) -> LauncherConfig:
    """Найти и прочитать конфиг рядом с лаунчером (или по явному пути)."""
    path = find_config(game_dir, explicit)
    config = read_config(path, game_dir=game_dir)
    LOGGER.info("Конфигурация: %s (%d кнопок)", path, len(config.options))
    for warning in config.warnings:
        LOGGER.warning("config.launcher: %s", warning)
    return config


def default_config(option: LaunchOption, *, game_dir: Path | None = None) -> LauncherConfig:
    """Минимальная конфигурация с одной кнопкой — удобно в тестах."""
    return LauncherConfig(
        game_dir=Path(game_dir) if game_dir is not None else Path.cwd(),
        name="Лаунчер",
        options=(option,),
    )


def with_warnings(config: LauncherConfig, warnings: Sequence[str]) -> LauncherConfig:
    """Копия конфига с дополнительными предупреждениями (используется тестами)."""
    return replace(config, warnings=tuple(config.warnings) + tuple(warnings))


# ------------------------------------------------------------------- образец

EXAMPLE_CONFIG = """// config.launcher — настройка лаунчера мода.
// Формат: JSON с комментариями (// и /* */) и висячими запятыми.
// Положите этот файл рядом с лаунчером (в корневой папке игры).
//
// Проверить файл без запуска игры:  Launcher.exe --check-config
// Создать такой образец заново:     Launcher.exe --create-config

{
  // Название в заголовке окна
  "name": "Лаунчер мода",

  // Подсказка, которая видна внизу до первого наведения на кнопку
  "hint": "Выберите режим запуска",

  // Подпись в самом низу. {version} — версия лаунчера
  "footer": "Лаунчер мода · версия {version}",

  // Цвет акцентной кнопки (и подсветок)
  "accent": "#c9821f",

  "window": {
    "width": 470,        // ширина окна, 340…1100
    "hero_height": 150   // высота шапки с заголовком, 0…420
  },

  // Шапка окна: надзаголовок, крупный заголовок, подпись
  "hero": {
    "kicker": "S.T.A.L.K.E.R.",
    "title": "НАЗВАНИЕ МОДА",
    "subtitle": "Версия мода · автор"
  },

  // Своя графика: пути относительно этого файла.
  // Если не указывать — останется встроенный арт лаунчера.
  "assets": {
    "background": null,
    "icon": null
  },

  // Что запускаем и что считаем обязательным для игры
  "game": {
    "executable": "Stalker-CoC.exe",
    "required_files": ["Stalker-CoC.exe", "gamedata"]
  },

  // Репозиторий GitHub для кнопки обновлений: "владелец/репозиторий".
  // Замените "owner/mod" на свой — иначе лаунчер просто не найдёт релизов.
  // Если обновления не нужны: "repo": null и удалите кнопку с action "update".
  "update": {
    "enabled": true,
    "repo": "owner/mod"
  },

  // Кнопки меню. Порядок в файле = порядок в окне.
  "options": [
    {
      "title": "ЗАПУСК",                    // надпись на кнопке
      "description": "Обычный запуск игры", // подпись под надписью
      "action": "run",                      // run | url | folder | update
      "args": ["-skip_reg"],                // аргументы командной строки
      "accent": true                        // главная кнопка (одна на лаунчер)
    },
    {
      "title": "ЗАПУСК (ОТЛАДКА)",
      "description": "С логом движка",
      "action": "run",
      "args": ["-skip_reg", "-dbg"],
      "keep_open": false                    // закрыть лаунчер после запуска
    },
    {
      "title": "ПАПКА СОХРАНЕНИЙ",
      "description": "Открыть saves",
      "action": "folder",                   // открыть папку или файл
      "path": "savedgames",
      "hide_if_missing": true               // прятать кнопку, если папки нет
    },
    {
      "title": "ГРУППА ВКОНТАКТЕ",
      "description": "Новости и обновления мода",
      "action": "url",                      // открыть ссылку в браузере
      "url": "https://vk.com/scoc174"
    },
    {
      "title": "ОБНОВЛЕНИЕ",
      "description": "Проверить свежую версию",
      "action": "update"                    // нужен update.repo выше
    }
  ]
}
"""


def example_config_text() -> str:
    """Текст образца ``config.launcher`` с комментариями."""
    return EXAMPLE_CONFIG


def write_example_config(path: Path, *, overwrite: bool = False) -> Path:
    """Записать образец конфига; существующий файл не перезаписываем без флага."""
    path = Path(path)
    if path.exists() and not overwrite:
        raise ConfigError(
            f"Файл уже существует: {path}",
            path=path,
            hint="Удалите его или укажите другой путь, чтобы не потерять настройки.",
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(example_config_text(), encoding="utf-8")
    LOGGER.info("Создан образец конфигурации: %s", path)
    return path


def summarize(config: LauncherConfig) -> str:
    """Короткая сводка для ``--check-config``."""
    lines = [
        f"Файл: {config.path or '(не используется)'}",
        f"Название: {config.name}",
        f"Акцент: {config.accent}",
        f"Окно: {config.window.width}×шапка {config.window.hero_height}",
        f"Игра: {config.game.executable or '(не задан executable)'}",
        f"Обязательные файлы: {', '.join(config.game.required_files) or '(нет)'}",
        f"Обновления: {'включены' if config.update.enabled else 'выключены'}"
        f"{f', репозиторий {config.update.repo}' if config.update.repo else ''}",
        f"Кнопок: {len(config.options)}",
    ]
    for option in config.options:
        detail = option.action
        if option.action == ACTION_RUN:
            detail = f"run → {option.target} {' '.join(option.args)}".strip()
        elif option.action == ACTION_URL:
            detail = f"url → {option.url}"
        elif option.action == ACTION_FOLDER:
            detail = f"folder → {option.path}"
        lines.append(f"  • {option.title} [{option.key}] — {detail}")
    if config.warnings:
        lines.append("Предупреждения:")
        lines.extend(f"  ! {warning}" for warning in config.warnings)
    return "\n".join(lines)
