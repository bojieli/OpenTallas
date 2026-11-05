#!/usr/bin/env python3
"""tests for substep_prune.py (SUBSTEP-1, COORD 11-05 10:53): no ssh, no docker; the remote program runs locally"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import substep_prune as SP  # noqa: E402

OLD = time.time() - 8 * 3600


def mk(p, data=b"x", t=OLD):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    os.utime(p, (t, t))
    return str(p)


def attempt(root, name="attempt_2"):
    d = Path(root) / "kit-wave/s81/ev/items/x" / name
    base = d / "gen/x/run/results/asap7/x/base"
    mk(base / "2_1_floorplan.odb", b"a" * 10, OLD - 60)
    mk(base / "2_4_floorplan_pdn.odb", b"a" * 20, OLD - 60)
    mk(base / "2_floorplan.odb", b"b" * 5, OLD)
    mk(base / "3_3_place_gp.odb", b"c" * 30, OLD - 60)      # no 3_place.odb: stays
    mk(base / "1_synth.odb", b"d", OLD)
    for x in (d / "gen/x/run/results/asap7/x/base", d / "gen/x/run/results/asap7/x", d / "gen/x/run/results/asap7",
              d / "gen/x/run/results", d / "gen/x/run", d / "gen/x", d / "gen", d):
        os.utime(x, (OLD, OLD))
    return str(d), base


class Candidates(unittest.TestCase):
    def st(self, **rows):
        return {"items": rows}

    def row(self, att, status, upd, q=None, item="x", ev="e", host="epyc4"):
        r = {"die": "s81", "event": ev, "item": item, "attempt": str(att), "status": status, "updated": upd,
             "evidence": f"{host}:/srv/s/kit-wave/s81/{ev}/items/{item}/attempt_{att}"}
        if q:
            r["q_status"] = q
        return r

    def test_terminal_idle_only(self):
        now = time.time()
        st = self.st(a=self.row(1, "ENQUEUED", now - 9 * 3600),            # superseded by attempt 3
                     b=self.row(2, "FAIL", now - 7 * 3600),
                     c=self.row(3, "ENQUEUED", now - 9 * 3600),             # newest, no verdict: live
                     d=self.row(1, "FAIL", now - 1 * 3600, item="y"),      # too recent
                     e=self.row(1, "ENQUEUED", now - 9 * 3600, q="FAIL", item="z"),
                     f=self.row(1, "RUNNING", now - 9 * 3600, item="w"),
                     g=dict(self.row(1, "CANCELLED", now - 9 * 3600, item="v"), substep_pruned="done"))
        got = sorted(k for k, _, _ in SP.candidates(st, now))
        self.assertEqual(got, ["a", "b", "e"])
        self.assertEqual(SP.candidates(st, now)[0][1], "epyc4")
        st["items"]["b"]["evidence"] += "/geom/auto_geom.json"
        self.assertIn(("b", "epyc4", "/srv/s/kit-wave/s81/e/items/x/attempt_2"), SP.candidates(st, now))

    def test_non_wave_evidence_ignored(self):
        r = self.row(1, "FAIL", 0)
        r["evidence"] = "epyc4:/home/ubuntu/x/attempt_1"
        self.assertEqual(SP.candidates({"items": {"a": r}}), [])

    def test_protected_union_root_space_rows(self):
        lanes = "# h\nepyc4\t/srv/a/b\tx\n"
        root = "# root\nintel2 /srv/opentallas-scratch2/claude/codex-kv CODEX keep\nepyc4 /srv/r/only/  note\n\n"
        root += "epyc4:/srv/r/colon/i1 S81 kit\nintel2:/srv/q x\n"
        self.assertEqual(SP.protected_for(lanes + "\n" + root, "epyc4"), ["/srv/a/b", "/srv/r/only", "/srv/r/colon/i1"])

    def test_root_list_only_row_skipped_in_tick(self):
        with tempfile.TemporaryDirectory() as t:
            d, base = attempt(t)
            st = {"items": {"k": {"die": "s81", "event": "ev", "item": "x", "attempt": "2", "status": "FAIL",
                                  "updated": 0, "evidence": "intel2:" + d}}}
            files = {"lanes/PROTECTED-DBS.txt": "intel2\t/srv/other\tx\n",
                     "PROTECTED-DBS.txt": f"intel2 {d}  root-list only\n"}
            orig = SP.candidates
            SP.candidates = lambda s, *a, **k: [] if s["items"]["k"].get("substep_pruned") else [("k", "intel2", d)]
            try:
                ap = Tick.AP()
                SP.tick(ap, {"dies": {}}, st, t, lambda h: [], files.get, _live=[])
                self.assertTrue((base / "2_1_floorplan.odb").exists())
                self.assertTrue(st["items"]["k"]["substep_pruned"].startswith("skip:protected"))
                # a missing root list stops the tick: nothing removed, nothing marked
                st["items"]["k"].pop("substep_pruned")
                SP.tick(ap, {"dies": {}}, st, t, lambda h: [], {"lanes/PROTECTED-DBS.txt": "intel2\t/srv/o\tx\n"}.get,
                        _live=[])
                self.assertTrue((base / "2_1_floorplan.odb").exists())
                self.assertNotIn("substep_pruned", st["items"]["k"])
                self.assertTrue(any("PROTECTED-DBS.txt unreadable" in m for m in ap.logs), ap.logs)
            finally:
                SP.candidates = orig

    def test_protected_for_host(self):
        txt = "# h\nepyc4\t/srv/a/b\tx\nintel2\t/srv/c\ty\n"
        self.assertEqual(SP.protected_for(txt, "epyc4"), ["/srv/a/b"])


class Judge(unittest.TestCase):
    NOLIVE = (set(), set())

    def test_removes_only_substeps_with_boundary(self):
        with tempfile.TemporaryDirectory() as t:
            d, base = attempt(t)
            v, rm = SP.judge_dir(d, [], self.NOLIVE, time.time())
            self.assertEqual(v, "done")
            self.assertEqual(sorted(os.path.basename(p) for p, _ in rm), ["2_1_floorplan.odb", "2_4_floorplan_pdn.odb"])
            self.assertFalse((base / "2_1_floorplan.odb").exists())
            for keep in ("2_floorplan.odb", "3_3_place_gp.odb", "1_synth.odb"):
                self.assertTrue((base / keep).exists(), keep)

    def test_hardlink_empty_or_older_boundary_kept(self):
        with tempfile.TemporaryDirectory() as t:
            d, base = attempt(t)
            os.link(base / "2_1_floorplan.odb", Path(t) / "other.odb")
            mk(base / "3_place.odb", b"", OLD)                    # empty boundary: 3_3 stays
            mk(base / "2_floorplan.odb", b"b", OLD - 3600)        # boundary older than 2_4: stays
            os.utime(d, (OLD, OLD))
            v, rm = SP.judge_dir(d, [], self.NOLIVE, time.time())
            self.assertEqual((v, rm), ("done", []))

    def test_skips(self):
        with tempfile.TemporaryDirectory() as t:
            d, base = attempt(t)
            now = time.time()
            self.assertEqual(SP.judge_dir(d, [d + "/gen"], self.NOLIVE, now)[0], "skip:protected")
            self.assertEqual(SP.judge_dir(d, [str(Path(d).parent)], self.NOLIVE, now)[0], "skip:protected")
            self.assertEqual(SP.judge_dir(d, [], ({str(base)}, set()), now)[0], "skip:live")
            self.assertEqual(SP.judge_dir(d, [], (set(), {str(Path(d).parent)}), now)[0], "skip:live")
            self.assertEqual(SP.judge_dir(d, [], (set(), None), now)[0], "skip:live")
            self.assertEqual(SP.judge_dir(d, [], ({"/", "/home"}, {"/srv", t}), now)[0], "done")  # not wave mounts
            for verdict in ("SIGNED", "LOCAL_PASS_NEEDS_PARENT"):
                with tempfile.TemporaryDirectory() as t2:
                    d2, b2 = attempt(t2)
                    mk(Path(d2) / "gen/x/signoff/signoff.json", json.dumps({"verdict": verdict}).encode())
                    self.assertEqual(SP.judge_dir(d2, [], self.NOLIVE, now)[0], "skip:signed")
                    self.assertTrue((b2 / "2_1_floorplan.odb").exists())
            with tempfile.TemporaryDirectory() as t3:
                d3, b3 = attempt(t3)
                mk(Path(d3).parent / ".keep", b"")
                self.assertEqual(SP.judge_dir(d3, [], self.NOLIVE, now)[0], "skip:keep")
            with tempfile.TemporaryDirectory() as t4:
                d4, b4 = attempt(t4)
                mk(b4 / "fresh.log", b"x", time.time())
                self.assertEqual(SP.judge_dir(d4, [], self.NOLIVE, now)[0], "skip:idle")
            self.assertEqual(SP.judge_dir(d + "/nope", [], self.NOLIVE, now)[0], "skip:missing")


class Tick(unittest.TestCase):
    class AP:
        DRY = False
        logs = []

        def log(self, m):
            self.logs.append(m)

        def sh(self, cmd, timeout=None, input=None):
            import subprocess
            r = subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)
            return r.returncode, r.stdout, r.stderr

    def test_tick_runs_program_and_marks(self):
        with tempfile.TemporaryDirectory() as t:
            d, base = attempt(t)
            d2, b2 = attempt(t, "attempt_3")
            mk(b2 / "fresh.log", b"x", time.time())
            now = time.time()
            st = {"items": {
                "k1": {"die": "s81", "event": "ev", "item": "x", "attempt": "2", "status": "FAIL",
                       "updated": now - 9 * 3600, "evidence": "intel2:" + d.replace(t, "/srv/T", 1)},
                "k2": {"die": "s81", "event": "ev", "item": "x", "attempt": "3", "status": "FAIL",
                       "updated": now - 9 * 3600, "evidence": "intel2:" + d2.replace(t, "/srv/T", 1)}}}
            # evidence paths must be /srv/...: map /srv/T -> t through a symlink-free rewrite in the request
            for r in st["items"].values():
                r["evidence"] = r["evidence"].replace("/srv/T", t)
            orig = SP.candidates
            SP.candidates = lambda s, *a, **k: [(k_, "intel2", r["evidence"].split(":", 1)[1])
                                                for k_, r in s["items"].items()
                                                if not r.get("substep_pruned") and not r.get("substep_checked")]
            try:
                ap = self.AP()
                SP.tick(ap, {"dies": {"s81": {}}}, st, t, lambda h: [], lambda rel: "intel2\t/srv/zz\tx\n", _live=[])
                SP.tick(ap, {"dies": {"s81": {}}}, st, t, lambda h: [], lambda rel: "intel2\t/srv/zz\tx\n", _live=[])
                self.assertFalse((base / "2_1_floorplan.odb").exists())
                self.assertTrue((b2 / "2_1_floorplan.odb").exists())          # idle: kept, not marked, re-checked
                self.assertTrue(st["items"]["k1"]["substep_pruned"].startswith("done"))
                self.assertNotIn("substep_pruned", st["items"]["k2"])
                self.assertIn("substep_checked", st["items"]["k2"])
                self.assertEqual(SP.candidates({"items": {"k2": dict(st["items"]["k2"], updated=0,
                                                                     evidence="h:/srv/kit-wave/attempt_3")}}), [])
                man = (Path(t) / SP.MANIFEST).read_text().splitlines()
                self.assertEqual(len(man), 2)
                self.assertIn("s81\tx@2", man[0])
                self.assertTrue(any("SUBSTEP-1 intel2: 2 sub-step ODBs" in m for m in ap.logs), ap.logs)
                # switched off
                st["items"]["k2"].pop("substep_checked", None)
                SP.tick(ap, {"substep_prune": False, "dies": {}}, st, t, lambda h: [], lambda rel: "x", _live=[])
                self.assertTrue((b2 / "2_1_floorplan.odb").exists())
            finally:
                SP.candidates = orig


if __name__ == "__main__":
    unittest.main()
