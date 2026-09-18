"""
Tests for autostart.py

Strategy:
- Force each OS branch by monkeypatching platform.system(), regardless of the
  host actually running the tests.
- Never touch the real system: subprocess.run, shutil.which, and Path.home()
  are all mocked/redirected.
- Assert on *what would have been run/written*, not on real side effects.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from technote.cli import autostart
from technote.cli.config import LINUX_SERVICE_NAME

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_home(tmp_path, monkeypatch):
    """Redirect Path.home() so file writes land in a tmp dir we can inspect."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    return tmp_path


@pytest.fixture
def mock_run(monkeypatch):
    """Replace subprocess.run with a MagicMock returning success by default."""
    mock = MagicMock(return_value=subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(subprocess, "run", mock)
    return mock


def force_platform(monkeypatch, name):
    monkeypatch.setattr(autostart.platform, "system", lambda: name)


# ---------------------------------------------------------------------------
# Linux
# ---------------------------------------------------------------------------

class TestLinux:
    def test_enable_writes_service_file_and_calls_systemctl(self, monkeypatch, fake_home, mock_run):
        force_platform(monkeypatch, "Linux")
        monkeypatch.setattr(autostart.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")

        autostart.enable(["technote", "serve", "--host", "127.0.0.1", "--port", "1234"])

        service_path = fake_home / ".config" / "systemd" / "user" / f"{LINUX_SERVICE_NAME}.service"
        assert service_path.exists()
        content = service_path.read_text()
        assert "ExecStart=/usr/bin/technote serve --host 127.0.0.1 --port 1234" in content
        assert "[Install]" in content

        # daemon-reload then enable --now, in that order
        calls = [c.args[0] for c in mock_run.call_args_list]
        assert ["systemctl", "--user", "daemon-reload"] in calls
        assert ["systemctl", "--user", "enable", "--now", f"{LINUX_SERVICE_NAME}.service"] in calls

    def test_enable_raises_if_systemctl_missing(self, monkeypatch, fake_home):
        force_platform(monkeypatch, "Linux")
        # the target command itself resolves fine; only systemctl is missing
        monkeypatch.setattr(
            autostart.shutil, "which",
            lambda cmd: None if cmd == "systemctl" else f"/usr/bin/{cmd}",
        )

        with pytest.raises(autostart.AutostartError, match="systemd"):
            autostart.enable(["technote"])

    def test_enable_raises_on_systemctl_failure(self, monkeypatch, fake_home, mock_run):
        force_platform(monkeypatch, "Linux")
        monkeypatch.setattr(autostart.shutil, "which", lambda cmd: "/usr/bin/systemctl")
        mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl")

        with pytest.raises(autostart.AutostartError, match="systemctl command failed"):
            autostart.enable(["technote"])

    def test_disable_removes_service_file(self, monkeypatch, fake_home, mock_run):
        force_platform(monkeypatch, "Linux")
        service_path = fake_home / ".config" / "systemd" / "user" / f"{LINUX_SERVICE_NAME}.service"
        service_path.parent.mkdir(parents=True)
        service_path.write_text("dummy")

        autostart.disable()

        assert not service_path.exists()

    def test_disable_is_safe_when_nothing_configured(self, monkeypatch, fake_home, mock_run):
        force_platform(monkeypatch, "Linux")
        # Should not raise even though no service file / unit exists
        autostart.disable()

    def test_status_not_configured(self, monkeypatch, fake_home):
        force_platform(monkeypatch, "Linux")
        result = autostart.status()
        assert result.is_configured is False
        assert result.is_working is False

    def test_status_configured_but_inactive(self, monkeypatch, fake_home, mock_run):
        force_platform(monkeypatch, "Linux")
        service_path = fake_home / ".config" / "systemd" / "user" / f"{LINUX_SERVICE_NAME}.service"
        service_path.parent.mkdir(parents=True)
        service_path.write_text("dummy")
        # is-enabled succeeds, is-active fails
        mock_run.side_effect = [
            subprocess.CompletedProcess(args=[], returncode=0),
            subprocess.CompletedProcess(args=[], returncode=1),
        ]

        result = autostart.status()

        assert result.is_configured is True
        assert result.is_working is False

    def test_status_configured_and_active(self, monkeypatch, fake_home, mock_run):
        force_platform(monkeypatch, "Linux")
        service_path = fake_home / ".config" / "systemd" / "user" / f"{LINUX_SERVICE_NAME}.service"
        service_path.parent.mkdir(parents=True)
        service_path.write_text("dummy")
        mock_run.return_value = subprocess.CompletedProcess(args=[], returncode=0)

        result = autostart.status()

        assert result.is_configured is True
        assert result.is_working is True
        assert result.tips

# ---------------------------------------------------------------------------
# Unsupported platform / shared helpers
# ---------------------------------------------------------------------------

class TestUnsupportedPlatform:
    @pytest.mark.parametrize("fn_name,args", [
        ("enable", (["technote"],)),
        ("disable", ()),
        ("status", ()),
    ])
    def test_raises_on_unknown_os(self, monkeypatch, fn_name, args):
        force_platform(monkeypatch, "PlayStation OS")
        monkeypatch.setattr(autostart.shutil, "which", lambda cmd: f"/usr/bin/{cmd}")
        fn = getattr(autostart, fn_name)
        with pytest.raises(autostart.AutostartError, match="PlayStation OS is not supported."):
            fn(*args)


class TestFindCommandPath:
    def test_resolves_to_absolute_path(self, monkeypatch):
        monkeypatch.setattr(autostart.shutil, "which", lambda cmd: "/usr/bin/technote")
        assert autostart._find_command_path("technote") == "/usr/bin/technote"

    def test_raises_when_not_found(self, monkeypatch):
        monkeypatch.setattr(autostart.shutil, "which", lambda cmd: None)
        with pytest.raises(autostart.AutostartError, match="executable on your PATH"):
            autostart._find_command_path("technote")
