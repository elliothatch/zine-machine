from threading import Timer
import time
import RPi.GPIO as GPIO

class Button(object):
    def __init__(self, pin, onPressed=None, onReleased=None, name=None, debounceTime=10/1000):
        self.pin = pin
        self.onPressed = onPressed
        self.onReleased = onReleased
        self.name = name
        self.debounceTime = debounceTime

        self.timer = Timer(debounceTime, self.makeButtonHandler())
        self.pressed = False

        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(pin, GPIO.BOTH, callback=self.fallingInterrupt)

    """
    Interrupt handler
    """
    def fallingInterrupt(self, pin):
        if self.timer.is_alive():
            return

        self.timer.start()

    def makeButtonHandler(self):
        def handler():
            self.timer = Timer(self.debounceTime, self.makeButtonHandler())
            lastPressed = self.pressed
            self.pressed = GPIO.input(self.pin) == GPIO.LOW
            # only call function if the state actually changed
            # this prevents erroneous double presses due to crosstalk
            if lastPressed != self.pressed:
                if self.pressed and self.onPressed:
                    self.onPressed(self)
                elif not self.pressed and self.onReleased:
                    self.onReleased(self)

        return handler
