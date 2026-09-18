import argparse
import logging
import platform
import sys
from importlib.metadata import PackageNotFoundError, version
from logging.handlers import RotatingFileHandler
from pathlib import Path

from technote.config import (
    APP_DESCRIPTION,
    APP_MODULE,
    APP_NAME,
    MODULE_NAME,
    SERVER_HOST,
    SERVER_PORT,
)

from . import autostart, browser, utils
from .server import (
    AddressInUseError,
    AddressNotAvailableError,
    HostResolveError,
    PortRefusedError,
    Server,
    ServerError,
)

try:
    __version__ = version("technote")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"  # running from source, not installed

PROG = MODULE_NAME
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        prog=PROG,
        description=f"{APP_NAME} — {APP_DESCRIPTION}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        help=(
            "Make TechNote output verbose information during the operation."
            "Useful for debugging and seeing what's going on under the hood."
        ),
        action="store_true",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"{APP_NAME} {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    _setup_commands(subparsers)
    args = parser.parse_args()

    _configure_logging(verbose=args.verbose)

    if args.command is None:
        parser.print_help()
        return

    args.func(args)


def _setup_commands(subparsers):
    # server arguments: [--host] [--port]
    server_arguments = argparse.ArgumentParser(add_help=False)
    server_arguments.add_argument(
        "-H",
        "--host",
        default=SERVER_HOST,
        help=(
            "The hostname to listen on. "
            "Set this to '0.0.0.0' to make TechNote available on your local network. "
            "Notice that on a machine with a public IP address, this also makes "
            "TechNote accessible from the Internet. "
            "If you are deploying TechNote on a public server, you should use "
            "a reverse proxy (e.g. Nginx) instead of exposing the app directly "
            "to the Internet. "
            f"The default is '{SERVER_HOST}'."
        ),
    )
    server_arguments.add_argument(
        "-p",
        "--port",
        type=int,
        default=SERVER_PORT,
        help=(
            "The port to run TechNote on. "
            "Please use a port >= 1024 (e.g. 8000). "
            f"The default is '{SERVER_PORT}'."
        ),
    )

    # command: run
    run_parser = subparsers.add_parser(
        "run",
        parents=[server_arguments],
        help="Start the server (see '%(prog)s run -h' for options)",
    )
    run_parser.set_defaults(func=_run_command)
    run_parser.add_argument(
        "-n",
        "--no-browser",
        action="store_true",
        help=(
            "By default, TechNote will open in your browser automatically. "
            "Use this option to prevent that."
        ),
    )
    run_parser.add_argument(
        "-s",
        "--service-mode",
        action="store_true",
        help=("In service mode, TechNote prints the logs instead of help messages."),
    )

    # command: autostart
    autostart_parser = subparsers.add_parser(
        "autostart",
        help="Manage the autostart service (see '%(prog)s autostart -h' for options)",
    )
    autostart_parser.set_defaults(func=_autostart_status_command)
    autostart_sub = autostart_parser.add_subparsers(dest="sub_command")
    # command: autostart enable
    autostart_sub.add_parser(
        "enable",
        parents=[server_arguments],
        help="Set up TechNote to start automatically on login  (see '%(prog)s enable -h' for options).",
    ).set_defaults(func=_autostart_enable_command)
    # command: autostart disable
    autostart_sub.add_parser(
        "disable", help="Remove the TechNote startup configurations."
    ).set_defaults(func=_autostart_disable_command)
    # command: autostart status
    autostart_sub.add_parser(
        "status", help="Check the status of the TechNote startup configurations."
    ).set_defaults(func=_autostart_status_command)


def _run_command(args):
    if args.service_mode:
        _run_server_service_mode(args.host, args.port)
    else:
        _run_server_terminal_mode(
            args.host, args.port, open_browser=not args.no_browser
        )


def _autostart_enable_command(args):
    # Try to init the Server to check if there are errors.
    server = _init_server_terminal_mode(args.host, args.port)
    try:
        autostart.enable(
            [
                PROG,
                "run",
                "--host",
                args.host,
                "--port",
                str(args.port),
                "--service-mode",
            ]
        )
    except autostart.AutostartError as e:
        print(f"Something went wrong: {e}")
        sys.exit(1)

    print(f"\n👉 TechNote is waiting for you on {server.url}\n")
    print("💡 Tips:")
    print(
        "   - You only need to run this command once — after that, TechNote will \n"
        "     start automatically on login without running the command again.\n"
        f"   - Use '{PROG} {args.command}' to check if autostart is configured correctly."
    )
    if args.host != "0.0.0.0":
        print(
            f"   - Add '--host 0.0.0.0' to make TechNote available on your local network, \n"
            f"     but notice that you should not do this on a machine with a public IP address.\n"
            f"     See '{PROG} {args.command} {args.sub_command} --help' for more information."
        )


def _autostart_disable_command(args):
    try:
        autostart.disable()
    except autostart.AutostartError as e:
        print(f"Something went wrong: {e}")
        sys.exit(1)


def _autostart_status_command(args):
    try:
        status = autostart.status()
    except autostart.AutostartError as e:
        print(f"Something went wrong: {e}")
        sys.exit(1)

    if not status.is_configured:
        print("Autostart is not configured yet.")
        print(f"Use '{PROG} autostart enable' to set it up.")
    elif not status.is_working:
        print("Autostart is configured already, but it's not working.")
    else:
        print("Autostart is configured correctly.")
        print(f"Use '{PROG} autostart disable' to disable autostart.")

    # Show extra information about the current situation if available
    if status.tips:
        print("\n".join(status.tips))


def _run_server_service_mode(host: str, port: int):
    try:
        server = Server(host=host, port=port)
        logger.info("TechNote starting on %s", server.address)
        server.run(app=APP_MODULE)
    except ServerError as e:
        logger.error(f"Could not start TechNote: {e}")
        sys.exit(1)
    except OSError:
        logger.exception("Unexpected error while starting TechNote")
        sys.exit(1)
    except KeyboardInterrupt:
        print("Keyboard interrupt received, exiting.")


def _run_server_terminal_mode(host: str, port: int, open_browser: bool):
    server = _init_server_terminal_mode(host, port)
    print("\n🚀 Starting the server...\n")

    if open_browser:
        print(
            f"👉 TechNote will open in your browser once the server is ready.\n"
            f"   You can also open the url manually: {server.url}\n"
        )
        browser.open_in_background(server)
    else:
        print(f"👉 Open {server.url}\n")

    print("💡 Tips:")
    print("   - Use Ctrl+C to stop the server.")
    if open_browser:
        print(
            "   - Add --no-browser or -n to prevent the browser from opening automatically."
        )
    if host != "0.0.0.0":
        print(
            f"   - Set '--host 0.0.0.0' to make TechNote available on your local network, \n"
            f"     but notice that you should not do this on a machine with a public IP address.\n"
            f"     See '{PROG} run --help' for more information."
        )

    try:
        server.run(app=APP_MODULE)
    except KeyboardInterrupt:
        print("\nShutting down the server 😴")
        sys.exit(0)


def _init_server_terminal_mode(host: str, port: int) -> Server:
    try:
        return Server(host=host, port=port)
    except AddressInUseError:
        tip = {
            "Linux": f"ss -ltnp | grep :{port}",
            "Darwin": f"lsof -P -i :{port}",
            "Windows": f"netstat -ano | findstr :{port}",
        }
        print(
            f"Port {port} is already in use — this is the default port TechNote uses.\n"
            "If TechNote is already running, you probably don't need to start another instance.\n"
            f"Otherwise, try a different port (e.g. {port + 1}):"
            if port == SERVER_PORT
            else (f"Port {port} is already in use.\nLet's try port {port + 1}:")
        )
        print(f"\n\t{_update_command(['--port', '-p'], port + 1)}\n")
        print(
            f"[tip] Identify which process is using this port: "
            f"{tip.get(platform.system(), '<UNKNOWN PLATFORM>')}"
        )
        sys.exit(1)
    except PortRefusedError:
        print(
            f"Port {port} may be privileged (root/admin required),\n"
            "reserved by the system (e.g. Windows Hyper-V port exclusions), or\n"
            "restricted by security policy.\n"
            "Please try a different port >=1024 (e.g. 8000):\n"
            f"\n\t{_update_command(['--port', '-p'], 8000)}\n",
        )
        sys.exit(1)
    except HostResolveError:
        print(
            "Could not resolve host. Please try again with a valid IP address (e.g. 127.0.0.1):\n"
            f"\n\t{_update_command(['--host', '-H'], '127.0.0.1')}\n",
        )
        sys.exit(1)
    except AddressNotAvailableError:
        print(
            "You requested an IP address that is NOT available on this machine.\n"
            "Please try again with a loopback address (e.g. 127.0.0.1):\n"
            f"\n\t{_update_command(['--host', '-H'], '127.0.0.1')}\n",
        )
        sys.exit(1)
    except OSError as e:
        print(f"An unexpected error occurred. OSError: {e}")
        sys.exit(1)


def _configure_logging(verbose: bool = False, log_file: Path | None = None) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    handlers = [logging.StreamHandler(sys.stderr)]

    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(
            RotatingFileHandler(log_file, maxBytes=1_000_000, backupCount=3)
        )

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


def _update_command(aliases: list[str], value: str | int) -> str:
    """Return the current command with `arg` set/overridden to `value`."""
    return utils.set_command_argument([PROG, *sys.argv[1:]], aliases, value)
