#!/usr/bin/env python3
"""Run the DS ROM system control-plane and index-scorer-location unit benches
(Icarus) with their mutants, and write source-pinned records:
  results/rtl/dsrom_system_rtl_20261003/ctrlplane_units.json
  results/rtl/dsrom_system_rtl_20261003/idx_scorer_loc_bench.json
"""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/rtl/dsrom_system_rtl_20261003"
BENCHES = {
    "ctrlplane_units": dict(
        src=["rtl/dsrom_sys/ot_dsrom_host_cq.sv", "rtl/dsrom_sys/ot_dsrom_stall_export.sv",
             "rtl/dsrom_sys/ot_dsrom_stage_guard.sv", "rtl/test/dsrom_sys/tb_dsrom_ctrlplane_units.sv"],
        verdict=r"UNITS (PASS|FAIL)",
        mutants={"DSROM_CQ_MUTANT_NORSV": "LAUNCH admitted without reserving completion space",
                 "DSROM_GUARD_MUTANT_NOSRC": "stage guard does not check the sender"}),
    "idx_scorer_loc_bench": dict(
        src=["rtl/dsrom_sys/ot_dsrom_idx_scorer_loc.sv", "rtl/test/dsrom_sys/tb_dsrom_idx_scorer_loc.sv"],
        verdict=r"IDXLOC (PASS|FAIL)",
        mutants={"DSROM_IDX_MUTANT_TIE": "ties broken to the HIGHER position (golden: lower)",
                 "DSROM_IDX_MUTANT_QID": "one stack carries a wrong query id"}),
}


def run(src, defines, tmp):
    exe = Path(tmp) / ("x_" + "_".join(defines or ["base"]))
    cmd = ["iverilog", "-g2012", *[f"-D{d}" for d in defines], "-o", str(exe), *src]
    subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    out = subprocess.run(["vvp", str(exe)], cwd=ROOT, capture_output=True, text=True, timeout=3600).stdout
    return cmd, out


def main():
    ver = subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0]
    ok_all = True
    with tempfile.TemporaryDirectory() as tmp:
        for name, b in BENCHES.items():
            cmd, out = run(b["src"], [], tmp)
            cases = [dict(line=l) for l in out.splitlines() if l.startswith("CASE ")]
            v = re.search(b["verdict"], out)
            rec = {"schema": "opentallas.dsrom.system_unit_bench.v1", "bench": name, "simulator": ver,
                   "command": cmd, "verdict": v.group(1) if v else "NO_VERDICT", "cases": cases,
                   "source_sha256": {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in b["src"]},
                   "mutants": {}}
            for d, why in b["mutants"].items():
                mcmd, mout = run(b["src"], [d], tmp)
                mv = re.search(b["verdict"], mout)
                rec["mutants"][d] = {"what": why, "command": mcmd, "verdict": mv.group(1) if mv else "NO_VERDICT",
                                     "must_fail": True, "ok": (mv is None or mv.group(1) == "FAIL"),
                                     "lines": [l for l in mout.splitlines() if l.startswith(("CASE", "IDXLOC"))]}
            rec["pass"] = rec["verdict"] == "PASS" and all(m["ok"] for m in rec["mutants"].values())
            ok_all &= rec["pass"]
            (OUT / f"{name}.json").write_text(json.dumps(rec, indent=1) + "\n")
            print(name, "PASS" if rec["pass"] else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
