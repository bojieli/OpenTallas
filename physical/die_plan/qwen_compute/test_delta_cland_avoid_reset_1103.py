"""DIE-QC-66/CLK CLAND class fix: slw_sc_v1 bands re-sited off reset relays; all other types byte-identical."""
import json, os, sys, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import delta_cland_avoid_reset_1103 as D  # noqa: E402

ROOT = os.path.join(HERE, "..", "..", "..")
PLAN = os.path.join(HERE, "plan_of_record", "plan_qc52.json")
SIDE = os.path.join(ROOT, "results", "qc_die63_red_1102", "bind", "sidecar.json")


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.load(open(PLAN))
        cls.side = json.load(open(SIDE))

    def test_plan_of_record_clean(self):
        # the plan of record carries the delta: opt-in present, no slw_sc_v1 band over a reset site
        self.assertTrue(set(D.base_types(self.plan, D.TYPES)) <= set(self.plan["budgets"]["cland_avoid_reset_types"]))
        self.assertEqual(D.relay_hits(self.plan, D.TYPES), [])

    def test_idempotent(self):
        new, rep = D.apply(self.plan, self.side)
        self.assertEqual(rep, [])
        self.assertEqual(new, self.plan)

    def test_fixes_relay_band(self):
        # undo: put x_fw_fe_p1_i back over u_rrl_15 (the as-failed band) -> the delta moves it off again
        p = json.loads(json.dumps(self.plan))
        p["budgets"]["cland_avoid_reset_types"] = []
        for tn in D.TYPES:
            p["partition_types"][tn]["clock"]["landing_contract"]["bands"]["x_fw_fe_p1_i"]["rect_um"] = [17.28, 629.16, 62.64, 730.84]
        self.assertTrue(D.relay_hits(p, D.TYPES))
        new, rep = D.apply(p, self.side)
        self.assertEqual(D.relay_hits(new, D.TYPES), [])
        self.assertTrue(all(r["hop_um"] <= 405 for r in rep))
        for tn in p["partition_types"]:
            if tn not in D.TYPES:
                self.assertEqual(new["partition_types"][tn], p["partition_types"][tn])


if __name__ == "__main__":
    unittest.main()
