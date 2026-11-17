import json, unittest
import apply_reviewed_tree_marker as A
from test_apply_reviewed_tree_marker import TC, mk, cand


class DropGuard(unittest.TestCase):
    def mk_with_hosts(self, hosts):
        c = mk(); p = c / "autopilot/kit_wave.json"
        j = json.loads(p.read_text()); j["dies"]["kv"]["gen_hosts"] = hosts; p.write_text(json.dumps(j))
        return c

    def test_apply_that_would_drop_a_gen_host_is_refused_untouched(self):
        c = self.mk_with_hosts(["epyc10", "intel1"])                # candidate verified on epyc10 only
        with self.assertRaises(SystemExit) as e:
            A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)
        self.assertIn("intel1", str(e.exception))
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/old"); self.assertEqual(d["gen_hosts"], ["epyc10", "intel1"])

    def test_explicit_drop_is_allowed_and_recorded(self):
        c = self.mk_with_hosts(["epyc10", "intel1"])
        r = A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC, drop_gen_hosts=True)
        self.assertEqual(r["dropped_gen_hosts"], ["intel1"])

    def test_no_drop_means_no_refusal(self):
        c = self.mk_with_hosts(["epyc10"])
        self.assertEqual(A.apply_marker(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)["dropped_gen_hosts"], [])
