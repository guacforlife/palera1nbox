import bakebit_128_64_oled as oled
from PIL import Image, ImageFont, ImageDraw
import time
import signal
import subprocess
import os
import sys

phases = [
    {"message": "Prepare enter DFU", "countdown": [3, 2, 1], "is_text": True},
    {"message": "Press", "countdown": [4, 3, 2, 1, 0]},
    {"message": "Release", "countdown": [8, 7, 6, 5, 4, 3, 2, 1]}
]


background_processes = []

# Initialisation
width, height = 128, 64
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
font18 = ImageFont.truetype('DejaVuSansMono.ttf', 18)
font14 = ImageFont.truetype('DejaVuSansMono.ttf', 14)
font10 = ImageFont.truetype('DejaVuSansMono.ttf', 10)

oled.init()
oled.setNormalDisplay()
oled.setHorizontalMode()

# Variables
current_menu = 'main'
cursor_position = 0
rootless_options = {'Verbose': True, 'Safe Mode': False, 'Force Revert': False, 'Debug': True}
rootfull_options = {'Create FakeFS': False, 'Create BindFS': False, 'Verbose': True, 'Safe Mode': False, 'Restore RootFS': False, 'Debug': True}

# Argument mappings
rootless_arg_map = {'Verbose': '--verbose-boot ', 'Safe Mode': '--safe-mode ', 'Force Revert': '--force-revert ', 'Debug': '--debug-logging '}
rootfull_arg_map = {'Create FakeFS': '--setup-fakefs ', 'Create BindFS': '--setup-partial-fakefs ', 'Verbose': '--verbose-boot ', 'Safe Mode': '--safe-mode ', 'Restore RootFS': '--force-revert ', 'Debug': '--debug-logging '}

# Menu options
menu_options = {
    'main': ['Rootless', 'Rootfull', 'Exit Recovery', 'Exit'],
    'rootless': ['Start', 'Options', 'Back'],
    'rootfull': ['Start', 'Options', 'Back'],
    'rootless_options': [],
    'rootfull_options': []
}

def display_prepare_dfu():
    words = ["Prepare to", "enter", "DFU mode"]
    y_offset = 1
    for word in words:
        _bbox = draw.textbbox((0, 0), word, font=font14)
        text_width = _bbox[2] - _bbox[0]
        text_height = _bbox[3] - _bbox[1]
        x = (width - text_width) // 2
        draw.text((x, y_offset), word, font=font10, fill=255)
        y_offset += text_height + 1


def update_checklist_options(menu, options):
    menu_options[menu] = [f"{'[*]' if options[key] else '[ ]'} {key}" for key in options.keys()] + ["Back"]

update_checklist_options('rootless_options', rootless_options)
update_checklist_options('rootfull_options', rootfull_options)

def display_menu_with_cursor(menu):
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    if current_menu in ['rootless', 'rootfull']:
        draw.text((0, 0), current_menu.upper(), font=font10, fill=255)
        font = font10
        item_height = 13
        y_offset = 13
    else:
        font = font14
        item_height = 15
        y_offset = 0

    start_index = max(0, cursor_position - 2)
    end_index = start_index + 4
    for i, line in enumerate(menu[start_index:end_index]):
        y_position = y_offset + i * item_height
        text_color = 255
        if i + start_index == cursor_position:
            draw.rectangle((0, y_position, width, y_position + item_height - 1), outline=255, fill=255)
            text_color = 0
        draw.text((0, y_position), line, font=font, fill=text_color)
    oled.drawImage(image)

def show_centered(text, subtitle=None):
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    _bbox = draw.textbbox((0, 0), text, font=font18)
    text_w, text_h = _bbox[2] - _bbox[0], _bbox[3] - _bbox[1]
    if subtitle:
        _sbbox = draw.textbbox((0, 0), subtitle, font=font10)
        sub_w, sub_h = _sbbox[2] - _sbbox[0], _sbbox[3] - _sbbox[1]
        y = (height - text_h - 4 - sub_h) / 2
        draw.text(((width - text_w) / 2, y), text, font=font14, fill=255)
        draw.text(((width - sub_w) / 2, y + text_h + 4), subtitle, font=font10, fill=255)
    else:
        draw.text(((width - text_w) / 2, (height - text_h) / 2), text, font=font14, fill=255)
    oled.drawImage(image)


def animation_connection(process, root_type):
    global current_menu, cursor_position

    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    draw.text((0, 0), "Entering Recovery \u231b", font=font10, fill=255)
    oled.drawImage(image)

    while True:
        result = subprocess.run(['sudo', '/usr/bin/irecovery', '-q'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if 'MODE: Recovery' in result.stdout:
            break
        time.sleep(1)

    dfu_detected = False
    for phase in phases:
        for second in phase["countdown"]:
            tick_start = time.monotonic()
            draw.rectangle((0, 0, width, height), outline=0, fill=0)
            anim_img = None

            if "is_text" in phase and phase["is_text"]:
                if phase["message"] == "Prepare enter DFU":
                    display_prepare_dfu()
                else:
                    draw.text((0, 0), phase["message"], font=font14, fill=255)
            elif "Press" in phase["message"]:
                anim_img = Image.open("/root/NanoHatOLED/BakeBit/Software/Python/powerandhome.png").convert('1')
            elif "Release" in phase["message"]:
                anim_img = Image.open("/root/NanoHatOLED/BakeBit/Software/Python/powerandhome2.png").convert('1')

            if anim_img:
                img_width, img_height = anim_img.size
                x_position = (width - img_width) // 2
                y_position = (height - img_height) // 2 - 10
                image.paste(anim_img, (x_position, y_position))

            draw.text((0, height - 20), f"Time: {second} sec", font=font18, fill=255)
            oled.drawImage(image)

            if not dfu_detected:
                try:
                    _r = subprocess.run(['sudo', '/usr/bin/irecovery', '-q'],
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, timeout=0.5)
                    if 'MODE: DFU' in _r.stdout:
                        dfu_detected = True
                except subprocess.TimeoutExpired:
                    pass

            time.sleep(max(0, 1.0 - (time.monotonic() - tick_start)))

    # Final check: DFU may have been entered during the last sleep window
    if not dfu_detected:
        for _ in range(3):
            try:
                _r = subprocess.run(['sudo', '/usr/bin/irecovery', '-q'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=0.5)
                if 'MODE: DFU' in _r.stdout:
                    dfu_detected = True
                    break
            except subprocess.TimeoutExpired:
                pass

    show_centered("JAILBREAKING")

    if not dfu_detected:
        process.terminate()
        show_centered("DFU FAILED", "Try again")
        time.sleep(3)
        current_menu = root_type
        cursor_position = 0
        display_menu_with_cursor(menu_options[current_menu])
        return

    for _ in range(20):
        exit_code = process.poll()
        if exit_code is not None:
            if exit_code != 0:
                show_centered("DFU FAILED", "Try again")
                time.sleep(3)
                current_menu = root_type
                cursor_position = 0
                display_menu_with_cursor(menu_options[current_menu])
                return
            break
        time.sleep(1)

    show_centered("BOOTING")
    time.sleep(20)

    current_menu = root_type
    cursor_position = 0
    display_menu_with_cursor(menu_options[current_menu])

def execute_command(root_type, options):
    global background_processes
    # Kill any stale palera1n before retrying (e.g. after a failed DFU)
    background_processes = [p for p in background_processes if p.poll() is None]
    for p in background_processes:
        p.terminate()
    background_processes = []
    cmd = ['sudo', '/root/NanoHatOLED/BakeBit/Software/Python/palera1n']
    args_map = rootless_arg_map if root_type == 'rootless' else rootfull_arg_map

    for option, is_checked in options.items():
        if is_checked:
            cmd += args_map[option].strip().split()

    if root_type == 'rootfull':
        cmd.append('--fakefs')
    else:
        cmd.append('-l')

    print("Command:", ' '.join(cmd))

    # palera1n v2.2.1 prompts "Press Enter when ready" — send it automatically
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    process.stdin.write(b"\n")
    process.stdin.flush()
    background_processes.append(process)

    animation_connection(process, root_type)

def receive_signal(signum, stack):
    global current_menu, cursor_position, rootless_options, rootfull_options
    if signum == signal.SIGUSR1:  # Button 1: scroll up
        cursor_position = (cursor_position - 1) % len(menu_options[current_menu])
    elif signum == signal.SIGUSR2:  # Button 2: scroll down
        cursor_position = (cursor_position + 1) % len(menu_options[current_menu])
    elif signum == signal.SIGALRM:  # Button 3: select
        if current_menu == 'main':
            if cursor_position == 0:
                current_menu = 'rootless'
                cursor_position = 0
            elif cursor_position == 1:
                current_menu = 'rootfull'
                cursor_position = 0
            elif cursor_position == 2:
                subprocess.run(['sudo', '/root/NanoHatOLED/BakeBit/Software/Python/palera1n', '--exit-recovery'])
                for process in background_processes:
                    process.terminate()
                subprocess.Popen('sudo pkill -f palera1n', shell=True, preexec_fn=os.setsid)
            elif cursor_position == 3:
                for process in background_processes:
                    process.terminate()
                os.execv(sys.executable, [sys.executable, '/root/NanoHatOLED/BakeBit/Software/Python/menu.py'])
        elif current_menu in ['rootless', 'rootfull']:
            if cursor_position == 0:  # Start
                execute_command(current_menu, rootless_options if current_menu == 'rootless' else rootfull_options)
            elif cursor_position == 1:  # Options
                current_menu = f"{current_menu}_options"
                cursor_position = 0
            elif cursor_position == 2:  # Back
                current_menu = 'main'
                cursor_position = 0
        elif current_menu.endswith('_options'):
            root_type = current_menu.split('_')[0]
            option_keys = list(rootless_options.keys() if root_type == 'rootless' else rootfull_options.keys())
            if cursor_position == len(option_keys):
                current_menu = root_type
                cursor_position = 0
            else:
                selected_option = option_keys[cursor_position]
                if root_type == 'rootless':
                    rootless_options[selected_option] = not rootless_options[selected_option]
                else:
                    rootfull_options[selected_option] = not rootfull_options[selected_option]
                update_checklist_options(current_menu, rootless_options if root_type == 'rootless' else rootfull_options)
    display_menu_with_cursor(menu_options[current_menu])

def main():
    signal.signal(signal.SIGUSR1, receive_signal)
    signal.signal(signal.SIGUSR2, receive_signal)
    signal.signal(signal.SIGALRM, receive_signal)

    display_menu_with_cursor(menu_options[current_menu])

    while True:
        time.sleep(0.2)

if __name__ == "__main__":
    main()
