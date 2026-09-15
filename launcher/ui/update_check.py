"""Фоновая проверка обновлений, чтобы не подвешивать интерфейс."""

from __future__ import annotations

import logging
from collections.abc import Callable

from PySide6.QtCore import QThread, Signal

from ..updates import ReleaseInfo, check_for_update

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
        checker: Callable[[str], ReleaseInfo | None] | None = None,
    ) -> None:
        super().__init__(parent)
        self._current_version = current_version
        self._checker = checker or check_for_update

    def run(self) -> None:
        try:
            release = self._checker(self._current_version)
        except Exception:  # pragma: no cover - страховка от любых сбоев сети
            LOGGER.exception("Проверка обновлений не удалась")
            return
        if release is not None:
            self.release_found.emit(release)
