"""Проверки разбора версий и обращения к GitHub API (без сети)."""

from __future__ import annotations

import io
import json

from launcher import REPO_URL, app_version
from launcher.updates import (
    REPO_SLUG,
    api_url,
    check_for_update,
    fetch_latest_release,
    is_newer,
    parse_version,
)


class FakeResponse(io.BytesIO):
    """Минимальная замена HTTP-ответа для urlopen."""

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc_info) -> bool:
        self.close()
        return False


def make_opener(payload: dict) -> callable:
    calls: list[str] = []

    def opener(request, timeout=None):
        calls.append(request.full_url)
        return FakeResponse(json.dumps(payload).encode("utf-8"))

    opener.calls = calls  # type: ignore[attr-defined]
    return opener


def test_repo_slug_matches_repo_url() -> None:
    assert REPO_SLUG == "ayonovdenizs/launcher-for-coc-by-stason172"
    assert api_url().endswith(f"/repos/{REPO_SLUG}/releases/latest")
    assert REPO_URL.startswith("https://github.com/")


def test_parse_version() -> None:
    assert parse_version("v1.2.3") == (1, 2, 3)
    assert parse_version("1.10") == (1, 10)
    assert parse_version("не версия") == ()
    assert parse_version("") == ()


def test_is_newer() -> None:
    assert is_newer("1.1.1", "1.1.0")
    assert is_newer("v2.0", "1.9.9")
    assert is_newer("1.2.1", "1.2")
    assert not is_newer("1.2.0", "1.2")
    assert not is_newer("1.1.0", "1.1.0")
    assert not is_newer("1.0.9", "1.1.0")
    assert not is_newer("мусор", "1.1.0")


def test_fetch_latest_release_reads_payload() -> None:
    opener = make_opener(
        {
            "tag_name": "v1.2.0",
            "name": "Лаунчер 1.2.0",
            "html_url": "https://example.invalid/release",
            "body": "Что нового",
        }
    )
    release = fetch_latest_release(opener=opener)

    assert release is not None
    assert release.version == "1.2.0"
    assert release.tag == "v1.2.0"
    assert release.url == "https://example.invalid/release"
    assert release.notes == "Что нового"
    assert opener.calls == [api_url()]


def test_fetch_latest_release_survives_network_error() -> None:
    def broken(request, timeout=None):
        raise OSError("сети нет")

    assert fetch_latest_release(opener=broken) is None


def test_check_for_update_only_reports_newer() -> None:
    newer = make_opener({"tag_name": "v9.9.9", "html_url": "https://example.invalid"})
    same = make_opener({"tag_name": f"v{app_version()}"})

    assert check_for_update("1.0.0", opener=newer) is not None
    assert check_for_update(app_version(), opener=same) is None


def test_launcher_version_looks_like_version() -> None:
    assert parse_version(app_version()) != ()
