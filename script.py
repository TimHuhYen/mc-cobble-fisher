# auto fishings script
"""
Minecraft Auto-Fisher (subtitle-OCR based)

How it works:
  Minecraft's accessibility setting "Show Subtitles" prints short text captions
  for game sounds, including "Fish Bobber splashes", in the bottom-right corner
  of the screen. Instead of trying to process real audio, this script watches
  that screen region with OCR and right-clicks the moment the phrase appears.

"""

import time
import re
from dataclasses import dataclass

import mss
import pytesseract
import pyautogui
from PIL import Image

# Screen region to OCR, in pixels. Tuned for a 1920x1080 screen with subtitles
# in the default bottom-right position. Widen/heighten if text gets cut off.
CAPTURE_REGION = {
    "left": 1250,
    "top": 850,
    "width": 650,
    "height": 200,
}

TARGET_PHRASE = "fish bobber splashes"   # matched case-insensitively
POLL_INTERVAL = 0.12                      # seconds between screen checks
COOLDOWN_AFTER_CATCH = 1.5                # seconds to wait after reeling in
RECAST_DELAY = 0.6                        # pause between reeling in and recasting
SCAN_TIMEOUT = 60.0                       # give up waiting and recast anyway after this long


@dataclass
class Stats:
    casts: int = 0
    catches: int = 0


def normalize(text: str) -> str:
    # collapse whitespace and strip junk OCR sometimes adds
    return re.sub(r"\s+", " ", text).strip().lower()


def capture_text(sct, region) -> str:
    shot = sct.grab(region)
    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
    return pytesseract.image_to_string(img)


def right_click():
    pyautogui.click(button="right")


def main():
    stats = Stats()
    print("Auto-fisher starting in 3 seconds — switch to the Minecraft window now.")
    time.sleep(3)

    with mss.mss() as sct:
        # Cast the first line
        right_click()
        stats.casts += 1
        cast_time = time.time()
        print(f"[cast #{stats.casts}] line out, watching for splash...")

        try:
            while True:
                text = normalize(capture_text(sct, CAPTURE_REGION))

                if TARGET_PHRASE in text:
                    right_click()  # reel in
                    stats.catches += 1
                    print(f"[catch #{stats.catches}] splash detected, reeled in.")
                    time.sleep(COOLDOWN_AFTER_CATCH)

                    right_click()  # recast
                    stats.casts += 1
                    cast_time = time.time()
                    print(f"[cast #{stats.casts}] line back out.")
                    time.sleep(RECAST_DELAY)
                    continue

                # Safety net: if nothing was detected for too long (bobber
                # snagged, missed splash, OCR miss), just recast rather than
                # sitting there forever.
                if time.time() - cast_time > SCAN_TIMEOUT:
                    print("No splash detected in time, recasting.")
                    right_click()  # reel in whatever's out there
                    time.sleep(RECAST_DELAY)
                    right_click()  # recast
                    stats.casts += 1
                    cast_time = time.time()

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print(f"\nStopped. Casts: {stats.casts}, Catches: {stats.catches}")


if __name__ == "__main__":
    main()