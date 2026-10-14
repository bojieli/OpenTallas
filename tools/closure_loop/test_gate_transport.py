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
            with patch.object(G, "ROOT", root), patch.object(G, "ship_tar", return_value=b"tar"), \
                 patch.object(G, "referenced_closure", return_value=(set(), [], set())), \
                 patch.object(G, "absent_working_inputs", return_value=[]), \
                 patch.object(G.HO, "capture_plan", return_value=({"files": []}, {})), \
                 patch.object(G.SB, "snapshot", return_value={"commit": "a" * 40, "manifest_sha256": "m", "archive_sha256": "s"}), \
                 patch.object(G, "analyse_remote", lambda *a, **k: None), \
                 patch.object(G.subprocess, "run", side_effect=run):
                g = G.Gate();G.remote(g, kd, {"name": "test", "top": "test", "clock_port": "ck"}, "auto", 600, 24, True)
            self.assertEqual(calls[0], ["ot-run", "--mem", "24", "--pick"])
            upload = [i for i,c in enumerate(calls) if c[0] == "ssh"]
            admitted = [i for i,c in enumerate(calls) if c[0] == "ot-run" and "--pick" not in c]
            self.assertEqual(len(admitted), 1)
            self.assertEqual(len(upload), 3)      # remote script, source archive, immutable source-binding manifest
            self.assertGreater(admitted[0], max(upload))
            cmd = calls[admitted[0]]
            self.assertEqual(cmd[cmd.index("--hosts")+1], "ot-epyc4")
            self.assertNotIn("ot-heavy", cmd)
            self.assertEqual(g.remote_host, "ot-epyc4")

    def test_failed_pick_cannot_ship_or_run(self):
        # remote() first checks the kit's referenced inputs (absent_working_inputs, before any host is chosen), so the
        # kit needs its floorplan.json; then a failed pick must stop before any ship or run
        with tempfile.TemporaryDirectory() as td:
            kd = Path(td) / "kit"; kd.mkdir()
            (kd / "floorplan.json").write_text(json.dumps({"referenced": []}))
            with patch.object(G, "absent_working_inputs", return_value=[]), \
                 patch.object(G.subprocess, "run", return_value=SimpleNamespace(returncode=75, stdout="", stderr="no hosts")) as run:
                g = G.Gate();G.remote(g, kd, {}, "auto", 600, 24, True)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(g.verdict, "FAIL")
