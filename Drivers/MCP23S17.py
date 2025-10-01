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

    REGISTER_BITS = dict(
        IODIRA=['IO0', 'IO1', 'IO2', 'IO3', 'IO4', 'IO5', 'IO6', 'IO7'],
        IODIRB=['IO0', 'IO1', 'IO2', 'IO3', 'IO4', 'IO5', 'IO6', 'IO7'],
        IPOLA=['IP0', 'IP1', 'IP2', 'IP3', 'IP4', 'IP5', 'IP6', 'IP7'],
        IPOLB=['IP0', 'IP1', 'IP2', 'IP3', 'IP4', 'IP5', 'IP6', 'IP7'],
        GPINTENA=['GPINT0', 'GPINT1', 'GPINT2', 'GPINT3', 'GPINT4', 'GPINT5', 'GPINT6', 'GPINT7'],
        GPINTENB=['GPINT0', 'GPINT1', 'GPINT2', 'GPINT3', 'GPINT4', 'GPINT5', 'GPINT6', 'GPINT7'],
        DEFVALA=['DEF0', 'DEF1', 'DEF2', 'DEF3', 'DEF4', 'DEF5', 'DEF6', 'DEF7'],
        DEFVALB=['DEF0', 'DEF1', 'DEF2', 'DEF3', 'DEF4', 'DEF5', 'DEF6', 'DEF7'],
        INTCONA=['IOC0', 'IOC1', 'IOC2', 'IOC3', 'IOC4', 'IOC5', 'IOC6', 'IOC7'],
        INTCONB=['IOC0', 'IOC1', 'IOC2', 'IOC3', 'IOC4', 'IOC5', 'IOC6', 'IOC7'],
        GPPUA=['PU0', 'PU1', 'PU2', 'PU3', 'PU4', 'PU5', 'PU6', 'PU7'],
        GPPUB=['PU0', 'PU1', 'PU2', 'PU3', 'PU4', 'PU5', 'PU6', 'PU7'],
        IOCON=['BANK', 'MIRROR', 'SEQOP', 'DISSLW', 'HAEN', 'ODR', 'INTPOL'],
        INTFA=['INT0', 'INT1', 'INT2', 'INT3', 'INT4', 'INT5', 'INT6', 'INT7'],
        INTFB=['INT0', 'INT1', 'INT2', 'INT3', 'INT4', 'INT5', 'INT6', 'INT7'],
        INTCAPA=['ICP0', 'ICP1', 'ICP2', 'ICP3', 'ICP4', 'ICP5', 'ICP6', 'ICP7'],
        INTCAPB=['ICP0', 'ICP1', 'ICP2', 'ICP3', 'ICP4', 'ICP5', 'ICP6', 'ICP7'],
        GPIOA=['GP0', 'GP1', 'GP2', 'GP3', 'GP4', 'GP5', 'GP6', 'GP7'],
        GPIOB=['GP0', 'GP1', 'GP2', 'GP3', 'GP4', 'GP5', 'GP6', 'GP7'],
        OLATA=['OL0', 'OL1', 'OL2', 'OL3', 'OL4', 'OL5', 'OL6', 'OL7'],
        OLATB=['OL0', 'OL1', 'OL2', 'OL3', 'OL4', 'OL5', 'OL6', 'OL7']
    )

    # MCP23S17 Register Addresses REGNAME=(ADDRESS BANK=0, ADDRESS BANK=1)
    REGISTERS = dict(
        IODIRA=(0x00, 0x00),    # I/O Direction Register A
        IODIRB=(0x01, 0x10),    # I/O Direction Register B
        IPOLA=(0x02, 0x01),     # Input Polarity Register A
        IPOLB=(0x03, 0x11),     # Input Polarity Register B
        GPINTENA=(0x04, 0x02),  # Interrupt-on-Change Control Register A
        GPINTENB=(0x05, 0x12),  # Interrupt-on-Change Control Register B
        DEFVALA=(0x06, 0x03),   # Default Compare Register for Interrupt-on-Change A
        DEFVALB=(0x07, 0x13),   # Default Compare Register for Interrupt-on-Change B
        INTCONA=(0x08, 0x04),   # Interrupt Control Register A
        INTCONB=(0x09, 0x14),   # Interrupt Control Register B
        IOCON=(0x0A, 0x05),     # Configuration Register
        GPPUA=(0x0C, 0x06),     # Pull-Up Resistor Configuration Register A
        GPPUB=(0x0D, 0x16),     # Pull-Up Resistor Configuration Register B
        INTFA=(0x0E, 0x07),     # Interrupt Flag Register A
        INTFB=(0x0F, 0x17),     # Interrupt Flag Register B
        INTCAPA=(0x10, 0x08),   # Interrupt Captured Value for Port Register A
        INTCAPB=(0x11, 0x18),   # Interrupt Captured Value for Port Register B
        GPIOA=(0x12, 0x09),     # General Purpose I/O Port Register A
        GPIOB=(0x13, 0x19),     # General Purpose I/O Port Register B
        OLATA=(0x14, 0x0A),     # Output Latch Register A
        OLATB=(0x15, 0x1A)      # Output Latch Register B
    )

    # MCP_DEFAULTS contains default settings for GPIO pins and SPI configuration
    #    GPIOS are defined as (pin_number, direction, [initial val]) tuples and are initialized in __init__()
    #    access them via self.mcp_pins[<pinname>], pinname is derived from key by removing 'GPIO_' and lowercasing
    #    e.g. self.mcp_pins['reset'] from self.mcp_settings['GPIO_RESET']
    #    SPI settings are used in init_spi() to initialize the SPI interface
    DEFAULTS = {
        'GPIO_RESET': (27, "out", True),  # GPIO pin for MCP23S17 RESET, in/out from raspberry perspective
        'GPIO_INTA': (23, "in"),    # GPIO pin for MCP23S17 INTA, in/out from raspberry perspective
        'GPIO_INTB': (24, "in"),    # GPIO pin for MCP23S17 INTB, in/out from raspberry perspective
        'GPIO_CE': (13, "out", True),       # GPIO pin for MCP23S17 CE, driven manually, must not conflict with device tree CS pin
        'SPI_MODE': 0b00,   # SPI mode (Clock Polarity 0, Clock Phase 0)
        'SPI_BUS': 1,       # SPI bus number (usually 0 or 1 on Raspberry Pi)
        'SPI_SPEED': 1000000,  # 1 MHz
        'BANK': 0   # 16 bit mode (=IOCON.BANK=0), 8 bit mode (=IOCON.BANK=1)
    }

    READ = 1
    WRITE = 0
    OPCODE = 0b01000000  # Fixed opcode for MCP23S17
    DEVICE_ADDRESS_MASK = 0b00000111  # Mask for device address bits A2, A1, A0
    DEVICE_ADDRESS = lambda addr: (addr & MCP23S17.DEVICE_ADDRESS_MASK) << 1  # Shifted device address
    CONTROLBYTE = lambda addr, rw: (MCP23S17.OPCODE | MCP23S17.DEVICE_ADDRESS(addr) |
                                    (0b1 if rw == MCP23S17.READ else 0b0))

    def __init__(self, **kwargs):
        """
        Initialize all MCP23S17 I/O expanders connected to the defined SPI bus
        :param **kwargs: optional settings to override MCP_DEFAULTS (case-sensitive!)
        Supported kwargs (all optional):
        1. GPIO_RESET: (pin_number, direction) tuple for RESET pin
        2. GPIO_INTA: (pin_number, direction) tuple for INTA pin
        3. GPIO_INTB: (pin_number, direction) tuple for INTB pin
        4. SPI_CE: GPIO pin number for Chip Enable (CE) pin, must not conflict with device tree CS pin
        5. SPI_MODE: SPI mode (0, 1, 2, or 3)
        6. SPI_BUS: SPI bus number (0 or 1)
        7. SPI_SPEED: SPI clock speed in Hz
        8. REGISTERMODE: 16 for IOCON.BANK=0 (default), 8 for IOCON.BANK=1
        9. Additional GPIOs can be added as needed
        10. Example: MCP23S17(GPIO_RESET=(27, "out"), SPI_BUS=0, SPI_CE=25)
        """
        # copy defaults to mcp_settings if not defined in kwargs
        self.mcp_settings = dict()
        self._opened_device = -1  # currently opened device address, -1 = none
        self._detect_devices_done = False  # True when detect_devices() has been run
        self._mode = None  # current mode (READ or WRITE) of opened device

        for key, value in self.DEFAULTS.items():
            self.mcp_settings[key] = kwargs.get(key, value)
            mcp23s17log.debug(f"MCP setting {key} = {self.mcp_settings[key]}")

        self.spi = self.init_spi()  # checks device tree for SPI bus and CS pin
        self._gpios = dict()  # will hold periphery.GPIO instances for MCP control
        self.setup_gpios()   # fills the dict self.gpios with periphery.GPIO instances for MCP control
        self.reset()         # reset all connected MCP23S17 devices
        # initial list of devices contains all possible addresses, will be filtered in detect_devices()
        self._devices = list(range(0, 8))  # possible device addresses (A2,A1,A0 = 000 to 111)
        self.detect_devices()

    @property
    def _devices(self):
        return self._devices

    @_devices.setter
    def _devices(self, value):
        raise RuntimeError("Devices is read-only, set by detect_devices().")

    @property
    def mode(self):
        """
        Current mode (READ or WRITE) of the opened device
        :return: MCP23S17.READ (=1) for read, MCP23S17.WRITE (=0) for write, None if no device is opened
        """
        return self._mode

    @mode.setter
    def mode(self, value):
        raise RuntimeError("Mode is read-only, set mode by calling _open_device().")

    @property
    def opened_device(self):
        """
        Currently opened device address, -1 if no device is opened
        :return: Device address (0-7) or -1 if no device is opened
        """
        return self._opened_device

    @opened_device.setter
    def opened_device(self, value):
        raise RuntimeError("Opened device is read-only, set opened device by calling _open_device().")

    @property
    def gpios(self):
        """
        Dictionary of GPIO instances for MCP23S17 control pins
        :return: dict with GPIO instances, keys are pin names (lowercase, without 'GPIO_' prefix)
        """
        return self._gpios

    @gpios.setter
    def gpios(self, value):
        raise RuntimeError("GPIOS is read-only, set by setup_gpios().")

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
                if cs_pin == self.mcp_settings['GPIO_CE']:
                    raise RuntimeError(f"CS GPIO {cs_pin} from device tree must not conflict with CE GPIO "
                                       f"{self.mcp_settings['SPI_CE']}. Check device tree configuration."
                                       f"GPIO{cs_pin} needs to be operated programatically as CE pin.")
                else:
                    mcp23s17log.debug(f"✅GPIO{cs_pin} assigned for SPI{spi_bus} CE")
            else:
                raise RuntimeError(f"❌No CS GPIO found for SPI bus {spi_bus}. Check device tree configuration.")
        else:
            raise RuntimeError(f"❌SPI bus {spi_bus} not found in device tree.")

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
            pin_nr, direction = value[0:2]
            gpio = GPIO("/dev/gpiochip0", pin_nr, direction)
            if direction == "out":
                if len(value) < 3:
                    initial_value = False
                else:
                    initial_value = value[2]

                gpio.write(initial_value)
                mcp23s17log.debug(f"Setup GPIO {pin_nr} as {direction} for {key} ({initial_value})")
            else:
                mcp23s17log.debug(f"Setup GPIO {pin_nr} as {direction} for {key}")

            self._gpios[key.removeprefix('GPIO_').lower()] = gpio

    def reset(self):
        """
        Reset all connected MCP23S17 devices by toggling their RESET pins.
        Assumes that all RESET pins are connected to a common GPIO pin.
        """
        if self._gpios.get('reset', None) is None:
            raise RuntimeError("RESET pin not configured in MCP settings.")

        self._gpios['reset'].write(False)  # Set RESET low
        time.sleep(0.1)  # Hold RESET low for 100ms
        if self._gpios['reset'].read():
            raise RuntimeError("Failed to set RESET pin low.")

        self._gpios['reset'].write(True)   # Set RESET high
        time.sleep(0.1)  # Wait for devices to stabilize
        if not self._gpios['reset'].read():
            raise RuntimeError("Failed to set RESET pin high.")

        mcp23s17log.info("MCP23S17 devices reset successfully.")

    def detect_devices(self):
        """
        Detect all MCP23S17 devices connected to the SPI bus by scanning possible addresses.
        MCP23S17 has a 3-bit hardware address (A2, A1, A0) allowing up to 8 devices.
        This function sets the IOCON.HAEN bit using device address 0. All devices attached to the bus
        will accept this, allowing subsequent communication using their unique addresses.
        reading the IOCON register back to verify communication from all device addresses (0-7). A response
        with the HAEN bit set indicates a present device.
        """
        if self._detect_devices_done:
            return  # Avoid running detection multiple times

        self._open_device(device=0, register='IOCON', mode=self.WRITE)  # HAEN is still 0 - all devices accept this

    def access(self):
        """
        Context manager to automatically open and close communication with a specific MCP23S17 device.
        Usage:
            with mcp.access(device=0, register='IODIRA', mode=MCP23S17.WRITE) as dev:
                dev.write_device([0xFF])  # Example write operation
        :return: self for use within the context
        """
        class DeviceContextManager:
            def __init__(self, outer, device, register, mode):
                self.outer = outer
                self.device = device
                self.register = register
                self.mode = mode

            def __enter__(self):
                self.outer._open_device(self.device, self.register, self.mode)
                return self.outer

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.outer.close_device()

        return DeviceContextManager(self, device, register, mode)


    def _open_device(self, device: int, register: Union[str, int], mode: int) -> None:
        """
        Open communication with a specific MCP23S17 device by sending the control byte and register address.
        if CE is low, it is pulled high first (auto close), then pulled low to start communication.
        The device address is validated against detected devices.
        The register can be specified by name (str) or address (int).
        keeps CE low until close_device() is called.

        :raises RuntimeError: if CE pin cannot be set correctly
        :raises ValueError: if the address is not detected or invalid
        :param device: Device address (0-7)
        :param register: Register name (str) or Register address (int)
        :param mode: MCP23S17.READ (=1) for read, MCP23S17.WRITE (=0) for write
        """

        if 0 <= device <= 7:
            if device not in self._devices:
                raise ValueError(f"Device address {device} not detected. Available addresses: {self._devices}")
            else:
                pass  # device is valid and detected
        else:
            raise ValueError("Device address must be between 0 and 7.")

        if isinstance(register, str):
            r_addr = self.register_address(register)  # determine register address based on BANK setting
        elif isinstance(register, int):
            r_addr = register
            if not (0x00 <= r_addr <= 0x1A):
                raise ValueError("Register address must be between 0x00 and 0x1A.")
        else:
            raise ValueError("Register must be a string (register name) or an integer (register address).")

        self.close_device()

        self._gpios['ce'].write(False)  # Set CE low to start communication
        if self._gpios['ce'].read():
            raise RuntimeError("Failed to set CE pin low.")

        self._opened_device = device
        control_byte = self.CONTROLBYTE(device, mode)

        self.spi.transfer([control_byte, r_addr])
        self._mode = mode

        mcp23s17log.debug(f"Opened communication with MCP23S17 device at address {device}, "
                          f"register {register} (0x{r_addr:02X}), "
                          f"mode {'READ' if mode == self.READ else 'WRITE'}")

    def close_device(self) -> None:
        """
        Close communication with the currently opened MCP23S17 device by pulling CE high.
        """
        if self._opened_device != -1:
            self._gpios['ce'].write(True)  # Set CE high to end communication
            if not self._gpios['ce'].read():
                raise RuntimeError("Failed to set CE pin high.")
            mcp23s17log.debug(f"Closed communication with MCP23S17 device at address {self._opened_device}")
            self._opened_device = -1  # No device is currently opened

    def _write_device(self, data: Union[List[int], int]) -> None:
        """
        Write data to the currently opened MCP23S17 device.
        :param data: List of bytes to write (each byte must be 0-255)
        :raises RuntimeError: if no device is currently opened
        :raises ValueError: if data contains invalid byte values
        """

        if self._opened_device == -1:
            raise RuntimeError("No MCP23S17 device is currently opened for writing.")

        if isinstance(data, int):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError("Data must be an integer or a list of integers.")

        if not all(0 <= byte <= 255 for byte in data):
            raise ValueError("All data bytes must be between 0 and 255.")

        r_data = self.spi.transfer(data)
        mcp23s17log.debug(f"Wrote data to MCP23S17 device at address {self._opened_device}: {data}\n"
                          f"    Received response: {r_data}")

    def _read_device(self, length: int) -> List[int]:
        """
        Read data from the currently opened MCP23S17 device.
        :param length: Number of bytes to read
        :return: List of bytes read from the device
        :raises RuntimeError: if no device is currently opened
        :raises ValueError: if length is not a positive integer
        """
        if self._opened_device == -1:
            raise RuntimeError("No MCP23S17 device is currently opened for reading.")

        if length <= 0:
            raise ValueError("Length must be a positive integer.")

        dummybytes = [0] * length
        data = self.spi.transfer(dummybytes)  # Send dummy bytes to read data
        mcp23s17log.debug(f"Read {length} bytes from MCP23S17 device at address {self._opened_device}:\n"
                          f"    {data}")
        return data

    def register_address(self, registername: str) -> int:
        """
        Get the register address based on the register name and current BANK setting.
        :param registername: string name of the register (e.g., 'IODIRA', 'GPIOB')
        :return: Register address based on BANK setting
        """
        bank = self.mcp_settings['BANK']
        if registername not in self.REGISTERS:
            raise ValueError(f"Invalid register name: {registername}")
        return self.REGISTERS[registername][bank]


if __name__ == "__main__":
    mcp = MCP23S17()
    mcp23s17log.info("MCP23S17 initialization complete.")
    # SPI loopback test
    test_data = [0x55, 0xAA, 0xFF, 0x00]
    response = mcp.spi.transfer(test_data)
    mcp23s17log.info(f"SPI loopback test sent: {test_data}, received: {response}")
    # Clean up GPIOs
    for gp in mcp._gpios.values():
        gp.close()
    mcp.spi.close()
    mcp23s17log.info("MCP23S17 test complete, GPIOs and SPI closed.")
