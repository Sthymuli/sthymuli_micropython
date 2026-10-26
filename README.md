# sthymuli — MicroPython Library

A MicroPython library for the **Sthymuli educational robot**, designed to work with [TigerPythonWeb](https://test.webtigerpython.ethz.ch). Inspired by the micro:bit API — simple enough for beginners, extensible enough for advanced users.

---

## Hardware

| Component | Details |
|---|---|
| Board | ESP32-S3-WROOM-1-N16 |
| Servo driver | PCA9685 @ I2C 0x40 |
| I/O expander | MCP23017 @ I2C 0x20 (IR mux) |
| Vibration motors | MCP23017 @ I2C 0x21 |
| IR sensors | 8-channel, 74HC4051 mux, ADC GPIO4 |
| LEDs | WS2812 × 25 (24 active), GPIO9 |
| I2C bus | SDA = GPIO48, SCL = GPIO47 |
| Power latch | GPIO6 (must be HIGH) |

---

## Installation

This is a **one-time setup** done by the teacher or lab technician. Students never need to repeat it.

---

### Step 1 — Flash MicroPython onto the board

The Sthymuli robot ships with Arduino firmware. You need to replace it with MicroPython once.

**Requirements:**
- Python 3 installed on your computer
- USB cable connected to the robot

**Install esptool:**
```bash
pip install esptool
```

**Download MicroPython** for ESP32-S3 from:
[micropython.org/download/ESP32_GENERIC_S3](https://micropython.org/download/ESP32_GENERIC_S3/)
Download the latest `.bin` file.

**Erase the old firmware:**
```bash
esptool --chip esp32s3 --port /dev/cu.usbmodem101 erase-flash
```
> On Windows the port will be `COM3` or similar. On Linux `/dev/ttyUSB0`.

**Flash MicroPython:**
```bash
esptool --chip esp32s3 --port /dev/cu.usbmodem101 write-flash -z 0x0 ESP32_GENERIC_S3.bin
```

---

### Step 2 — Upload the boot file

The `boot.py` file holds the power latch (GPIO6) so the board stays on, and keeps the REPL accessible so tools like mpremote can always connect — no buttons needed.

**Install mpremote:**
```bash
pip install mpremote
```

**Upload boot.py** from this repository:
```bash
mpremote connect /dev/cu.usbmodem101 cp boot.py :boot.py
```

> ⚠️ This step is critical. Without `boot.py`, the board may become unreachable after the first program runs, requiring physical access to the BOOT/RESET buttons to recover.

---

### Step 3 — Upload the library

From the root of this repository:
```bash
mpremote connect /dev/cu.usbmodem101 cp -r sthymuli/ :
```

**Verify the upload:**
```bash
mpremote connect /dev/cu.usbmodem101 ls :sthymuli/
```

You should see all 6 files: `__init__.py`, `_hardware.py`, `leds.py`, `sensors.py`, `tilting.py`, `vibration.py`.

---

### Step 4 — Test

Open [TigerPythonWeb](https://test.webtigerpython.ethz.ch), select **ESP32**, connect to the board, and run:

```python
from sthymuli.leds import LEDs, Shape

leds = LEDs()
leds.show(Shape.RING, color=(0, 150, 0))
```

The LED ring should light up green. The board is ready for students.

---

### mip (alternative — requires WiFi on the board)

```python
import mip
mip.install("github:Sthymuli/sthymuli_micropython")
```

---

### Recovering a locked board

If mpremote cannot connect (`could not enter raw repl`), a program is blocking the REPL. This should not happen if `boot.py` was uploaded correctly. If it does:

```bash
# Send Ctrl-C over serial to interrupt the running program
python3 -c "
import serial, time
s = serial.Serial('/dev/cu.usbmodem101', 115200, timeout=2)
s.write(b'\r\x03\x03\r\x03\x03')
time.sleep(1)
print(s.read(200))
s.close()
"
```

Then retry mpremote. As a last resort, re-flash MicroPython from Step 1.

---

## Quick Start

### Beginner — one object, event-driven

```python
from sthymuli import Sthymuli, Shape, Pattern

bot = Sthymuli("tilting")           # initialise tilting module
bot.leds.show(Shape.STAR)           # show a star on the LED ring

@bot.on_sensor("north")             # register an event handler
def north_triggered(value):
    bot.tilt.go("north", speed=value)

bot.run()                           # start the event loop
```

### Advanced — manual loop, direct imports

```python
from sthymuli.tilting import TiltingModule
from sthymuli.sensors import Sensors
from sthymuli.leds import LEDs, Shape, Pattern
import time

sensors = Sensors()
tilt    = TiltingModule()
leds    = LEDs()

while True:
    sensors.update()
    tilt.update(sensors)
    leds.reactive(sensors)
    time.sleep_ms(20)
```

---

## API Reference

### `Sthymuli` — main robot object

```python
bot = Sthymuli(module)
```

| Parameter | Values | Description |
|---|---|---|
| `module` | `"tilting"` \| `"vibration"` | Physical module attached to the robot |

**Attributes**

| Attribute | Type | Description |
|---|---|---|
| `bot.leds` | `LEDs` | LED ring controller |
| `bot.sensors` | `Sensors` | IR and IMU sensor reader |
| `bot.tilt` | `TiltingModule` | Servo control (tilting module only) |
| `bot.vibrate` | `VibrationModule` | Motor control (vibration module only) |

**Methods**

| Method | Description |
|---|---|
| `bot.run()` | Start main event loop. Blocks until Ctrl-C. |
| `bot.update()` | Single step — call inside your own `while True`. |
| `bot.stop()` | Turn off LEDs and center servos. |
| `bot.on_sensor(direction, threshold=0.1)` | Decorator — register event handler. |

**Event handler example**

```python
@bot.on_sensor("east", threshold=0.3)
def on_east(value):
    print(f"East sensor: {value:.2f}")
    bot.tilt.go("east", speed=value)
```

---

### `LEDs` — LED ring

```python
from sthymuli.leds import LEDs, Shape, Pattern
leds = LEDs(brightness=0.86)
```

#### `leds.show(shape_or_pattern, color=None)`

Display a `Shape` or `Pattern` constant.

```python
leds.show(Shape.RING)
leds.show(Shape.STAR, color=(255, 100, 0))   # orange star
leds.show(Shape.NORTH, color=(0, 0, 255))    # blue north arc
leds.show(Pattern.BREATHE, color=(0, 0, 255))
```

#### `leds.color(r, g, b)`

Set all active LEDs to one colour.

```python
leds.color(0, 255, 0)    # all green
leds.color(255, 0, 0)    # all red
```

#### `leds.off()`

Turn off all active LEDs.

#### `leds.set_pixel(index, r, g, b)`

Set a single LED (0–23).

```python
leds.set_pixel(0, 255, 0, 0)   # pixel 0 red
```

#### `leds.set_quadrant(quadrant, r, g, b)`

Light up one quadrant.

```python
leds.set_quadrant("north", 0, 255, 0)
leds.set_quadrant(0, 0, 255, 0)         # same — 0=north
```

#### `leds.animate(pattern, color=None, duration_ms=2000)`

Run an animated pattern for a fixed duration. Blocks.

```python
leds.animate(Pattern.BREATHE, color=(0, 0, 255), duration_ms=3000)
leds.animate(Pattern.SPIN, duration_ms=2000)
```

#### `leds.set_brightness(brightness)`

Set global brightness (0.0–1.0).

---

### `Shape` constants

Ring-native geometric shapes. All designed for the 24-LED ring layout.

```python
leds.show(Shape.STAR)
leds.show(Shape.NORTH, color=(0, 0, 255))
```

**Single quadrants**

| Constant | LEDs lit | Description |
|---|---|---|
| `Shape.NORTH` | 6 | Top-centre arc |
| `Shape.EAST` | 6 | Right arc |
| `Shape.SOUTH` | 6 | Bottom-centre arc |
| `Shape.WEST` | 6 | Left arc |

**Combined sectors**

| Constant | LEDs lit | Description |
|---|---|---|
| `Shape.NORTH_EAST` | 12 | Top-right half |
| `Shape.SOUTH_EAST` | 12 | Bottom-right half |
| `Shape.SOUTH_WEST` | 12 | Bottom-left half |
| `Shape.NORTH_WEST` | 12 | Top-left half |
| `Shape.TOP` | 12 | Alias for NORTH_EAST |
| `Shape.BOTTOM` | 12 | Alias for SOUTH_WEST |
| `Shape.LEFT_RIGHT` | 12 | East + West arcs |
| `Shape.TOP_BOTTOM` | 12 | North + South arcs |

**Geometric sparse patterns**

| Constant | LEDs lit | Description |
|---|---|---|
| `Shape.RING` | 24 | All LEDs |
| `Shape.STAR` | 8 | 8 evenly-spaced pixels (every 3rd) |
| `Shape.CROSS` | 4 | Centre pixel of each quadrant |
| `Shape.CORNERS` | 8 | First + last pixel of each quadrant |
| `Shape.DOTS` | 12 | Every other pixel |
| `Shape.HALF_TOP` | 12 | Upper 12 LEDs |
| `Shape.HALF_BOTTOM` | 12 | Lower 12 LEDs |

**Progress bar — `leds.level(n, color)`**

Fill `n` out of 24 LEDs clockwise around the ring.

```python
leds.level(24, color=(0, 255, 0))   # full ring green
leds.level(12, color=(0, 0, 255))   # half ring blue
leds.level(6,  color=(255, 0, 0))   # quarter ring red
leds.level(0)                       # empty
```

---

### `Pattern` constants

Sthymuli ring-specific patterns.

| Constant | Description |
|---|---|
| `Pattern.WELCOME` | Spinning meteor (boot animation) |
| `Pattern.NORTH` | North quadrant lit |
| `Pattern.EAST` | East quadrant lit |
| `Pattern.SOUTH` | South quadrant lit |
| `Pattern.WEST` | West quadrant lit |
| `Pattern.ALL` | All LEDs |
| `Pattern.BREATHE` | Slow sine fade in/out |
| `Pattern.PULSE` | Fast single pulse |
| `Pattern.SPIN` | Spinning meteor |
| `Pattern.REACTIVE` | Green→red per quadrant from sensors |

---

### `Sensors` — IR and IMU

```python
from sthymuli.sensors import Sensors
sensors = Sensors()
```

#### `sensors.update()`

Read all IR channels. Call once per loop iteration.

#### `sensors.ir(channel)` → `float` 0.0–1.0

Normalised proximity for a channel. `0.0` = nothing detected, `1.0` = very close.

```python
sensors.ir("north")    # by name
sensors.ir(1)          # by channel number
```

| Name | Channel |
|---|---|
| `"north"` | 1 |
| `"east"` | 3 |
| `"south"` | 5 |
| `"west"` | 7 |

#### `sensors.ir_raw(channel)` → `int` 0–4095

Raw ADC value before normalisation.

#### `sensors.active()` → `list[str]`

List of direction names currently above the detection threshold.

```python
sensors.active()   # e.g. ['north', 'east']
```

#### `sensors.any_active()` → `bool`

True if any sensor detects something.

#### `sensors.all_saturated()` → `bool`

True if all four sensors are near maximum (robot surrounded).

#### `sensors.all_idle()` → `bool`

True if no sensor detects anything.

#### `sensors.accel()` → `(x, y, z)`

Accelerometer readings in g.

```python
x, y, z = sensors.accel()
```

#### `sensors.tilt()` → `(pitch_deg, roll_deg)`

Board tilt angles in degrees from accelerometer.

```python
pitch, roll = sensors.tilt()
```

---

### `TiltingModule` — servo plate

```python
from sthymuli.tilting import TiltingModule
tilt = TiltingModule()
```

#### `tilt.center()`

Move both servos to center (0°, 0°). Blocking.

#### `tilt.go(direction, speed=1.0, wait=True)`

Move plate toward a named direction.

```python
tilt.go("north")                    # full speed, blocking
tilt.go("east", speed=0.5)          # half speed
tilt.go("west", wait=False)         # non-blocking, one step
```

| Parameter | Values | Default |
|---|---|---|
| `direction` | `"north"` \| `"east"` \| `"south"` \| `"west"` \| `"center"` | required |
| `speed` | `0.0–1.0` | `1.0` |
| `wait` | `True` \| `False` | `True` |

#### `tilt.set_angle(x_deg=None, y_deg=None)`

Set plate angle directly in degrees (±85° max).

```python
tilt.set_angle(x_deg=30)
tilt.set_angle(x_deg=20, y_deg=-15)
```

#### `tilt.get_angle()` → `(x_deg, y_deg)`

Current plate angle in degrees.

#### `tilt.update(sensors)`

Reactive update from live sensor readings. Call in your loop.

```python
while True:
    sensors.update()
    tilt.update(sensors)
    time.sleep_ms(20)
```

---

### `VibrationModule` — vibration motors

```python
from sthymuli.vibration import VibrationModule
vib = VibrationModule()
```

#### `vib.on(direction)`

Turn on one or more motors.

```python
vib.on("north")
vib.on(["north", "east"])
```

#### `vib.off(direction=None)`

Turn off motors. Pass nothing to turn all off.

```python
vib.off("north")
vib.off()           # all off
```

#### `vib.set(north=None, east=None, south=None, west=None)`

Set each motor explicitly.

```python
vib.set(north=True, east=False)
```

#### `vib.pulse(direction, duration=300)`

Turn motor on for `duration` ms then off. Blocking.

```python
vib.pulse("north", duration=500)
```

#### `vib.pattern(sequence, interval=200, repeat=1)`

Play a sequence of activations. Blocking.

```python
vib.pattern(["north","east","south","west"], interval=150, repeat=2)
```

#### `vib.buzz(times=3, on_ms=100, off_ms=100)`

Pulse all motors together.

```python
vib.buzz(times=2)
```

---

## Example programs

### Minimal tilt demo

```python
from sthymuli import Sthymuli

bot = Sthymuli("tilting")

while True:
    bot.update()
```

### Sensor-reactive with LEDs

```python
from sthymuli import Sthymuli, Shape

bot = Sthymuli("tilting")

@bot.on_sensor("north")
def on_north(v):
    bot.tilt.go("north", speed=v, wait=False)

@bot.on_sensor("south")
def on_south(v):
    bot.tilt.go("south", speed=v, wait=False)

bot.leds.show(Shape.NORTH)
bot.run()
```

### Vibration compass

```python
from sthymuli import Sthymuli

bot = Sthymuli("vibration")

@bot.on_sensor("north")
def on_north(v):
    bot.vibrate.pulse("north", duration=200)

@bot.on_sensor("east")
def on_east(v):
    bot.vibrate.pulse("east", duration=200)

bot.run()
```

### Direct angle control

```python
from sthymuli.tilting import TiltingModule
import time

tilt = TiltingModule()

# sweep north then back to center
tilt.set_angle(x_deg=45)
time.sleep(1)
tilt.center()
```

---

## Module architecture

```
sthymuli/
  __init__.py    ← Sthymuli class, Shape + Pattern re-exports
  _hardware.py   ← I2C bus, PCA9685, MCP23017 low-level drivers
  leds.py        ← LEDs class, Shape constants, Pattern constants
  sensors.py     ← Sensors class (IR + IMU)
  tilting.py     ← TiltingModule class
  vibration.py   ← VibrationModule class
```

New modules (wheels, sound, gripper...) follow the same pattern:
1. Create `yourmodule.py` with a single class
2. Import it in `__init__.py` under the matching `module=` string
3. Expose it as `bot.yourmodule`

---

## Licence

MIT — developed at EPFL as part of the Sthymuli educational robotics project.
