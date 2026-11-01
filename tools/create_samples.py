"""Generate clean sample prescription images used by the demo button.

Run from the backend folder:  python tools/create_samples.py
"""

import os

from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "frontend", "assets"))

WIDTH, HEIGHT = 1240, 1580
INK = (32, 41, 46)
MUTED = (105, 117, 124)
TEAL = (13, 118, 110)
LINE = (214, 222, 226)

FONT_DIR = r"C:\Windows\Fonts"


def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def draw_prescription(config):
    image = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(image)

    draw.rectangle([0, 0, WIDTH, 12], fill=TEAL)

    # Letterhead
    draw.text((72, 58), config["clinic"], font=font("segoeuib.ttf", 40), fill=INK)
    draw.text((72, 112), config["specialty"], font=font("segoeui.ttf", 22), fill=MUTED)
    draw.text((72, 146), config["address"], font=font("segoeui.ttf", 20), fill=MUTED)

    draw.line([72, 206, WIDTH - 72, 206], fill=LINE, width=2)

    draw.text((72, 228), config["doctor"], font=font("segoeui.ttf", 28), fill=INK)
    draw.text((72, 266), config["title"], font=font("segoeui.ttf", 20), fill=MUTED)

    # Patient block
    draw.line([72, 322, WIDTH - 72, 322], fill=LINE, width=2)
    draw.text((72, 342), f"Date: {config['date']}", font=font("segoeui.ttf", 22), fill=INK)
    draw.text((680, 342), "Rx No: 10482", font=font("segoeui.ttf", 22), fill=MUTED)
    draw.text((72, 382), f"Patient: {config['patient']}", font=font("segoeui.ttf", 24), fill=INK)
    draw.text((820, 382), f"Age: {config['age']}", font=font("segoeui.ttf", 24), fill=INK)
    draw.line([72, 430, WIDTH - 72, 430], fill=LINE, width=2)

    # Rx symbol
    draw.text((72, 456), "Rx", font=font("timesbd.ttf", 54), fill=TEAL)

    y = 540
    for number, medicine in enumerate(config["medicines"], start=1):
        draw.text((76, y + 2), f"{number}.", font=font("segoeuib.ttf", 26), fill=TEAL)
        draw.text((122, y), medicine, font=font("segoeui.ttf", 26), fill=INK)
        y += 74

    # Notes
    draw.line([72, y + 40, WIDTH - 72, y + 40], fill=LINE, width=2)
    draw.text((72, y + 64), "Advice", font=font("segoeuib.ttf", 22), fill=INK)
    draw.text((72, y + 100), config["advice"], font=font("segoeui.ttf", 21), fill=MUTED)

    # Signature
    draw.line([820, HEIGHT - 128, WIDTH - 72, HEIGHT - 128], fill=INK, width=2)
    draw.text(
        (820, HEIGHT - 112),
        "Doctor's Signature",
        font=font("segoeui.ttf", 18),
        fill=MUTED,
    )

    draw.text(
        (72, HEIGHT - 58),
        "This prescription is valid for 30 days from the date of issue.",
        font=font("segoeui.ttf", 16),
        fill=MUTED,
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, config["filename"])
    image.save(path, "PNG", optimize=True)
    print(f"created {path}")


SAMPLES = [
    {
        "filename": "sample-prescription.png",
        "clinic": "NORTHBRIDGE MEDICAL CENTER",
        "specialty": "Internal Medicine & Family Care",
        "address": "12 Nile Street, Zamalek  |  Tel: 02 2735 8890",
        "doctor": "Dr. Sarah Ahmed, MD",
        "title": "Consultant Internal Medicine",
        "date": "12 Oct 2026",
        "patient": "Omar Khaled",
        "age": "34",
        "medicines": [
            "Augmentin 625mg  -  1 tab every 12 hours - for 7 days",
            "Panadol 500mg  -  2 tabs every 8 hours - for 3 days",
            "Omeprazole 20mg  -  1 cap before breakfast - for 14 days",
            "Vitamin D3 1000IU  -  1 tab daily - for 30 days",
        ],
        "advice": "Drink plenty of water. Return if the fever persists for more than 3 days.",
    },
    {
        "filename": "sample-prescription-2.png",
        "clinic": "AL SHIFA CHILDREN'S CLINIC",
        "specialty": "Pediatrics & Child Health",
        "address": "48 El Horreya Road, Alexandria  |  Tel: 03 487 2210",
        "doctor": "Dr. Mona Hassan, MD",
        "title": "Consultant Pediatrician",
        "date": "05 Nov 2026",
        "patient": "Lina Youssef",
        "age": "7",
        "medicines": [
            "Zithromax 200mg  -  5ml once daily - for 5 days",
            "Ventolin inhaler 100mcg  -  2 puffs every 6 hours - as needed",
            "Cetirizine 10mg  -  1 tab at bedtime - for 10 days",
        ],
        "advice": "Keep the child hydrated and avoid cold drinks for one week.",
    },
]


if __name__ == "__main__":
    for sample in SAMPLES:
        draw_prescription(sample)
