import bakebit_128_64_oled as oled
from PIL import Image, ImageFont, ImageDraw
import time
import signal
import os
import sys
import subprocess

# Définition des dimensions de l'écran
width = 128
height = 64

# Initialise un nouveau groupe de processus
os.setpgrp()

# Initialisation de l'écran OLED
oled.init()
oled.setNormalDisplay()
oled.setHorizontalMode()

font14 = ImageFont.truetype('DejaVuSansMono.ttf', 14)

# Création de l'image et du contexte de dessin
image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
# Définition des options avec leurs images et commandes associées
options = [
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_palera1n.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/s00r1_palera1n.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_checkra1n.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/s00r1_checkra1n.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_wifi_manager.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/wifi.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_radio.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/radio.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_cas10.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/casi0.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_notes.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/notes.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_explorer.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/expl0r3r.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_info.png", "command": "sudo python3 /root/NanoHatOLED/BakeBit/Software/Python/original.py"},
    {"image": "/root/NanoHatOLED/BakeBit/Software/Python/menu_reboot.png", "command": "shutdown -r now"}
]

current_option_index = 0
in_reboot_confirmation = False
reboot_confirmation_option = "YES"  # Commence par "YES"

def display_image():
    image_path = options[current_option_index]['image']
    image = Image.open(image_path)
    oled.drawImage(image.convert('1'))  # Convertit l'image en noir et blanc

def display_reboot_confirmation():
    global reboot_confirmation_option
    clear_screen()  # Fonction pour effacer l'écran
    draw.text((10, 0), "Reboot?", font=font14, fill=255)
    
    # Affiche les options avec un curseur
    if reboot_confirmation_option == "YES":
        draw.rectangle((10, 20, 50, 35), outline=255, fill=255)  # Rectangle blanc pour "YES"
        draw.text((10, 20), "YES", font=font14, fill=0)  # Texte en noir
        draw.text((60, 20), "NO", font=font14, fill=255)  # Texte en blanc pour "NO"
    else:
        draw.rectangle((60, 20, 100, 35), outline=255, fill=255)  # Rectangle blanc pour "NO"
        draw.text((10, 20), "YES", font=font14, fill=255)  # Texte en blanc pour "YES"
        draw.text((60, 20), "NO", font=font14, fill=0)  # Texte en noir

    oled.drawImage(image)

def execute_option():
    global in_reboot_confirmation, reboot_confirmation_option
    command = options[current_option_index]['command']

    if current_option_index == len(options) - 1:  # L'index de l'option "Reboot"
        in_reboot_confirmation = True
        reboot_confirmation_option = "YES"
        display_reboot_confirmation()
    elif command:
        script = command.split()[-1]
        os.execv(sys.executable, [sys.executable, script])

def navigate_options(signum, stack):
    global current_option_index
    if signum == signal.SIGUSR1:  # Bouton 1: navigation vers le haut
        current_option_index = (current_option_index - 1) % len(options)
    elif signum == signal.SIGUSR2:  # Bouton 2: navigation vers le bas
        current_option_index = (current_option_index + 1) % len(options)
    
    display_image()
    
def validate_option(signum, stack):
    execute_option()

def navigate_reboot_confirmation(signum, stack):
    global reboot_confirmation_option
    if signum == signal.SIGUSR1:  # Bouton 1: sélectionner "YES"
        reboot_confirmation_option = "YES"
    elif signum == signal.SIGUSR2:  # Bouton 2: sélectionner "NO"
        reboot_confirmation_option = "NO"

    display_reboot_confirmation()

def validate_reboot_confirmation(signum, stack):
    global in_reboot_confirmation
    if reboot_confirmation_option == "YES":
        clear_screen()
        # Centre le message "Rebooting !" sur l'écran
        text = "Rebooting !"
        w, h = draw.textsize(text, font=font14)
        x = (width - w) // 2
        y = (height - h) // 2
        draw.text((x, y), text, font=font14, fill=255)
        oled.drawImage(image)
        time.sleep(3)  # Affiche le message pendant 3 secondes
        subprocess.Popen("shutdown -r now", shell=True)
    else:
        in_reboot_confirmation = False
        display_image()  # Revenir à l'affichage normal

def clear_screen():
    global draw, image
    draw.rectangle((0, 0, width, height), outline=0, fill=0)
    oled.drawImage(image)


if __name__ == "__main__":
    signal.signal(signal.SIGUSR1, navigate_options)
    signal.signal(signal.SIGUSR2, navigate_options)
    signal.signal(signal.SIGALRM, validate_option)
    
    display_image()  # Affiche l'image de bienvenue au démarrage

    while True:
        if in_reboot_confirmation:
            signal.signal(signal.SIGUSR1, navigate_reboot_confirmation)
            signal.signal(signal.SIGUSR2, navigate_reboot_confirmation)
            signal.signal(signal.SIGALRM, validate_reboot_confirmation)
        else:
            signal.signal(signal.SIGUSR1, navigate_options)
            signal.signal(signal.SIGUSR2, navigate_options)
            signal.signal(signal.SIGALRM, validate_option)

        time.sleep(0.2)