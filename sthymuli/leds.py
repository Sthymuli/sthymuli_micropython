# =============================================================================
# sthymuli/leds.py
#
# WS2812 LED ring — 25 physical / 24 active (pixel 6 = battery indicator)
#
# Ring layout (physical pixel indices):
#
#           [0][1][2][3][4][5]
#        [23]                [7]
#       [22]    NORTH(0-5)    [8]
#      [21]  WEST      EAST  [9]
#       [20]  (19-23)  (7-12) [10]
#        [19]                [11]
#           [18][17][16][15][14][13]
#                 SOUTH(13-18)
#
#   pixel 6 = battery indicator (reserved, always dim warm white)
#
# Provides:
#   Shape   — ring-native geometric shapes
#   Pattern — animated patterns
#   LEDs    — main LED controller class
# =============================================================================

from machine import Pin
from neopixel import NeoPixel
import math, time

# ── Constants ─────────────────────────────────────────────────────────────────
LED_PIN            = 9
NUM_LEDS_TOTAL     = 25
NUM_LEDS           = 24      # active
BATTERY_PIXEL      = 6
DEFAULT_BRIGHTNESS = 0.86    # 220/255

# Quadrant layout — logical indices 0-23 (battery pixel skipped in set_led)
QUAD_START = [0,  7, 13, 19]   # N, E, S, W
QUAD_COUNT = [6,  6,  6,  6]

# Half-ring: top (N+E = logical 0-12) / bottom (S+W = logical 13-23)
HALF_TOP    = list(range(0, 13))
HALF_BOTTOM = list(range(13, 24))

# Alternating pixels — two interleaved sets
EVEN_PIXELS = list(range(0, 24, 2))
ODD_PIXELS  = list(range(1, 24, 2))

# ── Shape constants (ring-native) ─────────────────────────────────────────────
class Shape:
    """
    Ring-native geometric shapes — use with LEDs.show(Shape.STAR).

    All shapes are defined on the 24-LED ring.
    Pass color=(r,g,b) to override the default green.

    Examples:
        leds.show(Shape.RING)
        leds.show(Shape.STAR, color=(255, 100, 0))
        leds.show(Shape.NORTH, color=(0, 0, 255))
    """
    # ── Full ring ──────────────────────────────────────────────────────────
    RING        = "ring"        # all 24 LEDs

    # ── Sectors (cardinal quadrants) ──────────────────────────────────────
    NORTH       = "north"       # 6 LEDs top-centre
    EAST        = "east"        # 6 LEDs right
    SOUTH       = "south"       # 6 LEDs bottom-centre
    WEST        = "west"        # 6 LEDs left

    # ── Multi-sector ──────────────────────────────────────────────────────
    NORTH_EAST  = "north_east"  # N + E quadrants
    SOUTH_EAST  = "south_east"  # S + E quadrants
    SOUTH_WEST  = "south_west"  # S + W quadrants
    NORTH_WEST  = "north_west"  # N + W quadrants
    TOP         = "top"         # N + E (same as NORTH_EAST, alias)
    BOTTOM      = "bottom"      # S + W (same as SOUTH_WEST, alias)
    LEFT_RIGHT  = "left_right"  # E + W quadrants
    TOP_BOTTOM  = "top_bottom"  # N + S quadrants

    # ── Sparse geometric ──────────────────────────────────────────────────
    STAR        = "star"        # 8 evenly-spaced pixels (every 3rd)
    CROSS       = "cross"       # centre pixel of each quadrant (4 pixels)
    CORNERS     = "corners"     # first + last pixel of each quadrant (8 pixels)
    DOTS        = "dots"        # every other pixel (12 pixels)
    HALF_TOP    = "half_top"    # upper 12 LEDs
    HALF_BOTTOM = "half_bottom" # lower 12 LEDs

    # ── Progress / level ──────────────────────────────────────────────────
    # Use LEDs.level(n, color) instead — not a show() constant

# ── Pattern constants (animated) ─────────────────────────────────────────────
class Pattern:
    """
    Animated patterns — use with LEDs.show() or LEDs.animate().

    Examples:
        leds.show(Pattern.BREATHE)
        leds.animate(Pattern.SPIN, color=(0,0,255), duration_ms=3000)
    """
    WELCOME     = "welcome"     # spinning meteor (boot)
    SPIN        = "spin"        # spinning meteor
    BREATHE     = "breathe"     # slow sine fade
    PULSE       = "pulse"       # fast single flash
    REACTIVE    = "reactive"    # green→red per quadrant from sensors

# =============================================================================
# LEDs class
# =============================================================================
class LEDs:
    """
    Controls the 24 active WS2812 LEDs on the Sthymuli ring.

    Usage:
        leds = LEDs()

        leds.show(Shape.RING)
        leds.show(Shape.STAR, color=(255, 100, 0))
        leds.show(Shape.NORTH, color=(0, 0, 255))
        leds.show(Pattern.BREATHE)
        leds.show(Pattern.SPIN, color=(255, 80, 0))

        leds.color(0, 255, 0)           # all green
        leds.off()
        leds.set_brightness(0.5)
        leds.level(18, color=(0,255,0)) # fill 18/24 LEDs like a progress bar
        leds.animate(Pattern.BREATHE, color=(0,0,255), duration_ms=3000)
    """

    def __init__(self, brightness=DEFAULT_BRIGHTNESS):
        self._np = NeoPixel(Pin(LED_PIN), NUM_LEDS_TOTAL)
        self._brightness = brightness
        self._default_color = (0, 180, 0)
        self._boot_ms = time.ticks_ms()
        self._np[BATTERY_PIXEL] = (10, 6, 0)
        self._np.write()

    # ── Public API ────────────────────────────────────────────────────────────

    def show(self, shape_or_pattern, color=None):
        """
        Display a Shape or Pattern.
        color=(r,g,b) sets the colour for Shape constants and some Patterns.

        Shape examples:
            leds.show(Shape.RING)
            leds.show(Shape.STAR, color=(255, 100, 0))
            leds.show(Shape.NORTH_EAST, color=(0, 0, 255))

        Pattern examples:
            leds.show(Pattern.BREATHE)
            leds.show(Pattern.SPIN, color=(255, 80, 0))
        """
        c   = color if color else self._default_color
        now = time.ticks_ms()
        self._clear()

        # ── Shape dispatch ────────────────────────────────────────────────
        if shape_or_pattern == Shape.RING:
            self._ring_all(c)

        elif shape_or_pattern == Shape.NORTH:
            self._quadrant(0, c)
        elif shape_or_pattern == Shape.EAST:
            self._quadrant(1, c)
        elif shape_or_pattern == Shape.SOUTH:
            self._quadrant(2, c)
        elif shape_or_pattern == Shape.WEST:
            self._quadrant(3, c)

        elif shape_or_pattern in (Shape.NORTH_EAST, Shape.TOP):
            self._quadrant(0, c); self._quadrant(1, c)
        elif shape_or_pattern == Shape.SOUTH_EAST:
            self._quadrant(2, c); self._quadrant(1, c)
        elif shape_or_pattern in (Shape.SOUTH_WEST, Shape.BOTTOM):
            self._quadrant(2, c); self._quadrant(3, c)
        elif shape_or_pattern == Shape.NORTH_WEST:
            self._quadrant(0, c); self._quadrant(3, c)
        elif shape_or_pattern == Shape.LEFT_RIGHT:
            self._quadrant(1, c); self._quadrant(3, c)
        elif shape_or_pattern == Shape.TOP_BOTTOM:
            self._quadrant(0, c); self._quadrant(2, c)

        elif shape_or_pattern == Shape.STAR:
            # 8 evenly-spaced pixels around the ring
            for i in range(8):
                self._set_led(i * 3, *c)
        elif shape_or_pattern == Shape.CROSS:
            # Centre pixel of each quadrant
            for q in range(4):
                self._set_led(QUAD_START[q] + QUAD_COUNT[q] // 2, *c)
        elif shape_or_pattern == Shape.CORNERS:
            # First + last pixel of each quadrant
            for q in range(4):
                self._set_led(QUAD_START[q], *c)
                self._set_led(QUAD_START[q] + QUAD_COUNT[q] - 1, *c)
        elif shape_or_pattern == Shape.DOTS:
            for i in EVEN_PIXELS:
                self._set_led(i, *c)
        elif shape_or_pattern == Shape.HALF_TOP:
            for i in HALF_TOP:
                self._set_led(i, *c)
        elif shape_or_pattern == Shape.HALF_BOTTOM:
            for i in HALF_BOTTOM:
                self._set_led(i, *c)

        # ── Pattern dispatch ──────────────────────────────────────────────
        elif shape_or_pattern in (Pattern.WELCOME, Pattern.SPIN):
            self._meteor_frame(now)
        elif shape_or_pattern == Pattern.BREATHE:
            self._breathe_frame(now, c)
        elif shape_or_pattern == Pattern.PULSE:
            self._pulse_frame(now, c)
        # Pattern.REACTIVE needs sensor data — use LEDs.reactive(sensors) instead

        self._write()

    def color(self, r, g, b):
        """Set all active LEDs to a single colour immediately."""
        self._ring_all((r, g, b))
        self._write()

    def off(self):
        """Turn off all active LEDs."""
        self._clear()
        self._write()

    def set_brightness(self, brightness):
        """Set global brightness 0.0–1.0."""
        self._brightness = max(0.0, min(1.0, brightness))

    def set_pixel(self, index, r, g, b):
        """Set a single active LED (0–23)."""
        self._set_led(index, r, g, b)
        self._write()

    def set_quadrant(self, quadrant, r, g, b):
        """
        Light up one quadrant.
        quadrant: 'north'|'east'|'south'|'west'  or  0|1|2|3
        """
        q = self._quad_index(quadrant)
        self._quadrant(q, (r, g, b))
        self._write()

    def level(self, n, color=None, direction='clockwise'):
        """
        Progress-bar style — fill n out of 24 LEDs around the ring.

        n         : 0–24
        color     : (r,g,b) — defaults to green
        direction : 'clockwise' | 'anticlockwise'

        Example:
            leds.level(12, color=(0, 0, 255))   # half ring blue
            leds.level(6,  color=(255, 0, 0))   # quarter ring red
        """
        c = color if color else self._default_color
        n = max(0, min(NUM_LEDS, n))
        self._clear()
        indices = range(NUM_LEDS) if direction == 'clockwise' else range(NUM_LEDS - 1, -1, -1)
        for count, i in enumerate(indices):
            if count >= n:
                break
            self._set_led(i, *c)
        self._write()

    def animate(self, pattern, color=None, duration_ms=2000):
        """
        Run an animated pattern for duration_ms milliseconds. Blocks.

        Example:
            leds.animate(Pattern.BREATHE, color=(0, 0, 255), duration_ms=3000)
            leds.animate(Pattern.SPIN, duration_ms=2000)
        """
        c = color if color else self._default_color
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < duration_ms:
            now = time.ticks_ms()
            self._clear()
            if pattern in (Pattern.BREATHE,):
                self._breathe_frame(now, c)
            elif pattern in (Pattern.SPIN, Pattern.WELCOME):
                self._meteor_frame(now)
            elif pattern == Pattern.PULSE:
                self._pulse_frame(now, c)
            else:
                self._ring_all(c)
            self._write()
            time.sleep_ms(16)

    def reactive(self, sensors):
        """
        Reactive LED update from sensor readings.
        Call this in your loop with a Sensors instance.

        Example:
            while True:
                sensors.update()
                leds.reactive(sensors)
        """
        self._clear()
        dirs = [('north', 0), ('east', 1), ('south', 2), ('west', 3)]
        for name, q in dirs:
            p = sensors.ir(name)
            if p < 0.05:
                self._quadrant(q, (0, 40, 0))
            else:
                r = int(255 * p)
                g = int(255 * (1.0 - p))
                self._quadrant(q, (r, g, 0))
        self._write()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _scale(self, r, g, b):
        bri = self._brightness
        return (int(r * bri), int(g * bri), int(b * bri))

    def _set_led(self, logical, r, g, b):
        if logical < 0 or logical >= NUM_LEDS:
            return
        physical = logical if logical < BATTERY_PIXEL else logical + 1
        self._np[physical] = self._scale(r, g, b)

    def _clear(self):
        for i in range(NUM_LEDS):
            self._set_led(i, 0, 0, 0)

    def _write(self):
        self._np[BATTERY_PIXEL] = (10, 6, 0)
        self._np.write()

    def _ring_all(self, color):
        r, g, b = color
        for i in range(NUM_LEDS):
            self._set_led(i, r, g, b)

    def _quadrant(self, q, color):
        r, g, b = color
        start = QUAD_START[q]
        for i in range(start, start + QUAD_COUNT[q]):
            physical = i if i < BATTERY_PIXEL else i + 1
            self._np[physical] = self._scale(r, g, b)

    def _quad_index(self, q):
        if isinstance(q, int):
            return q
        return {'north': 0, 'east': 1, 'south': 2, 'west': 3}.get(
            str(q).lower(), 0)

    def _breathe_frame(self, now_ms, color):
        t = (now_ms % 2500) / 2500
        v = 0.5 + 0.5 * math.sin(t * 2 * math.pi)
        self._ring_all((int(color[0]*v), int(color[1]*v), int(color[2]*v)))

    def _red_breathe_frame(self, now_ms):
        self._breathe_frame(now_ms, (220, 0, 0))

    def _pulse_frame(self, now_ms, color):
        t = (now_ms % 800) / 800
        v = max(0.0, math.sin(t * math.pi))
        self._ring_all((int(color[0]*v), int(color[1]*v), int(color[2]*v)))

    def _meteor_frame(self, now_ms):
        t    = (now_ms % 1200) / 1200.0
        head = int(t * NUM_LEDS)
        for tail in range(7):
            idx  = (head - tail) % NUM_LEDS
            fade = 1.0 - tail / 7.0
            r = int(60 + fade * (255 - 60))
            g = int(fade * 120)
            self._set_led(idx, r, g, 0)
