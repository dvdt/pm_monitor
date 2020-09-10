import time
import logging
logger = logging.getLogger(__name__)
import pyftdi
import pyftdi.serialext

import os
sensor_ftdi_url = os.environ.get('PM25_FTDI_URL', 'ftdi:///1')
port = pyftdi.serialext.serial_for_url(sensor_ftdi_url, baudrate=9600, timeout=10, write_timeout=10)

class HPMDriver:
    """
    Driver for Honeywell Particular Matter Sensor
    """

    READ_PM_RESULTS = bytes.fromhex("68010493")
    START_PARTICLE_MEASUREMENT = bytes.fromhex("68010196")
    STOP_PARTICLE_MEASUREMENT = bytes.fromhex("68010295")
    SET_CUSTOMER_ADJ_COEF = bytes.fromhex("680208642A")
    READ_CUSTOMER_ADJ_COEF = bytes.fromhex("68011087")
    STOP_AUTO_SEND = bytes.fromhex("68012077")
    ENABLE_AUTO_SEND = bytes.fromhex("68014057")

    def __init__(self, port):
        # Turn off auto-send
        self.port = port
        self.autosend_off()
        assert port.timeout, "Set a timeout for the prot"
        # Read anything in the buffer and throw it away.
        self.port.read(999)

    def autosend_off(self):
        self.port.write(self.STOP_AUTO_SEND)

    def autosend_on(self):
        self.port.write(self.ENABLE_AUTO_SEND)

    def read_particle_measurement(self):
        """
        Reads the PM2.5 sensor.
        :return: tuple of (pm2.5, pm10)
        """
        self.port.write(self.READ_PM_RESULTS)
        result = bytearray(self.port.read(8))
        if not result:
            # Timeout
            return None
        if len(result) != 8:
            # Sometimes not enough results are returned
            logger.error("Didn't get enough data back")
            return None
        head, length, cmd, df1, df2, df3, df4, cs = result
        assert self.is_checksum_valid(result)
        return 256*df1 + df2, 256*df3 + df4

    @classmethod
    def is_checksum_valid(cls, hpm_bytes):
        cs = hpm_bytes[-1] # The checksum is the last element
        # checksum computation is from the datasheet
        cs_computed = (65536 - sum(hpm_bytes[:-1])) % 256
        return cs == cs_computed

if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s %(message)s', level=logging.INFO)
    fh = logging.FileHandler('PM25.log')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(message)s'))
    pollution_logger = logging.getLogger('PollutionMonitor')
    pollution_logger.addHandler(fh)

    hpm = HPMDriver(port)
    while True:
        pm_measurements = hpm.read_particle_measurement()
        if pm_measurements:
            pm25, pm10 = pm_measurements
        pollution_logger.info(f"PM2.5 is {pm25}")
        time.sleep(5)

