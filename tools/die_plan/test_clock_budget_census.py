import unittest
from types import SimpleNamespace
from unittest.mock import patch
import clock_budget_census

class CensusTest(unittest.TestCase):
    def test_all_active_budgets_survive_earlier_failure(self):
        P=SimpleNamespace(types={n:{"clock":{"tap_mode":mode}} for n,mode in
          [("a","explicit"),("b","grid+explicit"),("c","explicit"),
           ("fixed","grid"),("unused","explicit")]})
        seen=[]
        def check(P,n):
            seen.append(n)
            if n in ("a","c"): raise ValueError(n+": radius exceeds native limit")
        with patch("taps.explicit_taps",check), patch("taps.grid_explicit_taps",check):
            out=clock_budget_census.census(P,["c","b","a","fixed","a"])
        self.assertEqual(seen,["a","b","c"])
        self.assertEqual(out["checked"],seen)
        self.assertEqual([f["type"] for f in out["failures"]],["a","c"])
        self.assertEqual([f["mode"] for f in out["failures"]],["explicit","explicit"])

    def test_unexpected_runtime_error_is_not_hidden(self):
        P=SimpleNamespace(types={"x":{"clock":{"tap_mode":"explicit"}}})
        with patch("taps.explicit_taps",side_effect=RuntimeError("broken native context")):
            with self.assertRaisesRegex(RuntimeError,"broken native context"):
                clock_budget_census.census(P,["x"])

if __name__=='__main__':unittest.main()
