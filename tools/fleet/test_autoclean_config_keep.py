#!/usr/bin/env python3
"""KW-SRCGONE-1: kitwave-reduce keeps the CURRENT sources named by the wave config even when no row of the die is active."""
import json, os, subprocess, sys, tempfile, unittest
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ot-autoclean.py")

class T(unittest.TestCase):
    def test_config_sources_kept(self):
        with tempfile.TemporaryDirectory() as d:
            st = os.path.join(d, "state.json"); json.dump({"items": {}}, open(st, "w"))
            tsv = os.path.join(d, "stages.tsv"); open(tsv, "w").write("die\titem\tkit\tstatus\tclass\n")
            cfg = os.path.join(d, "kit_wave.json")
            json.dump({"dies": {"s81_head": {"gen_hosts": ["epyc2", "epyc8"], "src": "/srv/opentallas-scratch2/claude/kw45/src_head_main_x1",
                                              "kit_rtl": {"bind_out": "/srv/opentallas-scratch2/claude/kw45/bind_h/out", "note": "x y"},
                                              "item_inputs": {"hd_host_e": {"src": "/srv/opentallas-scratch2/claude/kw45/src_head_h94_y"}}}}},
                      open(cfg, "w"))
            r = subprocess.run([sys.executable, "-I", SCRIPT, "kitwave-reduce", "--state-json", st, "--stages-tsv", tsv,
                                "--config-json", cfg], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            keep = set(json.loads(r.stdout)["keep"])
            for h in ("epyc2", "epyc8"):
                self.assertIn(f"{h}:/srv/opentallas-scratch2/claude/kw45/src_head_main_x1", keep)
                self.assertIn(f"{h}:/srv/opentallas-scratch2/claude/kw45/bind_h/out", keep)
                self.assertIn(f"{h}:/srv/opentallas-scratch2/claude/kw45/src_head_h94_y", keep)

if __name__ == "__main__":
    unittest.main()
