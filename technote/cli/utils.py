import re
import shlex


def set_command_argument(argv: list[str], aliases: list[str], value: str | int) -> str:
    """Set or override a single argument's value within a command."""
    value = str(value)
    command = shlex.join(argv)
    new_command = _update_command_argument(command, aliases, value)

    # The argument was not in the command, so we need to add it
    if new_command == command:
        new_command = _add_command_argument(argv, aliases[0], value)

    return new_command


def _update_command_argument(command: str, aliases: list[str], new_value: str) -> str:
    """Update the value of a single argument within a command if there was any match."""
    new_value = shlex.quote(new_value)

    pattern = rf"(({'|'.join(map(re.escape, aliases))})[ =]*)"
    # Cover quoted values, unquoted strings that don't start with a dash
    # and contain no spaces or quotes, and unquoted negative numbers
    pattern += r'("(.*)"|\'(.*)\'|([^ \'"\-][^ \'"]*)|(\-[0-9\.]+))'

    return re.sub(
        pattern,
        lambda match: f"{match.group(1)}{new_value}",
        command,
    )


def _add_command_argument(argv: list[str], arg: str, value: str) -> str:
    """Add a single argument to the given command."""
    return shlex.join([*argv, arg, value])
