# =============================================================================
# sthymuli/__init__.py
#
# Top-level API — exposes the Sthymuli class and all constants.
#
# Beginner usage:
#   from sthymuli import Sthymuli
#   bot = Sthymuli("tilting")
#   bot.leds.show(Image.HEART)
#   bot.tilt.go("north")
#   bot.run()
#
# Advanced usage:
#   from sthymuli.tilting import TiltingModule
#   from sthymuli.leds import LEDs, Image, Pattern
#   from sthymuli.sensors import Sensors
# =============================================================================

from .leds     import LEDs, Shape, Pattern
from .sensors  import Sensors
from ._hardware import power_latch, ir_emitter_on
import time

# Re-export for star imports
__all__ = ['Sthymuli', 'Shape', 'Pattern']

# =============================================================================
# Sthymuli — top-level robot object
# =============================================================================
class Sthymuli:
    """
    Main entry point for the Sthymuli robot.

    Parameters
    ----------
    module : str
        Which physical module is attached.
        'tilting'   — tilting plate with servos
        'vibration' — vibration motor array

    Example
    -------
        from sthymuli import Sthymuli, Image, Pattern

        bot = Sthymuli("tilting")
        bot.leds.show(Image.HEART)
        bot.tilt.go("north")

        @bot.on_sensor("north")
        def handle_north(value):
            bot.tilt.go("north", speed=value)

        bot.run()
    """

    def __init__(self, module="tilting"):
        print(f"[STHYMULI] Starting module: {module}")

        # Power latch + IR emitter — always first
        power_latch()
        ir_emitter_on()

        # Shared hardware
        self.leds    = LEDs()
        self.sensors = Sensors()

        # Module-specific
        self._module = module.lower()
        self.tilt    = None
        self.vibrate = None

        if self._module == "tilting":
            from .tilting import TiltingModule
            self.tilt = TiltingModule()
        elif self._module == "vibration":
            from .vibration import VibrationModule
            self.vibrate = VibrationModule()
        else:
            print(f"[STHYMULI] Unknown module '{module}' — hardware not initialised")

        # Event handlers registry
        self._handlers = {}

        # Welcome animation
        self.leds.animate(Pattern.WELCOME, duration_ms=5000)
        print("[STHYMULI] Ready.")

    # ── Event handler decorator ───────────────────────────────────────────────

    def on_sensor(self, direction, threshold=0.1):
        """
        Decorator — register a function to call when a sensor exceeds threshold.

        Example:
            @bot.on_sensor("north")
            def north_triggered(value):
                bot.tilt.go("north", speed=value)
        """
        def decorator(fn):
            self._handlers[direction.lower()] = (fn, threshold)
            return fn
        return decorator

    # ── Built-in run loop ─────────────────────────────────────────────────────

    def run(self, ir_poll_ms=100, servo_ms=20, led_ms=16):
        """
        Start the main event loop. Blocks until KeyboardInterrupt.

        Polls sensors, fires registered event handlers, updates servos
        and LEDs automatically.

        Example:
            bot.run()
        """
        print("[STHYMULI] run() started — Ctrl-C to stop")

        last_ir   = time.ticks_ms()
        last_srv  = time.ticks_ms()
        last_led  = time.ticks_ms()
        last_dbg  = time.ticks_ms()

        try:
            while True:
                now = time.ticks_ms()

                # IR polling
                if time.ticks_diff(now, last_ir) >= ir_poll_ms:
                    last_ir = now
                    self.sensors.update()
                    self._fire_handlers()

                # Servo update
                if time.ticks_diff(now, last_srv) >= servo_ms:
                    last_srv = now
                    if self.tilt:
                        self.tilt.update(self.sensors)

                # LED update
                if time.ticks_diff(now, last_led) >= led_ms:
                    last_led = now
                    self._auto_leds(now)

                # Debug print at 1 Hz
                if time.ticks_diff(now, last_dbg) >= 1000:
                    last_dbg = now
                    self._debug_print()

        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """Stop safely — LEDs off, servos centered."""
        self.leds.off()
        if self.tilt:
            self.tilt.center()
        print("[STHYMULI] Stopped.")

    # ── Manual loop helpers ───────────────────────────────────────────────────

    def update(self):
        """
        Single step — call this inside your own while loop.
        Reads sensors and updates servos.

        Example:
            while True:
                bot.update()
                time.sleep_ms(20)
        """
        self.sensors.update()
        self._fire_handlers()
        if self.tilt:
            self.tilt.update(self.sensors)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _fire_handlers(self):
        for direction, (fn, threshold) in self._handlers.items():
            value = self.sensors.ir(direction)
            if value >= threshold:
                fn(value)

    def _auto_leds(self, now_ms):
        """Auto LED mode based on sensor state."""
        if self.sensors.all_saturated():
            self.leds._clear()
            self.leds._red_breathe_frame(now_ms)
            self.leds._write()
        elif self.sensors.all_idle():
            self.leds._clear()
            self.leds._breathe_frame(now_ms, (0, 180, 0))
            self.leds._write()
        else:
            self._reactive_leds(now_ms)

    def _reactive_leds(self, now_ms):
        self.leds._clear()
        dirs = [('north',0), ('east',1), ('south',2), ('west',3)]
        for name, q in dirs:
            p = self.sensors.ir(name)
            if p < 0.05:
                self.leds._quadrant(q, (0, 40, 0))
            else:
                r = int(255 * p)
                g = int(255 * (1.0 - p))
                self.leds._quadrant(q, (r, g, 0))
        # Position overlay
        if self.tilt:
            dx = self.tilt._delta_x / 212
            dy = self.tilt._delta_y / 212
            v = int(abs(dx) * 200)
            if dx > 0.1:
                self._overlay_quad(0, v)
            elif dx < -0.1:
                self._overlay_quad(2, v)
            v = int(abs(dy) * 200)
            if dy > 0.1:
                self._overlay_quad(1, v)
            elif dy < -0.1:
                self._overlay_quad(3, v)
        self.leds._write()

    def _overlay_quad(self, q, v):
        from .leds import QUAD_START, QUAD_COUNT, BATTERY_PIXEL
        start = QUAD_START[q]
        np = self.leds._np
        for i in range(start, start + QUAD_COUNT[q]):
            if i == BATTERY_PIXEL:
                continue
            pr, pg, pb = np[i]
            np[i] = (min(255, pr + v), min(255, pg + v // 3), 0)

    def _debug_print(self):
        n = self.sensors.ir('north')
        s = self.sensors.ir('south')
        e = self.sensors.ir('east')
        w = self.sensors.ir('west')
        print(f"[IR] N={n:.2f} S={s:.2f} E={e:.2f} W={w:.2f}")
        if self.tilt:
            x, y = self.tilt.get_angle()
            print(f"[TILT] x={x:.1f}° y={y:.1f}°")
