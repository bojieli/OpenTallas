#!/usr/bin/env python3
"""One cached norm chain, actual registered transport, no oracle.

Run only on an admitted remote compute host. All expected files are reused.
The engine RTL and original bench are unchanged; the successor opts into
23 actual stages carrying output payload/index/valid at a 1.2 GHz clock.
--la6 selects the exact preserved candidate with LA=6 and also registers the
input payload beside its index and valid. No arithmetic source is rewritten.
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
    ap.add_argument("--la6", action="store_true", help="select the preserved LA6 source and registered input/output bench")
    ap.add_argument("--variant", choices=tuple(N.VARIANTS), default="hc")
    ap.add_argument("--fp", choices=("dpi", "rtl"), default="dpi")
    ap.add_argument("--prepare-only", action="store_true", help="write the exact compile inputs without starting a build")
    a = ap.parse_args()
    required = ["x.mem", "w.mem", "cfg.mem", "ey.mem", "eqc.mem", "eqe.mem", "eqy.mem"]
    if N.VARIANTS[a.variant]["RD"]:
        required += ["cs.mem", "er.mem"]
    for name in required:
        if not (a.case_dir / name).is_file():
            raise ValueError(f"missing cached golden input: {a.case_dir / name}")
    a.work.mkdir(parents=True, exist_ok=True)
    tb = N.ROOT / "rtl/test/tb_dsrom_su_norm_transport.sv"
    norm = N.RTL
    common = list(N.COMMON)
    if a.la6:
        norm = N.ROOT / "results/rtl/dsrom_recovery_20261004/su_fusion_takeover/la6_inputs/ot_dsrom_su_norm.sv"
        tb = N.ROOT / "rtl/test/tb_dsrom_su_norm_la6_transport.sv"
        common += ["rtl/hdc/v41x/ot_dsrom_aq12.sv", "rtl/hdc/v41x/ot_dsrom_divc.sv",
                   "rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv" if a.fp == "rtl"
                   else "rtl/test/sim_dsrom_fp32_add_l6_dpi.sv"]
    sources = [N.ROOT / s for s in common + N.FP_SRC[a.fp]] + [norm, tb]
    top = tb.stem
    obj = a.work / (f"obj_la6_{a.variant}_{a.fp}" if a.la6 else "obj")
    params = dict(N.VARIANTS[a.variant], RW=N.RW, BW=N.BW, HUB_IN=N.HUB_IN,
                  HUB_OUT=N.HUB_OUT, REGISTER_OUTPUT=1)
    if a.la6:
        params.update(LA=6, RXS=0)
    cmd = [N.VERILATOR, "--binary", "--timing", "-O2", "-Wno-fatal", "-Wno-WIDTH",
           "--top-module", top, "-Mdir", str(obj),
           "-j", "16", "--unroll-count", "4", "-fno-dfg",
           *[f"-G{k}={v}" for k, v in params.items()], *map(str, sources), "-CFLAGS", "-O1"]
    pin = dict(params=params, clock_hz=1200000000, command=cmd,
               driver_sha256=N.sha(Path(__file__)),
               selected_norm=str(norm.relative_to(N.ROOT)), fp=a.fp,
               transport="registered input and output payload/index/valid" if a.la6 else "registered output only",
               source_sha256={str(p.relative_to(N.ROOT)): N.sha(p) for p in sources},
               cached_files_sha256={p.name: N.sha(p) for p in sorted(a.case_dir.glob("*.mem"))},
               gain_loading="before go, exactly as original cached bench; not hidden or removed",
               cdc="not in this component; retain source-bound baseline graph crossings once",
               credits="always-accepting bench endpoint, integration not qualified")
    source_record = a.work / "source.json"
    if source_record.exists() and json.loads(source_record.read_text()) != pin:
        raise ValueError("work directory already binds a different source/shape; preserve its objects and use a distinct directory")
    source_record.write_text(json.dumps(pin, indent=2) + "\n")
    if a.prepare_only:
        print("PREPARED", top, a.variant, a.fp, "LA", params.get("LA", 4))
        return 0
    exe = obj / ("V" + top)
    if not exe.exists():
        with (a.work / "build.log").open("w") as log:
            build = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        (a.work / "build.rc").write_text(str(build.returncode) + "\n")
        if build.returncode:
            return build.returncode
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
        result["checked_y"], result["checked_q"]) == (params["D"], params["D"] // 32) and (
        params["RD"] == 0 or result["checked_ro"] == params["D"])
    result["boundary_events"] = [line for line in r.stdout.splitlines() if line.startswith("SU_BOUNDARY ")]
    result["source"] = pin
    result["binary_sha256"] = N.sha(exe)
    result["adoption"] = False
    (a.work / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("REGISTERED_TRANSPORT", "PASS" if result["pass"] else "FAIL", result["q_last"])
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
