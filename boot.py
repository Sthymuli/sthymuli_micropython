# boot.py — runs once on power-up, before main.py
#
# Holds the power latch (GPIO6) so the board stays on,
# then immediately returns so the REPL stays accessible.
# Do NOT put any blocking code here.

from machine import Pin
Pin(6, Pin.OUT).value(1)   # power latch — must be held HIGH
