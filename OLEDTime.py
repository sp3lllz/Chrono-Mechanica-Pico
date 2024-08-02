# import network
# import urequests
# import usocket
from machine import Pin, SPI
import usocket as socket
import utime, time, framebuf, network, urequests, struct

# Screen setup
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

NTP_DELTA = 2208988800  # NTP time starts from 1st Jan 1900, Unix time starts from 1st Jan 1970
NTP_HOST = "pool.ntp.org"
NTP_PORT = 123

# Define the timezone offset in hours (e.g., for UTC+2, set TZ_OFFSET to 2; for UTC-5, set TZ_OFFSET to -5)
TZ_OFFSET = 1

class OLED_2inch23(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 32

        self.cs = Pin(CS, Pin.OUT)
        self.rst = Pin(RST, Pin.OUT)

        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1, 1000_000)
        self.spi = SPI(1, 10000_000, polarity=0, phase=0, sck=Pin(SCK), mosi=Pin(MOSI), miso=None)
        self.dc = Pin(DC, Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

        self.white = 0xffff
        self.black = 0x0000

    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize display"""
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)

        self.write_cmd(0xAE)  # turn off OLED display

        self.write_cmd(0x04)  # turn off OLED display

        self.write_cmd(0x10)  # turn off OLED display

        self.write_cmd(0x40)  # set lower column address
        self.write_cmd(0x81)  # set higher column address
        self.write_cmd(0x80)  # --set start line address  Set Mapping RAM Display Start Line (0x00~0x3F, SSD1305_CMD)
        self.write_cmd(0xA1)  # --set contrast control register
        self.write_cmd(0xA6)  # Set SEG Output Current Brightness
        self.write_cmd(0xA8)  # --Set SEG/Column Mapping
        self.write_cmd(0x1F)  # Set COM/Row Scan Direction
        self.write_cmd(0xC8)  # --set normal display
        self.write_cmd(0xD3)  # --set multiplex ratio(1 to 64)
        self.write_cmd(0x00)  # --1/64 duty
        self.write_cmd(0xD5)  # -set display offset Shift Mapping RAM Counter (0x00~0x3F)
        self.write_cmd(0xF0)  # -not offset
        self.write_cmd(0xD8)  # --set display clock divide ratio/oscillator frequency
        self.write_cmd(0x05)  # --set divide ratio, Set Clock as 100 Frames/Sec
        self.write_cmd(0xD9)  # --set pre-charge period
        self.write_cmd(0xC2)  # Set Pre-Charge as 15 Clocks & Discharge as 1 Clock
        self.write_cmd(0xDA)  # --set com pins hardware configuration
        self.write_cmd(0x12)
        self.write_cmd(0xDB)  # set vcomh
        self.write_cmd(0x08)  # Set VCOM Deselect Level
        self.write_cmd(0xAF)  # -Set Page Addressing Mode (0x00/0x01/0x02)

    def show(self):
        for page in range(0, 4):
            self.write_cmd(0xb0 + page)
            self.write_cmd(0x04)
            self.write_cmd(0x10)
            self.dc(1)
            for num in range(0, 128):
                self.write_data(self.buffer[page * 128 + num])

if __name__ == '__main__':
    OLED = OLED_2inch23()
    OLED.fill(0x0000)
    OLED.text("Hello !", 32, 12, OLED.white)
    OLED.show()
    time.sleep(2)
    OLED.fill(0x0000)
    OLED.show()
    OLED.rect(0, 0, 128, 32, OLED.white)
    OLED.rect(10, 6, 20, 20, OLED.white)
    time.sleep(0.1)
    OLED.show()
    OLED.fill_rect(40, 6, 20, 20, OLED.white)
    time.sleep(0.1)
    OLED.show()
    OLED.rect(70, 6, 20, 20, OLED.white)
    time.sleep(0.1)
    OLED.show()
    OLED.fill_rect(100, 6, 20, 20, OLED.white)
    time.sleep(0.1)
    OLED.show()
    time.sleep(0.5)

# Define your Wi-Fi credentials
wifi_ssid = "Johto"
wifi_password = "saNhf2m@BDLD"

# Connect to Wi-Fi
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(wifi_ssid, wifi_password)

# Wait for the Wi-Fi connection to establish
while not wifi.isconnected():
    pass

print("Connected to Wi-Fi")
# Print network information
OLED.fill(0)
OLED.text("Connected", 32, 5)
OLED.text("to Wi-Fi", 32, 15)
OLED.show()
time.sleep(1)
OLED.fill(0)

def get_ntp_time():
    addr = socket.getaddrinfo(NTP_HOST, NTP_PORT)[0][-1]
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1)
    
    # NTP request packet
    msg = b'\x1b' + 47 * b'\0'
    s.sendto(msg, addr)
    
    try:
        msg, _ = s.recvfrom(48)
    except OSError as e:
        print("Failed to receive NTP response:", e)
        return None
    finally:
        s.close()
    
    val = struct.unpack("!I", msg[40:44])[0]
    return val - NTP_DELTA

def adjust_timezone(epoch_time, offset):
    return epoch_time + offset * 3600

def display_time_on_OLED(OLED, formatted_time):
    OLED.fill(0)
    OLED.text(formatted_time, 45, 10)
    OLED.show()

def main():
    # Fetch and set the time once at boot
    t = get_ntp_time()
    if t is not None:
        t = adjust_timezone(t, TZ_OFFSET)
        tm = time.localtime(t)
        time.mktime(tm)  # Set the internal clock

    last_displayed_time = ""

    while True:
        # Update time based on the internal clock
        current_time = time.localtime()
        formatted_time = "{:02}:{:02}".format(current_time[3], current_time[4])

        if formatted_time != last_displayed_time:
            print("Current time:", formatted_time)
            display_time_on_OLED(OLED, formatted_time)
            last_displayed_time = formatted_time
        
        # Update time every 1 second
        time.sleep(1)

if __name__ == "__main__":
    main()
