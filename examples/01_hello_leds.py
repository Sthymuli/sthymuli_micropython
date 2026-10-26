# =============================================================================
# 01_hello_leds.py
#
# Beginner example — show shapes on the LED ring.
# Run this on your Sthymuli robot from TigerPythonWeb.
# =============================================================================

from sthymuli import Sthymuli, Shape, Pattern

bot = Sthymuli()           # initialise (no module needed for LEDs only)

# Show a few shapes
bot.leds.show(Shape.RING)          # all LEDs on
import time; time.sleep(1)

bot.leds.show(Shape.STAR, color=(255, 100, 0))   # orange star
time.sleep(1)

bot.leds.show(Shape.NORTH, color=(0, 0, 255))    # blue north arc
time.sleep(1)

bot.leds.show(Shape.CROSS, color=(255, 0, 0))    # red cross
time.sleep(1)

# Progress bar — fill LEDs one by one
for n in range(25):
    bot.leds.level(n, color=(0, 200, 0))
    time.sleep_ms(80)

# Animated pattern
bot.leds.animate(Pattern.BREATHE, color=(0, 0, 200), duration_ms=3000)

bot.leds.off()
print("Done!")
