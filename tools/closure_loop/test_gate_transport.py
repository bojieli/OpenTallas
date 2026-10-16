"""Fleet-picked pre-route gates reserve resources once after shipping their inputs."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ref_tile"))
import pre_route_gate as G


def _tgz():
    import io, tarfile
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        data = b"module test; endmodule\n"
        ti = tarfile.TarInfo("kit/test.v"); ti.size = len(data); tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()

class Transport(unittest.TestCase):
    def test_auto_pick_ship_run_uses_one_guard(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); kd = root / "kit"; kd.mkdir()
            (kd / "floorplan.json").write_text(json.dumps({"referenced": []}))
            calls = []
            def run(cmd, **kwargs):
                calls.append(cmd)
                if "--pick" in cmd:
                    return SimpleNamespace(returncode=0, stdout="ot-epyc4\n", stderr="table")
                if cmd[:1] == ["git"]:
                    return SimpleNamespace(returncode=0, stdout="a" * 9, stderr="")
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            with patch.object(G, "ROOT", root), patch.object(G, "ship_tar", return_value=_tgz()), \
                 patch.object(G, "referenced_closure", return_value=(set(), [], set())), \
                 patch.object(G, "absent_working_inputs", return_value=[]), \
                 patch.object(G.HO, "capture_plan", return_value=({"files": []}, {})), \
                 patch.object(G.SB, "snapshot", return_value={"commit": "a" * 40, "manifest_sha256": "m", "archive_sha256": "s", "files": []}), \
                 patch.object(G, "analyse_remote", lambda *a, **k: None), \
                 patch.object(G, "gate_route_clock_hooks", lambda sh, spec: sh), \
                 patch.object(G, "gate_route_hold_context", lambda sh, spec, kd: sh), \
                 patch.object(G.RT, "route_hold_context", lambda spec, kd: {}), \
                 patch.object(G.subprocess, "run", side_effect=run):
                g = G.Gate();G.remote(g, kd, {"name": "test", "top": "test", "clock_port": "ck"}, "auto", 600, 24, True)
            calls = [c for c in calls if c[0] != "git"]
            self.assertEqual(calls[0][:3], ["ot-run", "--mem", "24"])
            self.assertIn("--pick", calls[0])
            upload = [i for i,c in enumerate(calls) if c[0] == "ssh"]
            admitted = [i for i,c in enumerate(calls) if c[0] == "ot-run" and "--pick" not in c]
            self.assertEqual(len(admitted), 1)
            self.assertEqual(len(upload), 3)      # remote script, source archive, immutable source-binding manifest
            self.assertGreater(admitted[0], max(upload))
            cmd = calls[admitted[0]]
            self.assertEqual(cmd[cmd.index("--hosts")+1], "ot-epyc4")
            self.assertNotIn("ot-heavy", cmd)
            self.assertEqual(g.remote_host, "ot-epyc4")

    def test_not_admitted_after_upload_reships_same_archive(self):
        """AFTER-UPLOAD RACE (ROOT 2026-10-15): NOT RUN on the uploaded host -> re-pick, re-ship the same bytes elsewhere"""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); kd = root / "kit"; kd.mkdir()
            (kd / "floorplan.json").write_text(json.dumps({"referenced": []}))
            calls, picks = [], iter(["ot-epyc4\n", "ot-epyc1tb\n"])
            runs = iter([SimpleNamespace(returncode=75, stdout=b"", stderr=b"ot-run: NOT RUN (max-wait)"),
                         SimpleNamespace(returncode=0, stdout=b"", stderr=b"ot-run: RAN on ot-epyc1tb: exit 0")])
            def run(cmd, **kwargs):
                calls.append((cmd, kwargs.get("input")))
                if "--pick" in cmd:
                    return SimpleNamespace(returncode=0, stdout=next(picks), stderr="table")
                if cmd[:1] == ["git"]:
                    return SimpleNamespace(returncode=0, stdout="a" * 9, stderr="")
                if cmd[0] == "ot-run":
                    return next(runs)
                return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")
            with patch.object(G, "ROOT", root), patch.object(G, "ship_tar", return_value=_tgz()), \
                 patch.object(G, "referenced_closure", return_value=(set(), [], set())), \
                 patch.object(G, "absent_working_inputs", return_value=[]), \
                 patch.object(G.HO, "capture_plan", return_value=({"files": []}, {})), \
                 patch.object(G.SB, "snapshot", return_value={"commit": "a" * 40, "manifest_sha256": "m", "archive_sha256": "s", "files": []}), \
                 patch.object(G, "analyse_remote", lambda *a, **k: None), \
                 patch.object(G, "gate_route_clock_hooks", lambda sh, spec: sh), \
                 patch.object(G, "gate_route_hold_context", lambda sh, spec, kd: sh), \
                 patch.object(G.RT, "route_hold_context", lambda spec, kd: {}), \
                 patch.object(G.subprocess, "run", side_effect=run):
                g = G.Gate(); G.remote(g, kd, {"name": "test", "top": "test", "clock_port": "ck"}, "auto", 600, 24, True)
            ssh = [(c[1], inp) for c, inp in calls if c[0] == "ssh"]
            self.assertEqual([h for h, _ in ssh], ["ot-epyc4"] * 3 + ["ot-epyc1tb"] * 3 + ["ot-epyc4"])
            self.assertEqual([inp for h, inp in ssh[:3]][1], [inp for h, inp in ssh[3:6]][1])   # same archive bytes
            launches = [c for c, _ in calls if c[0] == "ot-run" and "--pick" not in c]
            self.assertEqual([c[c.index("--hosts") + 1] for c in launches], ["ot-epyc4", "ot-epyc1tb"])
            self.assertTrue(all("--max-wait" in c for c in launches))
            self.assertEqual(g.remote_host, "ot-epyc1tb")

    def test_failed_pick_cannot_ship_or_run(self):
        # remote() first checks the kit's referenced inputs (absent_working_inputs, before any host is chosen), so the
        # kit needs its floorplan.json; then a failed pick must stop before any ship or run
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td) / "kit"; kd.mkdir()
            (kd / "floorplan.json").write_text(json.dumps({"referenced": []}))
            with patch.object(G, "ROOT", Path(td)), patch.object(G, "absent_working_inputs", return_value=[]), \
                 patch.object(G, "ship_tar", return_value=_tgz()), \
                 patch.object(G.HO, "capture_plan", return_value=({"files": []}, {})), \
                 patch.object(G.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="no hosts")) as run:
                g = G.Gate();G.remote(g, kd, {"name": "t", "top": "t", "clock_port": "ck"}, "auto", 600, 24, True)
        cmds = [c.args[0] for c in run.call_args_list]
        self.assertEqual([c for c in cmds if c[0] == "ot-run"], [cmds[-1]])        # the pick is the last call
        self.assertIn("--pick", cmds[-1])
        self.assertFalse([c for c in cmds if c[0] == "ssh"])
        self.assertEqual(g.verdict, "FAIL")
