# The Zine Machine

The Zine Machine is a little box that spits short passages of text out of a receipt printer.

It uses a python running on a Raspberry Pi Zero W to receive input from GPIO buttons and drive the receipt printer over bluetooth. When printing a zine, it loads `.zine` files from the filesystem and sends the commands to the printer over a serial connection, using the module [python-escpos](https://github.com/python-escpos/python-escpos) 

## Setup
```
pip install zinemachine
```

See [Raspberry Pi Setup](#raspberry-pi-setup) for full instructions on how to set up and configure your Raspberry Pi for the Zine Machine.

## Usage
```
python -m zinemachine [command]
```

Valid commands:
 - `print FILE`: Print a single zine file
 - `serve -c CATEGORY PIN`: Run persistently, and print random zine in `CATEGORY` when button on GPIO pin `PIN` is pressed. Provide multiple `-c` flags to register additional buttons. Categories are directories containing `.zine` files under `$PWD/zines/` (e.g. `-c diy 18` binds all zines under `$PWD/zines/diy` to pin 18)
 - `validate [FILE]`: Run the `.zine` file validator on the `FILE` or directory. Defaults to `$PWD/zines/`

 Use `-h` to list help and additional commands.
 ```
 python -m zinemachine -h
 python -m zinemachine print -h
 python -m zinemachine serve -h
 python -m zinemachine validate -h
 ```

### Adding zines
Create a `zines/` directory and add a subdirectory for each category of zine. Using the `serve` command, `.zine` and `.txt` files in a category are randomly printed when the button bound to that category is pressed.

Files and directories starting with a period `.` are ignored.

You can copy the [sample zines](https://github.com/elliothatch/zine-machine/tree/master/zines) directory from the Github repo as a starting point.

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
URL: https://github.com/elliothatch/zine-machine/blob/master/test-zines/.test/first-zine.zine
Date Published: 2023-08-19
-----
<h1>Hello</h1>
Welcome to my zine.
...
```

Header keys are case insensitive and must not contain a colon. All whitespace is stripped from keys. Leading and trailing whitespace is stripped from values.

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
  - `<img src="image.png">Caption</img>` - Insert an image with optional caption. src path is relative to the `.zine` file. You can group images with a zine by placing them all together in a directory.

### Validation
Running the Zine Machine with the `validate` command will check all zines in its index for header errors, invalid markup, and unprintable characters and images.

The default validation settings for printable characters and max image width are based on manually determined values for the generic receipt printer we used (LMP201). If your printer supports more fonts or prints images at a different pixel width, you can configure these settings with the printer profile (currently requires Python module usage).

You can provide the `--resize` flag with an optional maximum pixel width (`--resize 200`, default 576) to automatically downscale images that are too large for the printer. The original image will be saved with an `.orig` extension. If the Zine Machine will print an error if it tries to print an image that is too wide.

## Raspberry Pi Setup
### Wiring the buttons
You can run the Zine Machine to use any GPIO pins for the print category buttons. It configures the buttons in PULL_UP mode using the Pi's internal pull-up resistors.

The standard configuration is to use 4 buttons, wired to to the ground and GPIO pins opposite the micro USB power connector. This allows you to crimp all the wires into a standard 2x3 rectangular connector, sharing a common ground.

Pin numbers:
- Blue: 16
- Yellow: 20
- Green: 19
- Pink: 26

Connector diagram (g=ground, G=Green, .=unused, etc.):
```
| |g P G| . . .
| |. Y B| . . .
\------------ (edge of board)
```

### Flash Raspberry Pi OS

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

### Start up Raspberry Pi
Insert the SD card into the Raspberry Pi and apply power. It will take awhile to boot up, so wait 2-5 minutes. Since you configured the WiFi network and SSH during the flashing step, you should be able to see the raspberry pi show up in your router's device table.

Open a terminal and connect to the Raspberry Pi with the following command, replacing `IP_ADDR` with the address of your Pi:
```
ssh pi@IP_ADDR
```

Alternatively, plug a keyboard, mouse, and monitor into your Raspberry Pi and configure it directly from there.

### Update Package Repos
```
sudo apt-get update
sudo apt-get upgrade
```

### Bind Bluetooth on Boot
Before we can connect to the printer, we need to bind RFCOMM to the printer's bluetooth device. then we can use the device `/dev/rfcomm0` to establish a connection.

1. Open a text editor to create the systemd service file
```
sudo nano /etc/systemd/system/receipt-bluetooth.service
```

2. Copy and paste the [receipt-bluetooth.service](https://github.com/elliothatch/zine-machine/blob/master/etc/systemd/system/receipt-bluetooth.service) contents into the file. 

3. Modify the MAC address to match MAC address of your receipt printer (replace 02:3B:A9:4C:F0:AE with the MAC address listed by the printer, usually found by printing a test sheet)

4. Enable the service on boot. `--now` starts it immediately
```
sudo systemctl enable --now receipt-bluetooth.service
```

This service does NOT connect to the printer, it only configures the bluetooth connection. The actual connection is made when the device is used in `zine-machine.py`

### Python Setup
Upgrade the Python package manager, pip
```
pip install --upgrade pip
```

Install the zinemachine Python package.
```
pip install zinemachine
```

### Add zines and test
You will need to add some Zines to the Raspberry Pi before you can start printing them. As a starting point, download the [sample zines](https://github.com/elliothatch/zine-machine/tree/master/zines) from the Github repository.

If you are connected to the Pi via SSH, download these to your local computer, then copy them to the Pi by opening a new terminal and entering the command, replacing `IP_ADDR` with the IP address you used to SSH into the Pi:
```
rsync -avzh ./zines/ pi@IP_ADDR:/home/pi/zine-machine/zines/
```

The first argument of the command, `./zines/` should be the sample zine directory you downloaded eariler. The trailing `/` is important.

After the download is complete, you can test the Zine Machine. It looks for zines in the `zines/` directory under the current working directory, so first `cd` into the parent directory above `zines/`.

```
cd /home/pi/zine-machine
```

If you've wired the buttons according to the standard [Pin configuration](#wiring-the-buttons), you can run the Zine Machine with the following command:
```
python -m zinemachine serve -c theory pink -c ecology yellow -c diy green -c queer-stuff blue
```

After a few seconds, the receipt printer should output "Ready to print!", and you can push a button to print a random zine.

If you didn't use the standard wiring configuration, you can use pin numbers instead of color names. The following command is equivilent to the previous one:
```
python -m zinemachine serve -c theory 26 -c ecology 20 -c diy 19 -c queer-stuff 16
```

Press `CTRL-C` to stop the Zine Machine.

NOTE: The Zine machine also comes configured with two button combinations. Hold all 4 buttons for 5 seconds to shutdown the Pi, or hold just the pink, yellow, and green buttons for 5 seconds to stop the Zine Machine program without shutting down.

These commands are hardcoded via GPIO pin number, and will not work if you use custom GPIO pin.

### Enable start on boot
1. Open a text editor to create the systemd service file
```
sudo nano /etc/systemd/system/zine-machine.service
```

2. Copy and paste the [zine-machine.service](https://github.com/elliothatch/zine-machine/blob/master/etc/systemd/system/zine-machine.service) contents into the file. 

3. Modify the `ExecStart` line if you need to change the categories or buttons
4. Modify the `WorkingDirectory` line if you need to change where the zines will be loaded from. The path should be the directory containing the `zines/` folder.

5. Enable to start on boot.
```
sudo systemctl enable zine-machine.service
```

You can now start the Zine Machine as a background daemon with
```
sudo systemctl start zine-machine
```

Check the status of the zine machine service with
```
sudo systemctl status zine-machine
```

and view operational logs with 
```
sudo journalctl -u zine-machine
```

The Zine Machine will now automatically start when the Raspberry Pi turns on! Make sure the receipt printer is turned on BEFORE you power up the Raspberry Pi. If it loses connection with the printer at any point, you can reset the Zine Machine program by holding the PINK, YELLOW, and GREEN buttons for 5 seconds (assuming standard wiring). 

## Module Usage
The Zine Machine can also be used as a python module, with `import zinemachine` for further customization. Refer to [__main__.py](https://github.com/elliothatch/zine-machine/blob/master/src/zinemachine/__main__.py) for basic usage.

### Input Manager
The input manager allows you to bind a function to a combination of pressed or held buttons.

Use `addButton` to register a new button that can be used in button combinations.

Use `addChord` to create an input binding that will execute a function when the appropriate buttons are pressed.

When `holdTime` is 0 (default) it creates a "pressRelease" command, which fires when all buttons in the chord are pressed, then released.

When `holdTime` is greater than 0, a "pressHold" command is created, which fires when the buttons in the chord are pressed and held for the given time, in seconds. Whenever a button is pressed or released, the hold timer is reset back to zero, so the command is only triggered after the exact chord has been held for `holdTime`.

InputManager is also initialized with a `waitTime` (default 0.25 seconds), which adds a grace period where a button is still considered held down after it is released. This wait time is ONLY considered for "pressRelease" commands, so that even if you do not release all the buttons of a chord at the exact same time, it is still considered a press-release of the entire chord, instead of just the last button released. The wait timer resets whenever any button is released--even if each button in the chord is released one at a time, they are all considered part of the "pressRelease" chord as long as the time between each release is less than `waitTime`.

## Development
### Setup
1. clone this repo
```
git clone https://github.com/elliothatch/zine-machine.git

cd zine-machine
```

2. Upgrade pip
```
pip install --upgrade pip
```

3. Create virtual environment (optional)
```
python -m venv .
```
You must source the virtual environment before installing or running the project.

```
source bin/activate
```

4. install the package in editable mode (`--user` does nothing in venv)
```
python -m pip install -e . --user
```

<!--
5. install optional build dependencies
```
python -m pip install -e '.[build]' --user
```
-->

## run
```
python -m zinemachine
```

## test
```
python -m unittest
```
