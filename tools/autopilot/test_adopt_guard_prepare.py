import json, os, tempfile, unittest
import adopt_guard as G
import wave_prepare_refresh as W


def prep(edit):
    d = tempfile.mkdtemp()
    open(os.path.join(d, "source_plan.json"), "w").write("{}")
    open(os.path.join(d, "source_sidecar.json"), "w").write("{}")
    json.dump({"prepared_plan_sha256": W.digest(os.path.join(d, "source_plan.json")),
               "sidecar_sha256": W.digest(os.path.join(d, "source_sidecar.json"))}, open(os.path.join(d, "wave_prepare.json"), "w"))
    if edit:
        open(os.path.join(d, "source_plan.json"), "w").write('{"edited": 1}')
    return d


class PrepareCheck(unittest.TestCase):
    def cfg(self, d):
        return {"dies": {"s81_head": {"plan": os.path.join(d, "source_plan.json")}}}

    def test_current_passes(self):
        self.assertTrue(G.prepare_check(self.cfg(prep(False)), "s81_head", ["localhost"], True, log=lambda m: None))

    def test_stale_fails_in_check_mode_and_is_republished_otherwise(self):
        d = prep(True); logs = []
        self.assertFalse(G.prepare_check(self.cfg(d), "s81_head", ["localhost"], True, log=logs.append))
        self.assertTrue(any("PREPARE STALE" in m for m in logs))
        self.assertTrue(G.prepare_check(self.cfg(d), "s81_head", ["localhost"], False, log=logs.append))
        self.assertTrue(W.status(d)[0])
        self.assertTrue(any("PREPARE REFRESH" in m for m in logs))

    def test_not_a_prepared_tree_passes(self):
        d = tempfile.mkdtemp(); open(os.path.join(d, "plan.json"), "w").write("{}")
        self.assertTrue(G.prepare_check({"dies": {"x": {"plan": os.path.join(d, "plan.json")}}}, "x", ["localhost"], True, log=lambda m: None))


if __name__ == "__main__":
    unittest.main()
