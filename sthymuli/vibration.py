# =============================================================================
# sthymuli/vibration.py
#
# Vibration module — controls vibration motors via MCP23017 @ 0x21
# Each motor maps to a cardinal direction on the robot body.
# =============================================================================

from ._hardware import i2c_write, i2c_read, MCP_ADDR, get_i2c
import time

# ── MCP23017 @ 0x21 (motor direction / vibration) ────────────────────────────
VIB_ADDR   = 0x21
VIB_IODIRA = 0x00
VIB_IODIRB = 0x01
VIB_GPIOA  = 0x12
VIB_GPIOB  = 0x13

# Motor bit positions on GPIOA (update to match your PCB)
_MOTOR_BITS = {
    'north': 0,   # GPA0
    'east':  1,   # GPA1
    'south': 2,   # GPA2
    'west':  3,   # GPA3
}

# =============================================================================
# VibrationModule class
# =============================================================================
class VibrationModule:
    """
    Controls vibration motors on the Sthymuli vibration module.

    Usage:
        vib = VibrationModule()
        vib.on("north")
        vib.on(["north", "east"])
        vib.off("north")
        vib.off()                       # all off
        vib.pulse("north", duration=300)
        vib.set(north=True, east=False)
        vib.pattern(["north","south","east","west"], interval=150)
    """

    def __init__(self):
        self._state = 0x00   # shadow register for GPIOA
        self._vib_ok = VIB_ADDR in get_i2c().scan()

        if self._vib_ok:
            i2c_write(VIB_ADDR, VIB_IODIRA, 0x00)  # all outputs
            i2c_write(VIB_ADDR, VIB_IODIRB, 0x00)
            self._apply()
            print("[VIB] MCP23017 @ 0x21 ready")
        else:
            print("[VIB] MCP23017 @ 0x21 NOT FOUND — check wiring")

    # ── Public API ────────────────────────────────────────────────────────────

    def on(self, direction):
        """
        Turn on one or more motors.
        direction: 'north'|'east'|'south'|'west' or list of them

        Examples:
            vib.on("north")
            vib.on(["north", "east"])
        """
        for d in self._to_list(direction):
            bit = _MOTOR_BITS.get(str(d).lower())
            if bit is not None:
                self._state |= (1 << bit)
        self._apply()

    def off(self, direction=None):
        """
        Turn off one or more motors, or all if direction is None.

        Examples:
            vib.off("north")
            vib.off()
        """
        if direction is None:
            self._state = 0x00
        else:
            for d in self._to_list(direction):
                bit = _MOTOR_BITS.get(str(d).lower())
                if bit is not None:
                    self._state &= ~(1 << bit)
        self._apply()

    def set(self, north=None, east=None, south=None, west=None):
        """
        Set each motor explicitly.

        Example:
            vib.set(north=True, east=False, south=True, west=False)
        """
        mapping = {'north': north, 'east': east, 'south': south, 'west': west}
        for name, val in mapping.items():
            if val is None:
                continue
            bit = _MOTOR_BITS[name]
            if val:
                self._state |= (1 << bit)
            else:
                self._state &= ~(1 << bit)
        self._apply()

    def pulse(self, direction, duration=300):
        """
        Turn motor(s) on for duration ms then off. Blocking.

        Example:
            vib.pulse("north", duration=500)
        """
        self.on(direction)
        time.sleep_ms(duration)
        self.off(direction)

    def pattern(self, sequence, interval=200, repeat=1):
        """
        Play a sequence of motor activations. Blocking.

        sequence : list of direction names, played one at a time
        interval : ms each step lasts
        repeat   : how many times to loop

        Example:
            vib.pattern(["north","east","south","west"], interval=150, repeat=2)
        """
        for _ in range(repeat):
            for direction in sequence:
                self.off()
                self.on(direction)
                time.sleep_ms(interval)
        self.off()

    def buzz(self, times=3, on_ms=100, off_ms=100):
        """
        Pulse all motors together.

        Example:
            vib.buzz(times=2)
        """
        for _ in range(times):
            self.on(['north', 'east', 'south', 'west'])
            time.sleep_ms(on_ms)
            self.off()
            time.sleep_ms(off_ms)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _apply(self):
        if self._vib_ok:
            i2c_write(VIB_ADDR, VIB_GPIOA, self._state)

    @staticmethod
    def _to_list(val):
        if isinstance(val, list):
            return val
        return [val]
