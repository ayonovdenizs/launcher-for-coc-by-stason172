"""Фоновая проверка обновлений, чтобы не подвешивать интерфейс."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from ..updates import DEFAULT_REPO, ReleaseInfo, check_for_update

LOGGER = logging.getLogger(__name__)


class UpdateChecker(QThread):
    """Спрашивает у GitHub последний релиз в отдельном потоке.

    Ошибки сети наружу не выходят: поток просто ничего не сообщает.
    """

    release_found = Signal(object)

    def __init__(
        self,
        current_version: str,
        parent=None,
        *,
        repo: str | None = None,
        timeout: float = 6.0,
        checker: Callable[[str], ReleaseInfo | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_version = current_version
        self._repo = repo or DEFAULT_REPO
        self._timeout = timeout
        self._checker = checker or self._default_checker

    def _default_checker(self, version: str) -> ReleaseInfo | None:
        return check_for_update(version, repo=self._repo, timeout=self._timeout)

    def run(self) -> None:
        try:
            release = self._checker(self._current_version)
        except Exception:  # pragma: no cover - страховка от любых сбоев сети
            LOGGER.exception("Проверка обновлений не удалась")
            return
        if release is not None:
            self.release_found.emit(release)
