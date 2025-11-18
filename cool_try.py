import time
from inspire_hand import InspireHand, exceptions

PORT = "COM8"
BAUD = 115200
SLAVE_ID = 1

def main():
    hand = InspireHand(port=PORT, baudrate=BAUD, slave_id=SLAVE_ID)
    try:
        print(f"Connecting on {PORT} @ {BAUD}, slave {SLAVE_ID} ...")
        # IMPORTANT: connect() returns a context manager — enter it:
        with hand.connect():
            print("Connected.")

            # Quick motions
            hand.open_all_fingers()
            time.sleep(1.0)

            hand.pinch(force=500)
            time.sleep(1.0)

            hand.open_all_fingers()
            time.sleep(1.0)

            hand.cool()
            time.sleep(1.0)

            # Read state
            angles = hand.get_finger_angles()
            forces = hand.get_finger_forces()
            print("Angles:", angles)
            print("Forces:", forces)

            # Example: tweak speed/force and move index finger
            hand.set_all_finger_speeds(800)   # 0–1000
            hand.set_all_finger_forces(500)   # 0–1000
            # hand.index_finger.move(500)       # 0–1000 position
            time.sleep(0.8)

            # Leave it open at the end for safety
            hand.open_all_fingers()

        # Exiting the with-block closes the connection cleanly.

    except exceptions.ConnectionError as e:
        print("ConnectionError:", e)
        print("HINTS:")
        print(" • Make sure no other app (vendor PC tool) is holding COM8")
        print(" • Verify RS-485 wiring & ID (now that step 1 works, those should be fine)")
    except Exception as e:
        print("Unexpected error:", repr(e))
    finally:
        # Hand may already be closed by the context manager; this is just defensive.
        try:
            hand.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
