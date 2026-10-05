#!/usr/bin/env python3
"""Unit gates of the small system pieces built for the GPU-organised HBM comparator system (Icarus 11 benches,
quick): the command processor (rtl/test/gpu_sys/tb_gpu_cmdproc_unit.sv) and the Verilator -Wall lint of every
new rtl/gpu_sys module with ENABLE=0 and ENABLE=1 (IMPLICIT / UNDRIVEN / MULTIDRIVEN are failures; other
warnings are listed).

    python3 tools/gpu_sys/run_unit_small.py [--out results/rtl/hbm_system_rtl_20261003/unit_small.json]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERILATOR = Path(os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")) / "verilator-5.050/bin/verilator"
LINT = {
    "ot_gpu_cmdproc": ["rtl/gpu_sys/ot_gpu_cmdproc.sv"],
    "ot_gpu_host_bridge": ["rtl/gpu_sys/ot_gpu_host_bridge.sv", "rtl/gpu_sys/ot_gpu_cdc_fifo.sv", "rtl/link/ot_link_afifo.sv"],
    "ot_gpu_coll_mux": ["rtl/gpu_sys/ot_gpu_coll_mux.sv"],
    "ot_gpu_mreq_cdc": ["rtl/gpu_sys/ot_gpu_mreq_cdc.sv", "rtl/gpu_sys/ot_gpu_cdc_fifo.sv", "rtl/link/ot_link_afifo.sv"],
    "ot_gpu_cdc_fifo": ["rtl/gpu_sys/ot_gpu_cdc_fifo.sv", "rtl/link/ot_link_afifo.sv"],
    "ot_gpu_simt_lane": ["rtl/gpu_sys/ot_gpu_simt_lane.sv", "rtl/gpu/ot_gpu_fadd.sv", "rtl/hdc/ot_hdc_fpu.sv",
                         "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
                         "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv", "rtl/hdc/ot_hdc_prefix.sv"],
    "ot_gpu_reset_ctrl": ["rtl/gpu_sys/ot_gpu_reset_ctrl.sv"],
}
BENCH = ("tb_gpu_cmdproc_unit", ["rtl/gpu_sys/ot_gpu_cmdproc.sv", "rtl/test/gpu_sys/tb_gpu_cmdproc_unit.sv"],
         "TB_GPU_CMDPROC_UNIT PASS")


def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()


def lint(top, src, enable):
    params = [f"-GENABLE={enable}"] if top != "ot_gpu_simt_lane" else []
    r = subprocess.run([str(VERILATOR), "--lint-only", "-Wall", "-Wno-DECLFILENAME", "--top-module", top, *params,
                        *[str(ROOT / s) for s in src]], capture_output=True, text=True, cwd=ROOT)
    msgs = [l for l in r.stderr.splitlines() if l.startswith("%")]
    bad = [m for m in msgs if re.search(r"IMPLICIT|UNDRIVEN|MULTIDRIVEN|%Error-", m) and "Exiting due" not in m]
    return dict(top=top, enable=enable, fatal=bad, warnings=len(msgs), pass_=not bad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out")
    a = ap.parse_args()
    res = {"lint": [lint(t, s, e) for t, s in LINT.items() for e in ((0, 1) if t != "ot_gpu_simt_lane" else (1,))]}
    d = tempfile.mkdtemp(prefix="gpu_sys_unit_")
    name, src, token = BENCH
    subprocess.run(["iverilog", "-g2012", "-o", f"{d}/{name}.vvp", *[str(ROOT / s) for s in src]], check=True)
    out = subprocess.run(["vvp", "-n", f"{d}/{name}.vvp"], capture_output=True, text=True).stdout
    res["benches"] = [dict(bench=name, pass_=token in out, log=[l for l in out.splitlines() if "PASS" in l or "FAIL" in l])]
    ok = all(x["pass_"] for x in res["lint"]) and all(b["pass_"] for b in res["benches"])
    rec = dict(schema="opentallas.gpu_sys.unit_small.v1", tool="tools/gpu_sys/run_unit_small.py",
               simulators=[subprocess.run(["iverilog", "-V"], capture_output=True, text=True).stdout.splitlines()[0],
                           subprocess.run([str(VERILATOR), "--version"], capture_output=True, text=True).stdout.strip()],
               source_sha256={p: sha(p) for p in sorted({s for v in LINT.values() for s in v} | set(src))},
               status="pass" if ok else "fail", **res)
    if a.out:
        Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    for x in res["lint"]:
        print("LINT", "PASS" if x["pass_"] else "FAIL", x["top"], "ENABLE", x["enable"], "warnings", x["warnings"], *x["fatal"][:3])
    for b in res["benches"]:
        print("BENCH", "PASS" if b["pass_"] else "FAIL", b["bench"])
    print("RUN_UNIT_SMALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
