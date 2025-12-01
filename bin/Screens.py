import datetime
import logging
import textwrap
import time

from PIL import Image, ImageDraw, ImageFont, ImageOps

from bin.SSD1306 import SSD1306_128_32 as SSD1306
from bin.SSD1306 import SSD1309_128_64 as SSD1309
from bin.Utils import Utils


class Display:
    DEFAULT_BUSNUM = 1
    SCREENSHOT_PATH = "./img/examples/"

    def __init__(self, busnum = None, screenshot = False, rotate = False,
                 driver = "SSD1306"):
        self.logger = logging.getLogger('Display')

        if not isinstance(busnum, int):
            busnum = Display.DEFAULT_BUSNUM

        if driver == "SSD1306":
          self.logger.info("Creating a SSD1306 driver")
          self.device = SSD1306(busnum)
        elif driver == "SSD1309":
          self.logger.info("Creating a SSD1309 driver")
          self.device = SSD1309(busnum)
        else:
          # Preserve current behavior as default.
          self.device = SSD1306(busnum)
        self.clear()
        self.width = self.device.width
        self.height = self.device.height
        self.rotate = rotate

        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        self.screenshot = screenshot

    def clear(self):
        self.device.begin()
        self.device.clear()
        self.device.display()

    def prepare(self):
        self.draw.rectangle((0, 0, self.width, self.height), outline = 0, fill = 0)

    def show(self):
        if isinstance(self.rotate, int):
            self.image = self.image.rotate(self.rotate)
            self.draw = ImageDraw.Draw(self.image)

        self.device.image(self.image)
        self.device.display()

    def capture_screenshot(self, name):
        if self.screenshot:
            if isinstance(self.screenshot, str):
                dir = self.screenshot
            else:
                dir = Display.SCREENSHOT_PATH

            path = dir.rstrip('/') + '/' + name.lower() + '.png'
            self.logger.info("saving screenshot to '" + path + "'")
            self.image.save(path)

    def human_readable_time_now(self) -> str:
         now = datetime.datetime.now(datetime.timezone.utc)
         return "T["+now.strftime("%H:%M:%S")+"]"

    def human_readable_time_since(self, date_string: str) -> str:
        """
        Calculates the time elapsed from a given ISO format date string to now
        and returns it in a human-readable format.

        Args:
            date_string: An ISO 8601 formatted date string 
                         (e.g., "2025-10-17T18:19:13+00:00").

        Returns:
            A formatted string like "X m ago", "Y h ago", or "Z d ago"
            with two digits of precision.
        """
        # Parse the input string into a timezone-aware datetime object.
        past_date = datetime.datetime.fromisoformat(date_string)

        # Get the current time in UTC to ensure an apples-to-apples comparison.
        now = datetime.datetime.now(datetime.timezone.utc)

         # Calculate the difference between now and the past date.
        time_delta = now - past_date

        # Get the total number of seconds in the time difference.
        total_seconds = time_delta.total_seconds()

        # Determine the most appropriate unit (minutes, hours, or days).
        if total_seconds < 3600:  # Less than 1 hour
            value = total_seconds / 60.
            unit = "m"
        elif total_seconds < 86400:  # Less than 1 day (24 * 3600)
            value = total_seconds / 3600
            unit = "h"
        else:  # 1 day or more
            value = total_seconds / 86400
            unit = "d"

        # Format the string with 2 digits of precision and the determined unit.
        return f"{value:.2f}{unit} ago"


class BaseScreen:
    font_path = Utils.current_dir + "/fonts/DejaVuSans.ttf"
    font_bold_path = Utils.current_dir + "/fonts/DejaVuSans-Bold.ttf"
    fonts = {}

    def __init__(self, duration, display = Display(), utils = Utils(), config = None):
        self.display = display
        self.duration = duration
        self.utils = utils
        self.config = config
        self.font_size = 8
        self.logger = logging.getLogger('Screen')
        self.logger.info("'" + self.__class__.__name__ + "' created")

    @property
    def name(self):
        return str(self.__class__.__name__).lower().replace("screen", "")

    def set_icon(self, path):
        """ set the image for this screen """
        if not self.icon or self.icon_path != path:
           self.icon_path = path
           img = Image.open(r"" + Utils.current_dir + self.icon_path)
           # img = img.convert('RGBA') # MUST be in RGB mode for the OLED
           # invert black icon to white (255) for OLED display
           #self.icon = ImageOps.invert( self.icon )
           self.icon = img.resize([30, 30])


    @property
    def text_indent(self):
        """ :return: how far to indent a line of text for this screen """
        return 0

    def capture_screenshot(self, name = None):
        if not name:
            name = self.name
        self.display.capture_screenshot(name)

    def display_text(self, text_lines):
        """ Display multiple lines of text with auto-resizing/positioning
            of the text based on the passed in text. """
        if not text_lines:
           return

        # set the number of lines, which reconfigures fonts
        self.set_text_lines(len(text_lines))
        font = self.font()

        line = 0
        for text in text_lines:
           # display the text line at the correct x / y based on config
           x = self.text_indent
           y = self.text_y[line]
           self.display.draw.text((x, y), text, font=font, fill=255)

           line += 1
           if line >= 6:
              return # too many lines passed in!

    def set_text_lines(self, num_lines):
       """ Set the number of text lines that will be displayed. """
       self.text_lines = num_lines

       # set defaults based on number of lines
       if self.text_lines > 2:
          if self.text_indent < 10:
             self.font_size = 10
          else:
             self.font_size = 9
       else:
          if self.text_indent < 10:
             self.font_size = 14
          else:
             self.font_size = 13

    @property
    def text_y(self):
        if self.text_lines == 1:
           return [0]
        elif self.text_lines == 2:
           return [0, 18]
        elif self.text_lines == 3:
           return [0, 11, 21]
        elif self.text_lines < 6:
           return [0, 11, 21, 31, 41, 51]
        else:
           return None

    def font(self, size = None, is_bold = False):
        # default to the current screen's font size if none provided
        if not size:
           size = self.font_size

        suffix = None
        if is_bold:
            suffix = '_bold'

        key = 'font_{}{}'.format(str(size), suffix)

        if key not in BaseScreen.fonts:
            font = BaseScreen.font_path
            if is_bold:
                font = BaseScreen.font_bold_path

            font = ImageFont.truetype(font, int(size))
            BaseScreen.fonts[key] = font
        return BaseScreen.fonts[key]

    # helper function to display the current page (used by standard screens)
    def render_with_defaults(self):
        self.capture_screenshot()
        self.display.show()
        time.sleep(self.duration)

    def render(self):
        self.display.show()

    def run(self):
        self.display.prepare()
        self.render()


class ExitScreen(BaseScreen):
    def render(self):
      self.display_text(["GOOD BYE"])
      self.render_with_defaults()
       
class StatusScreen(BaseScreen):
    def render(self):
        hostname = self.utils.get_hostname()
        current_time = self.display.human_readable_time_now()
        hostname_line = f"{hostname} T={current_time} +"+current_time
        mem = self.utils.get_hassio_entity("sensor.system_monitor_memory_usage", "state")
        cpu = self.utils.get_hassio_entity("sensor.system_monitor_processor_use", "state")
        disk = self.utils.get_hassio_entity("sensor.system_monitor_disk_usage", "state")
        temp = self.utils.get_hassio_entity("sensor.system_monitor_processor_temperature", "state")
        resource_line = f"C{cpu}% M{mem}% D{disk}% t{temp}°C"

        ip_eth = self.utils.get_hassio_entity("sensor.system_monitor_ipv4_address_end0", "state")
        ip_wlan = self.utils.get_hassio_entity("sensor.system_monitor_ipv4_address_wlan0", "state")
        ip_line = f"A {ip_eth} {ip_wlan}"

        ping_status = self.utils.get_hassio_entity("binary_sensor.8_8_8_8", "state")
        ping_latency = self.utils.get_hassio_entity("sensor.8_8_8_8_round_trip_time_average", "state")
        if ping_status == "on":
          ping_line = ping_latency
        else:
          ping_line = "XXX"
        download_speed = self.utils.get_hassio_entity("sensor.wan_download_speed_mbps", "state")
        upload_speed = self.utils.get_hassio_entity("sensor.wan_upload_speed_mbps", "state")
        wan = f'P{ping_line} U{upload_speed} D{download_speed}'

        last_boot = self.utils.get_hassio_entity("sensor.system_monitor_last_boot", "state")
        boot_since = self.display.human_readable_time_since(last_boot)
        boot = f"B {boot_since}"
        self.logger.info(hostname)
        self.logger.info(ip_line)
        self.logger.info(resource_line)
        self.logger.info(wan)
        self.logger.info(boot)

        self.display_text([ hostname, resource_line, ip_line, wan, boot ])

        self.render_with_defaults()

