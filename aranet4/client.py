from bluepy import btle
import sys
import re

class Aranet4Error(Exception):
    pass

class Aranet4HistoryDelegate(btle.DefaultDelegate):
    def __init__(self, handle, param):
        btle.DefaultDelegate.__init__(self)
        self.param = param
        self.handle = handle
        self.results = {}
        self.reading = True

    def handleNotification(self, handle, data):
        raw = bytearray(data)
        if self.handle != handle:
            print "ERROR: invalid handle. Got", handle, ", expected", self.handle
            return

        param = raw[0]
        if self.param != param:
            print "ERROR: invalid handle. Got", param, ", expected", self.param
            return

        idx = raw[1] + (raw[2] << 8) - 1
        count = raw[3]
        pos = 4

        self.reading = count > 0

        while count > 0:
            step = 1 if param == Aranet4.PARAM_HUMIDITY else 2

            if len(raw) < pos + step:
                print "ERROR: unexpected end of data"
                break

            result = self._process(raw, pos, param)
            self.results[idx] = result
            pos += step
            idx += 1
            count -= 1

    def _process(self, data, pos, param):
        if param == Aranet4.PARAM_TEMPERATURE:
            return (data[pos] + (data[pos+1] << 8)) / 20.0
        elif param == Aranet4.PARAM_HUMIDITY:
            return data[pos]
        elif param == Aranet4.PARAM_PRESSURE:
            return (data[pos] + (data[pos+1] << 8)) / 10.0
        elif param == Aranet4.PARAM_CO2:
            return data[pos] + (data[pos+1] << 8)
        return None

class Aranet4:
    # Param IDs
    PARAM_TEMPERATURE = 1
    PARAM_HUMIDITY = 2
    PARAM_PRESSURE = 3
    PARAM_CO2 = 4

    # Aranet UUIDs and handles
    # Services
    AR4_SERVICE                   = btle.UUID("f0cd1400-95da-4f4b-9ac8-aa55d312af0c")
    GENERIC_SERVICE               = btle.UUID("00001800-0000-1000-8000-00805f9b34fb")
    COMMON_SERVICE                = btle.UUID("0000180a-0000-1000-8000-00805f9b34fb")

    # Read / Aranet service
    AR4_READ_CURRENT_READINGS     = btle.UUID("f0cd1503-95da-4f4b-9ac8-aa55d312af0c")
    AR4_READ_CURRENT_READINGS_DET = btle.UUID("f0cd3001-95da-4f4b-9ac8-aa55d312af0c")
    AR4_READ_INTERVAL             = btle.UUID("f0cd2002-95da-4f4b-9ac8-aa55d312af0c")
    AR4_READ_SECONDS_SINCE_UPDATE = btle.UUID("f0cd2004-95da-4f4b-9ac8-aa55d312af0c")
    AR4_READ_TOTAL_READINGS       = btle.UUID("f0cd2001-95da-4f4b-9ac8-aa55d312af0c")

    # Read / Generic servce
    GENERIC_READ_DEVICE_NAME       = btle.UUID("00002a00-0000-1000-8000-00805f9b34fb")

    # Read / Common servce
    COMMON_READ_MANUFACTURER_NAME = btle.UUID("00002a29-0000-1000-8000-00805f9b34fb")
    COMMON_READ_MODEL_NUMBER      = btle.UUID("00002a24-0000-1000-8000-00805f9b34fb")
    COMMON_READ_SERIAL_NO         = btle.UUID("00002a25-0000-1000-8000-00805f9b34fb")
    COMMON_READ_HW_REV            = btle.UUID("00002a27-0000-1000-8000-00805f9b34fb")
    COMMON_READ_SW_REV            = btle.UUID("00002a28-0000-1000-8000-00805f9b34fb")
    COMMON_READ_BATTERY           = btle.UUID("00002a19-0000-1000-8000-00805f9b34fb")

    # Write / Aranet service
    AR4_WRITE_CMD= btle.UUID("f0cd1402-95da-4f4b-9ac8-aa55d312af0c")

    # Subscribe / Aranet service
    AR4_SUBSCRIBE_HISTORY         = 0x0032
    AR4_NOTIFY_HISTORY            = 0x0031


    def __init__(self, *params):
        self.address = None
        if len(params):
            address=params[0]
            if not re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", address.lower()):
                raise Aranet4Error("Invalid device address")

            self.device = btle.Peripheral(address, btle.ADDR_TYPE_RANDOM)
            self.address = address
        else:
            candidates=self.findDevices()
            if candidates == []:
                 raise Aranet4Error("No paired Aranet4 device found")
            for x in candidates:
                print "WARN: Trying %s on %s..." % (x["name"], x["address"])
                try:
                    self.device = btle.Peripheral(x["address"], btle.ADDR_TYPE_RANDOM, iface=re.sub('[^0-9]','',x["adapter"]))
                    self.address = x["address"]
                except btle.BTLEDisconnectError:
                    pass
            if self.address == None:
                raise Aranet4Error("Couldn't connect to any paired Aranet4 devices")


    def findDevices(self):
        import dbus

        bus = dbus.SystemBus()
        o = dbus.Interface(bus.get_object('org.bluez','/'),
            'org.freedesktop.DBus.ObjectManager').GetManagedObjects()

        aranets=[]
        for dev in [p for p in o if any(x=="org.bluez.Device1" for x in o[p])]:

            obj = dbus.Interface(bus.get_object('org.bluez',dev),
            'org.freedesktop.DBus.Properties')

            if self.AR4_SERVICE in obj.Get("org.bluez.Device1", "UUIDs") \
                and obj.Get("org.bluez.Device1", "Paired"):
                    aranets.append({
                        "name": obj.Get("org.bluez.Device1", "Name"),
                        "address": obj.Get("org.bluez.Device1", "Address"),
                        "adapter": obj.Get("org.bluez.Device1", "Adapter"),
                    })

        return aranets

    def currentReadings(self, details=False):
        readings = {"temperature": -1, "humidity": -1, "pressure": -1, "co2": -1, "battery": -1, "ago": -1, "interval": -1}
        s = self.device.getServiceByUUID(self.AR4_SERVICE)
        if details:
            c = s.getCharacteristics(self.AR4_READ_CURRENT_READINGS_DET)
        else:
            c = s.getCharacteristics(self.AR4_READ_CURRENT_READINGS)

        b = bytearray(c[0].read())

        readings["co2"]         = self.le16(b, 0)
        readings["temperature"] = self.le16(b, 2) / 20.0
        readings["pressure"]    = self.le16(b, 4) / 10.0
        readings["humidity"]    = b[6]
        readings["battery"]     = b[7]

        if details:
            readings["interval"]      = self.le16(b, 9)
            readings["ago"] = self.le16(b, 11)

        return readings

    def getInterval(self):
        s = self.device.getServiceByUUID(self.AR4_SERVICE)
        c = s.getCharacteristics(self.AR4_READ_INTERVAL)
        return self.le16(c[0].read())

    def getName(self):
        s = self.device.getServiceByUUID(self.GENERIC_SERVICE)
        c = s.getCharacteristics(self.GENERIC_READ_DEVICE_NAME)
        return c[0].read()

    def getVersion(self):
        s = self.device.getServiceByUUID(self.COMMON_SERVICE)
        c = s.getCharacteristics(self.COMMON_READ_SW_REV)
        return c[0].read()

    def pullHistory(self, param, start=0x0001, end=0xFFFF):
        start = start + 1
        if start < 1:
            start = 0x0001

        val = bytearray.fromhex("820000000100ffff")
        val[1] = param
        self.writeLE16(val, 4, start)
        self.writeLE16(val, 6, end)

        s = self.device.getServiceByUUID(self.AR4_SERVICE)
        c = s.getCharacteristics(self.AR4_WRITE_CMD)
        rsp = c[0].write(val, True)

        # register delegate
        delegate = Aranet4HistoryDelegate(self.AR4_NOTIFY_HISTORY, param)
        self.device.setDelegate(delegate)

        rsp = self.device.writeCharacteristic(self.AR4_SUBSCRIBE_HISTORY, bytearray([1,0]), True)

        timeout = 3
        while timeout > 0 and delegate.reading:
            if self.device.waitForNotifications(1.0):
                continue
            timeout -= 1

        return delegate.results

    def getSecondsSinceUpdate(self):
        s = self.device.getServiceByUUID(self.AR4_SERVICE)
        c = s.getCharacteristics(self.AR4_READ_SECONDS_SINCE_UPDATE)
        return self.le16(c[0].read())

    def getTotalReadings(self):
        s = self.device.getServiceByUUID(self.AR4_SERVICE)
        c = s.getCharacteristics(self.AR4_READ_TOTAL_READINGS)
        return self.le16(c[0].read())

    def le16(self, data, start=0):
        raw = bytearray(data)
        return raw[start] + (raw[start+1] << 8)

    def writeLE16(self, data, pos, value):
        data[pos] = (value) & 0x00FF
        data[pos+1] = (value >> 8) & 0x00FF

    def dbgPrintChars(self):
        for s in self.device.getServices():
            print s
            for c in s.getCharacteristics():
                print " --> ", c
