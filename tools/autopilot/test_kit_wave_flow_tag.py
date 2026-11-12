"""Flow-tag metadata must not release a failed design for unchanged P&R."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

import kit_wave as KW
from test_kit_wave import cfg


class FlowTagIdentity(unittest.TestCase):
    def test_tag_add_change_remove_compare_equal_without_mutation(self):
        sp = {"src_sha": "same", "gen_env": {"OT_MAXWIRE_UM": "100"}}
        expected = KW.input_hash(sp)
        for tag in ("flow-20261107-cu-kv", "flow-20261107-cv-kv"):
            tagged = copy.deepcopy(sp)
            tagged["gen_env"]["OT_FLOW_TAG"] = tag
            saved = copy.deepcopy(tagged)
            self.assertEqual(expected, KW.input_hash(tagged))
            self.assertEqual(tagged, saved)
        self.assertEqual(KW.input_hash({"src_sha": "same"}),
            KW.input_hash({"src_sha": "same", "gen_env": {"OT_FLOW_TAG": "new"}}))

    def test_design_changes_still_differ(self):
        base = {"src_sha": "same", "gen_env": {"OT_FLOW_TAG": "old", "OT_MAXWIRE_UM": "100"}}
        changed = copy.deepcopy(base)
        changed["gen_env"]["OT_MAXWIRE_UM"] = "80"
        self.assertNotEqual(KW.input_hash(base), KW.input_hash(changed))
        self.assertNotEqual(KW.input_hash(base), KW.input_hash(dict(base, src_sha="new")))

    def test_actual_failed_row_remains_held_for_tag_only_change_on_either_side(self):
        # KW-FIX-45/46 11-12: an UNREADABLE source overlay hash now counts as changed (released), so the test pins a readable one
        with tempfile.TemporaryDirectory() as td:
            for old_tag in (None, "flow-20261107-cu-kv"):
                c = cfg()
                c["dies"]["qwen_kvsys"]["_src_overlay"] = "0" * 64     # a readable source overlay (both sides)
                old = KW.spec_for(c, "qwen_kvsys", "kv3_pc", "intel2")
                if old_tag:
                    old["gen_env"]["OT_FLOW_TAG"] = old_tag
                (Path(td)/"spec.json").write_text(json.dumps(old))
                rec = dict(die="qwen_kvsys", item="kv3_pc", status="FAIL", attempt=1,
                           dir=td, **{"class": "FLOW"})
                for new_tag in (None, "flow-20261107-cv-kv"):
                    c["dies"]["qwen_kvsys"]["flow_tag"] = new_tag
                    self.assertTrue(KW.unchanged_fail(c, {}, "qwen_kvsys", "kv3_pc", rec))
                    spec = KW.spec_for(c, "qwen_kvsys", "kv3_pc", "intel2")
                    self.assertEqual(spec["gen_env"].get("OT_FLOW_TAG"), new_tag)


if __name__ == "__main__":
    unittest.main()
