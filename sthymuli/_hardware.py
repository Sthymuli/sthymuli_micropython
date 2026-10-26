# =============================================================================
# sthymuli/_hardware.py
#
# Shared hardware initialisation — I2C bus, power latch, ADC, IR emitter.
# All other modules import from here so the bus is only created once.
# =============================================================================

from machine import Pin, I2C, ADC
import struct, time

# ── Singleton I2C bus ─────────────────────────────────────────────────────────
_i2c = None

def get_i2c():
    global _i2c
    if _i2c is None:
        _i2c = I2C(0, sda=Pin(48), scl=Pin(47), freq=400000)
    return _i2c

# ── Power latch ───────────────────────────────────────────────────────────────
_pwr = None

def power_latch():
    global _pwr
    if _pwr is None:
        _pwr = Pin(6, Pin.OUT)
        _pwr.on()
    return _pwr

# ── IR emitter ────────────────────────────────────────────────────────────────
_ir_mod = None

def ir_emitter_on():
    global _ir_mod
    if _ir_mod is None:
        _ir_mod = Pin(10, Pin.OUT)
        _ir_mod.on()

# ── ADC (IR analog return) ────────────────────────────────────────────────────
_adc = None

def get_adc():
    global _adc
    if _adc is None:
        _adc = ADC(Pin(4), atten=ADC.ATTN_11DB)
    return _adc

# ── I2C helpers ───────────────────────────────────────────────────────────────
def i2c_write(addr, reg, val):
    get_i2c().writeto_mem(addr, reg, bytes([val]))

def i2c_read(addr, reg, n=1):
    return get_i2c().readfrom_mem(addr, reg, n)

def i2c_write_bytes(addr, reg, data):
    get_i2c().writeto_mem(addr, reg, data)

def i2c_scan():
    return get_i2c().scan()

# ── PCA9685 (servo driver @ 0x40) ────────────────────────────────────────────
PCA_ADDR     = 0x40
PCA_MODE1    = 0x00
PCA_PRESCALE = 0xFE
PCA_LED0     = 0x06

def pca_init():
    i2c_write(PCA_ADDR, PCA_MODE1, 0x10)   # sleep
    time.sleep_ms(5)
    i2c_write(PCA_ADDR, PCA_PRESCALE, 130) # 50 Hz (27 MHz osc)
    i2c_write(PCA_ADDR, PCA_MODE1, 0x00)   # wake
    time.sleep_ms(5)
    i2c_write(PCA_ADDR, PCA_MODE1, 0xA0)   # auto-increment

def pca_set_pwm(channel, on, off):
    base = PCA_LED0 + 4 * channel
    i2c_write_bytes(PCA_ADDR, base,
        struct.pack('<HH', on & 0xFFFF, off & 0xFFFF))

# ── MCP23017 (I/O expander @ 0x20) ───────────────────────────────────────────
MCP_ADDR   = 0x20
MCP_IODIRA = 0x00
MCP_IODIRB = 0x01
MCP_GPIOA  = 0x12
MCP_GPIOB  = 0x13
MCP_GPPUA  = 0x0C

_mcp_gpioa = 0x00

def mcp_init():
    global _mcp_gpioa
    # GPA0-4 inputs, GPA5-7 outputs (IR mux S0/S1/S2)
    i2c_write(MCP_ADDR, MCP_IODIRA, 0b00011111)
    i2c_write(MCP_ADDR, MCP_IODIRB, 0xFF)        # GPB all inputs
    i2c_write(MCP_ADDR, MCP_GPPUA,  0b00011111)  # pull-ups on GPA0-4
    _mcp_gpioa = 0x00

def mcp_set_ir_channel(ch):
    global _mcp_gpioa
    s0 = (ch >> 0) & 1
    s1 = (ch >> 1) & 1
    s2 = (ch >> 2) & 1
    _mcp_gpioa = (_mcp_gpioa & 0x1F) | (s0 << 5) | (s1 << 6) | (s2 << 7)
    i2c_write(MCP_ADDR, MCP_GPIOA, _mcp_gpioa)

def mcp_read_gpiob():
    return i2c_read(MCP_ADDR, MCP_GPIOB, 1)[0]
