#!/usr/bin/env bash
# palera1nbox installer for NanoPi Neo2 Black / Armbian Noble
# Run as root. Will reboot once after phase 1, then auto-continue phase 2.
set -euo pipefail

PHASE_FILE="/root/.palera1nbox_phase"
PHASE=${1:-$(cat "$PHASE_FILE" 2>/dev/null || echo 1)}

log() { echo "[$(date +%H:%M:%S)] $*"; }

# ── Phase 1: system update, packages, hardware overlays, reboot ───────────────
if [[ "$PHASE" == "1" ]]; then
    log "=== Phase 1: packages + hardware overlays ==="

    log "Updating package lists..."
    apt-get update -q

    log "Upgrading existing packages..."
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y -q

    log "Installing core dependencies..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
        i2c-tools git vim armbian-config unzip \
        python3-dev python3-pil python3-smbus python3-pip python3-serial \
        libjpeg-dev

    log "Installing palera1n runtime dependencies..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
        libc6 libncurses6 libpango-1.0-0 libpangocairo-1.0-0 \
        libpangoft2-1.0-0 libatk1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 \
        libfontconfig1 libfreetype6 libgtk-3-0 libusb-1.0-0 \
        usbmuxd libimobiledevice-utils ifuse libusbmuxd-tools \
        mplayer

    log "Installing build tools..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
        pkg-config libplist-dev libreadline-dev libusb-1.0-0-dev \
        build-essential checkinstall autoconf automake libtool-bin

    log "Enabling i2c0 + analog-codec hardware overlays..."
    for OVERLAY in i2c0 analog-codec; do
        if ! grep -q "$OVERLAY" /boot/armbianEnv.txt 2>/dev/null; then
            if grep -q "^overlays=" /boot/armbianEnv.txt 2>/dev/null; then
                sed -i "s/^overlays=.*/& $OVERLAY/" /boot/armbianEnv.txt
            else
                echo "overlays=$OVERLAY" >> /boot/armbianEnv.txt
            fi
        fi
    done

    log "Phase 1 complete. Scheduling phase 2 on next boot..."
    echo "2" > "$PHASE_FILE"

    # Install self as a one-shot systemd service to continue after reboot
    cat > /etc/systemd/system/palera1nbox-install.service << 'EOF'
[Unit]
Description=palera1nbox installer phase 2
After=network-online.target
Wants=network-online.target
ConditionPathExists=/root/.palera1nbox_phase

[Service]
Type=oneshot
ExecStart=/root/palera1nbox-install.sh 2
RemainAfterExit=yes
StandardOutput=journal+console

[Install]
WantedBy=multi-user.target
EOF
    systemctl enable palera1nbox-install.service

    log "Rebooting in 5 seconds..."
    sleep 5
    reboot
fi

# ── Phase 2: build from source, clone repos, deploy project files ─────────────
if [[ "$PHASE" == "2" ]]; then
    log "=== Phase 2: build from source + deploy ==="

    # Disable the one-shot service so it doesn't run again
    systemctl disable palera1nbox-install.service 2>/dev/null || true
    rm -f /etc/systemd/system/palera1nbox-install.service

    log "Installing Python libraries..."
    pip3 install --break-system-packages --upgrade setuptools sh psutil luma.oled
    pip3 uninstall --break-system-packages -y pillow 2>/dev/null || true
    pip3 install --break-system-packages pillow

    # Prioritise /usr/local over system apt versions so all three libs
    # find each other rather than the older system packages
    export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

    log "Building libplist from source..."
    cd /tmp && rm -rf libplist
    git clone --depth=1 https://github.com/libimobiledevice/libplist.git
    cd libplist && ./autogen.sh && ./configure --prefix=/usr/local && make -j$(nproc)
    make install && ldconfig
    cd /tmp && rm -rf libplist

    log "Building libimobiledevice-glue from source..."
    cd /tmp && rm -rf libimobiledevice-glue
    git clone --depth=1 https://github.com/libimobiledevice/libimobiledevice-glue.git
    cd libimobiledevice-glue && ./autogen.sh && ./configure --prefix=/usr/local && make -j$(nproc)
    make install && ldconfig
    cd /tmp && rm -rf libimobiledevice-glue

    log "Building libirecovery from source..."
    cd /tmp && rm -rf libirecovery
    git clone --depth=1 https://github.com/libimobiledevice/libirecovery.git
    cd libirecovery && ./autogen.sh \
      && ./configure --prefix=/usr/local \
           LDFLAGS="-L/usr/local/lib -Wl,-rpath,/usr/local/lib" \
           CPPFLAGS="-I/usr/local/include" \
      && make -j$(nproc)
    make install && ldconfig
    cd /tmp && rm -rf libirecovery

    log "Cloning NanoHatOLED..."
    cd /root
    git clone --depth=1 https://github.com/friendlyarm/NanoHatOLED.git

    log "Downloading palera1nbox v2.0.0 project files..."
    DEPLOY_DIR="/root/NanoHatOLED/BakeBit/Software/Python"
    mkdir -p "$DEPLOY_DIR"
    cd "$DEPLOY_DIR"
    curl -L -o palera1nBoxV2.zip \
        "https://github.com/s00r1/palera1nbox/releases/download/v2.0.0/palera1nBoxV2.zip"
    unzip -o palera1nBoxV2.zip
    rm palera1nBoxV2.zip

    log "Upgrading palera1n to v2.2.1 (arm64)..."
    curl -L -o "$DEPLOY_DIR/palera1n" \
        "https://github.com/palera1n/palera1n/releases/download/v2.2.1/palera1n-linux-arm64"

    log "Blacklisting apple-mfi-fastcharge (interferes with checkm8)..."
    echo "blacklist apple-mfi-fastcharge" > /etc/modprobe.d/no-apple-mfi.conf
    rmmod apple-mfi-fastcharge 2>/dev/null || true

    log "Patching s00r1_palera1n.py for palera1n v2.2.1 compatibility..."
    SCRIPT="$DEPLOY_DIR/s00r1_palera1n.py"
    # Fix 1: textsize removed in Pillow 10+ -> use textbbox
    perl -i -pe "s/text_width, text_height = draw\\.textsize\\((\\w+), font=(\\w+)\\)/\$bbox = draw.textbbox((0, 0), \$1, font=\$2); \$text_width = \$bbox[2] - \$bbox[0]; \$text_height = \$bbox[3] - \$bbox[1]/g" "$SCRIPT"
    # Fix 2: reorder rootless/rootfull menu (Start before Options)
    sed -i "s/'rootless': \['Options', 'Start', 'Back'\]/'rootless': ['Start', 'Options', 'Back']/" "$SCRIPT"
    sed -i "s/'rootfull': \['Options', 'Start', 'Back'\]/'rootfull': ['Start', 'Options', 'Back']/" "$SCRIPT"
    # Fix 3: v2.2.1 requires explicit -l (rootless) flag
    sed -i "s/        cmd.append('--fakefs')/        cmd.append('--fakefs')\n    else:\n        cmd.append('-l')/" "$SCRIPT"
    # Fix 4: fork-bomb guard - don't spawn if palera1n already running
    perl -i -0pe "s/def execute_command\\(root_type, options\\):\n    cmd/def execute_command(root_type, options):\n    global background_processes\n    background_processes = [p for p in background_processes if p.poll() is None]\n    if background_processes:\n        return\n    cmd/" "$SCRIPT"
    # Fix 5: send Enter to palera1n stdin (v2.2.1 prompts for it)
    sed -i "s/process = subprocess.Popen(cmd)/process = subprocess.Popen(cmd, stdin=subprocess.PIPE)/" "$SCRIPT"
    sed -i "/process = subprocess.Popen(cmd, stdin=subprocess.PIPE)/a\\    process.stdin.write(b'\\\\n'); process.stdin.flush()" "$SCRIPT"

    log "Setting permissions..."
    chmod +x "$DEPLOY_DIR/palera1n" 2>/dev/null || true
    chmod +x "$DEPLOY_DIR/checkra1n" 2>/dev/null || true
    ln -sf /usr/local/bin/irecovery /usr/bin/irecovery 2>/dev/null || true

    echo "done" > "$PHASE_FILE"

    # NanoHatOLED install.sh triggers an automatic reboot — run it last
    log "Running NanoHatOLED install (will reboot automatically)..."
    cd /root/NanoHatOLED
    ./install.sh
fi
