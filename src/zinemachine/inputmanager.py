from typing import Dict, List, Set, FrozenSet, Callable, Tuple
from threading import Timer, Lock
import RPi.GPIO as GPIO
from .button import Button


class InputManager(object):
    """
    Maps complex inputs to simple buttons to support chords and held button commands.
    Possible commands:
        1. pressRelease - a button or chord is pressed and then released
        2. pressHold - a button or chord is pressed and held for the specified time

    Creating a chord with 0 holdTime makes it a pressRelease command.

    pressRelease commands execute when all buttons have been released. only buttons that remained pressed within waitTime seconds of total release are considered "pressed" for the chord.

    pressHold commands execute when all buttons for the command have been held for the specified holdTime. The hold timer is reset whenever a button is pressed or released.
    Multiple commands can be bound to the same chord with different nonzero holdTimes. In this case, each command will be executed when its holdTime expires, unless any keys are pressed or released.

    if any number of pressHold commands were executed, pressRelease commands will be blocked until all buttons are released
    """
    buttons: Dict[int, Button]
    pressed: Set[int]
    """currently pressed buttons
    """
    currentChord: Set[int]
    """currently pressed buttons, and buttons that were released within the waitTime
    """
    commands: Dict[FrozenSet, Dict[float, Callable]]

    def __init__(self, waitTime=0.25):
        self.buttons = dict()
        self.pressed = set()
        self.currentChord = set()
        self.commands = dict()

        self.waitTime = waitTime
        self.waitTimers = []
        self.holdTimers = []
        self.blockPressRelease = False

        self.inputLock = Lock()

    def addButton(self, pin, name):
        self.buttons[pin] = Button(
            pin,
            name=name,
            onPressed=self.onPressed,
            onReleased=self.onReleased
        )

        print(f"Regsiter pin {pin} to button '{name}'")

    def addChord(self, pins: FrozenSet[int], callback: Callable, holdTime:float=0.0):
        # holdTime is rounded to 6 digits to ensure reliable hashing
        holdTime = round(holdTime, 6)
        if pins not in self.commands:
            self.commands[pins] = dict()

        if holdTime in self.commands[pins]:
            print(f"Warning: chord already exists: {pins} ({holdTime}). Overwriting previous command...")
        self.commands[pins][holdTime] = callback

        print(f"Register command: {pins} ({holdTime})")

    def onPressed(self, button):
        with self.inputLock:
            self.resetHoldTimers()
            self.pressed.add(button.pin)
            self.currentChord.add(button.pin)

            self.startHoldTimers()

    def onReleased(self, button):
        try:
            # manually handle lock so we can unlock before we execute the requested command, which may take awhile
            # we don't need to do this for pressHold commands becauase they are automatically put on their own thread via the hold Timer
            self.inputLock.acquire()
            self.resetHoldTimers()
            self.pressed.remove(button.pin)

            # check for pressRelease commands
            if len(self.pressed) == 0:
                if self.blockPressRelease:
                    self.blockPressRelease = False
                    self.inputLock.release()
                    return

                frozenChord = frozenset(self.currentChord)
                if frozenChord in self.commands:
                    chordCommands = self.commands[frozenChord]
                    if 0.0 in chordCommands:
                        # pressRelease
                        self.resetInput()
                        # release lock before executing the command
                        self.inputLock.release()
                        chordCommands[0.0](frozenChord, 0.0)
                        return

            else:
                self.startHoldTimers()

            # remove the button from the current chord when the holdTime expires
            def onWait():
                with self.inputLock:
                    if button.pin in self.currentChord:
                        self.currentChord.remove(button.pin)

            timer = Timer(self.waitTime, onWait)
            self.waitTimers.append(timer)
            timer.start()
            self.inputLock.release()

        except Exception as e:
            self.inputLock.release()
            raise e


    def startHoldTimers(self):
        """hold timers are always based on pressed, not currentChord
        """
        frozenChord = frozenset(self.pressed)
        if frozenChord in self.commands:
            chordCommands = self.commands[frozenChord]
            for holdTime, command in chordCommands.items():
                if holdTime == 0.0:
                    continue

                def onHold(pins, hold):
                    with self.inputLock:
                        command(pins, hold)
                        self.blockPressRelease = True

                timer = Timer(holdTime, onHold, args=[frozenChord, holdTime])
                self.holdTimers.append(timer)
                timer.start()


    def resetHoldTimers(self):
        for timer in self.holdTimers:
            timer.cancel()
        self.holdTimers.clear()

    def resetInput(self):
        self.currentChord.clear()
        for timer in self.waitTimers:
            timer.cancel()

        self.waitTimers.clear()

