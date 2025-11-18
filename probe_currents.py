# file: probe_currents.py
import time
from inspire_hand import InspireHand, exceptions

PORT = "COM8"
BAUD = 115200
SLAVE = 1

FINGER_ATTRS = {
    "thumb": "thumb",
    "index": "index_finger",
    "middle": "middle_finger",
    "ring": "ring_finger",
    "little": "little_finger",
}

# Try these in order for BULK currents (hand.*)
BULK_TRIES = [
    "get_finger_currents",
    "get_currents",
    "get_motor_currents",
    "read_finger_currents",
]

# Try these for PER-FINGER currents (finger_node.*)
PER_TRIES = [
    "get_current",
    "current",
    "get_motor_current",
    "read_current",
]

def try_call(obj, name):
    fn = getattr(obj, name, None)
    if callable(fn):
        try:
            val = fn()
            return True, val
        except Exception as e:
            return True, f"ERROR: {e!r}"
    return False, "missing"

def main():
    hand = InspireHand(port=PORT, baudrate=BAUD, slave_id=SLAVE)
    try:
        print(f"Connecting on {PORT} @ {BAUD}, slave {SLAVE} ...")
        with hand.connect():
            print("Connected. Settling...")
            time.sleep(0.8)

            print("\n--- BULK current candidates on hand ---")
            for name in BULK_TRIES:
                exists, result = try_call(hand, name)
                print(f"hand.{name} ->", result if exists else "missing")

            print("\n--- PER-FINGER current candidates ---")
            for fname, attr in FINGER_ATTRS.items():
                node = getattr(hand, attr, None)
                print(f"\n[{fname}] node:", type(node).__name__ if node else "None")
                for name in PER_TRIES:
                    if node:
                        exists, result = try_call(node, name)
                        print(f"  {attr}.{name} ->", result if exists else "missing")
                    else:
                        print(f"  {attr}.{name} -> node missing")

    except exceptions.ConnectionError as e:
        print("ConnectionError:", e)
    except Exception as e:
        print("Unexpected error:", repr(e))

if __name__ == "__main__":
    main()
