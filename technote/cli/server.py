import errno
import logging
import socket
import subprocess
import sys

logger = logging.getLogger(__name__)


class ServerError(Exception):
    """Base exception for server errors."""


class HostResolveError(ServerError):
    """Raised if a host could not be resolved."""


class PortRefusedError(ServerError):
    """Raised if a port was refused by the OS."""


class AddressNotAvailableError(ServerError):
    """Raised if an address is not available on the machine."""


class AddressInUseError(ServerError):
    """Raised if an address was already in use."""


def host_info(host: str) -> tuple[int, str]:
    """Get the address family and IP address for a given host.

    Returns:
        tuple[int, str]: The address family and IP address.

    Raises:
        HostResolveError: if the host cannot be resolved.
    """
    try:
        infos = socket.getaddrinfo(
            host,
            port=None,
            type=socket.SOCK_STREAM,
            flags=socket.AI_PASSIVE,
        )
    except socket.gaierror as e:
        raise HostResolveError(f"Could not resolve '{host}'") from e

    family, _type, _proto, _canonname, sockaddr = next(iter(infos))
    ip_address = sockaddr[0]

    return family, ip_address


def build_reachable_url(host: str, port: int) -> str:
    """Build a browser-openable URL, converting wildcard bind
    addresses (0.0.0.0, ::) to loopback and bracketing IPv6 literals.
    """
    WILDCARD_TO_LOOPBACK = {
        "0.0.0.0": "127.0.0.1",  # IPv4 wildcard
        "::": "::1",  # IPv6 wildcard (canonical form)
    }
    host = WILDCARD_TO_LOOPBACK.get(host, host)

    # Is IPv6?
    if ":" in host:
        host = f"[{host}]"

    return f"http://{host}:{port}"


class Server:
    def __init__(self, host: str, port: int):
        """Initialize the server.

        Raises:
            HostResolveError: if the host cannot be resolved.
            PortRefusedError: if the port was refused.
            AddressInUseError: if the address was already in use.
        """
        logger.debug("Initializing server with host='%s', port='%d'", host, port)
        self._port = port
        self._family, self._ip = host_info(host)
        logger.debug("Host resolved to '%s', family is '%d'", self._ip, self._family)
        self._url = build_reachable_url(host, port)
        self._check_address_availability()

    @property
    def url(self) -> str:
        return self._url

    @property
    def address(self) -> str:
        # Is IPv6?
        ip = f"[{self._ip}]" if ":" in self._ip else self._ip
        return f"{ip}:{self._port}"

    def run(self, app: str):
        """Run the Gunicorn server."""
        subprocess.run(
            [
                sys.executable,
                "-m",
                "gunicorn",
                app,
                "--workers",
                "1",
                "--threads",
                "2",
                "--bind",
                self.address,
                "--log-level",
                "warning",
            ],
            check=False,
        )

    def is_up(self) -> bool:
        try:
            with socket.create_connection((self._ip, self._port), timeout=1):
                return True
        except OSError:
            return False

    def _check_address_availability(self):
        """Check if the port is available.

        Raises:
            PortRefusedError: if the port was refused.
            AddressInUseError: if the address was already in use.
        """
        try:
            with socket.socket(self._family, socket.SOCK_STREAM) as s:
                if hasattr(socket, "SO_REUSEADDR"):
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self._ip, self._port))
        except PermissionError as e:
            raise PortRefusedError(f"Port {self._port} was refused") from e
        except OSError as e:
            if e.errno == errno.EADDRNOTAVAIL:
                raise AddressNotAvailableError(
                    f"IP address {self._ip} is not available on this machine"
                ) from e
            if e.errno == errno.EADDRINUSE:
                raise AddressInUseError(
                    f"Address {self._ip}:{self._port} is already in use"
                ) from e
        except OverflowError as e:
            raise PortRefusedError(f"Port {self._port} is invalid") from e
