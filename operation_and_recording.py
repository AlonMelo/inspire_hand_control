# file: operation_and_recording.py
# Keyboard control + continuous data recording to CSV for Inspire Hand.
# All serial I/O is serialized via io_lock to prevent Modbus frame collisions.
#
# Keys:
#   g -> grip
#   o -> open_all_fingers
#   p -> pinch
#   f -> point
#   u -> thumbs_up
#   e -> cool
#   h -> hook_4
#   c -> close_all_fingers
#   Esc -> quit

import csv
import time
import threading
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

from pynput import keyboard
from inspire_hand import InspireHand, exceptions

# ---------- USER SETTINGS ----------
PORT = "COM8"
BAUD = 115200
SLAVE_ID = 1

DEFAULT_FORCE = 700
DEFAULT_SPEED = 800

SAMPLE_HZ = 10.0                   # samples per second
LOG_DIR = Path("recordings")       # ./recordings inside your project
CMD_COOLDOWN = 0.10                # short pause after each command (s)
RETRY_ON_INVALID = True            # retry once if a Modbus frame error occurs
# -----------------------------------

FINGERS = ["thumb", "index", "middle", "ring", "little"]
FINGER_ATTRS = {
    "thumb": "thumb",
    "index": "index_finger",
    "middle": "middle_finger",
    "ring": "ring_finger",
    "little": "little_finger",
}

# One lock for ALL serial I/O (reads AND writes)
io_lock = threading.RLock()


def with_io_lock(fn, *args, **kwargs):
    """Run a hand.* call under the shared serial I/O lock, with optional one retry."""
    try:
        with io_lock:
            return fn(*args, **kwargs)
    except Exception as e:
        msg = str(e)
        if RETRY_ON_INVALID and ("Invalid response" in msg or "Timeout" in msg):
            # brief backoff then retry once
            time.sleep(0.05)
            with io_lock:
                return fn(*args, **kwargs)
        raise


def safe_call(fn, default=None):
    try:
        return with_io_lock(fn)
    except Exception:
        return default


def read_metric_bulk(hand, bulk_name: str, per_method: str):
    """Try hand.get_finger_<bulk_name>(), else per-finger .<per_method>(). Locked."""
    bulk_fn = getattr(hand, f"get_finger_{bulk_name}", None)
    res = safe_call(bulk_fn, default=None)
    if isinstance(res, (list, tuple)):
        return list(res)

    out = []
    for _, attr in FINGER_ATTRS.items():
        node = getattr(hand, attr, None)
        getter = getattr(node, f"get_{per_method}", None) if node else None
        out.append(safe_call(getter, default=None))
    return out


def get_all_metrics(hand: InspireHand):
    return {
        "positions":    read_metric_bulk(hand, "positions", "position"),
        "angles":       read_metric_bulk(hand, "angles", "angle"),
        "forces":       read_metric_bulk(hand, "forces", "force"),
        "currents":     read_metric_bulk(hand, "currents", "current"),
        "speeds":       read_metric_bulk(hand, "speeds", "speed"),
        "temperatures": read_metric_bulk(hand, "temperatures", "temperature"),
    }


def make_writer():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = LOG_DIR / f"operation_log_{ts_name}.csv"

    header = ["timestamp", "action"]
    for prefix in ["pos", "angle", "force", "current", "speed", "temp"]:
        header += [f"{f}_{prefix}" for f in FINGERS]

    f = open(csv_path, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(header)
    return f, writer, csv_path


def format_row(ts: float, action: str, metrics: dict):
    dt_iso = datetime.fromtimestamp(ts).isoformat(timespec="milliseconds")
    row = [dt_iso, action]
    row += metrics["positions"]
    row += metrics["angles"]
    row += metrics["forces"]
    row += metrics["currents"]
    row += metrics["speeds"]
    row += metrics["temperatures"]
    return row


def print_help():
    print("\n=== Inspire Hand Keyboard Control + Recording ===")
    print(" g : grip")
    print(" o : open_all_fingers")
    print(" p : pinch")
    print(" f : point")
    print(" u : thumbs_up")
    print(" e : cool")
    print(" h : hook_4")
    print(" c : close_all_fingers")
    print(" Esc : quit")
    print("===============================================\n")


def main():
    f, writer, csv_path = make_writer()
    print(f"[Recording] Writing CSV to: {csv_path.resolve()}")

    hand = InspireHand(port=PORT, baudrate=BAUD, slave_id=SLAVE_ID)
    last_action = "idle"
    action_lock = threading.Lock()
    task_q = Queue()
    running = True

    try:
        print(f"Connecting on {PORT} @ {BAUD}, slave {SLAVE_ID} ...")
        with hand.connect():
            print("Connected.")
            with_io_lock(hand.set_all_finger_speeds, DEFAULT_SPEED)
            with_io_lock(hand.set_all_finger_forces, DEFAULT_FORCE)
            print_help()

            # Worker to execute queued commands (LOCKED)
            def worker():
                nonlocal last_action
                while running:
                    try:
                        fn, args, act = task_q.get(timeout=0.2)
                    except Empty:
                        continue
                    try:
                        if act:
                            with action_lock:
                                last_action = act
                        with_io_lock(fn, *args)
                        time.sleep(CMD_COOLDOWN)
                    except Exception as e:
                        print(f"{act or 'Command'} error:", e)
                    finally:
                        task_q.task_done()

            threading.Thread(target=worker, daemon=True).start()

            # Recorder thread (LOCKED reads)
            def recorder():
                nonlocal last_action
                dt = 1.0 / SAMPLE_HZ if SAMPLE_HZ > 0 else 0.1
                while running:
                    t0 = time.time()
                    try:
                        metrics = get_all_metrics(hand)  # uses with_io_lock() internally
                        with action_lock:
                            act = last_action
                        writer.writerow(format_row(t0, act, metrics))
                    except Exception as e:
                        print("Record error:", e)
                    # keep rate
                    t_elapsed = time.time() - t0
                    time.sleep(max(0.0, dt - t_elapsed))

            threading.Thread(target=recorder, daemon=True).start()

            # Helpers
            def enqueue(act, fn, *args):
                task_q.put((fn, args, act))

            # Keyboard handling
            def on_press(key):
                nonlocal running
                if key == keyboard.Key.esc:
                    print("Quitting...")
                    running = False
                    try:
                        with_io_lock(hand.open_all_fingers)
                    except Exception:
                        pass
                    return False

                if isinstance(key, keyboard.KeyCode) and key.char:
                    c = key.char.lower()
                    if c == 'g': enqueue("grip", hand.grip, DEFAULT_FORCE)
                    elif c == 'o': enqueue("open_all", hand.open_all_fingers)
                    elif c == 'p': enqueue("pinch", hand.pinch, DEFAULT_FORCE)
                    elif c == 'f': enqueue("point", hand.point)
                    elif c == 'u': enqueue("thumbs_up", hand.thumbs_up)
                    elif c == 'e': enqueue("cool", hand.cool)
                    elif c == 'h': enqueue("hook_4", hand.hook_4)
                    elif c == 'c': enqueue("close_all", hand.close_all_fingers)

            with keyboard.Listener(on_press=on_press) as listener:
                listener.join()

    except exceptions.ConnectionError as e:
        print("ConnectionError:", e)
    except Exception as e:
        print("Unexpected error:", e)
    finally:
        running = False
        # Wait a moment for threads to settle
        try:
            time.sleep(0.2)
        except Exception:
            pass
        f.close()
        print(f"CSV saved: {csv_path.resolve()}")


if __name__ == "__main__":
    main()
