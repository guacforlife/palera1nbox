# palera1nbox — NanoPi Neo2 Black

> A standalone, pocket-sized jailbreak station powered by a NanoPi Neo2 Black SBC, a NanoHat OLED display, and [palera1n v2.2.1](https://github.com/palera1n/palera1n). No laptop required — just plug in your iPhone or iPad and navigate with three hardware buttons.

This branch (`nanopi-neo2-black`) documents full support for the **NanoPi Neo2 Black** running **Armbian Noble** (Ubuntu 24.04 LTS). It includes a fully automated two-phase installer, compatibility patches for Pillow 10+ and palera1n v2.2.1, and fixes for several bugs present in the original release.

---

## Contents

- [What it does](#what-it-does)
- [Hardware](#hardware)
- [Supported iOS devices](#supported-ios-devices)
- [Quick start](#quick-start)
- [Manual install](#manual-install)
- [Using the OLED menu](#using-the-oled-menu)
- [Jailbreak options](#jailbreak-options)
- [Troubleshooting](#troubleshooting)
- [Changes from upstream](#changes-from-upstream)
- [Project layout](#project-layout)

---

## What it does

palera1nbox turns a cheap ARM SBC into a self-contained jailbreak tool:

- Three physical buttons navigate a menu on a 128×64 OLED screen
- Select Rootless or Rootfull, configure options, press Start
- The device guides you through DFU entry with a countdown and button diagrams
- palera1n runs in the background; the OLED shows progress

No PC, no macOS, no USB hub juggling — just the box and your device.

---

## Hardware

| Component | Requirement |
|-----------|-------------|
| SBC | **NanoPi Neo2 Black** (Allwinner H5, aarch64) |
| OS | **Armbian Noble** (Ubuntu 24.04 LTS) — CLI image |
| Display | **NanoHat OLED** (SSD1306, 128×64, I2C) |
| USB | Device connects directly to the Neo2 Black USB-A port |
| Power | 5V/2A via USB-C or barrel jack |
| Storage | MicroSD ≥ 8 GB (Class 10 / A1) |
| Optional | Edimax EW-7811Un USB WiFi adapter for wireless SSH access |

> **NanoPi Neo 1 / Neo2 (non-Black)**: The original palera1nbox was designed for the Neo 1. The Neo2 Black uses the same H5 SoC and the same Armbian images, so this branch applies equally. The automated install script has been tested only on the Neo2 Black with Armbian Noble.

### Flashing Armbian

1. Download the **Armbian Noble CLI** image for NanoPi Neo2 Black from [armbian.com](https://www.armbian.com/nanopi-neo2-black/).
2. Flash to microSD with [Balena Etcher](https://etcher.balena.io/) or `dd`.
3. Insert SD, connect Ethernet, power on.
4. First boot: SSH in as `root` (default password `1234`), set a new password when prompted.

---

## Supported iOS devices

palera1nbox uses the **checkm8** bootrom exploit via palera1n. This exploit is hardware-permanent — it cannot be patched by Apple software updates.

| Chip | Devices |
|------|---------|
| A7 (CPID:8960) | iPhone 5s, iPad Air, iPad mini 2, iPad mini 3 |
| A8 (CPID:7000/7001) | iPhone 6/6 Plus, iPad mini 4, iPod touch 6th gen |
| A9 (CPID:8000/8003) | iPhone 6s/6s Plus, iPhone SE (1st gen), iPad (5th gen), iPod touch 7th gen |
| A10 (CPID:8010) | iPhone 7/7 Plus, iPad (6th gen), iPad (7th gen), iPod touch 7th gen |
| A11 (CPID:8015) | iPhone 8/8 Plus, iPhone X |

> A11 (iPhone 8/X) supports **rootless only**. The passcode must be disabled before jailbreaking.

**Not supported**: A12 and later (iPhone XS, XR, 11, 12, …).

---

## Quick start

On a fresh Armbian Noble install, run as `root`:

```bash
curl -L https://raw.githubusercontent.com/guacforlife/palera1nbox/nanopi-neo2-black/install.sh \
    -o /root/install.sh
chmod +x /root/install.sh
/root/install.sh
```

The script runs in two phases separated by an automatic reboot:

- **Phase 1** (~5 min): installs packages, enables I2C + audio hardware overlays, schedules phase 2 as a systemd one-shot service, then reboots.
- **Phase 2** (~15 min, runs automatically after reboot): builds libplist, libimobiledevice-glue, and libirecovery from source; downloads and deploys the palera1nbox project files; downloads palera1n v2.2.1; blacklists the `apple-mfi-fastcharge` kernel module; applies Python compatibility patches; runs the NanoHatOLED installer (which triggers a final reboot).

After the final reboot the OLED display shows an animation and then the main menu. The box is ready.

---

## Manual install

If you prefer to understand each step or need to debug a failed install:

### Phase 1 — packages and overlays

```bash
apt-get update && apt-get upgrade -y

# Core system packages
apt-get install -y i2c-tools git vim armbian-config unzip \
    python3-dev python3-pil python3-smbus python3-pip python3-serial libjpeg-dev

# palera1n runtime libraries
apt-get install -y \
    libc6 libncurses6 libpango-1.0-0 libpangocairo-1.0-0 libpangoft2-1.0-0 \
    libatk1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 libfontconfig1 libfreetype6 \
    libgtk-3-0 libusb-1.0-0 usbmuxd libimobiledevice-utils ifuse \
    libusbmuxd-tools mplayer

# Build tools
apt-get install -y \
    pkg-config libplist-dev libreadline-dev libusb-1.0-0-dev \
    build-essential checkinstall autoconf automake libtool-bin
```

Enable hardware overlays. Edit `/boot/armbianEnv.txt` and add or extend the `overlays=` line:

```
overlays=i2c0 analog-codec
```

Then reboot.

### Phase 2 — build from source and deploy

```bash
# Python libraries (Pillow must be reinstalled after luma.oled to get a clean build)
pip3 install --break-system-packages --upgrade setuptools sh psutil luma.oled
pip3 uninstall --break-system-packages -y pillow
pip3 install --break-system-packages pillow

# Export PKG_CONFIG_PATH so all three libs find each other
export PKG_CONFIG_PATH="/usr/local/lib/pkgconfig"
```

Build and install the libimobiledevice stack from source (system packages are too old):

```bash
# libplist
cd /tmp && git clone --depth=1 https://github.com/libimobiledevice/libplist.git
cd libplist && ./autogen.sh && ./configure --prefix=/usr/local && make -j$(nproc)
make install && ldconfig

# libimobiledevice-glue
cd /tmp && git clone --depth=1 https://github.com/libimobiledevice/libimobiledevice-glue.git
cd libimobiledevice-glue && ./autogen.sh && ./configure --prefix=/usr/local && make -j$(nproc)
make install && ldconfig

# libirecovery (needs explicit rpath so it finds /usr/local/lib at runtime)
cd /tmp && git clone --depth=1 https://github.com/libimobiledevice/libirecovery.git
cd libirecovery && ./autogen.sh \
    && ./configure --prefix=/usr/local \
         LDFLAGS="-L/usr/local/lib -Wl,-rpath,/usr/local/lib" \
         CPPFLAGS="-I/usr/local/include" \
    && make -j$(nproc)
make install && ldconfig
```

Deploy palera1nbox project files:

```bash
DEPLOY_DIR="/root/NanoHatOLED/BakeBit/Software/Python"
cd /root && git clone --depth=1 https://github.com/friendlyarm/NanoHatOLED.git

mkdir -p "$DEPLOY_DIR" && cd "$DEPLOY_DIR"
curl -L -o palera1nBoxV2.zip \
    "https://github.com/s00r1/palera1nbox/releases/download/v2.0.0/palera1nBoxV2.zip"
unzip -o palera1nBoxV2.zip && rm palera1nBoxV2.zip

# palera1n v2.2.1 arm64
curl -L -o "$DEPLOY_DIR/palera1n" \
    "https://github.com/palera1n/palera1n/releases/download/v2.2.1/palera1n-linux-arm64"
chmod +x "$DEPLOY_DIR/palera1n"
```

Blacklist apple-mfi-fastcharge:

```bash
echo "blacklist apple-mfi-fastcharge" > /etc/modprobe.d/no-apple-mfi.conf
rmmod apple-mfi-fastcharge 2>/dev/null || true
```

Replace `s00r1_palera1n.py` with the patched version from this branch, then create a symlink and run the NanoHatOLED installer (this triggers an automatic reboot):

```bash
curl -L -o "$DEPLOY_DIR/s00r1_palera1n.py" \
    "https://raw.githubusercontent.com/guacforlife/palera1nbox/nanopi-neo2-black/BakeBit/Software/Python/s00r1_palera1n.py"

ln -sf /usr/local/bin/irecovery /usr/bin/irecovery
cd /root/NanoHatOLED && ./install.sh
```

---

## Using the OLED menu

The NanoHat OLED has **three buttons** on the left side of the board (looking at it from the top):

| Button | Action |
|--------|--------|
| K1 (top) | Scroll up |
| K2 (middle) | Scroll down |
| K3 (bottom) | Select / confirm |

### Menu structure

```
Main menu
├── Rootless       → jailbreak without modifying the root filesystem (recommended)
│   ├── Start      → begin jailbreak
│   ├── Options    → configure flags (see below)
│   └── Back
├── Rootfull       → jailbreak with persistent root filesystem modifications
│   ├── Start
│   ├── Options
│   └── Back
├── Exit Recovery  → send "exit recovery" command to a device stuck in recovery mode
└── Exit           → return to main NanoHatOLED menu
```

### Jailbreak flow

1. Navigate to **Rootless → Start** (or Rootfull → Start).
2. The screen shows "Enter Recovery" — plug in your iOS device. The box polls `irecovery -q` until it sees the device in Recovery mode.
3. Once in Recovery, the countdown begins:
   - "Prepare to enter DFU mode" (3 s)
   - Press and hold Power + Home (or Power + Volume Down on devices without a Home button) — 4 s countdown
   - Release Power, keep holding Home/Volume Down — 8 s countdown
4. The device enters DFU mode. palera1n takes over automatically.
5. Screen shows "JAILBREAKING" (~20 s), then "BOOTING" (~20 s).
6. The menu returns to the main screen when done.

> **Tip**: If DFU entry fails the first time, the device typically lands back in Recovery mode. Press Start again — the box will wait for the device and retry.

---

## Jailbreak options

Options are toggled per-mode (rootless/rootfull) and persist until changed.

### Rootless options

| Option | Flag | Default | Notes |
|--------|------|---------|-------|
| Verbose | `--verbose-boot` | on | Shows boot log instead of Apple logo |
| Safe Mode | `--safe-mode` | off | Boots with tweaks disabled |
| Force Revert | `--force-revert` | off | Removes jailbreak on next boot |
| Debug | `--debug-logging` | on | Extra diagnostic output |

### Rootfull options

| Option | Flag | Default | Notes |
|--------|------|---------|-------|
| Create FakeFS | `--setup-fakefs` | off | Creates the rootfull fake filesystem (run once) |
| Create BindFS | `--setup-partial-fakefs` | off | Lighter alternative to full FakeFS |
| Verbose | `--verbose-boot` | on | |
| Safe Mode | `--safe-mode` | off | |
| Restore RootFS | `--force-revert` | off | Removes jailbreak and fake filesystem |
| Debug | `--debug-logging` | on | |

> **First time rootfull**: enable **Create FakeFS**, run once, wait for reboot. On subsequent jailbreaks disable it — or you will recreate the filesystem every time.

---

## Troubleshooting

### Device not detected / palera1n hangs at "Enter Recovery"

- Ensure the device is not powered off — it should show a screen (normal boot, recovery pineapple, or charging screen).
- If the device is in a boot loop: hold Power + Home/Volume-Down for 10 s to force-off, then plug in while the screen is dark.
- Check `dmesg | tail -20` over SSH for USB detection messages.

### DFU entry fails every time

This is the most common issue. On iPad 7th gen (A10) and similar:

1. At the "Press Power + Home" prompt, press both buttons simultaneously and hold for the full 4-second countdown.
2. When the screen changes to "Release Power", release Power immediately but **keep holding Home**.
3. If the screen goes dark and then shows the Apple logo — too slow on the Power release. Try again.
4. If the device disconnects entirely and the OLED returns to the menu — successful DFU. palera1n will continue automatically.

### Device resets / disconnects with error `-110 ETIMEDOUT`

The `apple-mfi-fastcharge` kernel module races checkm8 for ownership of the USB device and wins, causing USB transfer timeouts. The install script blacklists it, but if the module loaded before the blacklist took effect:

```bash
rmmod apple-mfi-fastcharge
# Then retry the jailbreak
```

To make permanent (already done by install script):

```bash
echo "blacklist apple-mfi-fastcharge" > /etc/modprobe.d/no-apple-mfi.conf
```

### "Please specify rootful (-f) or rootless (-l)"

You have an old build of palera1n. palera1n v2.2.1 requires the mode flag. The install script downloads v2.2.1 automatically. If running manually:

```bash
curl -L -o /root/NanoHatOLED/BakeBit/Software/Python/palera1n \
    "https://github.com/palera1n/palera1n/releases/download/v2.2.1/palera1n-linux-arm64"
chmod +x /root/NanoHatOLED/BakeBit/Software/Python/palera1n
```

### OLED shows animation then goes blank / NanoPi reboots itself

The Sunxi hardware watchdog has a 16-second timeout. If the Python menu script crashes, the watchdog fires and resets the board. Root causes:

- **Pillow `textsize` error**: `AttributeError: 'ImageDraw' object has no attribute 'textsize'` — Pillow 10+ removed this method. The patched `s00r1_palera1n.py` in this branch uses `textbbox()` instead.
- **palera1n stuck on stdin prompt**: v2.2.1 prints "Press Enter when ready for DFU mode" and waits. The patch sends `\n` automatically via `process.stdin.write(b"\n")`.

To check what happened after a crash:

```bash
journalctl -u NanoHatOLED --since "5 minutes ago"
```

### Buttons don't respond after restarting the script manually

The NanoHatOLED daemon sends signals (SIGUSR1, SIGUSR2, SIGALRM) to its child process. If you start `s00r1_palera1n.py` manually in a separate SSH session, it is not a child of the daemon and receives no signals.

Always restart via the daemon:

```bash
pkill -9 -f NanoHatOLED
cd /root/NanoHatOLED && nohup ./NanoHatOLED > /tmp/oled.log 2>&1 &
```

### libirecovery / irecovery not found or wrong version

The system `apt` package is too old. The install script builds from source into `/usr/local`. If `irecovery` resolves to the wrong binary:

```bash
ln -sf /usr/local/bin/irecovery /usr/bin/irecovery
ldconfig
irecovery --version
```

### USB WiFi adapter not recognised

The Edimax EW-7811Un (rtl8192cu) works out of the box on Armbian Noble. After plugging in:

```bash
armbian-config   # → Network → WiFi
```

DHCP-reserve the adapter's MAC address on your router so the IP stays consistent, then add an SSH alias:

```
Host nanopi
    Hostname 10.0.0.X
    User root
    IdentityFile ~/.ssh/id_rsa
```

---

## Changes from upstream

This branch applies the following changes to the original s00r1/palera1nbox:

### `BakeBit/Software/Python/s00r1_palera1n.py`

| # | Change | Reason |
|---|--------|--------|
| 1 | `draw.textsize()` → `draw.textbbox()` everywhere | Pillow 10+ removed `textsize`; crashes on current Armbian Noble |
| 2 | Menu order changed to `['Start', 'Options', 'Back']` | Original had `['Options', 'Start', 'Back']`; Start is the primary action |
| 3 | Signal handler updated to match new menu positions | Handler still used old indices after menu reorder, causing wrong actions on button press |
| 4 | `cmd.append('-l')` for rootless | palera1n v2.2.1 requires explicit `-l`/`--fakefs` flag; old implicit rootless mode removed |
| 5 | Fork-bomb guard in `execute_command()` | Pressing Start multiple times spawned multiple palera1n processes; each fought for the USB device |
| 6 | `subprocess.Popen(stdin=PIPE)` + `stdin.write(b"\n")` | palera1n v2.2.1 prompts "Press Enter when ready for DFU mode"; without this the process hangs silently |

### `install.sh`

Replaces the original `install_palera1nbox.sh` with a fully automated two-phase installer:

- Automated two-phase install with a systemd one-shot service bridge across the reboot
- Installs `unzip` (needed to extract the release archive, missing from original)
- Enables both `i2c0` **and** `analog-codec` overlays automatically (original script required manual armbian-config)
- Builds libplist, libimobiledevice-glue, libirecovery from source with `--prefix=/usr/local` and correct `PKG_CONFIG_PATH` so all three libraries find each other
- Sets `LDFLAGS` and `CPPFLAGS` for libirecovery so it finds `/usr/local/lib` at both link time and runtime via `-Wl,-rpath`
- Downloads palera1n **v2.2.1** arm64 (original bundled old `palera1n-c`)
- Blacklists `apple-mfi-fastcharge` kernel module
- Applies all Python patches listed above
- Runs `NanoHatOLED/install.sh` **last** — it triggers an automatic reboot; in the original it ran mid-script, preventing all subsequent steps from executing
- Reinstalls Pillow after `luma.oled` to ensure a clean build against the system libjpeg

---

## Project layout

```
palera1nbox/
├── BakeBit/
│   └── Software/
│       └── Python/
│           └── s00r1_palera1n.py    # patched menu script (this branch)
├── install.sh                        # two-phase automated installer (this branch)
├── install_palera1nbox.sh            # original upstream install script
├── index.html                        # original website
└── README.md                         # this file
```

The main project files (images, fonts, `palera1n` binary, `menu.py`, etc.) are downloaded from the [v2.0.0 release archive](https://github.com/s00r1/palera1nbox/releases/tag/v2.0.0) during install and are not stored in this repository.

---

## Disclaimer

This project is provided for educational purposes only. Jailbreaking may void your device warranty and could violate applicable laws in your jurisdiction. You assume all responsibility for using this software.

## License

This project is licensed under the [MIT License](LICENSE).

---

## Credits

- [s00r1/palera1nbox](https://github.com/s00r1/palera1nbox) — original project
- [palera1n/palera1n](https://github.com/palera1n/palera1n) — jailbreak tool
- [libimobiledevice](https://github.com/libimobiledevice) — USB communication stack
- [FriendlyElec / NanoHatOLED](https://github.com/friendlyarm/NanoHatOLED) — OLED display driver and button handling
