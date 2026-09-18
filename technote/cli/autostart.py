import platform
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .config import LINUX_SERVICE_NAME


@dataclass
class AutostartStatus:
    is_configured: bool = False
    is_working: bool = False
    tips: list[str] = field(default_factory=list)


class AutostartError(Exception):
    """Raised when autostart setup fails."""


def enable(command: list[str]):
    # Replace the command name with its absolute path.
    command[0] = _find_command_path(command[0])
    system = platform.system()

    if system == "Linux":
        _linux_enable(command, LINUX_SERVICE_NAME)
    else:
        raise AutostartError(f"{system} is not supported.")


def disable():
    system = platform.system()

    if system == "Linux":
        _linux_disable(LINUX_SERVICE_NAME)
    else:
        raise AutostartError(f"{system} is not supported.")


def status() -> AutostartStatus:
    system = platform.system()

    if system == "Linux":
        return _linux_status(LINUX_SERVICE_NAME)
    else:
        raise AutostartError(f"{system} is not supported.")


# --- Linux (systemd --user) -------------------------------------------------


def _linux_enable(command: list[str], service_name: str):
    if not shutil.which("systemctl"):
        raise AutostartError("systemctl was not found. This feature requires systemd.")

    service_path = _linux_service_path(service_name)
    service_path.parent.mkdir(parents=True, exist_ok=True)
    exec_start = " ".join(command)

    service_content = f"""[Unit]
Description=TechNote Local Web Server
After=network.target

[Service]
ExecStart={exec_start}
Restart=on-failure
RestartSec=3

[Install]
WantedBy=default.target
"""
    service_path.write_text(service_content)

    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
        subprocess.run(
            ["systemctl", "--user", "enable", "--now", f"{service_name}.service"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise AutostartError(f"systemctl command failed: {e}") from e

    is_service_active = _linux_is_service_active(service_name)
    if not is_service_active:
        raise AutostartError(
            f"The systemd service file '{service_path}' was created but the service didn't get activated. "
            f"Use 'systemctl --user status {service_name}.service' to check if there are any errors."
        )


def _linux_disable(service_name: str):
    service_path = _linux_service_path(service_name)
    is_service_enabled = _linux_is_service_enabled(service_name)

    if is_service_enabled:
        try:
            subprocess.run(
                ["systemctl", "--user", "disable", "--now", f"{service_name}.service"],
                check=False,
            )
        except subprocess.CalledProcessError as e:
            raise AutostartError(f"systemctl command failed: {e}") from e

    if service_path.exists():
        service_path.unlink()

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)


def _linux_status(service_name: str):
    service_path = _linux_service_path(service_name)
    if not service_path.exists():
        return AutostartStatus(is_configured=False)

    is_service_enabled = _linux_is_service_enabled(service_name)
    is_service_active = _linux_is_service_active(service_name)

    if not is_service_enabled or not is_service_active:
        return AutostartStatus(
            is_configured=True,
            is_working=False,
            tips=[
                f"Check if there are any errors: systemctl --user status {service_name}.service",
                f"You can enable the service manually: systemctl --user enable --now {service_name}.service",
            ],
        )

    return AutostartStatus(
        is_configured=True,
        is_working=True,
        tips=[
            f"The systemd service file is located at '{service_path}'",
            f"To see more information about the service: systemctl --user status {service_name}.service",
        ],
    )


def _linux_service_path(service_name: str):
    return Path.home() / ".config" / "systemd" / "user" / f"{service_name}.service"


def _linux_is_service_enabled(service_name) -> bool:
    return (
        subprocess.run(
            ["systemctl", "--user", "is-enabled", f"{service_name}.service"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


def _linux_is_service_active(service_name) -> bool:
    return (
        subprocess.run(
            ["systemctl", "--user", "is-active", f"{service_name}.service"],
            check=False,
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )


# --- Utils -------------------------------------------------


def _find_command_path(command):
    """Find the absolute path to the installed command."""
    path = shutil.which(command)
    if not path:
        raise AutostartError(f"Could not find the '{command}' executable on your PATH.")
    return path
