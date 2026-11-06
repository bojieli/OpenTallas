"""Physical connectivity controls for existing clock-metal publication."""
import unittest
from clock_pin_publish import candidates


class ClockPinPublishTest(unittest.TestCase):
    def test_native_via_is_required_and_publication_stays_on_real_metal(self):
        # Existing M5 clock pad -> native VIA56 -> real M6 segment -> via -> load.
        nodes = [("M5", (0, 0, 4, 8)), ("M6", (0, 2, 4, 6)),
                 ("M6", (0, 2, 20, 6)), ("M6", (16, 2, 20, 6)),
                 ("M5", (16, 2, 20, 6))]
        original = [("M5", (0, 0, 4, 8))]
        loads = [[("M5", (16, 2, 20, 6))]]
        result = candidates(nodes, [(0, 1), (3, 4)], [2], original, loads, "M6", 4)
        self.assertEqual(result, [(0, 2, 4, 6)])
        with self.assertRaisesRegex(ValueError, "not physically connected"):
            candidates(nodes, [(3, 4)], [2], original, loads, "M6", 4)
        with self.assertRaisesRegex(ValueError, "not physically connected"):
            candidates(nodes, [(0, 1)], [2], original, loads, "M6", 4)
        with self.assertRaisesRegex(ValueError, "no connected target-layer"):
            candidates(nodes, [(0, 1), (3, 4)], [2], original, loads, "M7", 4)
        with self.assertRaisesRegex(ValueError, "legal width"):
            candidates(nodes, [(0, 1), (3, 4)], [2], original, loads, "M6", 5)
        with self.assertRaisesRegex(ValueError, "not physically connected"):
            candidates(nodes, [(0, 1), (3, 4)], [2], original,
                       loads + [[("M5", (30, 30, 34, 34))]], "M6", 4)


if __name__ == "__main__":
    unittest.main()
