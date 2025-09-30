import platform
import sys


def is_raspberry_pi():
    # Check for 'raspberrypi' in the platform string
    if 'raspberrypi' in platform.uname().node.lower():
        return True

    # Try to read /proc/device-tree/model
    try:
        with open('/proc/device-tree/model') as f:
            if 'Raspberry Pi' in f.read():
                return True
    except Exception:
        pass

    # Check for BCM in cpuinfo
    try:
        with open('/proc/cpuinfo') as f:
            for line in f:
                if line.startswith('Hardware') and 'BCM' in line:
                    return True
    except Exception:
        pass

    return False


def is_windows():
    # Checks if the platform is Windows
    return sys.platform.startswith('win') or platform.system() == 'Windows'


def is_linux():
    # Checks if the platform is Linux
    return sys.platform.startswith('linux') or platform.system() == 'Linux'


def get_platform():
    if is_windows():
        return 'Windows'
    elif is_linux():
        if is_raspberry_pi():
            return 'Raspberry Pi'
        else:
            return 'Linux'
    else:
        return 'Unknown'


if __name__ == "__main__":
    platform_name = get_platform()
    print(f"Detected platform: {platform_name}")
