"""NEARMISS-FIX-1 11-14: prd_run.sh must record prd_result.json even when its stdout pipe is closed (ot-run client gone)."""
import json
import os
import pathlib
import stat
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent
RUN = HERE / "prd_run.sh"


class SigpipeSurvival(unittest.TestCase):
    def test_closed_stdout_pipe_still_writes_result(self):
        with tempfile.TemporaryDirectory() as t:
            t = pathlib.Path(t)
            d = t / "pass"
            base = d / "run/results/asap7/x/base"
            base.mkdir(parents=True)
            (base / "5_route.odb").write_text("")
            (d / "PRD.json").write_text(json.dumps({"signoff_tools": "/none", "variant": "t5"}))
            (d / "variant.env").write_text("OT_MAX_FANOUT=1\nOT_SLEW_MARGIN=0\nOT_SETUP_MARGIN=0\nOT_HOLD_MARGIN=0\n"
                                           "OT_HOLD_ALLOW_SETUP=0\nOT_HOLD_MAXBUF=1\nROUTE_CORNERS=\n")
            (d / "clk_freeze_check.sh").write_text("#!/bin/bash\nexit 0\n")
            bin_ = t / "bin"
            bin_.mkdir()
            dk = bin_ / "docker"
            # stub: `docker run ... prd_count.tcl` prints the count line, every other call succeeds
            dk.write_text('#!/bin/bash\nsleep 1\ncase "$*" in *prd_count.tcl*) echo "OT_PRD_COUNT tag slew 0 cap 0 placement ok";; esac\nexit 0\n')
            dk.chmod(dk.stat().st_mode | stat.S_IEXEC)
            env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", OT_PRD_FINISH="0", OT_PRD_POST="0")
            # stdout = pipe whose reader is gone before the script writes anything
            r, w = os.pipe()
            os.close(r)
            p = subprocess.run(["bash", str(RUN), str(d), "2", "4", "1"], env=env, stdout=w, stderr=subprocess.DEVNULL)
            os.close(w)
            res = json.loads((d / "prd_result.json").read_text())
            self.assertGreaterEqual(len(res["passes"]), 1, f"rc {p.returncode}: no pass recorded")
            self.assertNotEqual(p.returncode, -13)


if __name__ == "__main__":
    unittest.main()
