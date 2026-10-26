# =============================================================================
# 02_sensor_reactive.py
#
# Beginner example — react to IR sensors with the tilting module.
# The plate tilts toward whatever direction detects an object nearby.
# Run this on your Sthymuli robot from TigerPythonWeb.
# =============================================================================

from sthymuli import Sthymuli, Shape

bot = Sthymuli("tilting")

# Register event handlers for each direction
@bot.on_sensor("north", threshold=0.15)
def on_north(value):
    bot.leds.show(Shape.NORTH, color=(0, 100, 255))
    bot.tilt.go("north", speed=value, wait=False)

@bot.on_sensor("south", threshold=0.15)
def on_south(value):
    bot.leds.show(Shape.SOUTH, color=(0, 100, 255))
    bot.tilt.go("south", speed=value, wait=False)

@bot.on_sensor("east", threshold=0.15)
def on_east(value):
    bot.leds.show(Shape.EAST, color=(0, 100, 255))
    bot.tilt.go("east", speed=value, wait=False)

@bot.on_sensor("west", threshold=0.15)
def on_west(value):
    bot.leds.show(Shape.WEST, color=(0, 100, 255))
    bot.tilt.go("west", speed=value, wait=False)

# Start — runs until Ctrl-C
bot.run()
