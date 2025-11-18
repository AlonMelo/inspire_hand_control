# file: keyboard_control_pynput.py
# Global hotkeys for Inspire Hand (works well inside PyCharm).
# Keys:
#   g -> grip
#   r -> thumb_front_ready
#   o -> open_all_fingers
#   p -> pinch
#   f -> point
#   u -> thumbs_up
#   e -> cool
#   h -> hook_4
#   j -> hook_2_1
#   k -> hook_2_2
#   l -> little_hook
#   c -> close_all_fingers
#   Esc -> quit

import time
import threading
from queue import Queue, Empty
from pynput import keyboard
from hands_1 import InspireHand_melon
from inspire_hand import InspireHand, exceptions

PORT = "COM5"
BAUD = 115200
SLAVE_ID = 1

DEFAULT_FORCE = 300   # 0–1000
DEFAULT_SPEED = 300   # 0–1000

def print_help():
    print("\n=== Inspire Hand Keyboard Control (pynput) ===")
    print(" r : thumb_front_ready")
    print(" g : grip")
    print(" s : stronger_no_bend")
    print(" o : open_all_fingers")
    print(" p : pinch")
    print(" f : point")
    print(" u : thumbs_up")
    print(" e : cool")
    print(" d : hook_for_door")
    print(" h : hook_4")
    print(" j : hook_2_1")
    print(" k : hook_2_2")
    print(" l : little_hook")
    print(" t : toilet stick")
    print(" c : close_all_fingers")
    print(" x : clear_errors + show current error decode")

    print(" Esc : quit")
    print("==============================================\n")

def main():
    hand = InspireHand_melon(port=PORT, baudrate=BAUD, slave_id=SLAVE_ID)
    try:
        print(f"Connecting on {PORT} @ {BAUD}, slave {SLAVE_ID} ...")
        with hand.connect():
            print("Connected.")
            hand.set_all_finger_speeds(DEFAULT_SPEED)
            hand.set_all_finger_forces(DEFAULT_FORCE)
            print_help()

            task_q: "Queue[tuple]" = Queue()
            running = True

            # Worker thread to execute hand commands sequentially
            def worker():
                while True:
                    try:
                        fn, args = task_q.get(timeout=0.2)
                    except Empty:
                        if not running:
                            break
                        continue
                    try:
                        fn(*args)
                    except Exception as e:
                        print("Command error:", repr(e))
                    finally:
                        task_q.task_done()

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            # Debounce to avoid floods on key repeat
            last_time = {}
            DEBOUNCE = 0.12  # seconds

            def enqueue(fn, *args):
                task_q.put((fn, args))

            # Key handlers
            def on_press(key):
                nonlocal running
                if key == keyboard.Key.esc:
                    print("Quitting...")
                    # drain and stop
                    def _shutdown():
                        try:
                            hand.open_all_fingers()
                        except Exception:
                            pass
                    enqueue(_shutdown)
                    # allow worker to finish queued tasks
                    def _stop():
                        nonlocal running
                        running = False
                    _stop()
                    return False  # stop listener

                ch = None
                if isinstance(key, keyboard.KeyCode) and key.char:
                    ch = key.char.lower()

                if not ch:
                    return

                now = time.time()
                if ch in last_time and now - last_time[ch] < DEBOUNCE:
                    return
                last_time[ch] = now

                if ch == 'g':
                    print("→ grip")
                    enqueue(hand.grip, DEFAULT_FORCE)
                elif ch == 's':
                    print("→ stronger_no_bend")
                    enqueue(hand.stronger_no_bend)
                elif ch == 'o':
                    print("→ open_all_fingers")
                    enqueue(hand.open_all_fingers)
                elif ch == 'p':
                    print("→ pinch")
                    enqueue(hand.pinch, DEFAULT_FORCE)
                elif ch == 'f':
                    print("→ point")
                    enqueue(hand.point)
                elif ch == 'u':
                    print("→ thumbs_up")
                    enqueue(hand.thumbs_up)
                elif ch == 'e':
                    print("→ cool")
                    enqueue(hand.cool)
                elif ch == 'h':
                    print("→ hook_4")
                    enqueue(hand.hook_4)
                elif ch == 'd':
                    print("→ hook_for_door")
                    enqueue(hand.hook_for_door)
                elif ch == 'j':
                    print("→ hook_2_1")
                    enqueue(hand.hook_2_1)
                elif ch == 'k':
                    print("→ hook_2_2")
                    enqueue(hand.hook_2_2)
                elif ch == 'l':
                    print("→ little_hook")
                    enqueue(hand.little_hook)
                elif ch == 'r':
                    print("→ thumb_front_ready")
                    enqueue(hand.thumb_front_ready)
                elif ch == 't':
                    print("→ toilet_stick")
                    enqueue(hand.toilet_stick)
                elif ch == 'c':
                    print("→ close_all_fingers")
                    enqueue(hand.close_all_fingers)
                elif ch == 'x':
                    print("→ clear_errors")

                    def _clear_and_report():
                        ok = hand.clear_errors(verify=True)
                        print("   clear_errors:", "OK" if ok else "FAILED")
                        try:
                            report = hand.describe_finger_errors()
                            for k, v in report.items():
                                print(f"   {k}: {', '.join(v)}")
                        except Exception as e:
                            print("   error read failed:", e)

                    enqueue(_clear_and_report)

            with keyboard.Listener(on_press=on_press) as listener:
                listener.join()

            # Wait for any remaining tasks to finish
            task_q.join()

    except exceptions.ConnectionError as e:
        print("ConnectionError:", e)
        print("HINTS: close vendor app, verify RS-485 wiring/ID/baud.")
    except Exception as e:
        print("Unexpected error:", repr(e))

if __name__ == "__main__":
    main()
