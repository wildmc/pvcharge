import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from controller import PVController


def controller_config():
    return {
        "control": {
            "poll_interval": 20,
            "wallbox_update_interval": 240,
            "averaging_window": 12,
            "voltage": 230.0,
            "min_current": 6,
            "max_current": 16,
            "surplus_start_threshold": 1500,
            "surplus_stop_threshold": 1200,
        }
    }


class PVControllerTest(unittest.TestCase):

    def test_average_returns_zero_for_empty_buffer(self):
        controller = PVController(None, None, controller_config())

        self.assertEqual(controller._avg(), 0.0)

    def test_average_uses_buffer_values(self):
        controller = PVController(None, None, controller_config())
        controller.buffer = [1000, 2000, 3000]

        self.assertEqual(controller._avg(), 2000.0)

    def test_calc_amps_converts_surplus_to_current(self):
        controller = PVController(None, None, controller_config())

        self.assertEqual(controller._calc_amps(1500), 6)
        self.assertEqual(controller._calc_amps(2300), 10)

    def test_calc_amps_clamps_to_zero_and_max_current(self):
        controller = PVController(None, None, controller_config())

        self.assertEqual(controller._calc_amps(-500), 0)
        self.assertEqual(controller._calc_amps(5000), 16)

    def test_charge_and_stop_thresholds_are_inclusive(self):
        controller = PVController(None, None, controller_config())

        self.assertFalse(controller._should_charge(1499))
        self.assertTrue(controller._should_charge(1500))
        self.assertTrue(controller._should_stop(1200))
        self.assertFalse(controller._should_stop(1201))


if __name__ == "__main__":
    unittest.main()
