"""A geometry-complete kit can wait for a die-owned ROUTE release without rebuilding."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import kit_wave as KW


class RouteHold(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.jd = Path(self.tmp.name)
        self.spec = dict(src_sha="abc123", src="/frozen/source", plan="/frozen/plan.json",
                         queue_src="/frozen/queue-source")
        (self.jd / "spec.json").write_text(json.dumps(self.spec))
        self.result = dict(verdict="PASS", stage="geom", kit="intel2:/retained/kit", geom="PASS",
                           geom_line="AUTO-GEOM PASS", geom_dir="intel2:/retained/geom", cells=100)
        (self.jd / "result.json").write_text(json.dumps(self.result))
        self.rec = dict(die="qc", item="cbf_q01", event="event", attempt=10, status="RUNNING",
                        unit="unit", dir=str(self.jd))
        self.st = dict(items={"key": self.rec})
        self.cfg = dict(enabled=True, hosts=["intel2"], geom_sample=1, wait_visual=False,   # die-owned holds only; visual gate: own tests
                        dies=dict(qc=dict(src_sha="abc123")))
        self.calls, self.logs, self.notices = [], [], {}
        def sh(argv, **kw):
            self.calls.append((argv, kw))
            return 0, "submitted", ""
        self.ap = SimpleNamespace(DRY=False, AP_DIR=self.jd, HUB_NAME="hub", sh=sh,
                                  unit_active=lambda unit: False, log=self.logs.append, coord_append=lambda *a: None)

    def hold(self):
        self.cfg["dies"]["qc"]["route_hold_items"] = {"cbf_q0*": "native reset redesign"}

    def test_completed_geometry_hold_release_once_and_protect(self):
        self.hold()
        KW.collect(self.ap, self.cfg, self.st, self.notices)
        self.assertEqual(self.rec["status"], "ROUTE-HELD")
        self.assertFalse(self.calls)  # no enqueue or launch/cancel
        retained = {k: self.rec[k] for k in ("kit", "geom", "geom_dir", "attempt", "dir")}
        KW.retry_enqueue(self.ap, self.cfg, self.st, self.notices)
        self.assertFalse(self.calls)
        self.assertEqual(len(self.notices["qc"]), 1)  # unchanged hold is quiet
        KW.protect_sources(self.ap, self.cfg, self.st, self.jd)
        protected = self.calls[-1][1]["input"]
        for p in ("/frozen/source", "/frozen/plan.json", "/frozen/queue-source", "/retained/kit"):
            self.assertIn(p + "\n", protected)
        self.calls.clear()
        # A new tick reads a config with the hold removed. No run-item or geometry operation is needed.
        self.cfg["dies"]["qc"].pop("route_hold_items")
        KW.retry_enqueue(self.ap, self.cfg, self.st, self.notices)
        self.assertEqual(self.rec["status"], "ENQUEUED")
        self.assertEqual({k: self.rec[k] for k in retained}, retained)
        self.assertEqual(len(self.calls), 1)
        argv = self.calls[0][0]
        self.assertTrue(argv[1].endswith("enqueue.py"))
        self.assertIn("/frozen/queue-source", argv)
        self.assertEqual(self.st["pass_n"], 1)
        self.assertIn("/frozen/source", KW.source_paths(self.cfg, self.st, self.jd))
        self.assertIn("/retained/kit", KW.source_paths(self.cfg, self.st, self.jd))
        KW.retry_enqueue(self.ap, self.cfg, self.st, self.notices)
        self.hold()  # adding a hold to an admitted item cannot cancel or relabel it
        KW.enqueue_pass(self.ap, self.cfg, self.st, self.rec, self.notices)
        self.assertEqual(self.rec["status"], "ENQUEUED")
        self.assertEqual(len(self.calls), 1)

    def test_default_wrong_item_and_wrong_die_do_not_hold(self):
        for holds in ({}, {"other*": "different item"}):
            with self.subTest(holds=holds):
                self.rec["status"] = "PASS"
                self.rec.update(kit=self.result["kit"], geom_dir=self.result["geom_dir"])
                self.cfg["dies"]["qc"]["route_hold_items"] = holds
                self.cfg["dies"]["hbm"] = {"route_hold_items": {"cbf_q*": "different die"}}
                KW.enqueue_pass(self.ap, self.cfg, self.st, self.rec, self.notices)
                self.assertEqual(self.rec["status"], "ENQUEUED")
        self.assertEqual(len(self.calls), 2)

    def test_holds_are_runtime_controls_not_row_inputs(self):
        from test_kit_wave import cfg
        c = cfg()
        before = KW.spec_for(c, "qwen_kvsys", "kv3_pc", "intel2")
        c["dies"]["qwen_kvsys"].update(hold_items={"kv3_pc": "new picks"},
            route_hold_items={"kv3_pc": "route only"})
        after = KW.spec_for(c, "qwen_kvsys", "kv3_pc", "intel2")
        self.assertEqual(before, after)
        self.assertEqual(KW.input_hash(before), KW.input_hash(after))
        # Defensive skip if a future caller carries runtime controls in the spec.
        self.assertEqual(KW.input_hash(before), KW.input_hash(dict(before,
            hold_items={"kv3_pc": "held"}, route_hold_items={"kv3_pc": "held"})))

    def test_source_snapshot_retention_includes_held_pinned_spec(self):
        import source_follow
        self.hold()
        KW.collect(self.ap, self.cfg, self.st, self.notices)
        (self.jd / "kit_wave_state.json").write_text(json.dumps(self.st))
        refs = source_follow.live_snapshot_refs(self.jd, self.cfg, self.st)
        self.assertIn(json.dumps(self.spec), refs)

    def test_transport_pending_is_held_before_resubmission(self):
        self.rec.update(status="PASS", enqueue_pending=1, kit=self.result["kit"], geom_dir=self.result["geom_dir"])
        self.hold()
        KW.retry_enqueue(self.ap, self.cfg, self.st, self.notices)
        self.assertEqual(self.rec["status"], "ROUTE-HELD")
        self.assertEqual(self.rec["enqueue_pending"], 1)
        self.assertFalse(self.calls)

    def test_superseded_held_block_does_not_enqueue(self):
        self.hold()
        KW.collect(self.ap, self.cfg, self.st, self.notices)
        self.cfg["dies"]["qc"].pop("route_hold_items")
        from unittest.mock import patch
        with patch.object(KW, "_plan_current", return_value=False):
            KW.retry_enqueue(self.ap, self.cfg, self.st, self.notices)
        self.assertEqual(self.rec["status"], "CANCELLED")
        self.assertEqual(self.rec["class"], "SUPERSEDED")
        self.assertFalse(self.calls)


if __name__ == "__main__":
    unittest.main()
