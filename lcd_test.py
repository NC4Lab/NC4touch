from luma.core.interface.serial import spi
from luma.lcd.device import ili9488
from PIL import Image, ImageDraw

def main():
    # Define your DC and RST GPIO pins
    DC_PIN = 25  # Replace with your chosen GPIO pin for DC
    RST_PIN = 24  # Replace with your chosen GPIO pin for Reset (if used)

    # Initialize SPI interface
    serial = spi(port=0, device=0, gpio_DC=DC_PIN, gpio_RST=RST_PIN)

    # Initialize the LCD device
    device = ili9488(serial_interface=serial, width=320, height=480)

    # Create a blank image to display
    image = Image.new("RGB", (320, 480), "black")  # Create a 320x480 black image
    draw = ImageDraw.Draw(image)

    # Draw a simple test pattern
    draw.rectangle((10, 10, 310, 470), outline="white", width=5)  # White border
    draw.text((100, 220), "Hello, LCD!", fill="white")  # Add text

    # Send the image to the LCD
    device.display(image)
    print("Image displayed on the LCD!")

if __name__ == "__main__":
    main()
