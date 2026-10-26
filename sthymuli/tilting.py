# =============================================================================
# sthymuli/tilting.py
#
# Tilting plate module — delta accumulation, no decay.
# Plate holds last position; only moves when sensors are active.
# =============================================================================

from ._hardware import pca_init, pca_set_pwm, PCA_ADDR, get_i2c
import time

# ── Servo config ──────────────────────────────────────────────────────────────
SERVO_NEUTRAL = 350      # pulse count = 90° center
SERVO_LIMIT   = 212      # ±85° in pulse counts  (~2.5 counts/degree)

DRIFT_SPEED   = 3.0      # delta growth per update
DELTA_DEAD    = 0.05     # ignore IR differences below this

# IR channels
CH_NORTH = 1
CH_SOUTH = 5
CH_EAST  = 3
CH_WEST  = 7

# ── Direction presets (normalised delta targets) ──────────────────────────────
_PRESETS = {
    'center': (0.0, 0.0),
    'north':  (1.0, 0.0),
    'south':  (-1.0, 0.0),
    'east':   (0.0, 1.0),
    'west':   (0.0, -1.0),
}

# =============================================================================
# TiltingModule class
# =============================================================================
class TiltingModule:
    """
    Controls the tilting plate via PCA9685 servo driver.

    Usage:
        tilt = TiltingModule()
        tilt.center()
        tilt.go("north")                     # blocking, full speed
        tilt.go("north", speed=0.5)          # half speed
        tilt.go("north", wait=False)         # non-blocking
        tilt.set_angle(x_deg=30, y_deg=-15)  # direct angle control
        tilt.update(sensors)                 # call in loop for reactive mode
    """

    def __init__(self):
        self._delta_x = 0.0
        self._delta_y = 0.0
        self._pca_ok = PCA_ADDR in get_i2c().scan()

        if self._pca_ok:
            pca_init()
            self._send(SERVO_NEUTRAL, SERVO_NEUTRAL)
            print("[TILT] PCA9685 ready — servos centered")
        else:
            print("[TILT] PCA9685 NOT FOUND at 0x40 — check wiring")

    # ── Public API ────────────────────────────────────────────────────────────

    def center(self):
        """Move both servos to center position (0°, 0°). Blocking."""
        self._delta_x = 0.0
        self._delta_y = 0.0
        self._send(SERVO_NEUTRAL, SERVO_NEUTRAL)

    def go(self, direction, speed=1.0, wait=True):
        """
        Move plate toward a named direction.

        direction : 'north'|'south'|'east'|'west'|'center'
        speed     : 0.0–1.0 (fraction of max drift speed)
        wait      : True = block until limit reached; False = one step only

        Examples:
            tilt.go("north")
            tilt.go("east", speed=0.5)
            tilt.go("west", wait=False)
        """
        preset = _PRESETS.get(str(direction).lower())
        if not preset:
            raise ValueError(f"Unknown direction '{direction}'. Use: {list(_PRESETS.keys())}")

        if direction == 'center':
            self.center()
            return

        target_x, target_y = preset
        drift = DRIFT_SPEED * max(0.0, min(1.0, speed))

        if wait:
            # Step until we hit the limit
            max_steps = int(SERVO_LIMIT / max(drift, 0.1)) + 10
            for _ in range(max_steps):
                moved = self._step_toward(target_x, target_y, drift)
                time.sleep_ms(20)
                if not moved:
                    break
        else:
            self._step_toward(target_x, target_y, drift)

    def set_angle(self, x_deg=None, y_deg=None):
        """
        Set plate angle directly in degrees.
        Range: ±85° (clamped to mechanical limit).

        Examples:
            tilt.set_angle(x_deg=30)
            tilt.set_angle(x_deg=20, y_deg=-15)
        """
        if x_deg is not None:
            self._delta_x = max(-SERVO_LIMIT, min(SERVO_LIMIT,
                float(x_deg) * 2.5))
        if y_deg is not None:
            self._delta_y = max(-SERVO_LIMIT, min(SERVO_LIMIT,
                float(y_deg) * 2.5))
        self._apply()

    def get_angle(self):
        """Return current (x_deg, y_deg) plate angle."""
        return (self._delta_x / 2.5, self._delta_y / 2.5)

    def update(self, sensors):
        """
        Reactive update — call this every loop with a Sensors instance.
        Accumulates delta from live IR readings (no-decay behaviour).

        Returns True if the plate moved.
        """
        from ._hardware import i2c_read   # avoid circular import at module level
        import math

        raw_x = float(sensors._ir_values[CH_NORTH] - sensors._ir_values[CH_SOUTH])
        raw_y = float(sensors._ir_values[CH_EAST]  - sensors._ir_values[CH_WEST])

        norm_x = max(-1.0, min(1.0, raw_x / 4095.0))
        norm_y = max(-1.0, min(1.0, raw_y / 4095.0))

        moved = False
        if abs(norm_x) >= DELTA_DEAD:
            self._delta_x += norm_x * DRIFT_SPEED
            moved = True
        if abs(norm_y) >= DELTA_DEAD:
            self._delta_y += norm_y * DRIFT_SPEED
            moved = True

        self._delta_x = max(-SERVO_LIMIT, min(SERVO_LIMIT, self._delta_x))
        self._delta_y = max(-SERVO_LIMIT, min(SERVO_LIMIT, self._delta_y))
        self._apply()
        return moved

    # ── Internal ──────────────────────────────────────────────────────────────

    def _step_toward(self, target_x, target_y, drift):
        """Take one drift step toward target. Returns False if already at limit."""
        prev_x, prev_y = self._delta_x, self._delta_y

        if abs(target_x) > 0:
            self._delta_x += target_x * drift
        if abs(target_y) > 0:
            self._delta_y += target_y * drift

        self._delta_x = max(-SERVO_LIMIT, min(SERVO_LIMIT, self._delta_x))
        self._delta_y = max(-SERVO_LIMIT, min(SERVO_LIMIT, self._delta_y))
        self._apply()

        return (self._delta_x != prev_x) or (self._delta_y != prev_y)

    def _apply(self):
        pos_x = int(SERVO_NEUTRAL + self._delta_x)
        pos_y = int(SERVO_NEUTRAL + self._delta_y)
        self._send(pos_x, pos_y)

    def _send(self, pos_x, pos_y):
        if not self._pca_ok:
            return
        pca_set_pwm(0, 0, pos_x)
        pca_set_pwm(1, 0, pos_y)
