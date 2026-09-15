import numpy as np
import pyautogui
import easyocr
import time
import cv2
import mss

SUBTITLE_REGION = {"top": 750, "left": 1500, "width": 400, "height": 300}
XP_SLEEP = 8 

# minigame bar tracking 
BAR_REGION = {"top": 300, "left": 950, "width": 40, "height": 480}
BAR_COLUMN_X = 20        # x offset *within* BAR_REGION where the bar's center column sits
CLICK_BUTTON = "right"   # confirmed by testing; change here if it stops working
CLICK_TAP_INTERVAL = 0.045
MAX_HOLD_TIME = 0.25
MIN_HOLD_TIME = 0.015
BAR_LOST_FRAMES_TO_END = 90
OCR_CHECK_EVERY_N_FRAMES = 15
DEBUG_EVERY_N_FRAMES = 5

GAIN_POSITION = 0.5 / 100
GAIN_RATE = 1.5 / 100
GAIN_BAR_VEL = 0.9 / 100

screenCapture = mss.mss()
reader = easyocr.Reader(["en"])


def pressRightMouse():
    pyautogui.click(button="right")


def readRegionText(region):
    frame = np.array(screenCapture.grab(region))
    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2GRAY)
    result = reader.readtext(frame)
    return [text.lower() for (_, text, _) in result]


# minigame tracking
def classify(r, g, b):
    if g > int(r) + 30 and g > int(b) + 60:
        return "green"
    if b > int(r) + 30 and b > int(g) - 20 and b > 150:
        return "blue"
    if r < 90 and abs(int(g) - int(b)) < 25 and g > 20:
        return "fish"
    return "other"


def readBarColumn():
    shot = screenCapture.grab(BAR_REGION)
    frame = np.array(shot)  # BGRA
    rgb_column = frame[:, BAR_COLUMN_X, [2, 1, 0]]  # BGR -> RGB, one column
    return [classify(*px) for px in rgb_column]


def findBarAndFish(labels):
    greenRows = [i for i, lbl in enumerate(labels) if lbl == "green"]
    fishRows = [i for i, lbl in enumerate(labels) if lbl == "fish"]

    if not greenRows:
        return None, None, None

    barTop = greenRows[0]
    barBottom = greenRows[-1]
    fishY = fishRows[len(fishRows) // 2] if fishRows else None
    return barTop, barBottom, fishY


def clickBump(holdTime):
    holdTime = max(MIN_HOLD_TIME, min(MAX_HOLD_TIME, holdTime))
    numTaps = max(1, round(holdTime / CLICK_TAP_INTERVAL))
    for _ in range(numTaps):
        pyautogui.click(button=CLICK_BUTTON)
        time.sleep(CLICK_TAP_INTERVAL)


def runMinigame():
    print("Minigame started, tracking bar...")
    prevDy = 0
    prevBarY = None
    lostFrames = 0
    frameCount = 0

    while True:
        frameCount += 1

        if frameCount % OCR_CHECK_EVERY_N_FRAMES == 0:
            for text in readRegionText(SUBTITLE_REGION):
                if "experience gained" in text:
                    print("Minigame end text detected:", text)
                    return

        labels = readBarColumn()
        barTop, barBottom, fishY = findBarAndFish(labels)

        if barTop is None or fishY is None:
            lostFrames += 1
            if frameCount % DEBUG_EVERY_N_FRAMES == 0:
                print(f"MINIGAME DEBUG no bar/fish detected (labels sample: {labels[::20]})")
            if lostFrames > BAR_LOST_FRAMES_TO_END:
                print("Bar not detected for a while, assuming minigame ended.")
                return
            time.sleep(0.02)
            continue

        lostFrames = 0
        barY = (barTop + barBottom) / 2
        if prevBarY is None:
            prevBarY = barY

        dy = barY - fishY
        dVel = dy - prevDy
        barVel = barY - prevBarY

        holdTime = (GAIN_POSITION * dy) + (GAIN_RATE * dVel) + (GAIN_BAR_VEL * barVel)

        prevDy = dy
        prevBarY = barY

        if frameCount % DEBUG_EVERY_N_FRAMES == 0:
            print(f"MINIGAME DEBUG barTop={barTop} barBottom={barBottom} fishY={fishY} dy={dy:.1f} holdTime={holdTime:.3f}")

        if holdTime > 0:
            clickBump(holdTime)

        time.sleep(0.02)


while True:
    try:
        time.sleep(0.4)

        texts = readRegionText(SUBTITLE_REGION)
        if texts:
            print("DEBUG saw:", texts)

        for text in texts:
            if "bobber splashes" in text:
                pressRightMouse()  # hook the fish, minigame starts

                time.sleep(0.3)
                runMinigame()

                print(f"Waiting {XP_SLEEP}s before recasting.")
                time.sleep(XP_SLEEP)

                pressRightMouse()  # recast
                break

    except KeyboardInterrupt:
        break

print("bye")