# Inspire-Hand Control & Gesture Framework  
Python control framework for the **Inspire Robots RH56-series dexterous hand**  
Keyboard control • safe threaded command execution • Modbus communication • custom gestures • error handling

## ✨ Features  
- **Full keyboard control** using `pynput`  
- **All official Inspire gestures** + many **custom gestures**  
- **Thread-safe command queue** (prevents mixed RS-485 frames)  
- **Live finger feedback:** angles, forces, temperatures, statuses  
- **Unified error handler:** read, decode, clear errors safely  
- **Modular structure:**  
  - `hands_1.py` → Hardware API + gestures  
  - `keyboard_control_pynput.py` → Hotkey controller  
  - `hello_hand.py` → Minimal usage example  
- **Easily extendable** - add new gestures in one class

## 🧩 Project Structure  
```
project/
│
├── hands_1.py                 # Inspire Hand interface + gestures + error tools
├── keyboard_control_pynput.py # Keyboard controller (hotkeys, queue, safe I/O)
├── hello_hand.py              # Quick connectivity + basic functionality test
└── recordings/                # (Optional) saved CSV logs from experiments
```

## 🔌 Hardware Requirements
- Inspire Robots RH56 DFQ / DFX dexterous hand  
- USB → RS-485 adapter (FTDI recommended)  
- Correct wiring:  
  - A ↔ A  
  - B ↔ B  
  - GND shared  
- Modbus RTU settings:  
  - ID = **1**  
  - Baud = **115200**, **8N1**

## 🛠 Installation

### 1. Create and activate a virtual environment  
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
```

### 2. Install dependencies  
```bash
pip install pynput
pip install inspire-hand
```

### 3. Clone the repository  
```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

## 🧪 Quick Test  
Run a simple connectivity test:

```bash
python hello_hand.py
```

## ⌨️ Keyboard Control  
Run the main controller:

```bash
python keyboard_control_pynput.py
```

### Hotkeys  
| Key | Action |
|-----|--------|
| **g** | Grip |
| **o** | Open all fingers |
| **p** | Pinch |
| **f** | Point |
| **u** | Thumbs up |
| **e** | Cool gesture |
| **h** | Hook 4 |
| **j** | Hook 2 (stage 1) |
| **k** | Hook 2 (stage 2) |
| **l** | Little finger hook |
| **d** | Hook for door |
| **r** | Thumb front ready |
| **t** | Toilet stick gesture |
| **c** | Close all fingers |
| **x** | Clear errors (safe, with decode) |
| **Esc** | Quit & open all |

## 🧠 Hand API (hands_1.py)

### Gesture Functions
- `open_all_fingers()`  
- `close_all_fingers()`  
- `pinch(force)`  
- `thumbs_up()`  
- `cool()`  
- `hook_4()`  
- `little_hook()`  
- `hook_2_1()`  
- `hook_2_2()`  
- `hook_for_door()`  
- `stronger_no_bend()`  
- `toilet_stick()`  

### Feedback Functions
- `get_finger_angles()`  
- `get_finger_forces()`  
- `get_finger_statuses()`  
- `get_finger_errors()`  
- `get_finger_temperatures()`  

### Error Handling
- `reset()` - clear errors (direct register write)  
- `clear_errors_if_needed()` - clear only if errors exist  
- `describe_finger_errors()` - decode bit-masks into readable messages  

## 🔒 Thread-Safe Command Execution  
The system uses:

- A **Queue()** for incoming commands  
- A **worker thread** for executing RS-485 writes  
- A **debounce layer** for keyboard events  
- A **global lock** for all Modbus reads/writes  

This ensures:

- Commands are never interleaved  
- No corrupted Modbus frames  
- No “No response” / “Invalid response” spam  
- Safe gesture execution every time  

## ⚠️ Safety Notes  
- Always test new gestures at **low force values** (200-400).  
- Keep the hand clear of edges/obstacles.  
- Before closing the application, fingers should be **opened**.  
- Allow cooling if temperature errors appear.

## 📈 Extending the Project  
To create a new gesture:

1. Open `hands_1.py`  
2. Add a new method  
3. Combine finger `.open()`, `.close()`, `.move()` sequences  
4. Add a key binding in `keyboard_control_pynput.py`  

Done - no communication-layer changes needed.

## 🪲 Troubleshooting

### “No response received”
- Another app is using the same COM port  
- Wrong wiring (swap A/B if needed - safe)  
- Wrong slave ID  
- Missing ground reference  

### “LOCKED_ROTOR” / “OVER_CURRENT”
- Something is blocking the motion  
- Force threshold too high  
- Clear via **`x`** hotkey  

### “Over temperature”
- Let motors cool 2-3 minutes  
- Lower force or speed  

## 📜 License  
MIT License

## 🙌 Credits  
- **Inspire Robots** - hardware & protocol  
- **sentdex** - code structure
- **Alon Laron** - controller, gestures, integration  

