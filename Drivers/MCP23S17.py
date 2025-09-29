from typing import List, Any, Union, Tuple, Dict, Optional
from peripheral import SPI, GPIO
import time
import logging

MODULENAME = sys.argv[1]

# logging setup
clientlog = logging.getLogger(__name__)
clientlog.setLevel(logging.INFO)
ch = logging.StreamHandler()
fh = None   # file handler if needed
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
clientlog.addHandler(ch)


class MCP23S17:
    """MCP23S17 16-Bit I/O Expander with SPI Interface"""

    # MCP23S17 Register Addresses
    IODIRA = 0x00  # I/O Direction Register A
    IODIRB = 0x01  # I/O Direction Register B
    IPOLA = 0x02   # Input Polarity Register A
    IPOLB = 0x03   # Input Polarity Register B
    GPINTENA = 0x04  # Interrupt-on-Change Control Register A
    GPINTENB = 0x05  # Interrupt-on-Change Control Register B
    DEFVALA = 0x06   # Default Compare Register for Interrupt-on-Change A
    DEFVALB = 0x07   # Default Compare Register for Interrupt-on-Change B
    INTCONA = 0x08   # Interrupt Control Register A
    INTCONB = 0x09   # Interrupt Control Register B
    IOCON = 0x0A     # Configuration Register
    GPPUA = 0x0C     # Pull-Up Resistor Configuration Register A
    GPPUB = 0x0D     # Pull-Up Resistor Configuration Register B
    INTFA = 0x0E     # Interrupt Flag Register A
    INTFB = 0x0F     # Interrupt Flag Register B
    INTCAPA = 0x10   # Interrupt Captured Value for Port Register A
    INTCAPB = 0x11   # Interrupt Captured Value for Port Register B
    GPIOA = 0x12     # General Purpose I/O Port Register A
    GPIOB = 0x13     # General Purpose I/O Port Register B
    OLATA = 0x14     # Output Latch Register A
    OLATB = 0x15     # Output Latch Register B

    MCPRESET_GPIO = 27  # GPIO pin for RESET
    MCPINTA_GPIO = 23  # GPIO pin for RESET
    MCPINTB_GPIO = 24  # GPIO pin for RESET
    OUT = "out"

    def __init__(self, spi_bus:int=1, io_expander_address:int=-1, spi_speed=1000000):
        """
        Initialize the MCP23S17 I/O expander on the specific RPI hat
        :param spi_bus: raspberry pi spi bus number (0 or 1)
        :param io_expander_address: 3-bit hardware address (A2, A1, A0 pins), 0-7 (000-111)
                                    if -1: addresses of all devices are determined automatically, reset and new
                                    initialization of all devices is done. self.devicelist contains the found addresses
                                    after initialization.
        :param spi_speed: frequency of the SPI bus in Hz (default: 1MHz)
        """
        self.setup_gpios()
        self.spi_device = f'/dev/spidev{spi_bus}.0'  # CE line is set in boot/firmware/config.txt to CE0, GPIO 13
        if 0 > io_expander_address <= 7:
            self.io_expander_address = io_expander_address
        elif io_expander_address == -1:
            self.io_expander_address = -1  # automatic address detection
            self.reset_all_devices()
        else:
            raise ValueError("io_expander_address must be in the range 0-7 or -1 for automatic detection")

        self.spi_speed = spi_speed
        self.mode = 0b00  # SPI mode 0 (Clock Polarity 0, Clock Phase 0)
        self.devicelist = []  # list of detected device addresses

        self.spi = SPI(devpath=self.spi_device, max_speed=self.spi_speed, mode=0b00, bit_order='msb',
                       bits_per_word=8)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.cs_pin, GPIO.OUT)
        GPIO.output(self.cs_pin, GPIO.HIGH)

    def setup_gpios(self):
        """
        Setup GPIO pins for MCP23S17 control
        """
        self.mcpresetpin_o = GPIO(MCPRESET_GPIO, OUT)
        self.inta_i = GPIO(MCPINTA_GPIO, GPIO.IN)  # Interrupt pin A from MCP23S17
        self.intB_i = GPIO(MCPINTB_GPIO, GPIO.IN)  # Interrupt pin B from MCP23S17

    def reset_all_devices(self):
        """
        Reset all connected MCP23S17 devices by toggling their RESET pins.
        Assumes that all RESET pins are connected to a common GPIO pin.
        """
        reset_pin_nr = 17  # Example GPIO pin for RESET, change as needed
        reset_pin = GPIO(reset_pin, GPIO.OUT)
        GPIO.output(reset_pin, GPIO.LOW)
        time.sleep(0.1)  # Hold reset low for 100ms
        GPIO.output(reset_pin, GPIO.HIGH)
        time.sleep(0.1)  # Wait for devices to stabilize