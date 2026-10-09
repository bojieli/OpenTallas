#!/usr/bin/env python3
"""Run the minimum full-shape owner gate on an admitted remote fleet host."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument("--out", required=True)
p.add_argument("--phase-mutant", type=int, default=0)
p.add_argument("--landing", type=int, default=1)
a = p.parse_args()
root = Path(__file__).resolve().parents[1]
out = Path(a.out).resolve()
out.mkdir(parents=True, exist_ok=False)
fl = root / "rtl/hbm_accel/ha2_ar/tb_ha2_tu_owner_banked_half_cx.f"
sources = [root / x for x in fl.read_text().splitlines() if x.strip()]
record = {
    "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "source_sha256": {str(x.relative_to(root)): hashlib.sha256(x.read_bytes()).hexdigest() for x in sources},
    "shape": {"NC": 8, "PFMAX": 384, "NPT": 8, "INJ": 2, "LANES": 16, "FD": 8},
    "fast_period_ps": 833.333334,
    "landing": a.landing, "phase_mutant": a.phase_mutant,
    "scope": "minimum full failed owner shape; no die closure or native INJ8 qualification",
}
top = "tb_ha2_tu_owner_banked_half_cx"
cmd = ["/usr/bin/time", "-v", "verilator", "--binary", "--timing", "-O1",
       "-Wno-fatal", "-Wno-WIDTH", "--top-module", top,
       f"-GPHASE_MUT={a.phase_mutant}", f"-GLANDING={a.landing}",
       "-Mdir", str(out / "obj"), "--build-jobs", "4", *map(str, sources)]
with (out / "build.log").open("w") as f:
    rc = subprocess.run(cmd, cwd=root, stdout=f, stderr=subprocess.STDOUT).returncode
record["build_rc"] = rc
if rc == 0:
    runs = {}
    for neg in (0, 1, 2, 3):
        with (out / f"run-neg{neg}.log").open("w") as f:
            runs[str(neg)] = subprocess.run([str(out / "obj" / ("V" + top)), f"+NEG={neg}"],
                                           cwd=root, stdout=f, stderr=subprocess.STDOUT).returncode
        if a.phase_mutant and neg == 0:
            break
    record["run_rc"] = runs
    record["verdict"] = "PASS" if all(x == 0 for x in runs.values()) else "FAIL"
else:
    record["verdict"] = "BUILD_FAIL"
(out / "gate.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record, indent=2))
raise SystemExit(0 if record["verdict"] == "PASS" else 1)
