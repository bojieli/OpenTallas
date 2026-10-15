#!/usr/bin/env python3
"""Production core lockstep vs the original parameterized flop buffer tiles.

The native DUT contains actual macro models; count is profile-dependent.
The fully split canonical profile has44 SRAMs (8AQ+4QB+32IX). The reference substitutes
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
    ap.add_argument("--mut", choices=["IX", "QB", "CONSUME", "BC", "AQPIN", "AQPAR", "AQMEM", "AQMAX", "QBBANK", "QBHEAD", "QBPRE", "FAULT", "QBX", "QBW", "WV"])
    ap.add_argument("--aq-pin", action="store_true")
    ap.add_argument("--aq-split", action="store_true")
    ap.add_argument("--qb-split", action="store_true")
    ap.add_argument("--qb-mut-bank", type=int, choices=range(4), default=0)
    ap.add_argument("--qb-pipe", action="store_true", help="opt-in QB +2 physical pipeline; independent feedback timing comparison")
    ap.add_argument("--qb-one", action="store_true", help="QB with ONE bank master placed four times (ot_s81_pq_qb_one_native.sv)")
    ap.add_argument("--ix-pins", action="store_true")
    ap.add_argument("--ix-split", action="store_true")
    ap.add_argument("--ix-bank-split", action="store_true")
    ap.add_argument("--aq-parity", action="store_true")
    ap.add_argument("--ctl-fixed", action="store_true")
    ap.add_argument("--bc-sliced", action="store_true")
    ap.add_argument("--bc-mut-slice", type=int, choices=range(4), default=0)
    a = ap.parse_args(); a.ix_split = a.ix_split or a.ix_bank_split; w = a.work.resolve(); w.mkdir(parents=True, exist_ok=True)
    if a.qb_pipe: a.qb_split=True
    src = CORE.read_text()
    ref = src.replace("module ot_s81_pq_core_native", "module ot_s81_pq_core_ref", 1)
    ref = ref.replace("ot_s81_pq_qb_sram u_qb", "ot_v41_pqc_qb #(.KMAX(6144)) u_qb")
    ref = ref.replace(",\n        .fault(storage_fault[4])", "")
    ref = ref.replace("ot_s81_pq_ix_sram u_ix", "ot_v41_pqc_ix #(.KMAX(6144), .VRD(64)) u_ix")
    # the reference IX (pinned ot_v41_pqc_ix) still compares its parity: give it the tie it was built with
    ref = ref.replace(".ba_wv(ba_wv[g >= 2])", ".par(g >= 2), .ba_v(ba_v)")
    ref = ref.replace(", .fault(storage_fault[g])", "")
    ref = ref.replace(".consume(q_consume), ", "").replace(".consume(b_consume), ", "").replace(".consume(b_consume),\n", "\n")
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
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_pin_variants.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ix_split_native.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_aq_split_native.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_sram.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_split_native.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_one_native.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pipe_native.sv",
            ROOT / "rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_ctl_fixed_native.sv"])
        defs = ["+define+OT_PQ_ROM_PORTS", "+define+OT_PQ_BENCH_TELEMETRY"]
        if name == "dut" and a.aq_pin: defs += ["+define+OT_PQ_AQ_PIN_LAUNCH"]
        if name == "dut" and a.aq_parity: defs += ["+define+OT_PQ_AQ_SIDE_PARITY"]
        if name == "dut" and a.ix_split: defs += ["+define+OT_PQ_IX_PHYS_SPLIT"]
        if name == "dut" and a.ix_bank_split: defs += ["+define+OT_PQ_IX_BANK_SPLIT"]
        if name == "dut" and a.aq_split: defs += ["+define+OT_PQ_AQ_PHYS_SPLIT"]
        if name == "dut" and a.qb_split: defs += ["+define+OT_PQ_QB_PHYS_SPLIT"]
        if name == "dut" and a.qb_pipe: defs += ["+define+OT_PQ_QB_PIPE"]
        if name == "dut" and a.qb_one: defs += ["+define+OT_PQ_QB_ONE_BANK"]
        if name == "dut" and a.ix_pins: defs += ["+define+OT_PQ_IX_PIN_VARIANTS"]
        if name == "dut" and a.ctl_fixed: defs += ["+define+OT_PQ_CTL_FIXED"]
        if name == "dut" and a.bc_sliced: defs += ["+define+OT_PQ_BC_SLICED"]
        if name == "ref": defs += ["+define+OT_PQ_REFERENCE"]
        if name == "dut" and a.mut == "BC": defs += ["+define+OT_S81_PQ_BC_MUT_SLICE_K=" + str(a.bc_mut_slice)]
        if name == "dut" and a.mut == "QBBANK": defs += ["+define+OT_S81_PQ_QB_BANK_MUT_K=" + str(a.qb_mut_bank)]
        if name == "dut" and a.mut:
            defs += ["+define+OT_S81_PQ_FAULT_MUT" if a.mut == "FAULT" else "+define+OT_S81_PQ_QB_HEAD_MUT" if a.mut == "QBHEAD" else "+define+OT_S81_PQ_QB_BANK_MUT_ACTIVE" if a.mut == "QBBANK" else "+define+OT_AQ12T_MUT_RA" if a.mut == "AQMEM" else "+define+OT_AQ12M_MUT_SEL" if a.mut == "AQMAX" else "+define+OT_PQ_AQ_PARITY_MUT" if a.mut == "AQPAR" else "+define+OT_PQ_AQ_PIN_MUT_DELAY" if a.mut == "AQPIN" else "+define+OT_S81_PQ_BC_MUT_SLICE" if a.mut == "BC" else "+define+OT_S81_PQ_CTL_MUT_EARLY_CONSUME" if a.mut == "CONSUME" else "+define+OT_S81_PQ_QBX_MUT_ROW" if a.mut == "QBX" else "+define+OT_S81_PQ_QBW_MUT_BANK" if a.mut == "QBW"
                     else "+define+OT_S81_PQ_" + a.mut + "_MUT_ROW"]
        md = w / name
        run([V,"--cc","-O2","-Wno-fatal","-Wno-lint","-Wno-style","--x-assign","0","--x-initial","0",
             "--prefix",f"V{name}","--top-module",top,"--Mdir",md,*defs,*files],w / f"{name}.verilate.log")
        run(["make","-C",md,"-f",f"V{name}.mk",f"-j{a.jobs}",f"V{name}__ALL.a","OPT_FAST=-O1","OPT_SLOW=-O0"],
            w / f"{name}.make.log")
        libs.append(md / f"V{name}__ALL.a")
    run(["g++","-std=c++20","-O2",f"-I{vroot}/include",f"-I{vroot}/include/vltstd",f"-I{w/'ref'}",f"-I{w/'dut'}",
         ROOT / ("rtl/test/dsrom_sys/tb_s81_pq_core_pipe.cpp" if a.qb_pipe else "rtl/test/dsrom_sys/tb_s81_pq_core_native.cpp"),*libs,
         f"{vroot}/include/verilated.cpp",f"{vroot}/include/verilated_threads.cpp","-pthread","-o",w / "bench"],w / "link.log")
    run([w / "bench"],w / "run.log")
    print((w / "run.log").read_text(), flush=True)


if __name__ == "__main__":
    main()
