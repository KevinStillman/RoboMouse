import random
import threading
import time
import tkinter as tk
from tkinter import ttk

from pynput.mouse import Button, Controller as MouseController
from pynput import keyboard

# ------------------ Defaults ------------------
DEFAULT_MIN_DELAY = 0.5
DEFAULT_MAX_DELAY = 2.0

TOGGLE_KEY = keyboard.Key.f6   # Toggle on/off
QUIT_KEY   = keyboard.Key.f7   # Quit
TURBO_KEY  = keyboard.Key.f9   # Hold for turbo
TURBO_DELAY = 0.2              # seconds
# ---------------------------------------------

mouse = MouseController()

# shared state
clicking_enabled = False
turbo_held = False
min_delay = DEFAULT_MIN_DELAY
max_delay = DEFAULT_MAX_DELAY

stop_all = threading.Event()
lock = threading.Lock()

# tkinter globals (set in build_ui)
root = None
status_var = None
turbo_var = None
min_var = None
max_var = None
error_var = None
min_entry = None
max_entry = None


def safe_ui_update():
    """Update UI labels from the Tk thread."""
    if root is None:
        return

    with lock:
        enabled = clicking_enabled
        turbo = turbo_held
        mn = min_delay
        mx = max_delay

    status = "ON" if enabled else "OFF"
    status_var.set(f"Clicking: {status}    (F6 to toggle, F7 to quit)")
    turbo_var.set(f"TURBO: {'ACTIVE' if turbo else 'OFF'}  (Hold F9 for {TURBO_DELAY:.1f}s clicks)")

    # show current applied values
    min_var.set(f"{mn:g}")
    max_var.set(f"{mx:g}")


def schedule_ui_update():
    if root is None:
        return
    root.after(0, safe_ui_update)


def click_loop():
    while not stop_all.is_set():
        with lock:
            enabled = clicking_enabled
            turbo = turbo_held
            mn = min_delay
            mx = max_delay

        if enabled:
            mouse.click(Button.left, 1)
            if turbo:
                time.sleep(TURBO_DELAY)
            else:
                lo = max(0.001, float(mn))
                hi = max(lo, float(mx))
                time.sleep(random.uniform(lo, hi))
        else:
            time.sleep(0.05)


def apply_thresholds_from_ui():
    """Read min/max from Entry boxes and apply them to the clicker."""
    mn_s = min_entry.get().strip()
    mx_s = max_entry.get().strip()

    try:
        mn = float(mn_s)
        mx = float(mx_s)
        if mn <= 0 or mx <= 0:
            raise ValueError("Delays must be > 0")
        if mn > mx:
            raise ValueError("Min delay must be <= Max delay")
    except Exception as e:
        error_var.set(f"Invalid values: {e}")
        return

    with lock:
        global min_delay, max_delay
        min_delay = mn
        max_delay = mx

    error_var.set("")
    schedule_ui_update()
    print(f"[RoboMouse] Updated delays: MIN={mn} MAX={mx}")


def on_press(key):
    global clicking_enabled, turbo_held

    if key == TOGGLE_KEY:
        with lock:
            clicking_enabled = not clicking_enabled
            state = "ON" if clicking_enabled else "OFF"
        print(f"[RoboMouse] Clicking: {state}")
        schedule_ui_update()

    elif key == TURBO_KEY:
        with lock:
            if not turbo_held:
                turbo_held = True
                print("[RoboMouse] TURBO: ACTIVE")
        schedule_ui_update()

    elif key == QUIT_KEY:
        print("[RoboMouse] Quitting...")
        stop_all.set()
        if root is not None:
            root.after(0, root.destroy)
        return False


def on_release(key):
    global turbo_held
    if key == TURBO_KEY:
        with lock:
            if turbo_held:
                turbo_held = False
                print("[RoboMouse] TURBO: OFF")
        schedule_ui_update()


def build_ui():
    global root, status_var, turbo_var, min_var, max_var
    global error_var, min_entry, max_entry

    root = tk.Tk()
    root.title("RoboMouse")
    root.geometry("460x260")
    root.resizable(False, False)

    main = ttk.Frame(root, padding=12)
    main.pack(fill="both", expand=True)

    ttk.Label(main, text="", font=("Segoe UI", 16, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w", pady=(0, 8)
    )

    status_var = tk.StringVar(value="")
    turbo_var = tk.StringVar(value="")
    min_var = tk.StringVar(value=f"{DEFAULT_MIN_DELAY:g}")
    max_var = tk.StringVar(value=f"{DEFAULT_MAX_DELAY:g}")
    error_var = tk.StringVar(value="")

    ttk.Label(main, textvariable=status_var).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 4))
    ttk.Label(main, textvariable=turbo_var).grid(row=2, column=0, columnspan=3, sticky="w", pady=(0, 10))

    ttk.Label(main, text="Min delay (s):").grid(row=3, column=0, sticky="w")
    min_entry = ttk.Entry(main, width=12)
    min_entry.grid(row=3, column=1, sticky="w", padx=(8, 0))
    min_entry.insert(0, f"{DEFAULT_MIN_DELAY:g}")

    ttk.Label(main, text="Max delay (s):").grid(row=4, column=0, sticky="w", pady=(6, 0))
    max_entry = ttk.Entry(main, width=12)
    max_entry.grid(row=4, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
    max_entry.insert(0, f"{DEFAULT_MAX_DELAY:g}")

    ttk.Button(main, text="Apply", command=apply_thresholds_from_ui).grid(
        row=3, column=2, rowspan=2, sticky="nsw", padx=(12, 0)
    )

    # show current applied values (so you can tell what's in effect)
    ttk.Label(main, text="Current applied:").grid(row=5, column=0, sticky="w", pady=(10, 0))
    ttk.Label(main, text="Min:").grid(row=5, column=1, sticky="w", pady=(10, 0))
    ttk.Label(main, textvariable=min_var).grid(row=5, column=1, sticky="e", pady=(10, 0), padx=(0, 12))

    ttk.Label(main, text="Max:").grid(row=5, column=2, sticky="w", pady=(10, 0))
    ttk.Label(main, textvariable=max_var).grid(row=5, column=2, sticky="e", pady=(10, 0))

    ttk.Label(main, textvariable=error_var, foreground="red").grid(
        row=6, column=0, columnspan=3, sticky="w", pady=(10, 0)
    )

    help_text = "Tips: Set min/max then Apply. F6 toggles. Hold F9 for turbo. F7 quits."
    ttk.Label(main, text=help_text, wraplength=430).grid(
        row=7, column=0, columnspan=3, sticky="w", pady=(10, 0)
    )

    safe_ui_update()
    return root


def main():
    t = threading.Thread(target=click_loop, daemon=True)
    t.start()

    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()

    ui = build_ui()
    ui.mainloop()

    stop_all.set()
    try:
        listener.stop()
    except Exception:
        pass


if __name__ == "__main__":
    main()
