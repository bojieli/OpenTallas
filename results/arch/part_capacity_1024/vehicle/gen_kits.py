#!/usr/bin/env python3
"""PART-CAP 2026-10-24: write ref_route.sh kits for the N x ot_qkh_lane8 capacity vehicle.

Every kit is identical except N and the outline: outline area = N x the closed lane8 tile (129.6 x 129.6 um, same
std-cell density), square, snapped up to the 2.16-um lattice; routing M2-M7 (partition layers, die M8/M9 above);
PG = the closed tile's M1/M2 rails + M5 stripes; route SDC 770 ps / 60 / 25 ps, sign-off 833.333 ps (the lane8 kit's
clock.sdc / signoff.sdc and hooks, unchanged).  NC = threads given to OpenROAD (NUM_CORES).
usage: gen_kits.py N [N ...] [--nc 48] [--suffix _t16]"""
import argparse, math, pathlib, shutil

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LANE8 = ROOT / "physical/ref_tile/ot_qkh_lane8_m5"
TILE = 129.6
SRCS = ("rtl/lib/ot_rst_relay.sv rtl/hdc/nearhbm/ot_qkh_subtiles.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv "
        "rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv "
        "rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv "
        "physical/ref_tile/ot_qkh_lane8_m5/src/rtl/hdc/ot_hdc_fastfp.sv "
        "results/arch/part_capacity_1024/vehicle/ot_pc_rep.sv")


def outline(n):
    side = TILE * math.sqrt(n)
    return round(math.ceil(side / 2.16 - 1e-9) * 2.16, 2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, nargs="+")
    ap.add_argument("--nc", type=int, default=48)
    ap.add_argument("--suffix", default="", help="kit name suffix (e.g. _t16 for a thread-count variant)")
    a = ap.parse_args()
    for n in a.n:
        name = f"pc_rep_n{n}{a.suffix}"
        kit = HERE.parent / "kits" / name
        kit.mkdir(parents=True, exist_ok=True)
        for f in ("clock.sdc", "signoff.sdc", "pre_cts.tcl", "pre_grt.tcl", "post_drt.tcl", "pdn.tcl"):
            shutil.copyfile(LANE8 / f, kit / f)
        w = outline(n)
        rel = kit.relative_to(ROOT)
        (kit / "kit.env").write_text(f"""# PART-CAP vehicle kit (results/arch/part_capacity_1024/vehicle/gen_kits.py): {n} x ot_qkh_lane8
TOP=ot_pc_rep
SRCS='{SRCS}'
PARAMS=(--param N={n})
FW={w}
FH={w}
PINS=(--pin-region '^(bsel|c_in|e_in|hid|lt_in|q_beat_in|q_data_in|q_valid_in|row_in)(\\[|$)=bottom' --pin-region '^(clk|rst_n)(\\[|$)=left' --pin-region '^(gf|kp|kpv|nb)(\\[|$)=right')
PINEX=1
INTER='none_*'
REFGLOB='*'
CLKPORT=clk
PD=0.6
NC={a.nc}
PIN_H='M4'
PIN_V='M5'
PIN_MIN_TRACKS=2
STAGES=pnr
RLAYERS='M2 M7'
ROUTE_PERIOD_NS=0.77
KIT=/src/{rel}
MACROS=()
EXTRA=(--orfs-var ADDER_MAP_FILE= --orfs-var PDN_TCL=/src/{rel}/pdn.tcl --orfs-var OT_PK_FRAC=0.5 --orfs-var OT_PK_ABOVE_ONLY=1 --orfs-var PLACE_DENSITY_LB_ADDON=)
""")
        print(name, w, "um", f"NC={a.nc}")


if __name__ == "__main__":
    main()
