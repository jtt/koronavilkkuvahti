# Simple Exposure Notification BLE beacon tracker

Uses [bluewalker](https://gitlab.com/jtaimisto/bluewalker/) to capture
Bluetooth LE beacons and gathers information about Covid-19 Exposure Notification
beacons.

## Usage

 Only Linux is supported as bluewalker needs the raw HCI socket available on linux.

 * Install bluewalker (requires golang to be installed): `go get gitlab.com/jtaimisto/bluewalker` (rest of the instructions assume bluewaker gets installed to ~/bin, this may be different directory depending on your golang installation).
 * bluewalker needs to have the `cap_net_admin` capability to be able to access HCI sockets: `sudo setcap cap_net_admin+eip ~/bin/bluewalker`
 * Install required python packages `pip install -r requirements.txt` (you may want to use python3 virtual environment)
 * Make sure the bluetooth device you are about to use is not in use `hciconfig hci0 down`
 * Start the tracker `python3 -m tracker --bluewalker ~/bin/bluewalker --hcidev hci0`
 * tracker will show the information about received Exposure Notification beacons.


