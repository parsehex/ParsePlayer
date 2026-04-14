import json
import subprocess


def _build_label(device: dict) -> str:
    for key in ("label", "model", "vendor", "name", "path"):
        value = (device.get(key) or "").strip()
        if value:
            return value
    return "Unnamed USB"


def _lsblk_devices() -> list[dict]:
    result = subprocess.run(
        [
            "lsblk",
            "-J",
            "-o",
            "NAME,PATH,UUID,LABEL,MOUNTPOINT,RM,TRAN,TYPE,MODEL,VENDOR,HOTPLUG",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "lsblk failed"
        raise RuntimeError(stderr)
    return json.loads(result.stdout or "{}").get("blockdevices", [])


def _is_usb_disk(disk: dict) -> bool:
    """True only for disks that are genuinely USB transport, not Pi internal media."""
    name = (disk.get("name") or "")
    # mmcblk* is always the SD card on Pi — never treat it as USB.
    if name.startswith("mmcblk"):
        return False
    return disk.get("tran") == "usb"


def _device_path_for_identifier(identifier: str) -> tuple[str, str]:
    """Return (device_path, current_mountpoint) for a UUID-or-path identifier."""
    for disk in _lsblk_devices():
        if not _is_usb_disk(disk):
            continue
        for child in (disk.get("children") or []):
            if child.get("type") != "part":
                continue
            child_path = (child.get("path") or "").strip()
            child_uuid = (child.get("uuid") or "").strip()
            child_mount = (child.get("mountpoint") or "").strip()
            if (child_uuid and child_uuid == identifier) or child_path == identifier:
                return child_path, child_mount
    return "", ""


def mount_usb_by_identifier(identifier: str) -> str:
    """Ensure a USB partition is mounted. Returns the mountpoint, or '' on failure."""
    device_path, mount_path = _device_path_for_identifier(identifier)
    if not device_path:
        return ""
    if mount_path:
        return mount_path  # already mounted
    subprocess.run(
        ["pmount", device_path],
        check=False,
        capture_output=True,
        text=True,
    )
    _, new_mount = _device_path_for_identifier(identifier)
    return new_mount


def unmount_usb_by_identifier(identifier: str) -> bool:
    """Unmount a USB partition. Returns True when unmounted (or already was)."""
    device_path, mount_path = _device_path_for_identifier(identifier)
    if not device_path:
        return False
    if not mount_path:
        return True  # already unmounted
    result = subprocess.run(
        ["pumount", device_path],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def detect_usb_partitions() -> list[dict[str, str]]:
    """Return all USB disk partitions (mounted or not) discovered by lsblk.

    The Pi SD card (mmcblk*) is always excluded. No mounting is performed;
    use mount_usb_by_identifier() / unmount_usb_by_identifier() explicitly.
    """
    devices = _lsblk_devices()
    found: dict[str, dict[str, str]] = {}

    for disk in devices:
        if not _is_usb_disk(disk):
            continue
        for child in disk.get("children") or []:
            if child.get("type") != "part":
                continue
            device_path = (child.get("path") or "").strip()
            mount_path = (child.get("mountpoint") or "").strip()
            device_uuid = (child.get("uuid") or "").strip()
            # Use device path as fallback key so UUID-less partitions still appear.
            key = device_uuid or device_path
            if not key:
                continue
            found[key] = {
                "device_uuid": key,
                "label": _build_label(child),
                "mount_path": mount_path,
            }

    return sorted(found.values(), key=lambda item: item["label"].lower())
