import os
import struct

SPI_NODE_TO_BUS = {
    "spi@7e204000": "SPI0",
    "spi@7e215080": "SPI1",
    "spi@7e2150c0": "SPI2",
}

def read_device_tree_spi_cs():
    dt_base = "/proc/device-tree"
    soc_path = os.path.join(dt_base, "soc")
    result = {}

    if not os.path.exists(soc_path):
        raise RuntimeError("Device tree not found. Are you running on a Raspberry Pi?")

    for entry in os.listdir(soc_path):
        if entry.startswith("spi@"):
            spi_path = os.path.join(soc_path, entry)
            cs_gpios_file = os.path.join(spi_path, "cs-gpios")
            cs_list = []
            if os.path.exists(cs_gpios_file):
                try:
                    with open(cs_gpios_file, "rb") as f:
                        data = f.read()
                        for i in range(0, len(data), 8):
                            gpio_data = data[i:i+8]
                            if len(gpio_data) < 8:
                                continue
                            phandle, flags_and_number = struct.unpack(">II", gpio_data)
                            gpio_number = flags_and_number & 0xff
                            flags = (flags_and_number >> 8)
                            cs_list.append({
                                "gpio_number": gpio_number,
                                "flags": flags,
                                "phandle": phandle
                            })
                except Exception as e:
                    cs_list.append({"error": str(e)})
            else:
                cs_list.append({"info": "No cs-gpios property found. Default CS pins may apply (CE0/CE1)."})
            result[SPI_NODE_TO_BUS.get(entry, entry)] = cs_list  # Use bus name if known, otherwise raw node

    return result

# Example usage:
if __name__ == "__main__":
    spi_cs_assignments = read_device_tree_spi_cs()
    import pprint
    pprint.pprint(spi_cs_assignments)
