import json
import os
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from pynput.mouse import Button, Controller as MouseController
from pynput import keyboard

# ------------------ Defaults ------------------
DEFAULT_MIN_DELAY = 0.5
DEFAULT_MAX_DELAY = 2.0

DEFAULT_TOGGLE = "F6"
DEFAULT_QUIT   = "F7"
DEFAULT_TURBO  = "F9"
TURBO_DELAY = 0.2
CONFIG_FILE = "robomouse_config.json"
# ---------------------------------------------

mouse = MouseController()

clicking_enabled = False
turbo_held = False

min_delay = DEFAULT_MIN_DELAY
max_delay = DEFAULT_MAX_DELAY

# store binds as strings like "F6", "ESC", "A", "SPACE"
toggle_bind = DEFAULT_TOGGLE
quit_bind   = DEFAULT_QUIT
turbo_bind  = DEFAULT_TURBO

stop_all = threading.Event()
lock = threading.Lock()

# UI globals
root = None
status_var = None
turbo_var = None
error_var = None
capture_var = None

min_entry = None
max_entry = None

toggle_var = None
quit_var = None
turbo_var_key = None

capture_target = None  # "toggle" | "quit" | "turbo" | None


# ------------------ config ------------------
def load_config():
    global min_delay, max_delay, toggle_bind, quit_bind, turbo_bind

    if not os.path.exists(CONFIG_FILE):
        return

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        min_delay = float(cfg.get("min_delay", DEFAULT_MIN_DELAY))
        max_delay = float(cfg.get("max_delay", DEFAULT_MAX_DELAY))

        toggle_bind = str(cfg.get("toggle_bind", DEFAULT_TOGGLE)).upper()
        quit_bind   = str(cfg.get("quit_bind",   DEFAULT_QUIT)).upper()
        turbo_bind  = str(cfg.get("turbo_bind",  DEFAULT_TURBO)).upper()

        # basic sanity
        if min_delay <= 0: min_delay = DEFAULT_MIN_DELAY
        if max_delay <= 0: max_delay = DEFAULT_MAX_DELAY
        if min_delay > max_delay:
            min_delay, max_delay = DEFAULT_MIN_DELAY, DEFAULT_MAX_DELAY

    except Exception as e:
        print(f"[RoboMouse] Could not load config: {e}")


def save_config():
    cfg = {
        "min_delay": min_delay,
        "max_delay": max_delay,
        "toggle_bind": toggle_bind,
        "quit_bind": quit_bind,
        "turbo_bind": turbo_bind,
    }
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[RoboMouse] Could not save config: {e}")


# ------------------ key helpers ------------------
def pretty_bind(s: str) -> str:
    s = (s or "").upper()
    # keep it simple
    if s == "SPACE": return "Space"
    if s == "ESC": return "Esc"
    if s == "ENTER": return "Enter"
    if s == "TAB": return "Tab"
    return s


def key_to_bind_str(k) -> str:
    # Convert pynput key -> our string form
    if isinstance(k, keyboard.Key):
        name = k.name  # like "f6", "esc", "space"
        if name and name.startswith("f") and name[1:].isdigit():
            return ("F" + name[1:]).upper()
        if name:
            return name.upper()
        return str(k).replace("Key.", "").upper()

    # KeyCode
    ch = getattr(k, "char", None)
    if ch is None:
        return ""
    if ch == " ":
        return "SPACE"
    if ch == "\t":
        return "TAB"
    if ch == "\n":
        return "ENTER"
    if len(ch) == 1 and ch.isalpha():
        return ch.upper()
    return ch.upper()


def bind_str_to_key(s: str):
    # Convert our string -> pynput key
    s = (s or "").upper()

    if s.startswith("F") and s[1:].isdigit():
        try:
            return keyboard.Key[f"f{int(s[1:])}"]
        except Exception:
            return None

    if s == "ESC": return keyboard.Key.esc
    if s == "SPACE": return keyboard.Key.space
    if s == "TAB": return keyboard.Key.tab
    if s == "ENTER": return keyboard.Key.enter

    if s == "SHIFT": return keyboard.Key.shift
    if s == "CTRL":  return keyboard.Key.ctrl
    if s == "ALT":   return keyboard.Key.alt

    # single character bind
    if len(s) == 1:
        return keyboard.KeyCode.from_char(s.lower())

    return None


def keys_match(pynput_key, bind_string: str) -> bool:
    want = bind_str_to_key(bind_string)
    if want is None:
        return False

    if isinstance(want, keyboard.Key) and isinstance(pynput_key, keyboard.Key):
        return pynput_key == want

    # KeyCode compare by char
    if not isinstance(want, keyboard.Key) and not isinstance(pynput_key, keyboard.Key):
        return getattr(want, "char", None) == getattr(pynput_key, "char", None)

    return False


# ------------------ click loop ------------------
def click_loop():
    while not stop_all.is_set():
        with lock:
            enabled = clicking_enabled
            turbo = turbo_held
            mn = min_delay
            mx = max_delay

        if not enabled:
            time.sleep(0.05)
            continue

        mouse.click(Button.left, 1)

        if turbo:
            time.sleep(TURBO_DELAY)
        else:
            lo = max(0.001, float(mn))
            hi = max(lo, float(mx))
            time.sleep(random.uniform(lo, hi))


# ------------------ UI updates ------------------
def refresh_ui():
    if root is None:
        return

    with lock:
        enabled = clicking_enabled
        turbo = turbo_held
        mn = min_delay
        mx = max_delay
        t = toggle_bind
        q = quit_bind
        tb = turbo_bind

    status_var.set(f"Clicking: {'ON' if enabled else 'OFF'}   ({pretty_bind(t)} toggle, {pretty_bind(q)} quit)")
    turbo_var.set(f"TURBO: {'ACTIVE' if turbo else 'OFF'}   (hold {pretty_bind(tb)} = {TURBO_DELAY}s clicks)")
    toggle_var.set(pretty_bind(t))
    quit_var.set(pretty_bind(q))
    turbo_var_key.set(pretty_bind(tb))

    # keep the entry boxes showing current values (without being annoying)
    # only set them if they differ (so you can still type)
    if min_entry.get().strip() == "" or float_safe(min_entry.get()) != mn:
        min_entry.delete(0, tk.END)
        min_entry.insert(0, f"{mn:g}")
    if max_entry.get().strip() == "" or float_safe(max_entry.get()) != mx:
        max_entry.delete(0, tk.END)
        max_entry.insert(0, f"{mx:g}")


def float_safe(s):
    try:
        return float(str(s).strip())
    except:
        return None


def ui_call(fn):
    if root is None:
        return
    root.after(0, fn)


# ------------------ controls ------------------
def apply_delays():
    global min_delay, max_delay

    mn_s = min_entry.get().strip()
    mx_s = max_entry.get().strip()

    try:
        mn = float(mn_s)
        mx = float(mx_s)
        if mn <= 0 or mx <= 0:
            raise ValueError("must be > 0")
        if mn > mx:
            raise ValueError("min must be <= max")
    except Exception as e:
        error_var.set(f"Invalid delay values: {e}")
        return

    with lock:
        min_delay = mn
        max_delay = mx

    error_var.set("")
    save_config()
    refresh_ui()
    print(f"[RoboMouse] Delays set: {mn} - {mx}")


def start_capture(which):
    global capture_target
    capture_target = which
    capture_var.set(f"Press a key to set {which.upper()} bind... (Esc cancels)")


def cancel_capture():
    global capture_target
    capture_target = None
    capture_var.set("")


def set_bind(which, new_bind_str):
    global toggle_bind, quit_bind, turbo_bind

    new_bind_str = (new_bind_str or "").upper()
    if not new_bind_str:
        return False

    # no duplicates
    binds = {
        "toggle": toggle_bind,
        "quit": quit_bind,
        "turbo": turbo_bind,
    }
    for k, v in binds.items():
        if k != which and v == new_bind_str:
            messagebox.showerror("Keybind conflict", f"{pretty_bind(new_bind_str)} is already used for {k.upper()}.")
            return False

    with lock:
        if which == "toggle":
            toggle_bind = new_bind_str
        elif which == "quit":
            quit_bind = new_bind_str
        elif which == "turbo":
            turbo_bind = new_bind_str

    save_config()
    return True


# ------------------ keyboard listener ------------------
def on_press(key):
    global clicking_enabled, turbo_held

    # if we are capturing a new bind, eat the next key
    if capture_target is not None:
        if key == keyboard.Key.esc:
            ui_call(cancel_capture)
            return

        new_bind = key_to_bind_str(key)

        def apply_new():
            ok = set_bind(capture_target, new_bind)
            if ok:
                cancel_capture()
                refresh_ui()

        ui_call(apply_new)
        return

    # normal controls
    with lock:
        t = toggle_bind
        q = quit_bind
        tb = turbo_bind

    if keys_match(key, t):
        with lock:
            clicking_enabled = not clicking_enabled
            state = "ON" if clicking_enabled else "OFF"
        print(f"[RoboMouse] Clicking: {state}")
        ui_call(refresh_ui)

    elif keys_match(key, tb):
        with lock:
            turbo_held = True
        ui_call(refresh_ui)

    elif keys_match(key, q):
        print("[RoboMouse] Quitting...")
        stop_all.set()
        if root is not None:
            ui_call(root.destroy)
        return False


def on_release(key):
    global turbo_held

    if capture_target is not None:
        return

    with lock:
        tb = turbo_bind

    if keys_match(key, tb):
        with lock:
            turbo_held = False
        ui_call(refresh_ui)


# ------------------ UI ------------------
def build_ui():
    global root, status_var, turbo_var, error_var, capture_var
    global min_entry, max_entry
    global toggle_var, quit_var, turbo_var_key

    root = tk.Tk()
    root.title("RoboMouse")
    root.geometry("520x300")
    root.resizable(False, False)

    main = ttk.Frame(root, padding=12)
    main.pack(fill="both", expand=True)

    ttk.Label(main, text="RoboMouse", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")

    status_var = tk.StringVar(value="")
    turbo_var = tk.StringVar(value="")
    error_var = tk.StringVar(value="")
    capture_var = tk.StringVar(value="")

    ttk.Label(main, textvariable=status_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=(8, 0))
    ttk.Label(main, textvariable=turbo_var).grid(row=2, column=0, columnspan=4, sticky="w", pady=(4, 10))

    # delays
    ttk.Label(main, text="Delay").grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))
    box1 = ttk.Frame(main, padding=10)
    box1.grid(row=4, column=0, columnspan=4, sticky="ew")

    ttk.Label(box1, text="Min (s):").grid(row=0, column=0, sticky="w")
    min_entry = ttk.Entry(box1, width=10)
    min_entry.grid(row=0, column=1, sticky="w", padx=(8, 18))

    ttk.Label(box1, text="Max (s):").grid(row=0, column=2, sticky="w")
    max_entry = ttk.Entry(box1, width=10)
    max_entry.grid(row=0, column=3, sticky="w", padx=(8, 18))

    ttk.Button(box1, text="Apply", command=apply_delays).grid(row=0, column=4, sticky="w")

    # keybinds
    ttk.Label(main, text="Keybinds").grid(row=5, column=0, columnspan=4, sticky="w", pady=(6, 0))
    box2 = ttk.Frame(main, padding=10)
    box2.grid(row=6, column=0, columnspan=4, sticky="ew")

    toggle_var = tk.StringVar(value="")
    quit_var = tk.StringVar(value="")
    turbo_var_key = tk.StringVar(value="")

    ttk.Label(box2, text="Toggle:").grid(row=0, column=0, sticky="w")
    ttk.Label(box2, textvariable=toggle_var, width=10).grid(row=0, column=1, sticky="w", padx=(8, 18))
    ttk.Button(box2, text="Change", command=lambda: start_capture("toggle")).grid(row=0, column=2, sticky="w")

    ttk.Label(box2, text="Quit:").grid(row=1, column=0, sticky="w", pady=(6, 0))
    ttk.Label(box2, textvariable=quit_var, width=10).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(6, 0))
    ttk.Button(box2, text="Change", command=lambda: start_capture("quit")).grid(row=1, column=2, sticky="w", pady=(6, 0))

    ttk.Label(box2, text="Turbo (hold):").grid(row=2, column=0, sticky="w", pady=(6, 0))
    ttk.Label(box2, textvariable=turbo_var_key, width=10).grid(row=2, column=1, sticky="w", padx=(8, 18), pady=(6, 0))
    ttk.Button(box2, text="Change", command=lambda: start_capture("turbo")).grid(row=2, column=2, sticky="w", pady=(6, 0))

    ttk.Label(main, textvariable=capture_var).grid(row=5, column=0, columnspan=4, sticky="w", pady=(8, 0))
    ttk.Label(main, textvariable=error_var, foreground="red").grid(row=6, column=0, columnspan=4, sticky="w", pady=(6, 0))

    refresh_ui()
    return root


def main():
    load_config()

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
