from typing import List, Any, Union, Tuple, Dict, Optional

import time
import logging
import check_platform

# logging setup
mcp23s17log = logging.getLogger(__name__)
# mcp23s17log.setLevel(logging.INFO)
mcp23s17log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
fh = None   # file handler if needed
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
mcp23s17log.addHandler(ch)

# Check if running on Raspberry Pi for real SPI and GPIO handling
if check_platform.is_raspberry_pi():
    from periphery import SPI, GPIO
    import get_spi_properties
    RPIPLATFORM = True
    mcp23s17log.info("Running on a Raspberry Pi, using real SPI & GPIO handling.")
else:
    from rpi_sim import GPIO, SPI
    mcp23s17log.info("Not running on a Raspberry Pi, SPI & GPIO handling will be simulated.")
    RPIPLATFORM = False


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

    # MCP_DEFAULTS contains default settings for GPIO pins and SPI configuration
    #    GPIOS are defined as (pin_number, direction) tuples and are initialized in __init__()
    #    access them via self.mcp_pins[<pinname>], pinname is derived from key by removing 'GPIO_' and lowercasing
    #    e.g. self.mcp_pins['reset'] from self.mcp_settings['GPIO_RESET']
    #    SPI settings are used in init_spi() to initialize the SPI interface
    MCP_DEFAULTS = {
        'GPIO_RESET': (27, "out"),  # GPIO pin for MCP23S17 RESET, in/out from raspberry perspective
        'GPIO_INTA': (23, "in"),    # GPIO pin for MCP23S17 INTA, in/out from raspberry perspective
        'GPIO_INTB': (24, "in"),    # GPIO pin for MCP23S17 INTB, in/out from raspberry perspective
        'SPI_CE': 13,       # GPIO pin for MCP23S17 CE, check if Rpi is configured acc. (/boot/firmware/config.txt)
        'SPI_MODE': 0b00,   # SPI mode (Clock Polarity 0, Clock Phase 0)
        'SPI_BUS': 1,       # SPI bus number (usually 0 or 1 on Raspberry Pi)
        'SPI_SPEED': 1000000  # 1 MHz
    }

    def __init__(self, mcp_settings: Union[Dict, None] = None):
        """
        Initialize all MCP23S17 I/O expanders connected to the defined SPI bus
        :param mcp_settings: Dictionary with MCP settings, if None defaults are used
        """
        # copy defaults to mcp_settings if not defined
        self.mcp_settings = dict()
        if mcp_settings is None:
            mcp_settings = dict()

        for key, value in self.MCP_DEFAULTS.items():
            self.mcp_settings[key] = mcp_settings.get(key, value)
            mcp23s17log.debug(f"MCP setting {key} = {self.mcp_settings[key]}")

        self.spi = self.init_spi()  # checks device tree for SPI bus and CS pin
        self.gpios = dict()  # will hold periphery.GPIO instances for MCP control
        self.setup_gpios()   # fills the dict self.mcp_pins with periphery.GPIO instances for MCP control
        self.reset()         # reset all connected MCP23S17 devices

    def init_spi(self):
        """
        Initialize SPI interface for MCP23S17 communication
        """
        if RPIPLATFORM:
            spi_properties = get_spi_properties.read_device_tree_spi_cs()
        else:
            spi_properties = {'SPI0': [],
                              'SPI1': [{'flags': 0, 'gpio_number': 13, 'phandle': 7}],
                              'SPI2': [{'info': 'No cs-gpios property found. Default CS pins may apply (CE0/CE1).'}]}

        spi_bus = self.mcp_settings['SPI_BUS']

        if f'SPI{spi_bus}' in spi_properties:
            cs_list = spi_properties[f'SPI{spi_bus}']
            if len(cs_list) > 0:
                cs_pin = cs_list[0]['gpio_number']  # Use the first CS pin found
                if cs_pin != self.mcp_settings['SPI_CE']:
                    raise RuntimeError(f"CS GPIO {cs_pin} from device tree does not match configured CE GPIO "
                                       f"{self.mcp_settings['SPI_CE']}. Check device tree configuration.")
                else:
                    mcp23s17log.debug(f"GPIO{cs_pin} assigned for SPI{spi_bus} CE")
            else:
                raise RuntimeError(f"No CS GPIO found for SPI bus {spi_bus}. Check device tree configuration.")
        else:
            raise RuntimeError(f"SPI bus {spi_bus} not found in device tree.")

        spi = SPI(devpath=f'/dev/spidev{spi_bus}.0',
                  max_speed=self.mcp_settings['SPI_SPEED'],
                  mode=self.mcp_settings['SPI_MODE'],
                  bit_order='msb',
                  bits_per_word=8)
        mcp23s17log.debug(f"Initialized SPI bus {spi_bus} with CE GPIO {cs_pin}, "
                          f"speed {self.mcp_settings['SPI_SPEED']} Hz, mode {self.mcp_settings['SPI_MODE']}")
        return spi

    def setup_gpios(self):
        """
        Setup GPIO pins for MCP23S17 control
        """
        for key, value in self.mcp_settings.items():
            if not key.startswith('GPIO_'):
                continue
            pin_nr, direction = value
            gpio = GPIO("/dev/gpiochip0", pin_nr, direction)
            mcp23s17log.debug(f"Setup GPIO {pin_nr} as {direction} for {key}")
            self.gpios[key.removeprefix('GPIO_').lower()] = gpio

    def reset(self):
        """
        Reset all connected MCP23S17 devices by toggling their RESET pins.
        Assumes that all RESET pins are connected to a common GPIO pin.
        """
        if self.gpios.get('reset', None) is None:
            raise RuntimeError("RESET pin not configured in MCP settings.")

        self.gpios['reset'].write(False)  # Set RESET low
        time.sleep(0.1)  # Hold RESET low for 100ms
        if self.gpios['reset'].read():
            raise RuntimeError("Failed to set RESET pin low.")

        self.gpios['reset'].write(True)   # Set RESET high
        time.sleep(0.1)  # Wait for devices to stabilize
        if not self.gpios['reset'].read():
            raise RuntimeError("Failed to set RESET pin high.")

        mcp23s17log.info("MCP23S17 devices reset successfully.")


if __name__ == "__main__":
    mcp = MCP23S17()
    mcp23s17log.info("MCP23S17 initialization complete.")
    # SPI loopback test
    test_data = [0x55, 0xAA, 0xFF, 0x00]
    response = mcp.spi.transfer(test_data)
    mcp23s17log.info(f"SPI loopback test sent: {test_data}, received: {response}")
    # Clean up GPIOs
    for gp in mcp.gpios.values():
        gp.close()
    mcp.spi.close()
    mcp23s17log.info("MCP23S17 test complete, GPIOs and SPI closed.")
