import unittest
import kit_wave as KW

BASE = {"plan": "/p/plan.json", "src_sha": "abc", "src_overlay": "ov1", "gen_env": {"A": "1"}, "src": "/x/D3", "src_manifest_hash": "m3"}


class Manifest(unittest.TestCase):
    def test_new_manifest_same_everything_else_is_eligible(self):
        old = dict(BASE); cand = dict(BASE, src="/x/D5", src_manifest_hash="m5")
        self.assertFalse(KW.same_inputs(old, cand))                     # changed -> relaunch allowed

    def test_same_manifest_is_refused(self):
        old = dict(BASE); cand = dict(BASE, src="/x/D3copy")           # path differs, content manifest identical
        self.assertTrue(KW.same_inputs(old, cand))

    def test_a_spec_without_the_manifest_is_never_held_on_it(self):
        old = {k: v for k, v in BASE.items() if k != "src_manifest_hash"}
        self.assertTrue(KW.same_inputs(old, dict(BASE, src_manifest_hash="m5")))   # one side unmeasured: old rule only
        self.assertTrue(KW.same_inputs(dict(BASE), {k: v for k, v in BASE.items() if k != "src_manifest_hash"}))

    def test_other_input_change_still_releases(self):
        self.assertFalse(KW.same_inputs(dict(BASE), dict(BASE, gen_env={"A": "2"})))
