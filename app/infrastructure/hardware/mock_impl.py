from app.infrastructure.hardware.interfaces import LedIndicator, Buzzer, DoorRelay, RFIDReader

class MockLedIndicator(LedIndicator):
    def __init__(self, color: str):
        self.color = color
        self.is_on = False

    def on(self):
        self.is_on = True

    def off(self):
        self.is_on = False

class MockBuzzer(Buzzer):
    def __init__(self):
        self.beep_count = 0

    def beep(self, times: int = 1, duration: float = 0.2):
        self.beep_count += times

class MockDoorRelay(DoorRelay):
    def __init__(self):
        self.is_triggered = False
        self.triggered_seconds = 0.0

    def trigger(self, seconds: float = 5.0):
        self.is_triggered = True
        self.triggered_seconds = seconds

class MockRFIDReader(RFIDReader):
    def __init__(self):
        self.next_read = None

    def read_card(self) -> str | None:
        val = self.next_read
        self.next_read = None
        return val
