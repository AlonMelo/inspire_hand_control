# file: operation_and_recording_forces.py
# Keyboard control + recording ONLY FORCES (+ last action) to CSV.
#
# Hotkeys: g grip | o open_all | p pinch | f point | u thumbs_up | e cool | h hook_4 | c close_all | Esc quit

import csv, time, threading
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty
from pynput import keyboard
from inspire_hand import InspireHand, exceptions

# --- settings ---
PORT, BAUD, SLAVE = "COM8", 115200, 1
DEFAULT_FORCE, DEFAULT_SPEED = 700, 800
SAMPLE_HZ = 10.0
LOG_DIR = Path("recordings")
INIT_SETTLE, BACKOFF = 1.0, 0.2
WRITE_TRIES, READ_TRIES, CMD_COOLDOWN = 3, 6, 0.10
FINGERS = ["thumb","index","middle","ring","little"]
# ---------------

io_lock = threading.RLock()

def with_lock(fn, *args, tries=1, backoff=BACKOFF):
    last=None
    for i in range(tries):
        try:
            with io_lock:
                return fn(*args)
        except Exception as e:
            last=e
            if i<tries-1 and any(s in str(e) for s in ("No response","Invalid response","Timeout")):
                time.sleep(backoff); continue
            raise
    raise last

def get_forces(hand: InspireHand):
    # try bulk first
    try:
        vals = with_lock(hand.get_finger_forces)
        if isinstance(vals,(list,tuple)) and len(vals)>=5:
            return list(vals)[:5]
    except Exception:
        pass
    # fallback per finger (names from lib)
    name_map = {"thumb":"thumb","index":"index_finger","middle":"middle_finger","ring":"ring_finger","little":"little_finger"}
    out=[]
    for f in FINGERS:
        node = getattr(hand, name_map[f], None)
        if node and hasattr(node, "get_force"):
            try: out.append(with_lock(node.get_force))
            except Exception: out.append(None)
        else:
            out.append(None)
    return out

def make_writer():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOG_DIR / f"forces_log_{ts}.csv"
    f = open(path,"w",newline="",encoding="utf-8"); w = csv.writer(f)
    w.writerow(["timestamp","action"] + [f"{x}_force" for x in FINGERS])
    return f,w,path

def print_help():
    print("\n g:grip o:open_all p:pinch f:point u:thumbs_up e:cool h:hook_4 c:close_all  Esc:quit\n")

def main():
    f,w,path = make_writer()
    print(f"[Recording] CSV: {path.resolve()}")

    last_action="idle"
    action_lock=threading.Lock()
    q: "Queue[tuple]" = Queue()
    running=True

    hand = InspireHand(port=PORT, baudrate=BAUD, slave_id=SLAVE)
    try:
        print(f"Connecting on {PORT} @ {BAUD}, slave {SLAVE} ...")
        with hand.connect():
            print("Connected."); time.sleep(INIT_SETTLE)

            # wake probe
            ok=False
            for _ in range(READ_TRIES):
                try:
                    with_lock(hand.get_finger_angles)
                    ok=True; break
                except Exception: time.sleep(BACKOFF)
            if not ok: print("Warning: read probe failed; continuing cautiously.")

            # init writes
            try:
                with_lock(hand.set_all_finger_speeds, DEFAULT_SPEED, tries=WRITE_TRIES)
                with_lock(hand.set_all_finger_forces, DEFAULT_FORCE, tries=WRITE_TRIES)
            except Exception as e:
                print("Init write failed:", e)

            print_help()

            def worker():
                nonlocal last_action
                while running:
                    try: fn,args,act = q.get(timeout=0.2)
                    except Empty: continue
                    try:
                        if act:
                            with action_lock: last_action=act
                        with_lock(fn,*args,tries=WRITE_TRIES)
                        time.sleep(CMD_COOLDOWN)
                    except Exception as e:
                        print(f"{act or 'Command'} error:", e)
                    finally: q.task_done()

            threading.Thread(target=worker,daemon=True).start()

            def recorder():
                nonlocal last_action
                dt = 1.0/SAMPLE_HZ if SAMPLE_HZ>0 else 0.1
                while running:
                    t0 = time.time()
                    try:
                        forces = get_forces(hand)
                        with action_lock: act = last_action
                        ts = datetime.fromtimestamp(t0).isoformat(timespec="milliseconds")
                        w.writerow([ts, act] + forces)
                    except Exception as e:
                        print("Record error:", e)
                    time.sleep(max(0.0, dt - (time.time()-t0)))

            threading.Thread(target=recorder,daemon=True).start()

            def enqueue(act, fn, *args): q.put((fn,args,act))

            def on_press(key):
                nonlocal running
                if key == keyboard.Key.esc:
                    print("Quitting..."); enqueue("open_all", hand.open_all_fingers); running=False; return False
                if isinstance(key, keyboard.KeyCode) and key.char:
                    c=key.char.lower()
                    if c=='g': enqueue("grip", hand.grip, DEFAULT_FORCE)
                    elif c=='o': enqueue("open_all", hand.open_all_fingers)
                    elif c=='p': enqueue("pinch", hand.pinch, DEFAULT_FORCE)
                    elif c=='f': enqueue("point", hand.point)
                    elif c=='u': enqueue("thumbs_up", hand.thumbs_up)
                    elif c=='e': enqueue("cool", hand.cool)
                    elif c=='h': enqueue("hook_4", hand.hook_4)
                    elif c=='c': enqueue("close_all", hand.close_all_fingers)

            from pynput import keyboard as kb
            with kb.Listener(on_press=on_press) as listener:
                listener.join()
            q.join()

    except exceptions.ConnectionError as e:
        print("ConnectionError:", e)
    except Exception as e:
        print("Unexpected error:", e)
    finally:
        running=False
        try: f.close()
        except: pass
        print(f"CSV saved: {path.resolve()}")

if __name__ == "__main__":
    main()
