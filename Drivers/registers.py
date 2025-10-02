from typing import List


class Register:
    def __init__(self, address: int, bit_map: List, alt_address: int = None, use_alt_address: bool = False):
        # alt_address: optional alternative address for the same register (e.g. for read vs write)
        # address: register address (e.g. integer)
        # bit_map: list of bit names in order of position, leftmost is MSB, e.g. ['BIT3', 'BIT2', 'BIT1', 'BIT0']
        #          use None for unused bits
        self.address = address            # register address (e.g. integer)
        self.alt_address = alt_address    # optional alternative address for the same register (e.g. for read vs write)
        self.bit_map = bit_map            # dict: bit name -> position
        self.use_alt_address = use_alt_address      # flag to indicate whether to use alt_address

    def __call__(self, *bits):
        # register instance called with bit names, returns integer value with those bits set
        pos = len(self.bit_map)  # start from MSB position
        value = 0
        for bit in self.bit_map:
            if bit in bits:
                value |= (1 << (pos - 1))
            pos -= 1

        return value

    def __int__(self):
        # returns the register address as integer
        if self.use_alt_address and self.alt_address is not None:
            return self.alt_address
        return self.address

    def __repr__(self):
        if self.alt_address is not None:
            return (f"<Register addr=0x{self.address:02X}, alt_addr=0x{self.alt_address:02X} "
                    f"bits={list(self.bit_map)}>")
        else:
            return f"<Register addr=0x{self.address:02X} bits={list(self.bit_map)}, alt_addr=None>"

    def __len__(self):
        # determine number of bits in the register from bit_map length
        return len(self.bit_map)


if __name__ == "__main__":
    reg = Register(0x1A, ['BIT3', 'BIT2', 'BIT1', 'BIT0'])
    print(reg)                  # <Register addr=0x1A bits=['BIT3', 'BIT2', 'BIT1', 'BIT0']>
    print(int(reg))             # 26
    print(len(reg))             # 4
    print(f"{reg('BIT0', 'BIT2'):08b}")  # 5 (0b0101)
    print(reg('BIT3'))          # 8 (0b1000)
    print(reg('BIT1'))          # 2 (0b0010)
    print(reg())                # 0 (no bits set)
