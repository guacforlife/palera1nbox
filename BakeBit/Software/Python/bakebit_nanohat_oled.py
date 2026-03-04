from luma.core.interface.serial import i2c
from luma.core.render import canvas
from luma.oled.device import ssd1306
from PIL import ImageFont, ImageDraw
from random import randint
import time
import os
import sys
import subprocess

serial = i2c(port=0, address=0x3C)
device = ssd1306(serial)

def draw_drop(draw, x, y):
    draw.ellipse((x, y, x+6, y+12), outline="white", fill="white")

def draw_text(draw, text, x, y, size=20):
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
    draw.text((x, y), text, font=font, fill="white")

def animate(device):
    sound_process = subprocess.Popen(["aplay", "/root/NanoHatOLED/BakeBit/Software/Python/pacman_beginning.wav"])
    y_shifts = [randint(0, device.height // 4) for _ in range(8)]
    word = "s00r1.gg"
    middle_y = device.height // 2 - 6
    pacman_x = 0
    mouth_open = True
    eaten_dashes = []
    snowflakes = [(randint(0, device.width), randint(0, middle_y - 10)) for _ in range(20)]
    show_snow = False

    while True:
        with canvas(device) as draw:
            for i in range(8):
                x = device.width // 2 - 40 + i * 12
                if y_shifts[i] >= middle_y:
                    draw_text(draw, word[i], x - 3, middle_y, size=20)
                else:
                    draw_drop(draw, x, y_shifts[i])
                y_shifts[i] += 5

            if all(y >= middle_y for y in y_shifts):
                show_snow = True

            if show_snow:
                new_snowflakes = []
                for x, y in snowflakes:
                    if randint(0, 1):
                        draw.ellipse((x, y, x+2, y+2), outline="white", fill="white")
                    if y < middle_y and randint(0, 1):
                        y += 1
                    new_snowflakes.append((x, y if y < middle_y else randint(0, middle_y - 10)))
                snowflakes = new_snowflakes

            for dash_x in range(0, device.width, 20):
                if dash_x not in eaten_dashes:
                    if dash_x < pacman_x + 10 and dash_x > pacman_x - 10:
                        eaten_dashes.append(dash_x)
                    else:
                        draw_text(draw, "-", dash_x, device.height - 15, size=15)

            if mouth_open:
                draw.pieslice((pacman_x, device.height - 15, pacman_x+10, device.height - 5), start=30, end=330, fill="white")
            else:
                draw.ellipse((pacman_x, device.height - 15, pacman_x+10, device.height - 5), outline="white", fill="white")

            pacman_x += 10
            if pacman_x > device.width:
                break

            mouth_open = not mouth_open

        time.sleep(0.1)
    sound_process.terminate()
    device.cleanup()
    os.system("python3 /root/NanoHatOLED/BakeBit/Software/Python/menu.py")

device.cleanup()
# Use Popen (non-blocking) so bakebit exits immediately and doesn't stay as a
# live python3 process — NanoHatOLED signals all python3.12 procs, so a
# long-lived bakebit would absorb signals and break button handling.
subprocess.Popen([sys.executable, '/root/NanoHatOLED/BakeBit/Software/Python/menu.py'])
