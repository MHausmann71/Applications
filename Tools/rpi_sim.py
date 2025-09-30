class GPIO:
    DIRECTION_IN = "in"
    DIRECTION_OUT = "out"

    def __init__(self, pin, direction, initial=None):
        self.pin = pin
        self._direction = direction
        self._value = initial if initial is not None else 0
        self._closed = False
        print(f"[SIM] GPIO(pin={pin}, direction={direction}, initial={initial})")

    @property
    def direction(self):
        return self._direction

    @direction.setter
    def direction(self, value):
        if value not in [self.DIRECTION_IN, self.DIRECTION_OUT]:
            raise ValueError("Invalid direction. Must be 'in' or 'out'.")
        self._direction = value
        print(f"[SIM] GPIO {self.pin} direction set to {value}")

    def read(self):
        print(f"[SIM] GPIO {self.pin} read -> {self._value}")
        return self._value

    def write(self, value):
        if self._direction != self.DIRECTION_OUT:
            raise RuntimeError("Cannot write to input GPIO")
        self._value = int(bool(value))
        print(f"[SIM] GPIO {self.pin} write <- {self._value}")

    def close(self):
        self._closed = True
        print(f"[SIM] GPIO {self.pin} closed")

    def __del__(self):
        if not self._closed:
            self.close()

class SPI:
    def __init__(self, device, mode=0, max_speed=500000, bit_order="msb"):
        self.device = device
        self._mode = mode
        self._max_speed = max_speed
        self._bit_order = bit_order
        self._closed = False
        print(f"[SIM] SPI(device={device}, mode={mode}, max_speed={max_speed}, bit_order={bit_order})")

    @property
    def mode(self):
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value
        print(f"[SIM] SPI {self.device} mode set to {value}")

    @property
    def max_speed(self):
        return self._max_speed

    @max_speed.setter
    def max_speed(self, value):
        self._max_speed = value
        print(f"[SIM] SPI {self.device} max_speed set to {value}")

    @property
    def bit_order(self):
        return self._bit_order

    @bit_order.setter
    def bit_order(self, value):
        if value not in ["msb", "lsb"]:
            raise ValueError("bit_order must be 'msb' or 'lsb'")
        self._bit_order = value
        print(f"[SIM] SPI {self.device} bit_order set to {value}")

    def transfer(self, data):
        # Simulate full-duplex transfer: echo the data
        print(f"[SIM] SPI {self.device} transfer: {data}")
        return data

    def read(self, length):
        # Return zeros as dummy data
        dummy = bytearray([0]*length)
        print(f"[SIM] SPI {self.device} read {length} bytes -> {dummy}")
        return dummy

    def write(self, data):
        print(f"[SIM] SPI {self.device} write: {data}")

    def close(self):
        self._closed = True
        print(f"[SIM] SPI {self.device} closed")

    def __del__(self):
        if not self._closed:
            self.close()


# Example usage
if __name__ == "__main__":
    spi = SPI("/dev/spidev0.0", mode=1, max_speed=1000000)
    spi.write(b'\x01\x02\x03')
    data = spi.read(3)
    result = spi.transfer(b'\x04\x05\x06')
    spi.max_speed = 500000
    spi.bit_order = "lsb"
    spi.close()

    gpio = GPIO(17, GPIO.DIRECTION_OUT, initial=1)
    print(gpio.read())
    gpio.write(0)
    gpio.direction = GPIO.DIRECTION_IN
    gpio.close()