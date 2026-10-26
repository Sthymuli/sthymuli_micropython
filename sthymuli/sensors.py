# =============================================================================
# sthymuli/sensors.py
#
# Sensor abstraction — IR proximity + IMU (LSM6DS3)
# Shared by all modules that read sensor data.
# =============================================================================

from ._hardware import (
    mcp_init, mcp_set_ir_channel, mcp_read_gpiob,
    get_adc, i2c_read, i2c_write, MCP_ADDR, get_i2c
)
import time

# ── IR config ─────────────────────────────────────────────────────────────────
IR_CHANNELS       = 8
IR_SAMPLES        = 10
IR_EMA_ALPHA      = 0.2
IR_THRESHOLD_LOW  = 300
IR_THRESHOLD_HIGH = 3500
IR_DEAD_ZONE      = 0.05
SATURATION_MARGIN = 0.90

# Named channel map
_CHANNEL_NAMES = {
    'north': 1, 'n': 1,
    'east':  3, 'e': 3,
    'south': 5, 's': 5,
    'west':  7, 'w': 7,
}

# ── IMU config (LSM6DS3 @ 0x6A) ───────────────────────────────────────────────
IMU_ADDR       = 0x6A
IMU_CTRL1_XL   = 0x10   # accel config
IMU_OUTX_L_XL  = 0x28   # accel X low byte

# =============================================================================
# Sensors class
# =============================================================================
class Sensors:
    """
    Reads IR proximity sensors and IMU.

    Usage:
        sensors = Sensors()
        sensors.update()                    # read all IR channels

        sensors.ir("north")                 # proximity 0.0–1.0
        sensors.ir(1)                       # by channel number
        sensors.ir_raw("north")             # raw ADC value 0–4095
        sensors.active()                    # list of active direction names
        sensors.any_active()                # True if anything detected
        sensors.all_saturated()             # True if all sensors maxed

        sensors.accel()                     # (x, y, z) in g
        sensors.tilt()                      # (pitch_deg, roll_deg)
    """

    def __init__(self):
        self._ir_values   = [0] * IR_CHANNELS
        self._ir_filtered = [0.0] * IR_CHANNELS
        self._mcp_ok = MCP_ADDR in get_i2c().scan()
        self._imu_ok = IMU_ADDR in get_i2c().scan()

        if self._mcp_ok:
            mcp_init()
        if self._imu_ok:
            self._imu_init()

    # ── IR ────────────────────────────────────────────────────────────────────

    def update(self):
        """Poll all IR channels. Call this once per loop iteration."""
        if not self._mcp_ok:
            return
        adc = get_adc()
        for ch in range(IR_CHANNELS):
            mcp_set_ir_channel(ch)
            time.sleep_us(200)
            total = sum(adc.read() for _ in range(IR_SAMPLES))
            time.sleep_us(100 * IR_SAMPLES)
            raw = total // IR_SAMPLES
            self._ir_values[ch] = raw
            if self._ir_filtered[ch] == 0.0:
                self._ir_filtered[ch] = float(raw)
            else:
                self._ir_filtered[ch] = (IR_EMA_ALPHA * raw +
                    (1.0 - IR_EMA_ALPHA) * self._ir_filtered[ch])

    def ir(self, channel):
        """
        Return normalised proximity for a channel (0.0 = nothing, 1.0 = very close).
        channel: 'north'|'east'|'south'|'west' or channel number 0–7
        """
        ch = self._resolve_channel(channel)
        return self._proximity(ch)

    def ir_raw(self, channel):
        """Return raw ADC value (0–4095) for a channel."""
        ch = self._resolve_channel(channel)
        return self._ir_values[ch]

    def active(self):
        """Return list of direction names currently above dead zone."""
        result = []
        for name, ch in [('north',1),('east',3),('south',5),('west',7)]:
            if self._proximity(ch) >= IR_DEAD_ZONE:
                result.append(name)
        return result

    def any_active(self):
        """True if any sensor is above the dead zone threshold."""
        return len(self.active()) > 0

    def all_saturated(self):
        """True if all four cardinal sensors are near maximum."""
        for ch in [1, 3, 5, 7]:
            if self._proximity(ch) < SATURATION_MARGIN:
                return False
        return True

    def all_idle(self):
        """True if no sensor is above the dead zone threshold."""
        for ch in [1, 3, 5, 7]:
            if self._proximity(ch) >= IR_DEAD_ZONE:
                return False
        return True

    # ── IMU ───────────────────────────────────────────────────────────────────

    def accel(self):
        """
        Return (x, y, z) accelerometer readings in g.
        Returns (0,0,0) if IMU not available.
        """
        if not self._imu_ok:
            return (0.0, 0.0, 0.0)
        try:
            data = i2c_read(IMU_ADDR, IMU_OUTX_L_XL, 6)
            x = self._to_signed(data[0] | (data[1] << 8)) * 0.000061
            y = self._to_signed(data[2] | (data[3] << 8)) * 0.000061
            z = self._to_signed(data[4] | (data[5] << 8)) * 0.000061
            return (x, y, z)
        except:
            return (0.0, 0.0, 0.0)

    def tilt(self):
        """
        Return (pitch_deg, roll_deg) from accelerometer.
        Returns (0,0) if IMU not available.
        """
        import math
        x, y, z = self.accel()
        pitch = math.atan2(x, math.sqrt(y*y + z*z)) * 57.2958
        roll  = math.atan2(y, math.sqrt(x*x + z*z)) * 57.2958
        return (pitch, roll)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _resolve_channel(self, channel):
        if isinstance(channel, int):
            return channel
        return _CHANNEL_NAMES.get(str(channel).lower(), 0)

    def _proximity(self, ch):
        v = self._ir_filtered[ch]
        if v <= IR_THRESHOLD_LOW:
            return 0.0
        return max(0.0, min(1.0,
            (v - IR_THRESHOLD_LOW) / (IR_THRESHOLD_HIGH - IR_THRESHOLD_LOW)))

    def _imu_init(self):
        try:
            # 104 Hz, ±2g
            i2c_write(IMU_ADDR, IMU_CTRL1_XL, 0x40)
        except:
            self._imu_ok = False

    @staticmethod
    def _to_signed(val):
        return val - 65536 if val > 32767 else val
