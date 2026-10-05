#!/usr/bin/env python3
"""Route the Qwen slab port group with the S1-S4 structural fix (handoff qwen_slab_structural_claude_to_codex_ampere.md).

S1: boundary delays re-referenced to the block's propagated tree after CTS (physical/qwen_slab_structural hooks,
    io_wc.sdc in the flow, io_lat.sdc per corner at sign-off; setup max 0.2 T, hold min 0 -- nothing relaxed).
    io_ref.sdc (-reference_pin) is not used: OpenSTA drops every input-port path under it and GRT crashes.
S2: BW_FIFO=0 -- the block-word meso FIFO is its own closed element (meso_d4_v7), not routed here.
S3: per-lane multiplier tag copies (already in rtl/physical/ot_qwen_slab_port_group.sv).
S4: res_in / outputs / control on the right (spine) face in separate ranges; bw_/tw_ parked on the left face.

    python3 tools/qwen_slab_structural_run.py --height 455.76 --mul-lat 6 [--diamond] [--td-only] \
        --root /srv/.../qwen-slab-route --name qssr_a --cores 20
Signoff: tools/w18/corner_sta.py with --post-sdc io_lat.sdc (SS 60 ps setup, FF 25 ps hold).
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import qwen_slab_share as share  # noqa: E402

S = "physical/qwen_slab_structural"
SOURCES = ["rtl/physical/ot_qwen_slab_port_group.sv", "rtl/common/ot_meso_fifo.sv", "rtl/hdc/ot_hdc_delay.sv",
           "rtl/hdc/ot_hdc_fp32_mul_lat.sv", "rtl/hdc/ot_hdc_fp32_add_lat.sv", "rtl/hdc/ot_hdc_fastfp.sv",
           "rtl/hdc/ot_hdc_prefix.sv", "physical/asap7_memory_macros/ot_rom_4096x266_m8/ot_rom_4096x266_m8_bb.v"]
MACRO = "physical/asap7_memory_macros/ot_rom_4096x266_m8"


def pins(h):
    """S4 pin ranges, given at H = 455.76 in the handoff and scaled with H on the 2.16 um lattice."""
    k = h / 455.76
    r = lambda lo, hi: f"{share.snap(lo * k):g}-{share.snap(hi * k):g}"  # noqa: E731
    return ["--pin-region", f"^res_in=right:{r(2.16, 150)}",
            "--pin-region", f"^(o_|ov$|am_|fault$)=right:{r(306, 453)}",
            "--pin-region", f"^(p_|rst_n$|clk$)=right:{r(160, 296)}",
            "--pin-region", "^(bw_|tw_)=left"]


def command(a, out):
    h = share.snap(a.height)
    argv = [sys.executable, "tools/run_abi3_physical_persistent.py",
            "--persistent-workdir", str(out / "work"), "--launch-receipt", str(out / "launch.json"),
            "--view", "asap7", "--top", "ot_qwen_slab_port_group"]
    for s in SOURCES:
        argv += ["--source", s]
    argv += ["--param", f"MUL_LAT={a.mul_lat}", "--param", "BW_FIFO=0",
             *[x for kv in a.param for x in ("--param", kv)],
             "--macro-view", f"ot_rom_4096x266_m8={MACRO}", "--macro-place-halo", "2.16", "2.16",
             "--die-area", "0", "0", f"{share.W}", f"{h:g}",
             "--core-area", f"{share.EDGE}", f"{share.EDGE}", f"{share.W - share.EDGE:.3f}", f"{h - share.EDGE:.3f}",
             *pins(h), "--routing-layers", "M2", "M7",
             "--clock-port", "clk", "--clock-period-ns", "0.833333", "--clock-uncertainty-ns", "0.06",
             "--clock-uncertainty-hold-ns", "0.025", "--orfs-corner", "WC", "--hold-corners", "WC,BC",
             "--io-delay-fraction", "0.2", "--stages", "pnr", "--hold-margin-ns", f"{a.hold_margin_ns:g}",
             "--synth-timeout-seconds", "unlimited", "--flow-timeout-seconds", "unlimited",
             "--orfs-var", "ADDER_MAP_FILE=", "--orfs-var", f"NUM_CORES={a.cores}",
             "--orfs-var", f"SDC_FILE=/src/{S}/port_group_s2.sdc", "--orfs-var", f"QSS_SDC_DIR=/src/{S}",
             "--orfs-var", f"QSS_IO_HOLD_EXTRA={a.io_hold_extra:g}",
             "--orfs-var", "PDN_TCL=/src/physical/qwen_slab_m5/pdn_m5.tcl",
             "--orfs-var", f"MACRO_PLACEMENT_TCL=/src/physical/qwen_slab_share/macro_place_h{h:g}.tcl",
             "--orfs-var", "GLOBAL_ROUTE_ARGS=-congestion_report_iter_step 5 -verbose -critical_nets_percentage 0",
             "--step-tcl", f"PRE_CTS={S}/pre_cts.tcl", "--step-tcl", f"POST_CTS={S}/post_plain.tcl"]
    for st in ("GLOBAL_ROUTE", "DETAIL_ROUTE", "FILLCELL"):
        argv += ["--step-tcl", f"PRE_{st}={S}/pre_ref.tcl", "--step-tcl", f"POST_{st}={S}/post_plain.tcl"]
    if a.diamond:
        argv += ["--orfs-var", "DETAIL_PLACEMENT_ARGS=-use_diamond_legalizer"]
    if a.cts_derate is not None:
        # obstruction-blind H-tree (measured on r2a's placement: SS -77 vs -78 ps, multiplier stage -8 vs -78) and
        # a macro-branch delay-buffer derate: the ROM clock leads the capture flops (clk->q 754 ps of 833 at SS)
        argv += ["--orfs-var", "CTS_ARGS=-sink_clustering_enable -repair_clock_nets -no_obstruction_aware "
                 f"-delay_buffer_derate {a.cts_derate:g}"]
    if a.td_only:
        argv += ["--orfs-var", "GPL_ROUTABILITY_DRIVEN=0"]
    for kv in a.orfs_var:
        argv += ["--orfs-var", kv]
    argv += ["--nickname-tag", a.name, "--purpose", "signoff_target", "--output", str(out / "physical.json")]
    return argv


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--height", type=float, required=True)
    p.add_argument("--mul-lat", type=int, choices=(6, 7), default=6)
    p.add_argument("--diamond", action="store_true")
    p.add_argument("--td-only", action="store_true")
    p.add_argument("--orfs-var", action="append", default=[])
    p.add_argument("--hold-margin-ns", type=float, default=0.01, help="ORFS hold repair margin (flow only, stricter)")
    p.add_argument("--cts-derate", type=float, default=None,
                   help="tuned CTS: -no_obstruction_aware and -delay_buffer_derate D (macro clock leads)")
    p.add_argument("--param", action="append", default=[], help="extra RTL parameter NAME=VALUE (IN_STAGE, AM_SPLIT, S5_CTL)")
    p.add_argument("--io-hold-extra", type=float, default=60.0,
                   help="flow-only extra boundary hold requirement, ps (io_wc.sdc; stricter only)")
    p.add_argument("--cores", type=int, default=20)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--name", required=True)
    a = p.parse_args()
    os.chdir(ROOT)
    commit = (ROOT / "SOURCE_COMMIT").read_text().strip()
    out = a.root / a.name
    out.mkdir(parents=True, exist_ok=False)
    argv = command(a, out)
    (out / "recipe.json").write_text(json.dumps(dict(source_commit=commit, args=vars(a) | {"root": str(a.root)},
                                                     argv=argv), indent=2) + "\n")
    env = os.environ.copy()
    env.update(OT_ORFS_NUM_CORES=str(a.cores), NUM_CORES=str(a.cores),
               OT_SYNTH_TIMEOUT_SECONDS="unlimited", OT_FLOW_TIMEOUT_SECONDS="unlimited")
    with (out / "driver.log").open("w") as log:
        rc = subprocess.run(argv, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    (out / "driver.exit").write_text(f"{rc}\n")
    if list((out / "work/orfs/results/asap7").glob("*/base/6_final.odb")):
        with (out / "corner.log").open("w") as log:
            c = subprocess.run([sys.executable, "tools/w18/corner_sta.py", "--orfs-dir", str(out / "work/orfs"),
                                "--macro", MACRO, "--post-sdc", f"{S}/io_lat.sdc",
                                "--output", str(out / "corner_sta.json")], env=env, stdout=log, stderr=subprocess.STDOUT)
        (out / "corner.exit").write_text(f"{c.returncode}\n")
    return rc


if __name__ == "__main__":
    sys.exit(main())
