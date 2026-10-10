#!/usr/bin/env python3
"""Minimum NK4/IH32/NB4 exact vehicle for the optional array ready-loop break.

Run only through measured remote admission. Arithmetic, masks, refusal and
backpressure reuse the retained W11 golden campaign; metadata corruption must fail.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import rtl_w11_idx_array as W

RTL = ["rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv",
       "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
       "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/ot_hdc_delay.sv",
       "rtl/hdc/ot_hdc_prefix.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv",
       "rtl/test/tb_hdc_v41x_idx_array_lat.sv"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    cfg = W.prepare_small(work, 1, 4, 301)
    vec = work / cfg["dir"]
    harness = work / "harness.cpp"
    harness.write_text('''#include "verilated.h"
#include "Vtb_hdc_v41x_idx_array.h"
int main(int argc, char** argv) {
  Verilated::commandArgs(argc, argv);
  Vtb_hdc_v41x_idx_array top;
  top.clk = 0;
  while (!Verilated::gotFinish()) {
    top.clk = !top.clk;
    top.eval();
    Verilated::timeInc(416);
  }
  top.final();
  return 0;
}
''')
    cmd = ["verilator", "--cc", "--exe", "--build", "--timing", "-O2",
           "-Wno-fatal", "-Wno-WIDTH", "-Wno-UNUSED", "-Wno-BLKANDNBLK",
           "--top-module", "tb_hdc_v41x_idx_array", "-GNS=1", "-GNK=4",
           "-GFPL=7", "-GFML=5", "-GQL=5", "-GSAFE_QUERY_GATE=1",
           "-j", str(args.jobs), "--Mdir", str(work / "obj"),
           str(ROOT / W.VLT), *[str(ROOT / x) for x in RTL], str(harness)]
    (work / "build_command.json").write_text(json.dumps(cmd, indent=2) + "\n")
    with (work / "build.log").open("w") as out:
        build = subprocess.run(cmd, stdout=out, stderr=subprocess.STDOUT)
    (work / "build.exit").write_text(str(build.returncode) + "\n")
    if build.returncode:
        return build.returncode
    exe = work / "obj/Vtb_hdc_v41x_idx_array"
    records = []
    for name, bubble, stall, mutant in [("full_ready", 0, 0, False),
                                       ("backpressure", 4, 6, False),
                                       ("MUT_QUERY_HEAD", 4, 6, True)]:
        argv = [str(exe), f"+NTOK={cfg['ntok']}", f"+NSLOT={cfg['nslot']}",
                "+SEED=3", f"+BUBBLE={bubble}", f"+ORDY={stall}"]
        if mutant:
            argv.append("+MUT_QUERY_HEAD")
        r = subprocess.run(argv, cwd=vec, capture_output=True, text=True)
        (work / f"{name}.log").write_text(r.stdout + r.stderr)
        match = W.RE.search(r.stdout)
        values = dict(zip(W.KEYS, map(int, match.groups()))) if match else {}
        exact = (r.returncode == 0 and bool(values)
                 and values["errors"] == 0 and values["checked"] == cfg["keys"]
                 and values["faults_expected_and_raised"] == cfg["expected_faults"]
                 and values["refused"] == cfg["expected_refused"]
                 and values["masked"] == cfg["expected_masked"]
                 and values["beats_in"] == values["beats_out"])
        records.append(dict(name=name, returncode=r.returncode, counters=values,
                            exact=exact, required_negative=mutant,
                            gate_pass=(bool(values) and values["errors"] > 0 and
                                       values["checked"] == cfg["keys"] if mutant else exact)))
    passed = all(x["gate_pass"] for x in records)
    report = dict(verdict="PASS" if passed else "FAIL", shape=dict(NS=1,NK=4,IH=32,NB=4),
                  parameters=dict(FPL=7,FML=5,QL=5,SAFE_QUERY_GATE=1),
                  data=cfg, runs=records,
                  source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest() for x in RTL},
                  scope="minimum complete ready-loop mechanism and full arithmetic; not die closure")
    (work / "record.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["verdict"])
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
