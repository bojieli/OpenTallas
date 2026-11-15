"""KIT-OPS-1 11-13 (COORD 07:5x via GEOM-VIS-15): (1) a GEOM VERDICT line whose text before the verdict holds nested
parentheses (with colons inside) parses; a row-attempt verdict line that does not parse is warned in the autopilot log once;
(2) VISUAL-QUEUE skips a WAIT-VISUAL row whose build already has an applicable accepting verdict but sits under a hold_items
pattern (die-wide '*' or the item), since enqueue_pass never re-judges a held row."""
import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import kit_wave as K

SPEC = {"item": "kv3_sys_c", "event": "ev", "plan": "/x/plan_c.json", "src": "/s/src_a", "core_kit": "ck", "gen_env": {}}
T_VERDICT = "2026-11-13 04:03"
TS = time.mktime(time.strptime(T_VERDICT, "%Y-%m-%d %H:%M"))
NESTED = ("- 2026-11-13 04:03 PST GEOM VERDICT [GEOM-VIS-14 viewed] s81/slice_station__t48 attempt_5 3_place (VISUAL-QUEUE row, "
          "event b1a2125433d0; epyc4 /srv/x/attempt_5/gen/slice_station__t48/run/layout_review has no place render (eco 6_final "
          "11-05 21:04 UTC); geom/auto_geom.png md5 5b6a7a4c, auto_geom.json and grt.log read): ISSUES-ACCEPT for route. No "
          "place/density.png exists (legacy run; 3_place never rendered): judged from auto_geom.png")


class FakeAP:
    def __init__(self):
        self.logs = []

    def log(self, m):
        self.logs.append(m)


class ParseLine(unittest.TestCase):
    def test_nested_parentheses_with_colons(self):
        self.assertEqual(K.parse_visual_line(NESTED), ("s81", "slice_station__t48", 5, "ISSUES-ACCEPT"))

    def test_old_forms_unchanged(self):
        for ln, want in (
                ("- x GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_12 3_place (epyc8): GOOD. text", "GOOD"),
                ("- x GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c a12 3_place: BAD, rebuild", "BAD"),
                ("- x GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_12 (render 10:25 PST): ISSUES. y: OK", "ISSUES"),
                ("- x GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_12 (a: b): OK", "OK")):
            self.assertEqual(K.parse_visual_line(ln), ("qwen_kvsys", "kv3_sys_c", 12, want), ln)

    def test_issues_accept_not_read_as_issues(self):
        r = K.parse_visual_line("GEOM VERDICT [V] d/t attempt_3 (p (q: r)): ISSUES-ACCEPT")
        self.assertEqual(r[3], "ISSUES-ACCEPT")

    def test_not_a_row_line_and_unparsed(self):
        self.assertIsNone(K.parse_visual_line("- x GEOM VERDICT [V viewed] s81_head rp18 whole-die render: GOOD"))
        self.assertIsNone(K.parse_visual_line("plain text"))
        self.assertEqual(K.parse_visual_line("GEOM VERDICT [V] d/t attempt_3 (sample): sample PASS, ISSUES-ACCEPT"), "UNPARSED")
        self.assertEqual(K.parse_visual_line("GEOM VERDICT [V] d/t attempt_3 (unclosed (x: GOOD"), "UNPARSED")


class Wave(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "coord" / "lanes").mkdir(parents=True)
        (self.root / "coord" / "autopilot").mkdir(parents=True)
        self.review = self.root / "coord" / "lanes" / "GEOM-REVIEW.md"
        self.review.write_text("# review\n")
        self.adir = self.root / "kv_sys_c" / "a12"
        self.adir.mkdir(parents=True)
        (self.adir / "spec.json").write_text(json.dumps(SPEC))
        self.cfg = {"dies": {"qwen_kvsys": {"gen_hosts": [], "plan": "/x/plan_c.json"}},
                    "visual_gate_since": "2026-11-12 04:25", "visual_gate": "signoff"}
        self.p = [mock.patch.object(K, "type_block_sha", lambda *a, **k: "tb1"),
                  mock.patch.object(K.Path, "home", lambda: self.root),
                  mock.patch.object(K.subprocess, "run", lambda *a, **k: None),
                  mock.patch.object(K, "kit_class", lambda d, i: "qwen_kvsys|kv3|fam")]
        for x in self.p:
            x.start()
        K._VISUAL_CACHE.update(mtime=None, v={}, ts={})

    def tearDown(self):
        for x in self.p:
            x.stop()
        K._VISUAL_CACHE.update(mtime=None, v={}, ts={})
        self.td.cleanup()

    def add(self, ln):
        with open(self.review, "a") as f:
            f.write(ln + "\n")
        st = os.stat(self.review)
        os.utime(self.review, (st.st_atime, st.st_mtime + 1))

    def rec(self, **kw):
        r = {"die": "qwen_kvsys", "item": "kv3_sys_c", "kind": "type", "attempt": 12, "started": TS - 3600,
             "dir": str(self.adir), "status": "ROUTE-HELD", "kit": "epyc8:/k", "kit_host": "epyc8", "updated": TS - 60,
             "route_hold": "WAIT-VISUAL: place done, needs a visual verdict GOOD / OK / ISSUES-ACCEPT"}
        r.update(kw)
        return r

    # ---- (1) the nested line counts; an unparsed row line is warned once
    def test_nested_line_reaches_verdicts(self):
        self.add(NESTED.replace("s81/slice_station__t48 attempt_5", "qwen_kvsys/kv3_sys_c attempt_12"))
        self.assertEqual(K.visual_verdicts().get(("qwen_kvsys", "kv3_sys_c", 12)), "ISSUES-ACCEPT")
        self.assertEqual(K.visual_signoff_state(self.cfg, self.rec())[0], "accept")

    def test_warn_once_per_unparsed_line(self):
        self.add(f"- {T_VERDICT} PST GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_12 (x): sample PASS, OK")
        self.add(f"- {T_VERDICT} PST GEOM VERDICT [V viewed] s81_head rp18 whole-die: GOOD")
        ap, st = FakeAP(), {}
        self.assertEqual(K.visual_parse_warn(ap, st), 1)
        self.assertEqual(len(ap.logs), 1)
        self.assertIn("VISUAL-PARSE WARN", ap.logs[0])
        self.assertIn("kv3_sys_c attempt_12", ap.logs[0])
        self.assertEqual(K.visual_parse_warn(ap, st), 0)          # same line: no second warning
        self.add(f"- {T_VERDICT} PST GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_13 (y): looks fine")
        self.assertEqual(K.visual_parse_warn(ap, st), 1)
        self.assertEqual(len(ap.logs), 2)

    def test_no_warn_when_all_parse(self):
        self.add(NESTED)
        ap = FakeAP()
        self.assertEqual(K.visual_parse_warn(ap, {}), 0)
        self.assertEqual(ap.logs, [])

    # ---- (2) a held row with its accepting verdict leaves the queue
    def queue(self, cfg, rec):
        st = {"items": {"a": rec}}
        n = K.visual_queue_publish(cfg, st)
        return n, st["items"]["a"]

    def test_held_row_with_accept_skipped(self):
        self.add(f"- {T_VERDICT} PST GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_12 (p): ISSUES-ACCEPT for route")
        for pat in ("*", "kv3_sys_*"):
            cfg = json.loads(json.dumps(self.cfg))
            cfg["dies"]["qwen_kvsys"]["hold_items"] = {pat: "WAIT-FORM die-wide"}
            r = self.rec()
            n, r2 = self.queue(cfg, r)
            self.assertEqual(n, 0, pat)
            self.assertEqual(r2["status"], "ROUTE-HELD")                 # row and its hold untouched
            self.assertTrue(r2["route_hold"].startswith("WAIT-VISUAL"))

    def test_held_row_without_verdict_still_listed(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["dies"]["qwen_kvsys"]["hold_items"] = {"*": "WAIT-FORM die-wide"}
        self.assertEqual(self.queue(cfg, self.rec())[0], 1)

    def test_unheld_row_with_accept_unchanged(self):
        # not held: enqueue_pass releases it, the queue logic is as before (still listed until then)
        self.add(f"- {T_VERDICT} PST GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_12 (p): GOOD")
        self.assertEqual(self.queue(self.cfg, self.rec())[0], 1)

    def test_held_row_verdict_of_other_attempt_listed(self):
        self.add(f"- {T_VERDICT} PST GEOM VERDICT [V viewed] qwen_kvsys/kv3_sys_c attempt_11 (p): GOOD")
        cfg = json.loads(json.dumps(self.cfg))
        cfg["dies"]["qwen_kvsys"]["hold_items"] = {"*": "x"}
        self.assertEqual(self.queue(cfg, self.rec())[0], 1)


if __name__ == "__main__":
    unittest.main()
