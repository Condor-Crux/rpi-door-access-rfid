import platform
from pathlib import Path


def is_raspberry_pi() -> bool:
    if platform.machine().lower() not in ("armv6l", "armv7l", "aarch64", "arm64"):
        return False
    model = Path("/proc/device-tree/model")
    if model.exists():
        try:
            return "raspberry pi" in model.read_text(errors="ignore").lower()
        except OSError:
            return False
    return True


def platform_name() -> str:
    return "raspberry-pi" if is_raspberry_pi() else f"{platform.system()}-{platform.machine()}"
