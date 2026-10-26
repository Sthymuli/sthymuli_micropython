# =============================================================================
# 03_manual_loop.py
#
# Advanced example — manual while loop with direct module imports.
# Gives full control over timing and what happens each step.
# =============================================================================

from sthymuli.tilting import TiltingModule
from sthymuli.sensors import Sensors
from sthymuli.leds import LEDs, Shape, Pattern
import time

# Initialise each module independently
sensors = Sensors()
tilt    = TiltingModule()
leds    = LEDs()

leds.show(Shape.RING, color=(0, 80, 0))   # dim green ring = ready

print("Running — Ctrl-C to stop")

try:
    while True:
        sensors.update()               # read all IR channels
        tilt.update(sensors)           # move plate based on sensors
        leds.reactive(sensors)         # colour LEDs green→red per quadrant
        time.sleep_ms(20)

except KeyboardInterrupt:
    leds.off()
    tilt.center()
    print("Stopped.")
