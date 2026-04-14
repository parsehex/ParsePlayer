#!/bin/bash
# setup_safe_usb.sh - Configure robust FAT32 mounting for Laptop and Pi

# 1. Set udisks2 defaults to use 'flush' and 'noatime'
echo "Configuring udisks2 defaults..."
echo -e "[defaults]\nvfat_defaults=uid=\$UID,gid=\$GID,shortname=mixed,utf8=1,showexec,flush,noatime" | sudo tee /etc/udisks2/mount_options.conf

# 2. Create the auto-repair service (clears the dirty bit on plug-in)
echo "Creating fsck repair service..."
sudo tee /etc/systemd/system/usb-fsck@.service <<'SERVICE'
[Unit]
Description=fsck USB drive partition %I
After=systemd-udevd.service

[Service]
Type=oneshot
ExecStart=/bin/sh -c '/usr/sbin/fsck.vfat -a /dev/%I'
RemainAfterExit=no
SERVICE

# 3. Create the udev rule to trigger the repair
echo "Creating udev rule..."
sudo tee /etc/udev/rules.d/99-fat32-repair.rules <<'RULE'
ACTION=="add", SUBSYSTEM=="block", KERNEL=="sd[a-z][0-9]", ENV{ID_FS_TYPE}=="vfat", ENV{SYSTEMD_WANTS}+="usb-fsck@%k.service"
RULE

# 4. (For Pi) Install and configure udiskie automounter
if [[ -f /etc/os-release ]] && grep -q "Raspberry Pi" /etc/os-release; then
    echo "Raspberry Pi detected. Installing udiskie..."
    sudo apt update && sudo apt install -y udiskie
    sudo tee /etc/systemd/system/udiskie.service <<'SERVICE'
[Unit]
Description=udiskie automounter
After=network.target

[Service]
ExecStart=/usr/bin/udiskie --no-notify --no-tray
Restart=always
User=user

[Install]
WantedBy=multi-user.target
SERVICE
    sudo systemctl enable --now udiskie.service
fi

# 5. Reload settings
echo "Reloading system settings..."
sudo udevadm control --reload-rules && sudo udevadm trigger
sudo systemctl daemon-reload

echo "Done! FAT32 drives are now handled safely."
