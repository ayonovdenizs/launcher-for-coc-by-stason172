"""Проверки таблицы режимов запуска."""

from __future__ import annotations

from launcher import GAME_BUILD, GAME_EXE
from launcher.options import (
    FAST_LAUNCH_SCRIPT,
    MOD_MANAGER_EXE,
    OPTIONS,
    OPTIONS_BY_KEY,
    SETTINGS_EXE,
    UPDATE_KEY,
)


def test_keys_are_unique_and_indexed() -> None:
    keys = [option.key for option in OPTIONS]
    assert len(keys) == len(set(keys))
    assert set(OPTIONS_BY_KEY) == set(keys)


def test_every_option_has_text_for_ui() -> None:
    for option in OPTIONS:
        assert option.title.strip(), option.key
        assert option.description.strip(), option.key
        assert option.title == option.title.upper(), option.key


def test_exactly_one_accent_option() -> None:
    assert [option.key for option in OPTIONS if option.accent] == ["run"]


def test_targets_match_game_files() -> None:
    assert OPTIONS_BY_KEY["run"].target == GAME_EXE
    assert OPTIONS_BY_KEY["run"].args == ("-skip_reg",)
    assert OPTIONS_BY_KEY["debug"].target == GAME_EXE
    assert OPTIONS_BY_KEY["debug"].args == ("-skip_reg", "-dbg")
    assert OPTIONS_BY_KEY["fast"].target == FAST_LAUNCH_SCRIPT
    assert OPTIONS_BY_KEY["mods"].target == MOD_MANAGER_EXE
    assert OPTIONS_BY_KEY["options"].target == SETTINGS_EXE


def test_update_option_has_no_target() -> None:
    update = OPTIONS_BY_KEY[UPDATE_KEY]
    assert update.is_update
    assert update.target is None
    assert not update.keep_open


def test_auxiliary_windows_are_kept_open() -> None:
    assert OPTIONS_BY_KEY["mods"].keep_open
    assert OPTIONS_BY_KEY["options"].keep_open
    assert not OPTIONS_BY_KEY["run"].keep_open
    assert not OPTIONS_BY_KEY["update"].keep_open


def test_build_label_is_used_in_descriptions() -> None:
    assert GAME_BUILD in OPTIONS_BY_KEY["run"].description
