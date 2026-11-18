import json, os, tempfile, unittest
from pathlib import Path
import apply_reviewed_tree_marker as A
from test_apply_reviewed_tree_marker import TC, mk, cand, apply


class Rollback(unittest.TestCase):
    def test_keep_current_plus_one_rollback_the_older_one_becomes_superseded(self):
        c = mk()
        apply(c, cand(), "/x/old", "E0", pilot_item="t1", TC=TC)                       # old -> new
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["rollback_tree"], "/x/old"); self.assertEqual(d.get("superseded_trees", []), [])
        c2 = dict(cand(), tree="/x/new2", manifest_hash="b" * 64, plan="/p2", plan_sha256="s2")
        d["event"] = "E1"; (c / "autopilot/kit_wave.json").write_text(json.dumps({"dies": {"kv": d}}))
        apply(c, c2, "/x/new", "E1", pilot_item="t1", TC=TC)                           # new -> new2
        d = json.loads((c / "autopilot/kit_wave.json").read_text())["dies"]["kv"]
        self.assertEqual(d["src"], "/x/new2"); self.assertEqual(d["rollback_tree"], "/x/new")
        self.assertEqual(d["superseded_trees"], ["/x/old"])                                      # two versions back
