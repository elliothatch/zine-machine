# The Zine Machine

The Zine Machine is a little box that spits short passages of text out of a receipt printer.

It uses a python running on a Raspberry Pi Zero W to receive input from GPIO buttons and drive the receipt printer over bluetooth. When printing a zine, it loads `.zine` files from the filesystem and sends the commands to the printer over a serial connection, using the module [python-escpos](https://github.com/python-escpos/python-escpos) 

#  Usage
Create directories in `zines/` to add new categories of zines. `.zine` and `.txt` files placed in a category's directory are randomly selected when the button bound to that category is pressed.

## .zine files
A zine file is a text file (UTF-8) containing an optional metadata header followed by the text of a zine.

The header encodes metadata using colon `:` separated key-value pairs.  
It must begin with a line consisting of five dashes `-----`.  
Each key-value pair must be on a single line ended by a newline character `\n`.  
The header should be terminated with a line of five dashes `-----`. The first non-empty line that does not contain a colon is also considered the end of the header.

The rest of the file contains the text of the zine.

```
-----
Title: My first zine
Author: Elliot Hatch
Description: A receipt printer will print this!
URL: https://
Date Published: 2023-07-02
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
 - `Date Published` - ISO format. Recommended format: YYYY-MM-DD
 - `URL`

 ### Markup
 `.zine` files support rich markup for enhanced features. Markup resembles a limited set of HTML tags. Some tags can be nested in other tags.
  - `<h1>Header</h1>` - Header, printed in double sized text.
  - `<u>Underlined</u>` - Underline
  - `<u2>Underlined 2</u2>` - Underline style 2
  - `<b>Bolded</b>` - Bold. Does not have an effect with default configuration because the Zine Machine bolds all text for improved readability. Auto-bold can be disabled with a command line argument.
  - `<invert>Inverted</invert>` - Invert (black background, white text)
  - `<img src="image.png">Caption</img>` - Insert an image with optional caption. src path is relative to the `.zine` file.

### Indexing
When the Zine Machine runs, all files in `$PWD/zines/` with the `.zine` or `.txt` extension are indexed. Directories and files that begin with a `.` (period) are ignored.

The zine directory can be specified with a command line argument.

### Validation
Running the Zine Machine with the `--validate` flag will check all zines in its index for header errors, invalid markup, and unprintable characters and images.

The default validation settings for printable characters and max image width are based on manually determined values for the generic receipt printer we used (LMP201). If your printer supports more fonts or prints images at a different pixel width, you can configure these settings with the printer profile.

# Setup

## Flash Raspberry Pi OS

Use the Raspberry Pi imager to flash Raspberry Pi OS to the SD card.
After you select the OS image, click the gear in the bottom right to set some advanced options that will make it easier to work with the Pi.

Set hostname
zinemachine.local

Enable SSH
Use password authentication
Set username and password

Configure wireless LAN
Enter your WiFi SSID and password, and select your country code.

Set locale settings
Set to your keyboard layout, or certain keypresses may be interpreted differently than you expect.

## Start up Raspberry Pi
Insert the SD card into the Raspberry Pi and apply power. It will take awhile to boot up, so wait 2-5 minutes. Since you configured the WiFi network and SSH during the flashing step, you should be able to see the raspberry pi show up in your router's device table.

Open a terminal and connect to the Raspberry Pi with the following command, replacing `IP_ADDR` with the address of your Pi:
```
ssh pi@IP_ADDR
```

## Update Package Repos
```
sudo apt-get update
sudo apt-get upgrade
```

## Bind Bluetooth on Boot
1. Before we can connect to the printer, we need to bind RFCOMM to the printer's bluetooth device. then we can use the device `/dev/rfcomm0` to establish a connection.

Modify `etc/systemd/system/receipt-bluetooth.service` in this repo so the MAC address matches the MAC address of your receipt printer (replace 02:3B:A9:4C:F0:AE with the MAC address listed by the printer, usually found by printing a test sheet)

```
nano etc/systemd/system/receipt-bluetooth.service
```

2. Copy the bluetooth service file onto the system

```
sudo cp etc/systemd/system/receipt-bluetooth.service /etc/systemd/system/receipt-bluetooth.service
```

3. enable the service on boot. `--now` starts it immediately

```
sudo systemctl enable --now receipt-bluetooth.service
```

This service does NOT connect to the printer, it only configures the bluetooth connection. The actual connection is made when the device is used in `zine-machine.py`

## Python Setup

Install the `[python-escpos](https://github.com/python-escpos/python-escpos) module
```
pip install --user python-escpos==3.0a8
```

The project also makes use of [RPi.GPIO](https://pypi.org/project/RPi.GPIO/), which should already be installed if you are running the zine machine on a Raspberry Pi.

## Start on boot
1. Copy the zine machine service file onto the system
```
sudo cp etc/systemd/system/zine-machine.service /etc/systemd/system/zine-machine.service
```

2. Enable to start on boot. `--now` starts it immediately
```
sudo systemctl enable --now zine-machine.service
```

You can check the status of the zine machine service with
```
sudo systemctl status zine-machine
```

and view operational logs with 
```
sudo journalctl -u zine-machine
```

# Module Usage
The Zine Machine can also be used as a python module, with `import zinemachine`.

## Input Manager
The input manager allows you to bind a function to a combination of pressed or held buttons.

Use `addButton` to register a new button that can be used in button combinations.

Use `addChord` to create an input binding that will execute a function when the appropriate buttons are pressed.

When `holdTime` is 0 (default) it creates a "pressRelease" command, which fires when all buttons in the chord are pressed, then released.

When `holdTime` is greater than 0, a "pressHold" command is created, which fires when the buttons in the chord are pressed and held for the given time, in seconds. Whenever a button is pressed or released, the hold timer is reset back to zero, so the command is only triggered after the exact chord has been held for `holdTime`.

InputManager is also initialized with a `waitTime` (default 0.25 seconds), which adds a grace period where a button is still considered held down after it is released. This wait time is ONLY considered for "pressRelease" commands, so that even if you do not release all the buttons of a chord at the exact same time, it is still considered a press-release of the entire chord, instead of just the last button released. The wait timer resets whenever any button is released--even if each button in the chord is released one at a time, they are all considered part of the "pressRelease" chord as long as the time between each release is less than `waitTime`.

# Development
## Setup
1. clone this repo
```
git clone https://github.com/elliothatch/zine-machine.git

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
python -m zinemachine
```

## test
```
python -m unittest
```
