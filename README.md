# zine machine

The zine machine is a little box that spits short passages of text out of a receipt printer.

It uses a raspberry pi zero w to drive the receipt printer over bluetooth and receive input from buttons. the python script `zine-machine.py` sends commands to the printer over a serial connection, using the module  [python-escpos](https://github.com/python-escpos/python-escpos) 

#  usage
Create directories in `zines/` to add new categories. `.zine` and `.txt` files placed in a category's directory are randomly selected when the button bound to that category is pressed.

## .zine files
A zine file is a text file (UTF-8) containing an optional metadata header followed by the text of a zine.

The header encodes metadata using colon `:` separated key-value pairs.  
It must begin with a line consisting of five dashes `-----`.  
Each key-value pair must be on a single line ended by a newline character `\n`.  
The header should be terminated with a line of five dashes `-----`, but is also considered ended by the first non-empty line that does not contain a colon.

The rest of the file contains the text of the zine.

```
-----
Title: a
Author: b
Description: c
URL: https://
Date Published: 
-----

Hello, welcome to my zine.
...
```

Keys are case insensitive and must not contain a colon. All whitespace is stripped from keys. Leading and trailing whitespace is stripped from values.

The zine machine recognizes these fields. More fields may be provided but may not be used by the zine machine.
 - `Title`
 - `Author`
 - `Description`
 - `Publisher`
 - `Date Published` - should be in ISO format. Recommended format: YYYY-MM-DD
 - `URL`

 ### markup
 `.zine` files support rich markup for enhanced features. Markup resembles a limited set of HTML tags. Some tags can be nested in other tags.
  - `<u>Text</u>` - Underline
  - `<img src="image.png">Caption</img>` - Insert an image with caption.

# setup

## flash raspberry pi OS

use the raspberry pi imager to flash Raspberry Pi OS to the SD card.
After you select the OS image, click the gear in the bottom right to set some advanced options that will make it easier to work with the pi.

Set hostname
zinemachine.local

Enable SSH
Use password authentication
Set username and password

Configure wireless LAN
Enter your WiFi SSID and password, and select your country code

Set locale settings
Set to your keyboard layout, or certain keypresses may be interpreted differently than you expect.

## start up raspberry pi
Insert the SD card into the raspberry pi and apply power. It will take awhile to boot up, so wait 2-5 minutes. Since you configured the WiFi network and SSH during the flashing step, you should be able to see the raspberry pi show up in your router's device table.

Open a terminal and connect to the raspberry pi with the following command, replacing `IP_ADDR` with the address of your Pi:
```
ssh pi@IP_ADDR
```

## update package repos
```
sudo apt-get upgrade
```

## bind bluetooth on boot
1. before we can connect to the printer, we need to bind RFCOMM to the printer's bluetooth device. then we can use the device `/dev/rfcomm0` to establish a connection.

modify etc/systemd/system/receipt-bluetooth.service so the MAC address matches the MAC address of your receipt printer (replace 02:3B:A9:4C:F0:AE with the MAC address listed by the printer, usually found by printing a test sheet)

```
nano etc/systemd/system/receipt-bluetooth.service
```

2. copy the bluetooth service file onto the system

```
sudo cp etc/systemd/system/receipt-bluetooth.service /etc/systemd/system/receipt-bluetooth.service
```

3. enable the service on boot. `--now` starts it immediately

```
sudo systemctl enable --now receipt-bluetooth.service
```

This service does NOT connect to the printer, it only configures the bluetooth connection. The actual connection is made when the device is used in `zine-machine.py`

## python setup

install the `[python-escpos](https://github.com/python-escpos/python-escpos) module
```
pip install --user python-escpos==3.0a8
```

The project also makes use of [RPi.GPIO](https://pypi.org/project/RPi.GPIO/), which should already be installed if you are running the zine machine on a Raspberry Pi.

# development
## setup
1. clone this repo
```
git clone 

cd zine-machine
```

2. Upgrade pip
```
pip install --upgrade pip
```

3. install the package in editable mode
```
python -m pip install -e . --user
```

## run
```
python -m zine-machine
```

## test
```
python -m unittest
```
