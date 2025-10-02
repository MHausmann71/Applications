from typing import List, Any, Union, Tuple, Dict, Optional

import time
import logging
import check_platform
from registers import Register

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

    # MCP23S17 registers with their addresses and bit maps
    # address is for IOCON.BANK=0 (default), alt_address is for IOCON.BANK=1
    REGISTERS = dict(
        IODIRA=Register(0x00, ['IO7', 'IO6', 'IO5', 'IO4', 'IO3', 'IO2', 'IO1', 'IO0'],
                        alt_address=0x00, use_alt_address=False),
        IODIRB=Register(0x01, ['IO7', 'IO6', 'IO5', 'IO4', 'IO3', 'IO2', 'IO1', 'IO0'],
                        alt_address=0x10, use_alt_address=False),
        IPOLA=Register(0x02, ['IP7', 'IP6', 'IP5', 'IP4', 'IP3', 'IP2', 'IP1', 'IP0'],
                       alt_address=0x01, use_alt_address=False),
        IPOLB=Register(0x03, ['IP7', 'IP6', 'IP5', 'IP4', 'IP3', 'IP2', 'IP1', 'IP0'],
                       alt_address=0x11, use_alt_address=False),
        GPINTENA=Register(0x04, ['GPINT7', 'GPINT6', 'GPINT5', 'GPINT4', 'GPINT3', 'GPINT2', 'GPINT1', 'GPINT0'],
                          alt_address=0x02, use_alt_address=False),
        GPINTENB=Register(0x05, ['GPINT7', 'GPINT6', 'GPINT5', 'GPINT4', 'GPINT3', 'GPINT2', 'GPINT1', 'GPINT0'],
                          alt_address=0x12, use_alt_address=False),
        DEFVALA=Register(0x06, ['DEF7', 'DEF6', 'DEF5', 'DEF4', 'DEF3', 'DEF2', 'DEF1', 'DEF0'],
                         alt_address=0x03, use_alt_address=False),
        DEFVALB=Register(0x07, ['DEF7', 'DEF6', 'DEF5', 'DEF4', 'DEF3', 'DEF2', 'DEF1', 'DEF0'],
                         alt_address=0x13, use_alt_address=False),
        INTCONA=Register(0x08, ['IOC7', 'IOC6', 'IOC5', 'IOC4', 'IOC3', 'IOC2', 'IOC1', 'IOC0'],
                         alt_address=0x04, use_alt_address=False),
        INTCONB=Register(0x09, ['IOC7', 'IOC6', 'IOC5', 'IOC4', 'IOC3', 'IOC2', 'IOC1', 'IOC0'],
                         alt_address=0x14, use_alt_address=False),
        IOCONA=Register(0x0A, ['BANK', 'MIRROR', 'SEQOP', 'DISSLW', 'HAEN', 'ODR', 'INTPOL', 'UNUSED'],
                        alt_address=0x05, use_alt_address=False),
        IOCONB=Register(0x0B, ['BANK', 'MIRROR', 'SEQOP', 'DISSLW', 'HAEN', 'ODR', 'INTPOL', 'UNUSED'],
                        alt_address=0x15, use_alt_address=False),
        GPPUA=Register(0x0C, ['PU7', 'PU6', 'PU5', 'PU4', 'PU3', 'PU2', 'PU1', 'PU0'],
                       alt_address=0x06, use_alt_address=False),
        GPPUB=Register(0x0D, ['PU7', 'PU6', 'PU5', 'PU4', 'PU3', 'PU2', 'PU1', 'PU0'],
                       alt_address=0x16, use_alt_address=False),
        INTFA=Register(0x0E, ['INT7', 'INT6', 'INT5', 'INT4', 'INT3', 'INT2', 'INT1', 'INT0'],
                       alt_address=0x07, use_alt_address=False),
        INTFB=Register(0x0F, ['INT7', 'INT6', 'INT5', 'INT4', 'INT3', 'INT2', 'INT1', 'INT0'],
                       alt_address=0x17, use_alt_address=False),
        INTCAPA=Register(0x10, ['ICP7', 'ICP6', 'ICP5', 'ICP4', 'ICP3', 'ICP2', 'ICP1', 'ICP0'],
                         alt_address=0x08, use_alt_address=False),
        INTCAPB=Register(0x11, ['ICP7', 'ICP6', 'ICP5', 'ICP4', 'ICP3', 'ICP2', 'ICP1', 'ICP0'],
                         alt_address=0x18, use_alt_address=False),
        GPIOA=Register(0x12, ['GP7', 'GP6', 'GP5', 'GP4', 'GP3', 'GP2', 'GP1', 'GP0'],
                       alt_address=0x09, use_alt_address=False),
        GPIOB=Register(0x13, ['GP7', 'GP6', 'GP5', 'GP4', 'GP3', 'GP2', 'GP1', 'GP0'],
                       alt_address=0x19, use_alt_address=False),
        OLATA=Register(0x14, ['OL7', 'OL6', 'OL5', 'OL4', 'OL3', 'OL2', 'OL1', 'OL0'],
                       alt_address=0x0A, use_alt_address=False),
        OLATB=Register(0x15, ['OL7', 'OL6', 'OL5', 'OL4', 'OL3', 'OL2', 'OL1', 'OL0'],
                       alt_address=0x1A, use_alt_address=False),
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
        'BANK': 0,   # 16 bit mode (=IOCON.BANK=0), 8 bit mode (=IOCON.BANK=1)
        'SEQOP': 0  # Sequential operation mode (0=enabled, 1=disabled)
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
        self._available_devices = list(range(0, 8))  # list of detected device addresses
        self.mcp_settings = dict()
        self._opened_device = -1  # currently opened device address, -1 = none
        self._mode = None  # current mode (READ or WRITE) of opened device

        for key, value in self.DEFAULTS.items():
            self.mcp_settings[key] = kwargs.get(key, value)
            mcp23s17log.debug(f"MCP setting {key} = {self.mcp_settings[key]}")

        self.spi = self.init_spi()  # checks device tree for SPI bus and CS pin
        self._gpios = dict()  # will hold periphery.GPIO instances for MCP control
        self.setup_gpios()   # fills the dict self.gpios with periphery.GPIO instances for MCP control
        self.reset()         # reset all connected MCP23S17 devices
        # initial list of devices contains all possible addresses, will be filtered in detect_devices()
        self.detect_devices()  # writes self._available_devices with detected device addresses

    class writeContext:
        def __init__(self, device_obj, device_addr, register):
            self.device_obj = device_obj     # object of class MCP23S17
            self.device_addr = device_addr   # device address (0-7)
            self.register = register         # register name (str) or address (int)

        def __enter__(self):
            # open_device(self, device: int, register: Union[str, int], mode: int) -> None:
            self.device_obj.open_device(self.device_addr, self.register, MCP23S17.WRITE)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.device_obj.close_device()

        def transfer(self, data: List[int]) -> List[int]:
            if self.device_obj.mode != MCP23S17.WRITE:
                raise RuntimeError("Device not opened in WRITE mode.")
            return self.device_obj.spi.transfer(data)

    def write(self, device_addr, register, bank=0):
        """
        Context manager to automatically open and close communication with a specific MCP23S17 device for writing.
        Usage:
            with mcp.write(device=0, register='IODIRA', bank=0) as dev:
                dev._write_device([0xFF])  # Example write operation
        """
        reg_addr = MCP23S17.REGISTERS[register].address if bank == 0 else MCP23S17.REGISTERS[register].alt_address
        return MCP23S17.writeContext(self, device_addr, reg_addr)

    class readContext:
        def __init__(self, device_obj, device_addr, register):
            self.device_obj = device_obj     # object of class MCP23S17
            self.device_addr = device_addr   # device address (0-7)
            self.register = register         # register name (str) or address (int)

        def __enter__(self):
            # open_device(self, device: int, register: Union[str, int], mode: int) -> None:
            self.device_obj.open_device(self.device_addr, self.register, MCP23S17.READ)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.device_obj.close_device()

        def transfer(self, nbytes: int) -> List[int]:
            if self.device_obj.mode != MCP23S17.READ:
                raise RuntimeError("Device not opened in READ mode.")
            dummy = [0x00] * nbytes  # send dummy bytes to read data
            return self.device_obj.spi.transfer(dummy)

    def read(self, device_addr, register, bank=0):
        """
        Context manager to automatically open and close communication with a specific MCP23S17 device for writing.
        Usage:
            with mcp.write(device=0, register='IODIRA', bank=0) as dev:
                dev._write_device([0xFF])  # Example write operation
        """
        reg_addr = MCP23S17.REGISTERS[register].address if bank == 0 else MCP23S17.REGISTERS[register].alt_address
        return self.readContext(self, device_addr, reg_addr)

    @property
    def available_devices(self):
        return self._available_devices

    @available_devices.setter
    def available_devices(self, value):
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
        raise RuntimeError("Mode is read-only, set mode by calling open_device().")

    @property
    def opened_device(self):
        """
        Currently opened device address, -1 if no device is opened
        :return: Device address (0-7) or -1 if no device is opened
        """
        return self._opened_device

    @opened_device.setter
    def opened_device(self, value):
        raise RuntimeError("Opened device is read-only, set opened device by calling open_device().")

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

        if len(self._available_devices):
            mcp23s17log.info(f"Redetecting devices, previous detected addresses: {self._available_devices}")
            return

        self.open_device(device_addr=0, register='IOCON', mode=self.WRITE)  # HAEN is still 0 - all devices accept this
        haen_bit = MCP23S17.REGISTERS['IOCON']('HAEN')  # value with HAEN=1
        self.spi.transfer([haen_bit])  # Set IOCON.HAEN=1, other bits unchanged
        self.close_device()
        # HEAN is now set at all devices, we can address them individually
        detected_devices = []
        dummybyte = [0b00000000]
        for addr in range(0, 8):
            # send control byte and register address
            self.open_device(device_addr=addr, register='IOCON', mode=self.READ)
            r_data = self.spi.transfer(dummybyte)  # Send dummy bytes to read data
            self.close_device()
            if r_data[0] & haen_bit:  # Check if HAEN bit is set
                detected_devices.append(addr)
                mcp23s17log.info(f"Detected MCP23S17 device at address {addr}")
            else:
                mcp23s17log.debug(f"No MCP23S17 device at address {addr} (no HAEN bit set)")

        self._available_devices = detected_devices

    def open_device(self, device_addr: int, register: Union[str, int], mode: int, bank: int = 0) -> None:
        """
        Open communication with a specific MCP23S17 device by sending the control byte and register address.
        if CE is low, it is pulled high first (auto close), then pulled low to start communication.
        The device address is validated against detected devices.
        The register can be specified by name (str) or address (int).
        keeps CE low until close_device() is called.

        :raises RuntimeError: if CE pin cannot be set correctly
        :raises ValueError: if the address is not detected or invalid
        :param device_addr: Device address (0-7)
        :param register: Register name (str) or Register address (int). if str, BANK setting is used to determine address
                         if int is provided, it is directly used as register address
        :param mode: MCP23S17.READ (=1) for read, MCP23S17.WRITE (=0) for write
        :param bank: BANK setting (0 or 1) to determine register addressing mode, default is 0
        """

        if 0 <= device_addr <= 7:
            if device_addr not in self._available_devices:
                raise ValueError(f"Device address {device_addr} not detected. Available addresses: "
                                 f"{self._available_devices}")
            else:
                pass  # device is valid and detected
        else:
            raise ValueError("Device address must be between 0 and 7.")

        if isinstance(register, str):
            reg_addr = MCP23S17.REGISTERS[register].address if bank == 0 else MCP23S17.REGISTERS[register].alt_address
        elif isinstance(register, int):
            reg_addr = register
            if not (0x00 <= reg_addr <= 0x1A):
                raise ValueError("Register address must be between 0x00 and 0x1A.")
        else:
            raise ValueError("Register must be a string (register name) or an integer (register address).")

        self.close_device()   # sets CE high if it was low

        self._gpios['ce'].write(False)  # Set CE low to start communication
        if self._gpios['ce'].read():
            raise RuntimeError("Failed to set CE pin low.")

        self._opened_device = device_addr
        control_byte = MCP23S17.CONTROLBYTE(device_addr, mode)

        self.spi.transfer([control_byte, reg_addr])
        self._mode = mode

        mcp23s17log.debug(f"Opened communication with MCP23S17 device at address {device_addr}, "
                          f"register {register} (0x{reg_addr:02X}), "
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

    # Example usage of context manager
    with mcp.write(device_addr=0, register='IODIRA', bank=1) as dev:
        dev.transfer([0xFF])  # Example write operation

    with mcp.read(device_addr=0, register='GPIOA', bank=1) as dev:
        data = dev.transfer(1)  # Example read operation
        print(f"Read data: {data}")

    #     do something with dev
