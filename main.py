import random
import threading
import time

from pynput.mouse import Button, Controller as MouseController
from pynput import keyboard

# ---- Settings ----
MIN_DELAY = 0.5
MAX_DELAY = 2.0

TOGGLE_KEY = keyboard.Key.f6   # Press F6 to start/stop
QUIT_KEY   = keyboard.Key.f7   # Press F7 to quit
# ------------------

mouse = MouseController()
clicking_enabled = False
stop_all = threading.Event()
lock = threading.Lock()


def click_loop():
    global clicking_enabled
    while not stop_all.is_set():
        with lock:
            enabled = clicking_enabled

        if enabled:
            mouse.click(Button.left, 1)
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        else:
            time.sleep(0.05)  # small sleep to keep CPU low


def on_press(key):
    global clicking_enabled

    if key == TOGGLE_KEY:
        with lock:
            clicking_enabled = not clicking_enabled
            state = "ON" if clicking_enabled else "OFF"
        print(f"[AutoClicker] Clicking: {state}")

    elif key == QUIT_KEY:
        print("[AutoClicker] Quitting...")
        stop_all.set()
        return False  # stop keyboard listener


def main():
    print("[AutoClicker] Ready.")
    print(f"[AutoClicker] F6 = Toggle clicking ({MIN_DELAY}-{MAX_DELAY}s random)")
    print("[AutoClicker] F7 = Quit")

    t = threading.Thread(target=click_loop, daemon=True)
    t.start()

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
import random
import threading
import time

from pynput.mouse import Button, Controller as MouseController
from pynput import keyboard

# ---- Settings ----
MIN_DELAY = 0.5
MAX_DELAY = 2.0

TOGGLE_KEY = keyboard.Key.f6   # Press F6 to start/stop
QUIT_KEY   = keyboard.Key.f7   # Press F7 to quit
# ------------------

mouse = MouseController()
clicking_enabled = False
stop_all = threading.Event()
lock = threading.Lock()


def click_loop():
    global clicking_enabled
    while not stop_all.is_set():
        with lock:
            enabled = clicking_enabled

        if enabled:
            mouse.click(Button.left, 1)
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        else:
            time.sleep(0.05)  # small sleep to keep CPU low


def on_press(key):
    global clicking_enabled

    if key == TOGGLE_KEY:
        with lock:
            clicking_enabled = not clicking_enabled
            state = "ON" if clicking_enabled else "OFF"
        print(f"[AutoClicker] Clicking: {state}")

    elif key == QUIT_KEY:
        print("[AutoClicker] Quitting...")
        stop_all.set()
        return False  # stop keyboard listener


def main():
    print("[AutoClicker] Ready.")
    print(f"[AutoClicker] F6 = Toggle clicking ({MIN_DELAY}-{MAX_DELAY}s random)")
    print("[AutoClicker] F7 = Quit")

    t = threading.Thread(target=click_loop, daemon=True)
    t.start()

    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
