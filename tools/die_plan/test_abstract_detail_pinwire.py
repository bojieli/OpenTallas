"""abstract_detail pinwire: a pin's own same-layer OBS wire becomes pin shape (S81-COLABS-1115, Lef58EolKeepOut)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abstract_detail as A

LEF = """VERSION 5.8 ;
MACRO core
  CLASS BLOCK ;
  SIZE 100 BY 50 ;
  PIN p
    DIRECTION OUTPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  10 0 10.024 0.084 ;
    END
  END p
  PIN q
    DIRECTION INPUT ;
    USE SIGNAL ;
    PORT
      LAYER M5 ;
        RECT  20 0 20.024 0.084 ;
    END
  END q
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
    PORT
      LAYER M5 ;
        RECT  30 0 30.024 0.084 ;
    END
  END VDD
  OBS
    LAYER M4 ;
     RECT  0 0 100 50 ;
    LAYER M5 ;
     RECT  10 0.084 10.024 1 ;
     RECT  10 1 10.024 2 ;
     RECT  10.024 1.5 12 1.548 ;
     RECT  20 0.2 20.024 3 ;
     RECT  30 0.084 30.024 2 ;
     RECT  40 5 40.024 6 ;
  END
END core
"""


class PinWire(unittest.TestCase):
    def run_merge(self):
        lines = LEF.splitlines(keepends=True)
        return lines, *A.merge_pin_wires(lines)

    def test_chain_merged_and_obs_removed(self):
        _, new, rep = self.run_merge()
        txt = "".join(new)
        self.assertEqual(rep["merged_rects"], 3)
        self.assertEqual(rep["pins"], 1)
        pin = txt.split("PIN p")[1].split("END p")[0]
        for r in ("10 0.084 10.024 1", "10 1 10.024 2", "10.024 1.5 12 1.548"):
            self.assertIn("RECT  " + r, pin)
        obs = txt.split("  OBS")[1]
        self.assertNotIn("10 0.084", obs)
        self.assertNotIn("10.024 1.5", obs)

    def test_gap_pg_blanket_and_foreign_untouched(self):
        _, new, _ = self.run_merge()
        obs = "".join(new).split("  OBS")[1]
        self.assertIn("RECT  20 0.2 20.024 3", obs)      # gap above pin q: not its wire
        self.assertIn("RECT  30 0.084 30.024 2", obs)    # PG pin: never merged
        self.assertIn("RECT  40 5 40.024 6", obs)        # foreign
        self.assertIn("RECT  0 0 100 50", obs)           # blanket

    def test_only_obs_and_pins_change_and_idempotent(self):
        lines, new, _ = self.run_merge()
        ok, probs = A.check(lines, new, ["M5"])
        self.assertEqual(probs, ["header/PIN sections differ"])  # pins grow by design; PG + SIZE unchanged
        again, rep2 = A.merge_pin_wires(new)
        self.assertEqual(again, new)
        self.assertEqual(rep2["merged_rects"], 0)

    def test_layers_filter(self):
        _, new, rep = (lambda L: (L, *A.merge_pin_wires(L, {"M6"})))(LEF.splitlines(keepends=True))
        self.assertEqual(rep["merged_rects"], 0)


if __name__ == "__main__":
    unittest.main()
