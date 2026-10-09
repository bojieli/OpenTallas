#!/usr/bin/env python3
"""Run the instrumented original build and two-message diagnostic, preserving receipts."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

root = Path(sys.argv[1])
command = json.loads((root / "diagnostic_build_cmd.json").read_text())
command[0] = "/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator"
receipt = {"scope": "original reduced campaign14 diagnostic; no engine RTL changes", "command": command}
env = dict(os.environ, PATH="/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:" + os.environ["PATH"])
start = time.time()
with (root / "diagnostic_build.log").open("w") as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
receipt.update(build_rc=result.returncode, build_seconds=time.time() - start)
(root / "diagnostic_run.json").write_text(json.dumps(receipt, indent=2) + "\n")
if result.returncode:
    raise SystemExit(result.returncode)
command = [str(root / "wf2/obj_stage2_wfc_w1_deep/Vtb_dsrom_wavefront_array"),
           f"+DIR={root}/wf2/cfg_stage2_deep", f"+ROMS={root}/wf2/roms", "+NUSERS=1", "+NOUT=2"]
with (root / "diagnostic_sim.log").open("w") as log:
    result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
receipt.update(sim_command=command, sim_rc=result.returncode, elapsed_seconds=time.time() - start)
(root / "diagnostic_run.json").write_text(json.dumps(receipt, indent=2) + "\n")
raise SystemExit(result.returncode)
