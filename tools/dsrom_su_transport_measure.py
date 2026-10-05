#!/usr/bin/env python3
"""One cached HC norm chain, actual registered output transport, no oracle.

Run only on an admitted remote compute host. All expected files are reused.
The engine RTL and original bench are unchanged; the successor opts into
23 actual stages carrying output payload/index/valid at a 1.2 GHz clock.
"""
import argparse
import json
import subprocess
from pathlib import Path

import dsrom_su_norm as N


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--case-dir", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    a = ap.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    tb = N.ROOT / "rtl/test/tb_dsrom_su_norm_transport.sv"
    sources = [N.ROOT / s for s in N.COMMON + N.FP_SRC["dpi"]] + [N.RTL, tb]
    obj = a.work / "obj"
    params = dict(N.VARIANTS["hc"], RW=N.RW, BW=N.BW, HUB_IN=N.HUB_IN,
                  HUB_OUT=N.HUB_OUT, REGISTER_OUTPUT=1)
    cmd = [N.VERILATOR, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH",
           "--top-module", "tb_dsrom_su_norm_transport", "-Mdir", str(obj),
           "-j", "16", "--unroll-count", "4", "-fno-dfg",
           *[f"-G{k}={v}" for k, v in params.items()], *map(str, sources), "-CFLAGS", "-O1"]
    pin = dict(params=params, clock_hz=1200000000, command=cmd,
               source_sha256={str(p.relative_to(N.ROOT)): N.sha(p) for p in sources},
               cached_files_sha256={p.name: N.sha(p) for p in sorted(a.case_dir.glob("*.mem"))},
               gain_loading="before go, exactly as original cached bench; not hidden or removed",
               cdc="not in this component; retain source-bound baseline graph crossings once",
               credits="always-accepting bench endpoint, integration not qualified")
    (a.work / "source.json").write_text(json.dumps(pin, indent=2) + "\n")
    with (a.work / "build.log").open("w") as log:
        build = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    (a.work / "build.rc").write_text(str(build.returncode) + "\n")
    if build.returncode:
        return build.returncode
    exe = obj / "Vtb_dsrom_su_norm_transport"
    r = subprocess.run([str(exe)], cwd=a.case_dir, capture_output=True, text=True)
    (a.work / "run.log").write_text(r.stdout + r.stderr)
    (a.work / "run.rc").write_text(str(r.returncode) + "\n")
    match = N.SUN.search(r.stdout)
    if not match:
        raise ValueError("missing terminal boundary/check record")
    keys = ("go", "y_last", "r", "ro_last", "q_last", "err_y", "err_ro", "err_q",
            "checked_y", "checked_ro", "checked_q", "fault")
    result = dict(zip(keys, map(int, match.groups())))
    result["pass"] = r.returncode == 0 and "PASS" in r.stdout and all(
        result[k] == 0 for k in ("err_y", "err_ro", "err_q", "fault")) and (
        result["checked_y"], result["checked_q"]) == (5120, 160)
    result["boundary_events"] = [line for line in r.stdout.splitlines() if line.startswith("SU_BOUNDARY ")]
    result["source"] = pin
    result["binary_sha256"] = N.sha(exe)
    result["adoption"] = False
    (a.work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("REGISTERED_TRANSPORT", "PASS" if result["pass"] else "FAIL", result["q_last"])
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
