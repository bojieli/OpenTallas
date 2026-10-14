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
                 patch.object(G, "referenced_closure", return_value=(set(), [])), \
                 patch.object(G.subprocess, "run", side_effect=run):
                g = G.Gate();G.remote(g, kd, {"name": "test", "top": "test", "clock_port": "ck"}, "auto", 600, 24, True)
            self.assertEqual(calls[0], ["ot-run", "--mem", "24", "--pick"])
            upload = [i for i,c in enumerate(calls) if c[0] == "ssh"]
            admitted = [i for i,c in enumerate(calls) if c[0] == "ot-run" and "--pick" not in c]
            self.assertEqual(len(admitted), 1)
            self.assertEqual(len(upload), 2)
            self.assertGreater(admitted[0], max(upload))
            cmd = calls[admitted[0]]
            self.assertEqual(cmd[cmd.index("--hosts")+1], "ot-epyc4")
            self.assertNotIn("ot-heavy", cmd)
            self.assertEqual(g.remote_host, "ot-epyc4")

    def test_failed_pick_cannot_ship_or_run(self):
        with patch.object(G.subprocess, "run", return_value=SimpleNamespace(returncode=75, stdout="", stderr="no hosts")) as run:
            g = G.Gate();G.remote(g, Path("missing"), {}, "auto", 600, 24, True)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(g.verdict, "FAIL")
