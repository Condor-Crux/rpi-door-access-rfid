from abc import ABC, abstractmethod

class LedIndicator(ABC):
    @abstractmethod
    def on(self):
        pass

    @abstractmethod
    def off(self):
        pass

class Buzzer(ABC):
    @abstractmethod
    def beep(self, times: int = 1, duration: float = 0.2):
        pass

class DoorRelay(ABC):
    @abstractmethod
    def trigger(self, seconds: float = 5.0):
        pass

class RFIDReader(ABC):
    @abstractmethod
    def read_card(self) -> str | None:
        """Reads card and returns UID as string or None if no card"""
        pass
