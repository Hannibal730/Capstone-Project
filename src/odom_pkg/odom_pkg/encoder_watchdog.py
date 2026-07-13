import threading


class EncoderWatchdog:
    """Determine whether encoder speed samples are still fresh."""

    def __init__(self, timeout_sec):
        if timeout_sec <= 0.0:
            raise ValueError('timeout_sec must be greater than 0.0')

        self.timeout_sec = float(timeout_sec)
        self._last_sample_time = None
        self._timeout_active = False
        self._lock = threading.Lock()

    def record_sample(self, sample_time):
        """Record a sample and return True when recovering from timeout."""
        with self._lock:
            recovered = self._timeout_active
            self._last_sample_time = float(sample_time)
            self._timeout_active = False
            return recovered

    def check(self, now):
        """Return (fresh, just_timed_out, elapsed_sec)."""
        with self._lock:
            if self._last_sample_time is None:
                return False, False, None

            elapsed_sec = max(0.0, float(now) - self._last_sample_time)
            if elapsed_sec <= self.timeout_sec:
                return True, False, elapsed_sec

            just_timed_out = not self._timeout_active
            self._timeout_active = True
            return False, just_timed_out, elapsed_sec
