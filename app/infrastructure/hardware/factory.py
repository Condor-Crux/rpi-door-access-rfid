from app.core.config import settings
from app.infrastructure.hardware.interfaces import LedIndicator, Buzzer, DoorRelay, RFIDReader
from app.infrastructure.hardware.platform import is_raspberry_pi, platform_name


class HardwareFactory:
    """Strategy that picks real GPIO or mock drivers based on platform."""

    def green_led(self) -> LedIndicator: ...
    def red_led(self) -> LedIndicator: ...
    def buzzer(self) -> Buzzer: ...
    def door_relay(self) -> DoorRelay: ...
    def rfid_reader(self) -> RFIDReader: ...


class GpioHardwareFactory(HardwareFactory):
    def green_led(self) -> LedIndicator:
        from app.infrastructure.hardware.gpio_impl import GpioLedIndicator
        return GpioLedIndicator(settings.LED_GREEN_PIN)

    def red_led(self) -> LedIndicator:
        from app.infrastructure.hardware.gpio_impl import GpioLedIndicator
        return GpioLedIndicator(settings.LED_RED_PIN)

    def buzzer(self) -> Buzzer:
        from app.infrastructure.hardware.gpio_impl import GpioBuzzerImpl
        return GpioBuzzerImpl(settings.BUZZER_PIN)

    def door_relay(self) -> DoorRelay:
        from app.infrastructure.hardware.gpio_impl import GpioDoorRelay
        return GpioDoorRelay(settings.RELAY_PIN)

    def rfid_reader(self) -> RFIDReader:
        from app.infrastructure.hardware.gpio_impl import Mfrc522RFIDReader
        return Mfrc522RFIDReader()


class MockHardwareFactory(HardwareFactory):
    def green_led(self) -> LedIndicator:
        from app.infrastructure.hardware.mock_impl import MockLedIndicator
        return MockLedIndicator("green")

    def red_led(self) -> LedIndicator:
        from app.infrastructure.hardware.mock_impl import MockLedIndicator
        return MockLedIndicator("red")

    def buzzer(self) -> Buzzer:
        from app.infrastructure.hardware.mock_impl import MockBuzzer
        return MockBuzzer()

    def door_relay(self) -> DoorRelay:
        from app.infrastructure.hardware.mock_impl import MockDoorRelay
        return MockDoorRelay()

    def rfid_reader(self) -> RFIDReader:
        from app.infrastructure.hardware.mock_impl import MockRFIDReader
        return MockRFIDReader()


def build_factory() -> tuple[HardwareFactory, str]:
    name = platform_name()
    if is_raspberry_pi():
        return GpioHardwareFactory(), name
    return MockHardwareFactory(), name
