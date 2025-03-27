import sys
import asyncio

async def check_ble_support():
    try:
        if sys.platform == "win32":
            from bleak import BleakScanner
            devices = await BleakScanner.discover(timeout=2)
            return bool(devices)
        
        elif sys.platform.startswith("linux"):
            import subprocess
            result = subprocess.run(["hciconfig"], capture_output=True, text=True)
            return "LE" in result.stdout
        
        elif sys.platform == "darwin":
            from CoreBluetooth import CBCentralManager
            return CBCentralManager().state() == 5  # 5 = Powered On
        
        else:
            return False  # Unsupported OS
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(check_ble_support())
    if result:
        print("Your computer supports Bluetooth Low Energy (BLE).")
    else:
        print("Your computer does NOT support BLE.")
