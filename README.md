# Aranet4 Python client
## Installation
You will need a dongle/adapter that supports at least Bluetooth 4.0 or higher and host stack that supports BLE features.
1. Install BLE stack and bluepy:
```
sudo apt-get update
sudo apt-get install libgtk2.0-dev libglib2.0-dev build-essential bluez
sudo pip2 install bluepy
sudo pip2 install requests
```
2. Make sure that `bluetoothd` is running with `--experimental`. On systemd (*sigh*), try this:
```
sudo sed -i 's#/bluetoothd$#/bluetoothd --experimental#' /lib/systemd/system/bluetooth.service
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
```
3. Pair device:
   1. Open bluetoothctl: `sudo bluetoothctl`
   1. Enable passcode support: `agent KeyboardOnly`
   1. Enable adapter: `power on`
   1. Scan devices: `scan on`
   1. When found your device, stop scan: `scan off`
   1. Pair device: `pair <DEVICE_ADDRESS>`
   1. Disconnect if automatically connected: `disconnect <DEVICE_ADDRESS>`
   1. Exit from bluetooth ctl: `exit`

## Usage
Run script:  `python aranet.py <DEVCE_ADDRESS> [OPTIONS]`
Options:
```
-n          Print current info only
-o <file>   Save history to file
-l <count>  Get <count> last records
-u <url>    Remote url for current value push
```

### Usage as library
You can use this in your own project by adding aranet4 folder to your project and in main code just import it:
```
import aranet4

device_mac = "00:00:00:00:00:00"

ar4 = aranet4.Aranet4(device_mac)
current = ar4.currentReadings()

print "Temperature:", current["temperature"]
print "Humidity:", current["humidity"]
print "Pressure:", current["pressure"]
print "CO2:", current["co2"]
```

## Examples
### Current readings
Input: `python aranet.py AA:BB:CC:DD:EE:FF -n`

Output:
```
--------------------------------------
Connected: Aranet4 00000 | v0.3.1
Updated 51 s ago. Intervals: 60 s
5040 total readings
--------------------------------------
CO2:          904 ppm
Temperature:  19.9 C
Humidity:     51 %
Pressure:     997.0 hPa
Battery:      96 %
--------------------------------------
```

### History
History file format: `Id;Date;Temperature;Humidity;Pressure;CO2`

History file example:
```
0;2019-09-09 15:11;25.00;43;1015.2;504
1;2019-09-09 15:12;25.00;43;1015.2;504
...
```

