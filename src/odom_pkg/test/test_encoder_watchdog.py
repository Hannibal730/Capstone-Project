import pytest

from odom_pkg.encoder_watchdog import EncoderWatchdog


def test_waiting_for_first_sample_is_not_a_timeout_transition():
    watchdog = EncoderWatchdog(0.1)

    assert watchdog.check(10.0) == (False, False, None)


def test_sample_becomes_stale_and_timeout_is_reported_once():
    watchdog = EncoderWatchdog(0.1)
    assert watchdog.record_sample(1.0) is False

    fresh, just_timed_out, elapsed = watchdog.check(1.099)
    assert fresh is True
    assert just_timed_out is False
    assert elapsed == pytest.approx(0.099)

    fresh, just_timed_out, elapsed = watchdog.check(1.101)
    assert fresh is False
    assert just_timed_out is True
    assert elapsed == pytest.approx(0.101)

    fresh, just_timed_out, _ = watchdog.check(1.2)
    assert fresh is False
    assert just_timed_out is False


def test_new_sample_recovers_watchdog():
    watchdog = EncoderWatchdog(0.1)
    watchdog.record_sample(1.0)
    watchdog.check(1.2)

    assert watchdog.record_sample(1.21) is True
    assert watchdog.check(1.25)[0] is True


def test_timeout_must_be_positive():
    with pytest.raises(ValueError):
        EncoderWatchdog(0.0)
