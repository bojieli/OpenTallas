#!/usr/bin/env python3
"""s81-die-rtl-bind 2026-10-14: exact bench of the die-name PQ slot dsfd_sp_pq_n (rtl/dsrom_sys/s81_die_bind) against
the bare production core ot_s81_pq_core_native, cycle lockstep (rtl/test/dsrom_sys/tb_s81_pq_die_n.cpp): every core
port equal through the die ports, the ROMs as one-cycle macros on ra*/rq*, the lane words = the die-lane encoding of the
reference broadcast one cycle later.  Same sources / defines for both models (the PQ's pinned tree + its SRAM model).

  pq_die_n_bench.py --work DIR [--mut ROMREG|LANE] [--define OT_PQ_...]...     PASS = exit 0
Mutants (must FAIL): ROMREG = a relay register on the ROM data (three-cycle ROM); LANE = two lane bits swapped.
"""
import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "physical/s81_pq_hier/pinned"
V = os.environ.get("OT_VERILATOR", os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))
PQ = ROOT / "rtl/dsrom_sys/s81_ph/pq"
CORE_FILES = [PQ / n for n in ("ot_s81_pq_core_native.sv", "ot_s81_pq_ctl_native.sv", "ot_s81_pq_ix_sram.sv",
              "ot_s81_pq_ix_pin_variants.sv", "ot_s81_pq_ix_split_native.sv", "ot_s81_pq_aq_split_native.sv",
              "ot_s81_pq_qb_sram.sv", "ot_s81_pq_qb_split_native.sv", "ot_s81_pq_qb_one_native.sv",
              "ot_s81_pq_ctl_fixed_native.sv")]


def run(cmd, log):
    with log.open("w") as f:
        f.write(" ".join(map(str, cmd)) + "\n"); f.flush()
        rc = subprocess.run(list(map(str, cmd)), stdout=f, stderr=subprocess.STDOUT).returncode
    if rc:
        print(log.read_text()[-3000:], flush=True)
        raise SystemExit(rc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--mut", choices=["ROMREG", "LANE", "X2"])
    ap.add_argument("--bf-x2", action="store_true", help="qualify die BF x2 extension lane")
    ap.add_argument("--define", action="append", default=[], help="core leaf-set define (OT_PQ_*), both models")
    a = ap.parse_args()
    w = a.work.resolve(); w.mkdir(parents=True, exist_ok=True)
    srcs = [p for p in sorted(PIN.rglob("*.sv")) if p.name != "ot_sram_1r1w_128x256_m1_r2c2.sv"]
    srcs += [ROOT / "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"]
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([V, "-V"], text=True))[1]
    libs = []
    for name, top in (("core", "ot_s81_pq_core_native"), ("die", "dsfd_sp_pq_n")):
        files = srcs + CORE_FILES + ([ROOT / "rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv"] if name == "die" else [])
        defs = ["+define+OT_PQ_ROM_PORTS"] + [f"+define+{d}" for d in a.define]
        if name == "die" and a.bf_x2: defs.append("+define+DSFD_PQ_BF_X2")
        if name == "die" and a.mut == "X2": defs.append("+define+DSFD_PQ_X2_MUT_SWAP")
        if name == "die" and a.mut == "ROMREG":
            defs.append("+define+DSFD_PQ_ROM_MUT_REG")
        if name == "die" and a.mut == "LANE":
            defs.append("+define+DSFD_PQ_LX_MUT_SWAP")
        md = w / name
        run([V, "--cc", "-O2", "-Wno-fatal", "-Wno-lint", "-Wno-style", "--x-assign", "0", "--x-initial", "0",
             "--prefix", f"V{name}", "--top-module", top, "--Mdir", md, *defs, *files], w / f"{name}.verilate.log")
        run(["make", "-C", md, "-f", f"V{name}.mk", f"-j{a.jobs}", f"V{name}__ALL.a", "OPT_FAST=-O1", "OPT_SLOW=-O0"],
            w / f"{name}.make.log")
        libs.append(md / f"V{name}__ALL.a")
    run(["g++", "-std=c++20", "-O2", *(["-DDSFD_PQ_BF_X2"] if a.bf_x2 else []), f"-I{vroot}/include", f"-I{vroot}/include/vltstd", f"-I{w / 'core'}", f"-I{w / 'die'}",
         ROOT / "rtl/test/dsrom_sys/tb_s81_pq_die_n.cpp", *libs,
         f"{vroot}/include/verilated.cpp", f"{vroot}/include/verilated_threads.cpp", "-pthread", "-o", w / "bench"], w / "link.log")
    rc = subprocess.run([str(w / "bench")], stdout=(w / "run.log").open("w"), stderr=subprocess.STDOUT).returncode
    out = (w / "run.log").read_text()
    print(out[-1500:], flush=True)
    raise SystemExit(0 if rc == 0 and "PQ_DIE_N PASS" in out else 1)


if __name__ == "__main__":
    main()
