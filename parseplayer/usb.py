import json
import subprocess


def _build_label(device: dict) -> str:
    for key in ("label", "model", "vendor", "name", "path"):
        value = (device.get(key) or "").strip()
        if value:
            return value
    return "Unnamed USB"


def detect_usb_partitions() -> list[dict[str, str]]:
    """Return mounted USB-like partitions discovered by lsblk.

    We prioritize partitions that are removable, hotplugged, or transport=usb.
    """
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

    payload = json.loads(result.stdout or "{}")
    devices: list[dict] = payload.get("blockdevices", [])
    found: dict[str, dict[str, str]] = {}

    def walk(node: dict, inherited_usb: bool = False) -> None:
        is_usb_like = inherited_usb or node.get("tran") == "usb" or int(node.get("hotplug") or 0) == 1
        children = node.get("children") or []

        if node.get("type") == "part":
            is_removable = int(node.get("rm") or 0) == 1
            mount_path = (node.get("mountpoint") or "").strip()
            device_uuid = (node.get("uuid") or "").strip()
            if device_uuid and mount_path and (is_usb_like or is_removable):
                found[device_uuid] = {
                    "device_uuid": device_uuid,
                    "label": _build_label(node),
                    "mount_path": mount_path,
                }

        for child in children:
            walk(child, inherited_usb=is_usb_like)

    for device in devices:
        walk(device)

    return sorted(found.values(), key=lambda item: item["label"].lower())
