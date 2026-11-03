import time
from app.infrastructure.hardware.interfaces import LedIndicator, Buzzer, DoorRelay, RFIDReader


class GpioLedIndicator(LedIndicator):
    def __init__(self, pin: int):
        from gpiozero import LED
        self.led = LED(pin)

    def on(self):
        self.led.on()

    def off(self):
        self.led.off()


class GpioBuzzerImpl(Buzzer):
    def __init__(self, pin: int):
        from gpiozero import Buzzer as GpioBuzzer
        self.buzzer = GpioBuzzer(pin)

    def beep(self, times: int = 1, duration: float = 0.2):
        for _ in range(times):
            self.buzzer.on()
            time.sleep(duration)
            self.buzzer.off()
            time.sleep(duration)


class GpioDoorRelay(DoorRelay):
    def __init__(self, pin: int):
        from gpiozero import OutputDevice
        # Most 5V relay modules are active low.
        self.relay = OutputDevice(pin, active_high=False, initial_value=False)

    def trigger(self, seconds: float = 5.0):
        self.relay.on()
        time.sleep(seconds)
        self.relay.off()


class Mfrc522RFIDReader(RFIDReader):
    def __init__(self):
        from mfrc522 import SimpleMFRC522
        self.reader = SimpleMFRC522()

    def read_card(self) -> str | None:
        try:
            id, _ = self.reader.read_no_block()
            return str(id) if id is not None else None
        except Exception as e:
            print(f"[RFID] Error reading card: {e}")
            return None
