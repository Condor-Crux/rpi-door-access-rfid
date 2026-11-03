import datetime
from app.domain.workflows import process_swipe
from app.infrastructure.models import AccountModel
from app.infrastructure.hardware.mock_impl import MockLedIndicator, MockBuzzer, MockDoorRelay
from app.core.time import utcnow

def test_process_swipe_grant(db_session):
    # Setup account
    acc = AccountModel(
        account_id="1234",
        status="active",
        expiration_date=utcnow() + datetime.timedelta(days=10),
        credits=5
    )
    db_session.add(acc)
    db_session.commit()

    # Mocks
    green_led = MockLedIndicator("green")
    red_led = MockLedIndicator("red")
    buzzer = MockBuzzer()
    relay = MockDoorRelay()

    result = process_swipe("1234", db_session, green_led, red_led, buzzer, relay)

    assert result["status"] == "granted"
    assert buzzer.beep_count == 1
    assert relay.is_triggered is True
    assert relay.triggered_seconds == 5.0
    
    # Check if LED was toggled (since we do green_led.off() in a finally block, it ends up False in mock)
    # But we can assume it was called if relay passed and beeped once
    
    # Check DB changes
    db_session.refresh(acc)
    assert acc.credits == 4

def test_process_swipe_deny_no_credits(db_session):
    acc = AccountModel(
        account_id="5678",
        status="active",
        expiration_date=utcnow() + datetime.timedelta(days=10),
        credits=0
    )
    db_session.add(acc)
    db_session.commit()

    green_led = MockLedIndicator("green")
    red_led = MockLedIndicator("red")
    buzzer = MockBuzzer()
    relay = MockDoorRelay()

    result = process_swipe("5678", db_session, green_led, red_led, buzzer, relay)

    assert result["status"] == "denied"
    assert result["reason"] == "Out of Credits"
    assert buzzer.beep_count == 3
    assert relay.is_triggered is False

def test_process_swipe_invalid_status(db_session):
    acc = AccountModel(
        account_id="9999",
        status="inactive",
        expiration_date=utcnow() + datetime.timedelta(days=10),
        credits=5
    )
    db_session.add(acc)
    db_session.commit()

    green_led = MockLedIndicator("green")
    red_led = MockLedIndicator("red")
    buzzer = MockBuzzer()
    relay = MockDoorRelay()

    result = process_swipe("9999", db_session, green_led, red_led, buzzer, relay)

    assert result["status"] == "denied"
    assert result["reason"] == "Invalid Status"
    assert buzzer.beep_count == 1 # default error beep
    assert relay.is_triggered is False
