#!/usr/bin/env python3
"""Production core lockstep vs the original parameterized flop buffer tiles.

The native DUT contains the real 36 macro models. The reference substitutes
only unchanged IX/QB tiles; control, quantisers, ROM model and external twelve
group count stimulus are shared. This gate covers core integration, separately
from the storage adversarial gates and the still-required physical die gates.
"""
import argparse
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_core_native.sv"
PIN = ROOT / "physical/s81_pq_hier/pinned"
V = os.environ.get("OT_VERILATOR", os.path.expanduser("~/.local/opentallas-tools/verilator-5.050/bin/verilator"))


def run(cmd, log):
    with log.open("w") as f:
        f.write(" ".join(map(str,cmd))+"\n"); f.flush()
        rc = subprocess.run(list(map(str,cmd)), stdout=f, stderr=subprocess.STDOUT).returncode
    if rc:
        print(log.read_text()[-4000:], flush=True)
        raise SystemExit(rc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--mut", choices=["IX", "QB", "CONSUME", "BC"])
    ap.add_argument("--bc-sliced", action="store_true")
    ap.add_argument("--bc-mut-slice", type=int, choices=range(4), default=0)
    a = ap.parse_args(); w = a.work.resolve(); w.mkdir(parents=True, exist_ok=True)
    src = CORE.read_text()
    ref = src.replace("module ot_s81_pq_core_native", "module ot_s81_pq_core_ref", 1)
    ref = ref.replace("ot_s81_pq_qb_sram u_qb", "ot_v41_pqc_qb #(.KMAX(6144)) u_qb")
    ref = ref.replace(",\n        .fault(storage_fault[4])", "")
    ref = ref.replace("ot_s81_pq_ix_sram u_ix", "ot_v41_pqc_ix #(.KMAX(6144), .VRD(64)) u_ix")
    ref = ref.replace(", .fault(storage_fault[g])", "")
    ref = ref.replace(".consume(q_consume), ", "").replace(".consume(b_consume), ", "")
    ref = ref.replace("wire [4:0] storage_fault;", "wire [4:0] storage_fault = 5'd0;")
    # Each model builds separately, so the common fault leaf is defined once.
    (w / "reference.sv").write_text(ref)
    srcs = [p for p in sorted(PIN.rglob("*.sv")) if p.name != "ot_sram_1r1w_128x256_m1_r2c2.sv"]
    srcs += [ROOT / "physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v"]
    vroot = re.search(r"VERILATOR_ROOT\s*=\s*(\S+)", subprocess.check_output([V,"-V"], text=True))[1]
    libs = []
    for name in ("ref", "dut"):
        top = "ot_s81_pq_core_ref" if name == "ref" else "ot_s81_pq_core_native"
        files = srcs + [ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_native.sv"] + ([w / "reference.sv"] if name == "ref" else [CORE,
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_sram.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_sram.sv"])
        defs = ["+define+OT_PQ_ROM_PORTS", "+define+OT_PQ_BENCH_TELEMETRY"]
        if name == "dut" and a.bc_sliced: defs += ["+define+OT_PQ_BC_SLICED"]
        if name == "ref": defs += ["+define+OT_PQ_REFERENCE"]
        if name == "dut" and a.mut == "BC": defs += ["+define+OT_S81_PQ_BC_MUT_SLICE_K=" + str(a.bc_mut_slice)]
        if name == "dut" and a.mut:
            defs += ["+define+OT_S81_PQ_BC_MUT_SLICE" if a.mut == "BC" else "+define+OT_S81_PQ_CTL_MUT_EARLY_CONSUME" if a.mut == "CONSUME"
                     else "+define+OT_S81_PQ_" + a.mut + "_MUT_ROW"]
        md = w / name
        run([V,"--cc","-O2","-Wno-fatal","-Wno-lint","-Wno-style","--x-assign","0","--x-initial","0",
             "--prefix",f"V{name}","--top-module",top,"--Mdir",md,*defs,*files],w / f"{name}.verilate.log")
        run(["make","-C",md,"-f",f"V{name}.mk",f"-j{a.jobs}",f"V{name}__ALL.a","OPT_FAST=-O1","OPT_SLOW=-O0"],
            w / f"{name}.make.log")
        libs.append(md / f"V{name}__ALL.a")
    run(["g++","-std=c++20","-O2",f"-I{vroot}/include",f"-I{vroot}/include/vltstd",f"-I{w/'ref'}",f"-I{w/'dut'}",
         ROOT / "rtl/test/dsrom_sys/tb_s81_pq_core_native.cpp",*libs,
         f"{vroot}/include/verilated.cpp",f"{vroot}/include/verilated_threads.cpp","-pthread","-o",w / "bench"],w / "link.log")
    run([w / "bench"],w / "run.log")
    print((w / "run.log").read_text(), flush=True)


if __name__ == "__main__":
    main()
