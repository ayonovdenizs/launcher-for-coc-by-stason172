"""Проверка свежих релизов лаунчера через GitHub API.

Лаунчер не подменяет сам себя: он показывает, что вышла новая версия,
и открывает страницу релиза, где лежит собранный CI ``Launcher-CoC.exe``.
Любая ошибка сети — не проблема пользователя, поэтому функции возвращают
``None``/``False`` вместо исключений.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

from . import REPO_URL

LOGGER = logging.getLogger(__name__)

API_URL = "https://api.github.com/repos/{repo}/releases/latest"
REPO_SLUG = REPO_URL.removeprefix("https://github.com/")
DEFAULT_TIMEOUT = 6.0
USER_AGENT = "Launcher-CoC"

_VERSION_RE = re.compile(r"(\d+(?:\.\d+)*)")


@dataclass(frozen=True)
class ReleaseInfo:
    """Данные о последнем релизе на GitHub."""

    version: str
    tag: str
    name: str
    url: str
    notes: str = ""


def parse_version(text: str) -> tuple[int, ...]:
    """``"v1.2.3"`` → ``(1, 2, 3)``.

    Неразбираемые строки дают ``()`` — такая версия считается «не новее».
    """
    match = _VERSION_RE.search(text or "")
    if match is None:
        return ()
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(candidate: str, current: str) -> bool:
    """Версия ``candidate`` новее ``current`` (сравнение по числам)."""
    new_parts, current_parts = parse_version(candidate), parse_version(current)
    if not new_parts or not current_parts:
        return False
    length = max(len(new_parts), len(current_parts))
    padded_new = new_parts + (0,) * (length - len(new_parts))
    padded_current = current_parts + (0,) * (length - len(current_parts))
    return padded_new > padded_current


def api_url(slug: str = REPO_SLUG) -> str:
    """URL GitHub API для последнего релиза репозитория ``slug``."""
    return API_URL.format(repo=slug)


def fetch_latest_release(
    timeout: float = DEFAULT_TIMEOUT,
    opener: Callable[..., object] | None = None,
    slug: str = REPO_SLUG,
) -> ReleaseInfo | None:
    """Последний релиз репозитория или ``None``, если узнать не удалось.

    :param opener: подменяемый «сетевой» вызов (в тестах — без интернета).
    """
    fetch = opener or urllib.request.urlopen
    request = urllib.request.Request(
        api_url(slug),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with fetch(request, timeout=timeout) as response:  # type: ignore[attr-defined]
            payload = json.loads(response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        OSError,
        ValueError,
        AttributeError,
    ) as exc:
        LOGGER.info("Не удалось проверить обновления: %s", exc)
        return None

    tag = str(payload.get("tag_name") or "")
    return ReleaseInfo(
        version=tag.lstrip("vV") or str(payload.get("name") or ""),
        tag=tag,
        name=str(payload.get("name") or tag),
        url=str(payload.get("html_url") or f"{REPO_URL}/releases/latest"),
        notes=str(payload.get("body") or ""),
    )


def check_for_update(
    current_version: str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
    opener: Callable[..., object] | None = None,
) -> ReleaseInfo | None:
    """Вернуть описание нового релиза, если он новее ``current_version``."""
    release = fetch_latest_release(timeout=timeout, opener=opener)
    if release is None or not release.version:
        return None
    if is_newer(release.version, current_version):
        LOGGER.info("Доступна новая версия лаунчера: %s", release.version)
        return release
    LOGGER.info("Лаунчер актуален (версия %s)", current_version)
    return None
