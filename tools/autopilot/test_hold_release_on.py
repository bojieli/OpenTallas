import json, sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_wave as KW  # noqa: E402


def cfg(**k):
    d = {"event": "s29q103S4Q3C", "plan": "/x/zz_s29_qc103_s4q3c.json",
         "hold_items": {"a": "r", "b": "r", "c": "r", "d": "r", "e": "r", "f": "r"},
         "hold_release_on": {"a": "event_adopt:S4q3c", "b": "event_adopt:S4q3d", "c": "lane_ready:KV-101",
                             "d": "merge:claude/x + event_adopt:S4q3c", "e": "event_adopt:Event F", "zz": "event_adopt:S4q3c"}}
    d.update(k)
    return json.dumps({"dies": {"qwen_compute": d}})


class HoldReleaseOn(unittest.TestCase):
    def test_event_adopt_releases_only_matching_whole_token(self):
        c = KW.load_config(cfg())
        h = c["dies"]["qwen_compute"]["hold_items"]
        self.assertNotIn("a", h)            # plan name carries s4q3c as a token
        self.assertIn("b", h)               # s4q3d is not s4q3c
        self.assertIn("c", h)               # lane_ready is a human post
        self.assertIn("e", h)               # 'Event F' is too short to auto-check
        self.assertIn("f", h)               # no release_on entry stays held
        self.assertEqual([x[1] for x in c["_hold_auto_released"]][0], "a")

    def test_compound_needs_every_term(self):
        d = json.loads(cfg())["dies"]["qwen_compute"]
        c = {"dies": {"qwen_compute": d}}
        self.assertEqual([k for _, k, _ in KW.apply_hold_release_on(c, lambda r: False)], ["a"])
        self.assertIn("d", c["dies"]["qwen_compute"]["hold_items"])
        c = {"dies": {"qwen_compute": json.loads(cfg())["dies"]["qwen_compute"]}}
        got = [k for _, k, _ in KW.apply_hold_release_on(c, lambda r: r == "claude/x")]
        self.assertEqual(sorted(got), ["a", "d"])

    def test_token_boundary(self):
        c = KW.load_config(cfg(event="kvgeom7j", plan="/x/p.json", hold_items={"k": "r"}, hold_release_on={"k": "event_adopt:kvgeom7"}))
        self.assertIn("k", c["dies"]["qwen_compute"]["hold_items"])   # kvgeom7j is not kvgeom7

    def test_merge_error_is_not_released(self):
        def boom(r):
            raise RuntimeError("no git")
        c = {"dies": {"x": {"hold_items": {"k": "r"}, "hold_release_on": {"k": "merge:abc"}}}}
        self.assertEqual(KW.apply_hold_release_on(c, boom), [])
        self.assertIn("k", c["dies"]["x"]["hold_items"])

    def test_config_without_the_key_is_unchanged(self):
        c = KW.load_config(json.dumps({"dies": {"x": {"hold_items": {"k": "r"}}}}))
        self.assertEqual(c["dies"]["x"]["hold_items"], {"k": "r"})
        self.assertNotIn("_hold_auto_released", c)


if __name__ == "__main__":
    unittest.main()
