"""FABLE-FLOW-0445 #7: the autopilot timer starts the next tick 2 minutes after the previous one ends (no fixed 10-minute calendar)."""
import configparser
import pathlib
import unittest

D = pathlib.Path(__file__).with_name("systemd")


def timer():
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read(D / "autopilot.timer")
    return cp["Timer"]


class AutopilotTimer(unittest.TestCase):
    def test_next_tick_two_minutes_after_the_unit_went_inactive(self):
        t = timer()
        self.assertEqual(t["OnUnitInactiveSec"], "120")
        self.assertIn("OnActiveSec", t)                 # the first tick: OnUnitInactiveSec needs a run to count from

    def test_no_calendar_schedule_or_catch_up(self):
        t = timer()
        self.assertNotIn("OnCalendar", t)               # a calendar would fire during a running tick and stack ticks
        self.assertNotIn("Persistent", t)

    def test_service_is_a_oneshot_so_inactive_means_the_tick_ended(self):
        s = (D / "autopilot.service").read_text()
        self.assertIn("Type=oneshot", s)

    def test_tick_keeps_its_single_instance_lock(self):
        src = (pathlib.Path(__file__).with_name("autopilot.py")).read_text()
        self.assertIn(".tick.lock", src)
        self.assertIn("LOCK_EX | fcntl.LOCK_NB", src)


if __name__ == "__main__":
    unittest.main()
