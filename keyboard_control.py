# file: keyboard_control.py
# cd C:\Users\alonl\PycharmProjects\inspire_hand_control.\venv\Scripts\python.exe keyboard_control.py
# Windows console keyboard control for Inspire Hand
# Keys:
#   g -> grip
#   o -> open_all_fingers
#   p -> pinch
#   f -> point
#   u -> thumbs_up
#   e -> cool
#   h -> hook_4
#   c -> close_all_fingers
#   q -> quit

import time
import msvcrt  # Windows-only
from inspire_hand import InspireHand, exceptions

PORT = "COM8"       # <-- change if needed
BAUD = 115200
SLAVE_ID = 1

# You can tweak default effort for gestures here (0–1000)
DEFAULT_FORCE = 300
DEFAULT_SPEED = 600


def print_help():
    print("\n=== Inspire Hand Keyboard Control ===")
    print(" g : grip")
    print(" o : open_all_fingers")
    print(" p : pinch")
    print(" f : point")
    print(" u : thumbs_up")
    print(" e : cool")
    print(" h : hook_4")
    print(" c : close_all_fingers")
    print(" q : quit")
    print("=====================================\n")


def main():
    hand = InspireHand(port=PORT, baudrate=BAUD, slave_id=SLAVE_ID)
    try:
        print(f"Connecting on {PORT} @ {BAUD}, slave {SLAVE_ID} ...")
        with hand.connect():
            print("Connected.")
            hand.set_all_finger_speeds(DEFAULT_SPEED)
            hand.set_all_finger_forces(DEFAULT_FORCE)
            print_help()

            print("Listening for keys... (press 'q' to quit)")
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()  # wide char; handles standard keys
                    if not ch:
                        continue
                    key = ch.lower()

                    if key == 'q':
                        print("Quitting...")
                        break

                    elif key == 'g':
                        print("→ grip")
                        hand.grip(force=DEFAULT_FORCE)

                    elif key == 'o':
                        print("→ open_all_fingers")
                        hand.open_all_fingers()

                    elif key == 'p':
                        print("→ pinch")
                        hand.pinch(force=DEFAULT_FORCE)

                    elif key == 'f':
                        print("→ point")
                        hand.point()

                    elif key == 'u':
                        print("→ thumbs_up")
                        hand.thumbs_up()

                    elif key == 'e':
                        print("→ cool")
                        hand.cool()

                    elif key == 'h':
                        print("→ hook_4")
                        hand.hook_4()

                    elif key == 'c':
                        print("→ close_all_fingers")
                        hand.close_all_fingers()

                    # quick debounce so repeat doesn't spam too hard
                    time.sleep(0.05)

                else:
                    # idle loop (keep this light)
                    time.sleep(0.01)

            # Leave the hand open for safety when exiting
            try:
                hand.open_all_fingers()
            except Exception:
                pass

    except exceptions.ConnectionError as e:
        print("ConnectionError:", e)
        print("HINTS: close vendor app, verify RS-485 wiring/ID/baud.")
    except Exception as e:
        print("Unexpected error:", repr(e))
    finally:
        # Close if not already closed by context exit
        try:
            hand.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
