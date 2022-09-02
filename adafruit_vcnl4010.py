# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
#
# SPDX-License-Identifier: MIT

"""
`adafruit_vcnl4010`
====================================================

CircuitPython module for the VCNL4010 proximity and light sensor.  See
examples/vcnl4010_simpletest.py for an example of the usage.

* Author(s): Tony DiCola

Implementation Notes
--------------------

**Hardware:**

* Adafruit `VCNL4010 Proximity/Light sensor breakout
  <https://www.adafruit.com/product/466>`_ (Product ID: 466)

**Software and Dependencies:**

* Adafruit CircuitPython firmware for the supported boards:
  https://circuitpython.org/downloads

* Adafruit's Bus Device library: https://github.com/adafruit/Adafruit_CircuitPython_BusDevice
"""
from micropython import const

from adafruit_bus_device import i2c_device

try:
    from typing import Optional, List  # pylint: disable=unused-import
    from busio import I2C
except ImportError:
    pass

__version__ = "0.0.0+auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_VCNL4010.git"


# Internal constants:
_VCNL4010_I2CADDR_DEFAULT = const(0x13)
_VCNL4010_COMMAND = const(0x80)
_VCNL4010_PRODUCTID = const(0x81)
_VCNL4010_PROXRATE = const(0x82)
_VCNL4010_IRLED = const(0x83)
_VCNL4010_AMBIENTPARAMETER = const(0x84)
_VCNL4010_AMBIENTDATA = const(0x85)
_VCNL4010_PROXIMITYDATA = const(0x87)
_VCNL4010_INTCONTROL = const(0x89)
_VCNL4010_PROXIMITYADJUST = const(0x8A)
_VCNL4010_INTSTAT = const(0x8E)
_VCNL4010_MODTIMING = const(0x8F)
_VCNL4010_MEASUREAMBIENT = const(0x10)
_VCNL4010_MEASUREPROXIMITY = const(0x08)
_VCNL4010_AMBIENTREADY = const(0x40)
_VCNL4010_PROXIMITYREADY = const(0x20)
_VCNL4010_AMBIENT_LUX_SCALE = 0.25  # Lux value per 16-bit result value.

# User-facing constants:
# Number of proximity measuremenrs per second
SAMPLERATE_1_95 = 0
SAMPLERATE_3_90625 = 1
SAMPLERATE_7_8125 = 2
SAMPLERATE_16_625 = 3
SAMPLERATE_31_25 = 4
SAMPLERATE_62_5 = 5
SAMPLERATE_125 = 6
SAMPLERATE_250 = 7

# Proximity modulator timing
FREQUENCY_3M125 = 3
FREQUENCY_1M5625 = 2
FREQUENCY_781K25 = 1
FREQUENCY_390K625 = 0

# Disable pylint's name warning as it causes too much noise.  Suffixes like
# BE (big-endian) or mA (milli-amps) don't confirm to its conventions--by
# design (clarity of code and explicit units).  Disable this globally to prevent
# littering the code with pylint disable and enable and making it less readable.
# pylint: disable=invalid-name


class VCNL4010:
    """Vishay VCNL4010 proximity and ambient light sensor.

    :param ~busio.I2C i2c: The I2C bus the VCNL4010 is connected to
    :param int address: (optional) The I2C address of the device. Defaults to :const:`0x13`

    **Quickstart: Importing and using the VCNL4010**

        Here is an example of using the :class:`VCNL4010` class.
        First you will need to import the libraries to use the sensor

        .. code-block:: python

            import board
            import adafruit_vcnl4010

        Once this is done you can define your `board.I2C` object and define your sensor object

        .. code-block:: python

            i2c = board.I2C()   # uses board.SCL and board.SDA
            sensor = adafruit_vcnl4010.VCNL4010(i2c)

        Now you have access to the :attr:`sensor.proximity` and
        :attr:`ambient_lux` attributes


        .. code-block:: python

            proximity = sensor.proximity
            ambient_lux = sensor.ambient_lux

    """

    # Class-level buffer for reading and writing data with the sensor.
    # This reduces memory allocations but means the code is not re-entrant or
    # thread safe!
    _BUFFER = bytearray(3)

    def __init__(self, i2c: I2C, address: int = _VCNL4010_I2CADDR_DEFAULT) -> None:
        self._device = i2c_device.I2CDevice(i2c, address)
        # Verify chip ID.
        revision = self._read_u8(_VCNL4010_PRODUCTID)
        if (revision & 0xF0) != 0x20:
            raise RuntimeError("Failed to find VCNL4010, check wiring!")
        self.led_current = 20
        self.samplerate = SAMPLERATE_1_95
        self.frequency = FREQUENCY_390K625
        self._write_u8(_VCNL4010_INTCONTROL, 0x08)

    def _read_u8(self, address: int) -> int:
        # Read an 8-bit unsigned value from the specified 8-bit address.
        with self._device as i2c:
            self._BUFFER[0] = address & 0xFF
            i2c.write_then_readinto(self._BUFFER, self._BUFFER, out_end=1, in_start=1)
        return self._BUFFER[1]

    def _read_u16BE(self, address: int) -> int:
        # Read a 16-bit big-endian unsigned value from the specified 8-bit address.
        with self._device as i2c:
            self._BUFFER[0] = address & 0xFF
            i2c.write_then_readinto(self._BUFFER, self._BUFFER, out_end=1, in_start=1)
        return (self._BUFFER[1] << 8) | self._BUFFER[2]

    def _write_u8(self, address: int, val: int) -> None:
        # Write an 8-bit unsigned value to the specified 8-bit address.
        with self._device as i2c:
            self._BUFFER[0] = address & 0xFF
            self._BUFFER[1] = val & 0xFF
            i2c.write(self._BUFFER, end=2)

    @property
    def led_current(self) -> int:
        """The current of the LED.  The value is in units of 10mA
        and can only be set to 0 (0mA/off) to 20 (200mA).  See the datasheet
        for how LED current impacts proximity measurements.  The default is
        200mA.
        """
        return self._read_u8(_VCNL4010_IRLED) & 0x3F

    @led_current.setter
    def led_current(self, val: int) -> None:
        assert 0 <= val <= 20
        self._write_u8(_VCNL4010_IRLED, val)

    @property
    def led_current_mA(self) -> int:
        """The current of the LED in milliamps.  The value here is
        specified in milliamps from 0-200.  Note that this value will be
        quantized down to a smaller less-accurate value as the chip only
        supports current changes in 10mA increments, i.e. a value of 123 mA will
        actually use 120 mA.  See the datasheet for how the LED current impacts
        proximity measurements, and the led_current property to explicitly set
        values without quantization or unit conversion.
        """
        return self.led_current * 10

    @led_current_mA.setter
    def led_current_mA(self, val: int) -> None:
        self.led_current = val // 10

    @property
    def samplerate(self) -> int:
        """
        The frequency of proximity measurements per second.  Must be a value of:

        - SAMPLERATE_1_95: 1.95 measurements/sec (default)
        - SAMPLERATE_3_90625: 3.90625 measurements/sec
        - SAMPLERATE_7_8125: 7.8125 measurements/sec
        - SAMPLERATE_16_625: 16.625 measurements/sec
        - SAMPLERATE_31_25: 31.25 measurements/sec
        - SAMPLERATE_62_5: 62.5 measurements/sec
        - SAMPLERATE_125: 125 measurements/sec
        - SAMPLERATE_250: 250 measurements/sec

        See the datasheet for how frequency changes the power consumption and
        proximity detection accuracy.
        """
        return self._read_u8(_VCNL4010_PROXRATE)

    @samplerate.setter
    def samplerate(self, val: int) -> None:
        assert 0 <= val <= 7
        self._write_u8(_VCNL4010_PROXRATE, val)

    @property
    def frequency(self) -> int:
        """
        Proximity modulator timimg. This is the frequency of the IR square
        wave used for the proximity measurement.

                Must be a value of:

        - FREQUENCY_3M125: 3.125 Mhz
        - FREQUENCY_1M5625: 1.5625 Mhz
        - FREQUENCY_781K25: 781.25 Khz
        - FREQUENCY_390K625: 390.625 Khz (default)

        The datasheet recommended leaving this at the default.
        """
        return (self._read_u8(_VCNL4010_MODTIMING) >> 3) & 0x03

    @frequency.setter
    def frequency(self, val: int) -> None:
        assert 0 <= val <= 3
        timing = self._read_u8(_VCNL4010_MODTIMING)
        timing &= ~0b00011000
        timing |= (val << 3) & 0xFF
        self._write_u8(_VCNL4010_MODTIMING, timing)

    # Pylint gets confused with loops and return values.  Disable the spurious
    # warning for the next few functions (it hates when a loop returns a value).
    # pylint: disable=inconsistent-return-statements
    @property
    def proximity(self) -> int:
        """The detected proximity of an object in front of the sensor.  This
        is a unit-less unsigned 16-bit value (0-65535) INVERSELY proportional
        to the distance of an object in front of the sensor (up to a max of
        ~200mm).  For example a value of 10 is an object farther away than a
        value of 1000.  Note there is no conversion from this value to absolute
        distance possible, you can only make relative comparisons.
        """
        # Clear interrupt.
        status = self._read_u8(_VCNL4010_INTSTAT)
        status &= ~0x80
        self._write_u8(_VCNL4010_INTSTAT, status)
        # Grab a proximity measurement.
        self._write_u8(_VCNL4010_COMMAND, _VCNL4010_MEASUREPROXIMITY)
        # Wait for result, then read and return the 16-bit value.
        while True:
            result = self._read_u8(_VCNL4010_COMMAND)
            if result & _VCNL4010_PROXIMITYREADY:
                return self._read_u16BE(_VCNL4010_PROXIMITYDATA)

    @property
    def ambient(self) -> int:
        """The detected ambient light in front of the sensor.  This is
        a unit-less unsigned 16-bit value (0-65535) with higher values for
        more detected light.  See the :attr:`ambient_lux property` for a value in lux.
        """
        # Clear interrupt.
        status = self._read_u8(_VCNL4010_INTSTAT)
        status &= ~0x80
        self._write_u8(_VCNL4010_INTSTAT, status)
        # Grab an ambient light measurement.
        self._write_u8(_VCNL4010_COMMAND, _VCNL4010_MEASUREAMBIENT)
        # Wait for result, then read and return the 16-bit value.
        while True:
            result = self._read_u8(_VCNL4010_COMMAND)
            if result & _VCNL4010_AMBIENTREADY:
                return self._read_u16BE(_VCNL4010_AMBIENTDATA)

    # pylint: enable=inconsistent-return-statements

    @property
    def ambient_lux(self) -> int:
        """The detected ambient light in front of the sensor as a value in
        lux.
        """
        return self.ambient * _VCNL4010_AMBIENT_LUX_SCALE
