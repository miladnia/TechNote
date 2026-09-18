import shlex

from technote.cli.utils import _update_command_argument, set_command_argument

# --- set_command_argument() - Update path (argument already present) ---


def test_set_command_argument_overrides_existing_unquoted_value():
    argv = ["prog", "run", "--port", "5000"]
    assert set_command_argument(argv, ["--port"], "8080") == "prog run --port 8080"


def test_set_command_argument_overrides_existing_value_with_int():
    # value: str | int -- confirm int inputs are coerced correctly.
    argv = ["prog", "run", "--port", "5000"]
    assert set_command_argument(argv, ["--port"], 8080) == "prog run --port 8080"


def test_set_command_argument_overrides_with_equals_sign_form():
    argv = ["prog", "run", "--port=5000"]
    assert set_command_argument(argv, ["--port"], 8080) == "prog run --port=8080"


def test_set_command_argument_overrides_quoted_value():
    argv = ["prog", "run", "--dir", "my notes"]
    result = set_command_argument(argv, ["--dir"], "other notes")
    assert result == "prog run --dir 'other notes'"
    assert shlex.split(result)[-1] == "other notes"


def test_set_command_argument_matches_first_present_alias():
    argv = ["prog", "run", "-p", "5000"]
    assert set_command_argument(argv, ["-p", "--port"], 8080) == "prog run -p 8080"


def test_set_command_argument_overrides_negative_float_value():
    argv = ["prog", "run", "--offset", "-3.14"]
    assert set_command_argument(argv, ["--offset"], -2.5) == "prog run --offset -2.5"


# --- set_command_argument() - Add path (argument not present) ---


def test_set_command_argument_adds_argument_when_absent():
    argv = ["prog", "run"]
    assert set_command_argument(argv, ["--port"], 8080) == "prog run --port 8080"


def test_set_command_argument_adds_using_first_alias_when_none_present():
    argv = ["prog", "run"]
    assert set_command_argument(argv, ["-p", "--port"], 8080) == "prog run -p 8080"


def test_set_command_argument_adds_argument_with_value_containing_space():
    argv = ["prog", "run"]
    result = set_command_argument(argv, ["--dir"], "my notes")
    assert result == "prog run --dir 'my notes'"
    assert shlex.split(result)[-1] == "my notes"


def test_set_command_argument_adds_argument_to_empty_argv():
    argv = []
    assert set_command_argument(argv, ["--port"], 8080) == "--port 8080"


# --- set_command_argument() - Non-mutation of argv ---


def test_set_command_argument_does_not_mutate_argv_on_update():
    argv = ["prog", "run", "--port", "5000"]
    original = list(argv)
    set_command_argument(argv, ["--port"], 8080)
    assert argv == original


def test_set_command_argument_does_not_mutate_argv_on_add():
    argv = ["prog", "run"]
    original = list(argv)
    set_command_argument(argv, ["--port"], 8080)
    assert argv == original


# --- set_command_argument() - Return type / round-trip sanity ---


def test_set_command_argument_return_value_round_trips_via_shlex():
    argv = ["prog", "run", "--port", "5000", "--verbose"]
    result = set_command_argument(argv, ["--port"], 8080)
    assert shlex.split(result) == ["prog", "run", "--port", "8080", "--verbose"]


# --- _update_command_argument() ---


def test_update_command_argument_simple_unquoted_value():
    command = "prog run --port 5000"
    assert (
        _update_command_argument(command, ["--port"], "8080") == "prog run --port 8080"
    )


def test_update_command_argument_with_equals_sign():
    command = "prog run --port=5000"
    assert (
        _update_command_argument(command, ["--port"], "8080") == "prog run --port=8080"
    )


def test_update_command_argument_double_quoted_value_no_space_in_new_value():
    command = 'prog run --dir "notes"'
    assert (
        _update_command_argument(command, ["--dir"], "other") == "prog run --dir other"
    )


def test_update_command_argument_single_quoted_value_no_space_in_new_value():
    command = "prog run --dir 'notes'"
    assert (
        _update_command_argument(command, ["--dir"], "other") == "prog run --dir other"
    )


def test_update_command_argument_value_with_space_gets_quoted():
    # Regression test for the fix: multi-word replacement values must stay a single token.
    command = 'prog run --dir "my notes"'
    result = _update_command_argument(command, ["--dir"], "other notes")
    assert result == "prog run --dir 'other notes'"
    # And it must round-trip correctly back into a single argv element.
    assert shlex.split(result)[-1] == "other notes"


def test_update_command_argument_hyphenated_unquoted_value():
    command = "prog run --mode case-sensitive"
    assert (
        _update_command_argument(command, ["--mode"], "case-insensitive")
        == "prog run --mode case-insensitive"
    )


def test_update_command_argument_positive_float_value():
    command = "prog run --scale 1.5"
    assert (
        _update_command_argument(command, ["--scale"], "2.75")
        == "prog run --scale 2.75"
    )


def test_update_command_argument_negative_integer_value():
    command = "prog run --offset -5 --other 1"
    assert (
        _update_command_argument(command, ["--offset"], "-10")
        == "prog run --offset -10 --other 1"
    )


def test_update_command_argument_negative_float_value():
    command = "prog run --offset -3.14 --other 1"
    assert (
        _update_command_argument(command, ["--offset"], "-2.5")
        == "prog run --offset -2.5 --other 1"
    )


def test_update_command_argument_single_character_unquoted_value():
    command = "prog run --port 5"
    assert (
        _update_command_argument(command, ["--port"], "8080") == "prog run --port 8080"
    )


def test_update_command_argument_single_character_alpha_value():
    command = "prog run --level x"
    assert _update_command_argument(command, ["--level"], "y") == "prog run --level y"


def test_update_command_argument_argument_not_present_returns_unchanged():
    command = "prog run --port 5000"
    assert _update_command_argument(command, ["--host"], "localhost") == command


def test_update_command_argument_matches_first_present_alias():
    command = "prog run -p 5000"
    assert (
        _update_command_argument(command, ["-p", "--port"], "8080")
        == "prog run -p 8080"
    )


def test_update_command_argument_does_not_consume_following_long_flag_when_value_missing():
    command = "prog run --port --verbose"
    assert _update_command_argument(command, ["--port"], "8080") == command


def test_update_command_argument_does_not_consume_following_short_flag_when_value_missing():
    command = "prog run --port -v"
    assert _update_command_argument(command, ["--port"], "8080") == command


def test_update_command_argument_value_with_apostrophe_no_space_is_shlex_safe():
    command = "prog run --note x"
    result = _update_command_argument(command, ["--note"], "O'Brien")
    # Must not raise, and must round-trip to the exact original value.
    assert shlex.split(result)[-1] == "O'Brien"


def test_update_command_argument_value_with_apostrophe_and_space_is_shlex_safe():
    command = "prog run --note x"
    result = _update_command_argument(command, ["--note"], "it's broken")
    assert shlex.split(result)[-1] == "it's broken"
