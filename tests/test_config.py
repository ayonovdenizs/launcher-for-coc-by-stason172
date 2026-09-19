"""Проверки разбора и валидации config.launcher."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from launcher.config import (
    CONFIG_FILENAME,
    ConfigError,
    LauncherConfig,
    example_config_text,
    expand_path,
    find_config,
    loads_jsonc,
    parse_config,
    read_config,
    slugify,
    strip_jsonc,
    strip_trailing_commas,
    summarize,
    write_example_config,
)
from launcher.options import ACTION_FOLDER, ACTION_RUN, ACTION_UPDATE, ACTION_URL

ROOT = Path(__file__).resolve().parent.parent


# ------------------------------------------------------------- JSON с комментами


def test_comments_are_removed_but_lines_kept() -> None:
    text = '{\n  // строка комментария\n  "a": 1, /* блочный\n  комментарий */\n  "b": 2\n}'
    stripped = strip_jsonc(text)

    assert "//" not in stripped
    assert "/*" not in stripped
    assert stripped.count("\n") == text.count("\n")


def test_comment_inside_string_is_kept() -> None:
    stripped = strip_jsonc('{"url": "https://vk.com/scoc174"}')
    assert json.loads(stripped)["url"] == "https://vk.com/scoc174"


def test_escaped_quote_does_not_end_string() -> None:
    stripped = strip_jsonc('{"text": "кавычка \\" и //фрагмент"}  // хвост')
    assert json.loads(stripped)["text"] == 'кавычка " и //фрагмент'


def test_unterminated_block_comment_reports_line() -> None:
    with pytest.raises(ConfigError) as error:
        strip_jsonc('{\n  "a": 1\n}\n/* не закрыт', path=Path(CONFIG_FILENAME))

    assert error.value.line == 4
    assert "не закрыт" in error.value.message.lower()


def test_trailing_commas_are_allowed() -> None:
    text = '{"options": [{"title": "A",},],}'
    payload = loads_jsonc(text)
    assert payload["options"][0]["title"] == "A"


def test_trailing_comma_inside_string_is_kept() -> None:
    assert json.loads(strip_trailing_commas('{"a": "1,}"}'))["a"] == "1,}"


def test_syntax_error_points_to_line_and_column() -> None:
    text = '{\n  "options": [\n    {"title": "A"}\n    {"title": "B"}\n  ]\n}'
    with pytest.raises(ConfigError) as error:
        loads_jsonc(text, path=Path("config.launcher"))

    assert error.value.line == 4
    assert error.value.snippet
    assert "^" in error.value.snippet
    assert "config.launcher:4" in error.value.location


# ------------------------------------------------------------------- утилиты


def test_expand_path_is_relative_to_game_dir(tmp_path: Path) -> None:
    assert expand_path("savedgames", tmp_path) == tmp_path / "savedgames"
    absolute = tmp_path / "абсолютный"
    assert expand_path(str(absolute), Path("/другая")) == absolute


def test_expand_path_expands_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    assert expand_path("~/logs", tmp_path) == tmp_path / "logs"


@pytest.mark.parametrize("template", ["%TEST_MOD_DIR%", "$TEST_MOD_DIR", "${TEST_MOD_DIR}"])
def test_expand_path_expands_variables(
    template: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """И Windows-стиль ``%VAR%``, и ``$VAR`` — чтобы конфиги были переносимы."""
    monkeypatch.setenv("TEST_MOD_DIR", "logs")
    assert expand_path(template, tmp_path) == tmp_path / "logs"


def test_expand_path_keeps_unknown_variable(tmp_path: Path) -> None:
    assert expand_path("%НЕТ_ТАКОЙ%", tmp_path) == tmp_path / "%НЕТ_ТАКОЙ%"


def test_slugify_makes_keys() -> None:
    assert slugify("ФАСТ ЗАПУСК", "fallback") == "fast-zapusk"
    assert slugify("ИГРАТЬ", "option-1") == "igrat"
    assert slugify("!!!", "option-3") == "option-3"


# -------------------------------------------------------------- разбор конфига


def test_parses_full_config(simple_config: LauncherConfig) -> None:
    assert simple_config.name == "Тестовый лаунчер"
    assert simple_config.hero.title == "ЗАГОЛОВОК"
    assert simple_config.window.width == 420
    assert simple_config.accent == "#3f7d5a"
    assert simple_config.game.executable == "Stalker-CoC.exe"
    assert simple_config.update.repo == "owner/repo"
    assert len(simple_config.options) == 2
    assert simple_config.footer_text().startswith("Тест · ")


def test_option_defaults_from_game_section(simple_config: LauncherConfig) -> None:
    run = simple_config.option_by_key("run")
    assert run is not None
    assert run.action == ACTION_RUN
    assert run.target == "Stalker-CoC.exe"  # взят из game.executable
    assert run.args == ("-skip_reg",)
    assert run.required_files == ("Stalker-CoC.exe", "gamedata")
    assert run.accent
    assert not run.keep_open


def test_args_can_be_written_as_single_string(tmp_path: Path) -> None:
    config = parse_config(
        {
            "options": [
                {"title": "A", "args": "-nointro -x64", "target": "game.exe"},
            ]
        },
        path=tmp_path / CONFIG_FILENAME,
        game_dir=tmp_path,
    )
    assert config.options[0].args == ("-nointro", "-x64")


def test_hero_defaults_to_launcher_name(tmp_path: Path) -> None:
    config = parse_config(
        {"name": "Мод X", "options": [{"title": "A", "target": "a.exe"}]},
        game_dir=tmp_path,
    )
    assert config.hero.title == "Мод X"
    assert config.hero.kicker == ""


def test_unknown_fields_become_warnings(tmp_path: Path) -> None:
    config = parse_config(
        {
            "nmae": "опечатка",
            "options": [{"title": "A", "target": "a.exe", "color": "red"}],
        },
        game_dir=tmp_path,
    )
    joined = " ".join(config.warnings)
    assert "nmae" in joined
    assert "color" in joined


def test_several_accents_warn(tmp_path: Path) -> None:
    config = parse_config(
        {
            "options": [
                {"title": "A", "target": "a.exe", "accent": True},
                {"title": "B", "target": "b.exe", "accent": True},
            ]
        },
        game_dir=tmp_path,
    )
    assert any("акцент" in warning for warning in config.warnings)


def test_action_defaults_to_run(tmp_path: Path) -> None:
    config = parse_config(
        {"game": {"executable": "g.exe"}, "options": [{"title": "Играть"}]},
        game_dir=tmp_path,
    )
    option = config.options[0]
    assert option.action == ACTION_RUN
    assert option.target == "g.exe"
    assert option.key == "igrat"


def test_folder_option_keeps_launcher_open(tmp_path: Path) -> None:
    config = parse_config(
        {
            "options": [
                {"title": "Сохранения", "action": "folder", "path": "savedgames"},
            ]
        },
        game_dir=tmp_path,
    )
    option = config.options[0]
    assert option.action == ACTION_FOLDER
    assert option.path == "savedgames"
    assert option.keep_open is True


def test_windows_path_in_config_is_relative_to_game_dir(tmp_path: Path) -> None:
    config = parse_config(
        {"options": [{"title": "Лог", "action": "folder", "path": "logs\\engine"}]},
        game_dir=tmp_path,
    )
    assert config.options[0].path == "logs\\engine"


def test_update_option_requires_repo(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as error:
        parse_config(
            {"options": [{"title": "Обновление", "action": ACTION_UPDATE}]},
            path=tmp_path / CONFIG_FILENAME,
            game_dir=tmp_path,
        )
    assert "репозиторий" in error.value.hint


def test_update_option_with_repo_is_parsed(tmp_path: Path) -> None:
    config = parse_config(
        {
            "update": {"repo": "owner/mod"},
            "options": [{"title": "Обновление", "action": ACTION_UPDATE}],
        },
        game_dir=tmp_path,
    )
    assert config.options[0].is_update
    assert config.update.repo == "owner/mod"


def test_update_disabled_warns_about_button(tmp_path: Path) -> None:
    config = parse_config(
        {
            "update": {"repo": "owner/mod", "enabled": False},
            "options": [{"title": "Обновление", "action": ACTION_UPDATE}],
        },
        game_dir=tmp_path,
    )
    assert any("выключена" in warning for warning in config.warnings)


# ------------------------------------------------------------------- ошибки


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({}, '"options"'),
        ({"options": []}, "пуст"),
        ({"options": [{"description": "нет названия"}]}, "title"),
        ({"options": [{"title": "A"}]}, "target"),
        ({"options": [{"title": "A", "action": "запуск"}]}, "действие"),
        ({"options": [{"title": "A", "action": "url"}]}, "url"),
        ({"options": [{"title": "A", "action": "url", "url": "vk.com"}]}, "http"),
        ({"options": [{"title": "A", "action": "folder"}]}, "path"),
        (
            {"options": [{"title": "A", "target": "a.exe"}, {"title": "A", "target": "b.exe"}]},
            "повтор",
        ),
        ({"accent": "красный", "options": [{"title": "A", "target": "a.exe"}]}, "accent"),
        ({"name": 42, "options": [{"title": "A", "target": "a.exe"}]}, "строк"),
        ({"window": {"width": "широкое"}, "options": [{"title": "A", "target": "a.exe"}]}, "целым"),
        ({"window": {"width": 10}, "options": [{"title": "A", "target": "a.exe"}]}, "от 340"),
        ({"options": "кнопки"}, "спис"),
        ({"options": [{"title": "A", "target": "a.exe", "accent": "да"}]}, "true или false"),
        (
            {"update": {"repo": "нет-слэша"}, "options": [{"title": "A", "target": "a.exe"}]},
            "владелец",
        ),
    ],
)
def test_invalid_configs_raise_readable_errors(
    payload: dict, expected: str, tmp_path: Path
) -> None:
    with pytest.raises(ConfigError) as error:
        parse_config(payload, path=tmp_path / CONFIG_FILENAME, game_dir=tmp_path)
    message = f"{error.value.message} {error.value.hint}"
    assert expected in message


def test_error_text_includes_path_and_hint(tmp_path: Path) -> None:
    path = tmp_path / CONFIG_FILENAME
    with pytest.raises(ConfigError) as error:
        parse_config({}, path=path, game_dir=tmp_path)

    summary = error.value.summary()
    assert str(path) in summary
    assert "Подсказка" in summary


def test_duplicate_keys_detected_only_by_key(tmp_path: Path) -> None:
    payload = {
        "options": [
            {"key": "play", "title": "Играть", "target": "a.exe"},
            {"key": "play", "title": "Запуск", "target": "a.exe"},
        ]
    }
    with pytest.raises(ConfigError, match="play"):
        parse_config(payload, game_dir=tmp_path)


# ------------------------------------------------------------- файл на диске


def test_read_config_from_file(tmp_path: Path, game_dir: Path) -> None:
    path = game_dir / CONFIG_FILENAME
    path.write_text(example_config_text(), encoding="utf-8")
    config = read_config(path, game_dir=game_dir)

    assert config.path == path
    assert config.options
    assert not config.is_default_config


def test_read_config_reports_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as error:
        read_config(tmp_path / CONFIG_FILENAME, game_dir=tmp_path)

    assert "не найден" in error.value.message
    assert "--create-config" in (error.value.hint or "")


def test_read_config_handles_utf8_bom(tmp_path: Path, game_dir: Path) -> None:
    path = game_dir / CONFIG_FILENAME
    path.write_text('{"options": [{"title": "A", "target": "a.exe"}]}', encoding="utf-8-sig")
    assert read_config(path, game_dir=game_dir).options[0].title == "A"


def test_find_config_defaults_to_game_dir(tmp_path: Path) -> None:
    assert find_config(tmp_path) == tmp_path / CONFIG_FILENAME
    assert find_config(tmp_path, "мой.launcher") == Path.cwd() / "мой.launcher"


def test_write_example_config_refuses_to_overwrite(tmp_path: Path) -> None:
    path = write_example_config(tmp_path / CONFIG_FILENAME)
    assert path.exists()
    with pytest.raises(ConfigError, match="существует"):
        write_example_config(path)
    assert write_example_config(path, overwrite=True).exists()


def test_summarize_lists_options(simple_config: LauncherConfig) -> None:
    text = summarize(simple_config)
    assert "ЗАПУСК" in text
    assert "https://example.com" in text
    assert "Кнопок: 2" in text


# ----------------------------------------------- конфиги из репозитория


@pytest.mark.parametrize(
    "relative",
    [CONFIG_FILENAME, "examples/other-mod/config.launcher"],
)
def test_repository_configs_are_valid(relative: str) -> None:
    """Файлы в репозитории должны проходить проверку — их читают люди и CI."""
    path = ROOT / relative
    config = read_config(path, game_dir=path.parent)

    assert config.options
    assert config.update.repo
    assert sum(1 for option in config.options if option.accent) <= 1


def test_example_config_parses(tmp_path: Path) -> None:
    """Образец из --create-config обязан быть валидным."""
    path = tmp_path / CONFIG_FILENAME
    path.write_text(example_config_text(), encoding="utf-8")
    config = read_config(path, game_dir=tmp_path)

    assert len(config.options) >= 5
    actions = {option.action for option in config.options}
    assert {ACTION_RUN, ACTION_URL, ACTION_FOLDER, ACTION_UPDATE}.issubset(actions)
