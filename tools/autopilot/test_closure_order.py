#!/usr/bin/env python3
"""closure order (owner 2026-10-25 18:45, lanes/_LANE_PREAMBLE.md): path die gate (rule 1), sign-off provenance =
src commit + flow tag (rule 3), pending plan deltas (rule 4).  No ssh / ot-run / systemd (faked as in test_autopilot)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from test_autopilot import KIT, ROW, TickBase, so  # noqa: E402

KPATH = KIT.split(":", 1)[1]
QC = ["qwen_compute", "qfd_tile_nk_a0c", "epyc2:/srv/opentallas-scratch2/claude/path-qc/nk", "claude/qc@0123456789ab",
      "PASS", "GEOM-REVIEW [PATH-QC-NK] 10:07", "24", "120000", "PATH-QC"]
QPATH = QC[2].split(":", 1)[1]
FREEZE_HEAD = ("# PATH-FREEZE\n"
               "S81   | GRT0 | FAIL (FT G0C222) | see PATH-S81.md | 2026-10-25 18:45\n"
               "QC    | GRT0 | NOT RUN on current plan | - | 2026-10-25 18:45\n"
               "KV    | CLOCK-ROUTE / PATH-STA | NOT RUN (blocked on GRT0) | - | 2026-10-25 18:46\n")


def mode(row, m, flow=""):
    return row + ["", "", "", m, "", flow]


class TestParse(unittest.TestCase):
    def setUp(self):
        import autopilot
        self.ap = autopilot

    def test_gate_states(self):
        g, parts = self.ap.parse_path_freeze(
            FREEZE_HEAD + "QC | GRT0 | PASS | x | d\nQC | CLOCK-ROUTE / PATH-STA | PASS | y | d\n"
            "HBM | GRT0 | PASS | x | d\nFROZEN HBM plan@0123456789\nHBM | PATH-STA | FAIL new | z | d\n"
            "KV | GRT0 | PASS | x | d\nFROZEN KV plan@abcdef0123\nPATH-PARTS KV kv3_pc, kv3_phy\n")
        self.assertFalse(g["S81"]["pass"])
        self.assertTrue(g["QC"]["pass"])                     # all three items PASS
        self.assertFalse(g["HBM"]["pass"])                   # a FAIL after the FROZEN line reopens the gate
        self.assertTrue(g["KV"]["pass"])                     # FROZEN
        self.assertEqual(parts["KV"], {"kv3_pc", "kv3_phy"})
        self.assertNotIn("CLOCK", [k for k, v in g.items() if v["pass"]])

    def test_plan_delta(self):
        d = self.ap.parse_plan_delta("PENDING-DELTA kv-c qwen_kvsys kv3_hgi_v8,kv3_sys_c\nPENDING-DELTA s1 s81 bk_sel\n"
                                     "CLOSED-DELTA s1\nprose PENDING-DELTA x y z\n")
        self.assertEqual(d, {("qwen_kvsys", "kv3_hgi_v8"): "kv-c", ("qwen_kvsys", "kv3_sys_c"): "kv-c"})


class TestGates(TickBase):
    def setUp(self):
        super().setUp()
        base = self.f.rpy

        def rpy(host, code, args, timeout=600):
            if code is self.ap.PROBE_PROVENANCE:
                self.f.calls.append((host, code[:40], args))
                return {"ok": True}
            return base(host, code, args, timeout)
        self.ap.rpy = rpy

    def freeze(self, text):
        (Path(self.tmp.name) / "coord" / "lanes" / "PATH-FREEZE.md").write_text(text)

    def delta(self, text):
        (Path(self.tmp.name) / "coord" / "lanes" / "PLAN-DELTA.md").write_text(text)

    def signed_finish(self, path, unit_idx=0):
        self.f.kits[path] = {"classify": so("SIGNED", 3.0, 2.0, ()), "mtime": 9e9}
        self.finish_client(self.f.launched[unit_idx][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        return self.tick()

    def test_path_part_waits_for_die_gate(self):
        self.freeze(FREEZE_HEAD)
        self.queue(QC)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-PATH-GATE")
        self.assertIn("trial", j["history"][-1][2])
        self.assertEqual(self.f.launched, [])
        self.tick()                                          # logged once, still held
        self.assertEqual(sum("HOLD" in l for l in (Path(self.tmp.name) / "log.txt").read_text().splitlines()), 1)
        self.freeze(FREEZE_HEAD + "FROZEN QC plan@0123456789ab\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        jobs = self.signed_finish(QPATH)
        self.assertEqual(list(jobs.values())[0]["status"], "ARCHIVED")

    def test_trial_build_runs_but_never_signs_off(self):
        self.freeze(FREEZE_HEAD)
        self.queue(mode(QC, "trial"))
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        jobs = self.signed_finish(QPATH)
        (j,) = jobs.values()
        self.assertEqual(j["status"], "TRIAL-SIGNED")
        self.assertFalse((Path(self.tmp.name) / "signed.tsv").exists())
        self.assertIn("TRIAL", (Path(self.tmp.name) / "trial.tsv").read_text().upper())
        self.assertNotIn(self.ap.PROBE_ARCHIVE[:40], [c[1] for c in self.f.calls])

    def test_path_part_by_freeze_list_and_running_job_becomes_trial(self):
        self.freeze("PATH-PARTS S81 slice_station\n")       # no gate lines: fail closed
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-PATH-GATE")
        self.freeze("")                                      # not a path part any more -> submitted
        self.tick()
        self.freeze("PATH-PARTS S81 slice_station__t5\n")   # listed again before it finishes -> trial only
        (j,) = self.signed_finish(KPATH).values()
        self.assertEqual(j["status"], "TRIAL-SIGNED")

    def test_cts_only_diagnostic_is_a_trial(self):
        self.freeze(FREEZE_HEAD)
        row = QC + ["cts", "/srv/opentallas-scratch2/claude/path-qc/nk/run_cts.sh"]
        self.queue(row)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")
        self.assertIn("cts", j["trial"])
        self.f.kits[QPATH] = {"classify": {"goal": "cts", "cts_odb": QPATH + "/run/results/asap7/x/base/4_cts.odb"},
                              "mtime": 9e9}
        self.finish_client(self.f.launched[0][0], "ot-run: RAN on epyc2: exit 0\nAP_RC=0\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "CTS-DONE")
        self.assertFalse((Path(self.tmp.name) / "structural.tsv").exists())
        self.assertIn("CTS-DONE", (Path(self.tmp.name) / "trial.tsv").read_text())
        self.assertEqual(self.ap.classify({"goal": "route"}, {"exit": 0})[0], "CRASH")

    def test_pending_plan_delta_holds_spare_kits(self):
        self.delta("PENDING-DELTA s81-d1 s81 slice_station__t5,bk_sel\n")
        self.queue(ROW)
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "WAIT-PLAN-DELTA")
        self.delta("PENDING-DELTA s81-d1 s81 slice_station__t5,bk_sel\nMERGED-DELTA s81-d1\n")
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "RUNNING")

    def test_unversioned_signoff_not_counted_then_promoted(self):
        self.ap.resolve_provenance = lambda src, flow="": {"src_commit": "0123456789ab" + "0" * 28, "flow_tag": "",
                                                           "error": "no flow-* tag on origin yet"}
        self.queue(ROW)
        self.tick()
        (j,) = self.signed_finish(KPATH).values()
        self.assertEqual(j["status"], "SIGNED-UNVERSIONED")
        self.assertFalse((Path(self.tmp.name) / "signed.tsv").exists())
        self.assertEqual(len((Path(self.tmp.name) / "unversioned.tsv").read_text().splitlines()), 2)
        self.ap.resolve_provenance = lambda src, flow="": {"src_commit": "0123456789ab" + "0" * 28,
                                                           "flow_tag": "flow-20261026-a"}
        (j,) = self.tick().values()
        self.assertEqual(j["status"], "ARCHIVED")
        head, row = (Path(self.tmp.name) / "signed.tsv").read_text().splitlines()
        self.assertTrue(head.endswith("src_commit\tflow_tag"))
        self.assertTrue(row.endswith("0123456789ab" + "0" * 28 + "\tflow-20261026-a"))
        provs = [c[2]["prov"] for c in self.f.calls if c[1] == self.ap.PROBE_PROVENANCE[:40]]
        self.assertEqual([p["verdict"] for p in provs], ["SIGNED-UNVERSIONED", "SIGNED"])

    def test_signed_header_upgraded_in_place(self):
        p = Path(self.tmp.name) / "signed.tsv"
        old = "time\tid\tdie\ttype\tsrc\thost\tkit\tarchive\tmirror\ttt_wns_ps\tff_wns_ps\tlane"
        p.write_text(old + "\nt\tabc\ts81\tx\ty\th\tk\ta\tm\t1\t2\tS81\n")
        self.ap.tsv_append("signed.tsv", "def", ["s81"] * 12)
        lines = p.read_text().splitlines()
        self.assertEqual(lines[0], self.ap.TSV_HEAD["signed.tsv"])
        self.assertEqual(len(lines), 3)


class TestProvenanceGit(unittest.TestCase):
    """resolve_provenance on a real throw-away repo: tag match by watched flow content, never guessed"""
    def setUp(self):
        import importlib
        import autopilot
        self.ap = importlib.reload(autopilot)
        self.ap.CLOSURE.clear()
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        g = lambda *a: subprocess.run(["git", "-C", str(self.repo)] + list(a), check=True, capture_output=True, text=True).stdout.strip()
        self.g = g
        g("init", "-q")
        g("config", "user.email", "t@t"); g("config", "user.name", "t")
        (self.repo / "tools/die_plan").mkdir(parents=True)
        (self.repo / "tools/die_plan/signoff.py").write_text("v1\n")
        (self.repo / "rtl.sv").write_text("a\n")
        g("add", "."); g("commit", "-qm", "c1")
        g("tag", "flow-20261025-a")
        (self.repo / "rtl.sv").write_text("b\n")
        g("add", "."); g("commit", "-qm", "design only")
        self.design = g("rev-parse", "HEAD")
        (self.repo / "tools/die_plan/signoff.py").write_text("v2\n")
        g("add", "."); g("commit", "-qm", "flow change")
        self.flow2 = g("rev-parse", "HEAD")
        self._repo, self._watch = self.ap.REPO, self.ap.flow_watch
        self.ap.REPO = self.repo
        self.ap.flow_watch = lambda: ["tools/die_plan/signoff.py"]

    def tearDown(self):
        self.ap.REPO, self.ap.flow_watch = self._repo, self._watch
        self.ap.CLOSURE.clear()
        self.tmp.cleanup()

    def test_match(self):
        p = self.ap.resolve_provenance(f"claude/x@{self.design[:10]}")
        self.assertEqual((p["src_commit"], p["flow_tag"], p.get("error")), (self.design, "flow-20261025-a", None))
        p = self.ap.resolve_provenance(f"claude/x@{self.flow2[:10]}")
        self.assertEqual(p["flow_tag"], "")
        self.assertIn("no flow release tag", p["error"])
        p = self.ap.resolve_provenance(f"claude/x@{self.flow2[:10]}", "flow-20261025-a")
        self.assertIn("differs from flow-20261025-a", p["error"])
        p = self.ap.resolve_provenance("claude/x@deadbeef12")
        self.assertIn("not found", p["error"])


class TestOwnershipProvenance(unittest.TestCase):
    def test_only_versioned_records_count(self):
        import ownership as O
        items = [{"die": "s81", "item": "bk_sel__t2", "kind": "type", "module": "bk_sel__t2", "members": ["bk_sel__t2"]}]
        rec = {"name": "dp_bk_sel__t2", "top": "bk_sel__t2", "path": "/k/signoff.json", "scan_host": "epyc1"}
        unv = {}
        self.assertEqual(O.signed_items(items, {"signed_records": [rec]}, unv), {})          # old cache: no rule
        self.assertIn(("s81", "bk_sel__t2"), unv)
        unv = {}
        self.assertEqual(O.signed_items(items, {"provenance_rule": "v1", "signed_records": [rec]}, unv), {})
        self.assertIn(("s81", "bk_sel__t2"), unv)
        ok = dict(rec, versioned=True, src_commit="ab" * 20, flow_tag="flow-20261025-a")
        unv = {}
        out = O.signed_items(items, {"provenance_rule": "v1", "signed_records": [rec, ok]}, unv)
        self.assertIn("flow-20261025-a", out[("s81", "bk_sel__t2")])
        self.assertEqual(unv, {})


if __name__ == "__main__":
    unittest.main()
