import json
import subprocess


def _humanize_bytes(byte_count: int) -> str:
    size = float(byte_count)
    units = ["B", "KB", "MB", "GB", "TB"]
    index = 0
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    if index == 0:
        return f"{int(size)} {units[index]}"
    return f"{size:.1f} {units[index]}"


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
            "-b",
            "-o",
            "NAME,PATH,UUID,LABEL,MOUNTPOINT,RM,TRAN,TYPE,MODEL,VENDOR,HOTPLUG,SIZE",
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
        
    result = subprocess.run(
        ["udisksctl", "mount", "-b", device_path, "--no-user-interaction"],
        check=False,
        capture_output=True,
        text=True,
    )
    
    import re
    if result.returncode != 0:
        # Check if already mounted
        match = re.search(r"is already mounted at [`']([^']+)'", result.stderr)
        if match:
            return match.group(1).strip()
        return ""
        
    # Extract from stdout to avoid lsblk race condition
    match = re.search(r"Mounted .* at (.*)", result.stdout)
    if match:
        return match.group(1).strip()
        
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
        ["udisksctl", "unmount", "-b", device_path, "--no-user-interaction"],
        check=False,
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        return True
        
    if "is not mounted" in result.stderr:
        return True
        
    return False


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
        disk_vendor = (disk.get("vendor") or "").strip()
        disk_model = (disk.get("model") or "").strip()
        disk_identity = " ".join(part for part in [disk_vendor, disk_model] if part).strip()

        for child in disk.get("children") or []:
            if child.get("type") != "part":
                continue
            device_path = (child.get("path") or "").strip()
            mount_path = (child.get("mountpoint") or "").strip()
            device_uuid = (child.get("uuid") or "").strip()
            device_name = (child.get("name") or "").strip()
            size_bytes = int(child.get("size") or 0)
            # Use device path as fallback key so UUID-less partitions still appear.
            key = device_uuid or device_path
            if not key:
                continue

            fs_label = (child.get("label") or "").strip()
            if fs_label:
                display_name = f"{fs_label} ({device_name})" if device_name else fs_label
            elif disk_identity:
                display_name = f"{disk_identity} ({device_name})" if device_name else disk_identity
            else:
                display_name = _build_label(child)

            found[key] = {
                "device_uuid": key,
                "label": display_name,
                "display_name": display_name,
                "device_path": device_path,
                "mount_path": mount_path,
                "size_human": _humanize_bytes(size_bytes),
            }

    return sorted(found.values(), key=lambda item: item["label"].lower())
