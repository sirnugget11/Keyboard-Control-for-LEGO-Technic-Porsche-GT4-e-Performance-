import pygame
import asyncio
from bleak import BleakScanner, BleakClient
import time

start_time = 0

class TechnicMoveHub:
    def __init__(self, device_name):
        self.device_name = device_name
        self.service_uuid = "00001623-1212-EFDE-1623-785FEABCD123"
        self.char_uuid = "00001624-1212-EFDE-1623-785FEABCD123"
        self.client = None
        
        self.BRAKE_OFF_OFF =    0b100
        self.BRAKE_OFF_ON =     0b101
        self.BRAKE_ON_ON =      0b000

    def run_discover(self):
        try:
            devices = BleakScanner.discover(timeout=20)
            return devices
        except Exception as e:
            print(f"Discovery failed with error: {e}")
            return None

    async def scan_and_connect(self):
        scanner = BleakScanner()
        print(f"searching for Technic Move Hub...")
        devices = await scanner.discover(timeout=5)

        for device in devices:
            if device.name is not None and self.device_name in device.name:
                print(f"Found device: {device.name} with address: {device.address}")
                self.client = BleakClient(device)
                
                await self.client.connect()
                if self.client.is_connected:
                    print(f"Connected to {self.device_name}")
                    
                    paired = await self.client.pair(protection_level=2)  # this is crucial!!!
                    if not paired:
                        print(f"could not pair")
                    return True
                else:
                    print(f"Failed to connect to {self.device_name}")
        print(f"Device {self.device_name} not found.")
        return False

    async def send_data(self, data):
        global start_time
        if self.client is None:
            print("No BLE client connected.")
            return

        try:
            # Write the data to the characteristic
            await self.client.write_gatt_char(self.char_uuid, data)
            #print(f"Data written to characteristic {self.char_uuid}: {data}")
       
            elapsed_time_ms = (time.time() - start_time) * 1000
            #print(f"Timestamp: {elapsed_time_ms:.2f} ms", end=" ")
            #print(' '.join(f'{byte:02x}' for byte in data))

        except Exception as e:
            print(f"Failed to write data: {e}")

    async def disconnect(self):
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            print("Disconnected from the device")
    
    LED_MODE_COLOR = 0x00
    LED_MODE_RGB = 0x01

    async def change_led_color(self, colorID):
        if self.client and self.client.is_connected:
            await self.send_data(bytearray([0x08, 0x00, 0x81, self.ID_LED, self.IO_TYPE_RGB_LED, 0x51, self.LED_MODE_COLOR, colorID]))

    async def motor_start_power(self, motor, power):
        if self.client and self.client.is_connected:
            await self.send_data(bytearray([0x08, 0x00, 0x81, motor & 0xFF, self.SC_BUFFER_NO_FEEDBACK, 0x51, self.MOTOR_MODE_POWER, 0xFF & power]))

    async def motor_stop(self, motor, brake=True):
        # motor can be 0x32, 0x33, 0x34
        if self.client and self.client.is_connected:
            await self.send_data(bytearray([0x08, 0x00, 0x81, motor & 0xFF, self.SC_BUFFER_NO_FEEDBACK, 0x51, self.MOTOR_MODE_POWER, self.END_STATE_BRAKE if brake else 0x00]))

    async def calibrate_steering(self):
        await self.send_data(bytes.fromhex("0d008136115100030000001000"))
        #await asyncio.sleep(0.1)
        await self.send_data(bytes.fromhex("0d008136115100030000000800"))
        #await asyncio.sleep(0.1)

    async def drive(self, speed=0, angle=0, brake=0x00):
        # Convert speed and angle to integers before applying bitwise operations
        speed = int(speed)
        angle = int(angle)

        await self.send_data(bytearray([0x0d, 0x00, 0x81, 0x36, 0x11, 0x51, 0x00, 0x03, 0x00, speed & 0xFF, angle & 0xFF, brake & 0xFF, 0x00]))
        #await asyncio.sleep(0.1)


def get_brake():
    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE]:
        return 0x01  # Brake (when spacebar is pressed)
    return 0x00

def draw_slider(surface, rect, value):
    # Draw the slider's outline
    pygame.draw.rect(surface, (255, 255, 255), rect, 2)
    # Fill the slider based on the current value (throttle)
    filled_rect = pygame.Rect(rect.left + 5, rect.top + 5, (rect.width - 10) * value, rect.height - 10)
    pygame.draw.rect(surface, (0, 255, 0), filled_rect)

async def main():
    device_name = "Technic Move"  # Replace with your BLE device's name
    hub = TechnicMoveHub(device_name)
    if not await hub.scan_and_connect():
        print("Technic hub not found!")
        return
        
    # Initialize Pygame and create a window
    pygame.init()
    screen = pygame.display.set_mode((640, 480))  # Create a simple window
    pygame.display.set_caption("Technic Move Hub Control")

    # Check for keyboard
    print("Press A to steer left, D to steer right, Spacebar to use brake.")
    print("Use W for forward, S for backward, and the slider to adjust throttle.")

    await hub.calibrate_steering()

    brake = 0x00  # Ensure brake starts off
    throttle_old = 0
    brake_oldwwx = 0
    was_brake = False
    start_time = time.time()

    slider_rect = pygame.Rect(50, 400, 540, 20)  # Throttle slider rectangle
    throttle = 0.5  # Initial throttle value (50%)
    
    steering_angle = 0
    last_steering_time = 0
    steering_speed = 400  # How fast the steering angle changes

    try:
        while True:
            # Pump Pygame event loop to process key presses
            pygame.event.pump()

            # Get the throttle value from keyboard inputs
            brake = get_brake()  # Check the brake status from the keyboard

            # Handle mouse drag for throttle slider
            if pygame.mouse.get_pressed()[0]:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                if slider_rect.collidepoint(mouse_x, mouse_y):
                    throttle = (mouse_x - slider_rect.left) / (slider_rect.width - 10)
                    throttle = min(max(throttle, 0), 1)  # Clamps the throttle between 0 and 1

            # Check if W or S is pressed for forward/backward movement
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:  # Forward
                speed = int(throttle * 100)
            elif keys[pygame.K_s]:  # Backward
                speed = -int(throttle * 100)
            else:
                speed = 0  # No movement if neither W nor S is pressed

            # Steering logic (based on how long the button is held)
            if keys[pygame.K_a]:  # Left
                steering_angle = max(-100, steering_angle - steering_speed * 0.05)
            elif keys[pygame.K_d]:  # Right
                steering_angle = min(100, steering_angle + steering_speed * 0.05)
            else:
                # Gradually return to center (0) if no key is pressed
                if steering_angle < 0:
                    steering_angle += steering_speed * 0.05
                    if steering_angle > 0:
                        steering_angle = 0
                elif steering_angle > 0:
                    steering_angle -= steering_speed * 0.05
                    if steering_angle < 0:
                        steering_angle = 0

            # Print throttle, steering, and brake status
            print(f"Throttle: {throttle*100:.1f}%, Steering: {steering_angle}, Brake: {'On' if brake else 'Off'}, Speed: {speed}")
            await hub.drive(speed, steering_angle, brake)

            # Fill the screen with black
            screen.fill((0, 0, 0))

            # Draw the slider
            draw_slider(screen, slider_rect, throttle)

            # Render simple text on the window to show current state
            font = pygame.font.Font(None, 36)
            text = font.render(f"Throttle: {throttle*100:.1f}%, Steering: {steering_angle}, Brake: {'On' if brake else 'Off'}", True, (255, 255, 255))
            screen.blit(text, (10, 10))

            # Update the display
            pygame.display.flip()

            # Sleep to avoid excessive CPU usage
            await asyncio.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        pygame.quit()

if __name__ == "__main__":
    asyncio.run(main())
