# =============================================================================
# 04_vibration.py
#
# Beginner example — vibration module.
# Pulses vibration motors in the direction of detected objects.
# =============================================================================

from sthymuli import Sthymuli

bot = Sthymuli("vibration")

@bot.on_sensor("north", threshold=0.2)
def on_north(value):
    bot.vibrate.pulse("north", duration=200)

@bot.on_sensor("south", threshold=0.2)
def on_south(value):
    bot.vibrate.pulse("south", duration=200)

@bot.on_sensor("east", threshold=0.2)
def on_east(value):
    bot.vibrate.pulse("east", duration=200)

@bot.on_sensor("west", threshold=0.2)
def on_west(value):
    bot.vibrate.pulse("west", duration=200)

bot.run()
