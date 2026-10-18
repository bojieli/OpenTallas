#!/usr/bin/env python3
"""Q-CLUSTER3 (2026-10-17, coordinator decision HANDOFF 0de+5): ref_tile specs of the qfd_c_b16_dv fabric STATION masters
(rtl/physical/qcluster/qfd_c_stn.sv), one hardened master per width class, replicated at the qc_gen.py stage sites:

  qfd_c_stn516  34.56 x 34.56  column-run relay / pin register (bc -> bco), 52 per cluster
  qfd_c_stn514  34.56 x 34.56  tree leg / rs exit / rs_i -> rs_o relay, 83 per cluster (MX where the word flows south)
  qfd_c_xstn    34.56 x 86.4   column station (qfd_xcst_n logic) with the 508-b tap to its A0 tile on the E face (x8);
  qfd_c_xstnw   34.56 x 86.4   the same with the tap on the W face (x8; a mirrored master would put the S / N M3 / M5 pins
                               off the track lattice, as qfd_xcst_n_my showed); tap pins on the E face at exactly the A0 tap y range (437.184..485.856 above
                               the A0 origin, xstn origin = A0 row origin + 414.72), so tap wires are straight 8.64-um stubs

Geometry: 34.56 = 4 x 8.64, so every station keeps an 8.64-um channel to the A0 faces it faces (the L / R strips are 43.2
wide and the A0 W / E faces carry their clock / data pins).  Data in on S (flop-first), data out on N (flop-last), on
M3 + M5 alternating (pin_balance; xcst_n precedent).  ck (and rst_n / sidx) on the S face E end.  Leaf tile layer cap M5
(PG M5 stripes = pins; the cluster straps M6, cluster signals M6 / M7 over the station).  Recipe 4, hold_budget die,
pin_regs off (the RTL is one register stage: every data pin is a flop D or a flop Q).

    qc_stn_kit.py      -> tools/ref_tile/specs_qcluster/qfd_c_{stn516,stn514,xstn,xstnw}.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SW = 34.56          # station width (4 x 8.64)
XH = 86.4           # xstn height
TAP_LO, TAP_HI = 437.184 - 414.72, 485.856 - 414.72   # A0 tap range relative to the xstn origin (qc_gen XSTN_DY)
SRC_STN = ["rtl/physical/qcluster/qfd_c_stn.sv"]
SRC_X = SRC_STN + ["rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/hdc/ot_hdc_delay.sv"]
BENCH = [dict(name="qcluster_lockstep", cmd="bash tools/qwen_cluster/bench_lockstep.sh bench_out", expect="pass",
              pass_regex="LOCKSTEP_EXIT 0", threads=8, peak_ram_gb=12)]
WHY = ("Q-CLUSTER3 (coordinator 0de+5): qfd_c_b16_dv 8-root gates failed the clock rule (TritonCTS 1.5-1.9 ns insertion, "
       "400-530 ps spread; spine 4.1 ns) because ~78k loose fabric flops sat at 282 stage sites over the whole cluster; "
       "the stations are hardened as small replicated tiles with their own clock pin and local tree, and the cluster "
       "clock reaches only child clock pins.")


def spec(name, w, h, pins, ranges, reset, src, purpose):
    return dict(
        name=name, top=name, kind="tile", sources=src, params={}, clock_port="ck", reset_ports=reset,
        outline=dict(w=w, h=h, exact=True), layer_cap="M5", pins=pins, pin_ranges=ranges,
        route=dict(pd=0.5, threads=8, peak_ram_gb=16, pin_h="M4", pin_v="M5", hold_margin_ns=0.03, macro_halo_um=5.4,
                   pin_balance=dict(group_max=1, h="M4", v="M3 M5")),
        macros=[], children=[], inter=[], recipe=4, io_flop_at_pins=False, hold_budget="die", inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="the RTL is one register stage: every data input pin drives a flop D "
                                           "(flop-first) and every data output pin is a flop Q (flop-last)"),
        structural_change=WHY,
        job=dict(owner="Claude:Q-CLUSTER3", branch="claude/qcluster-1017", tag="s0", purpose=purpose, submit=False,
                 benches=BENCH))


def main():
    out = ROOT / "tools/ref_tile/specs_qcluster"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for w_ in (516, 514):
        n = f"qfd_c_stn{w_}"
        rows.append(spec(n, SW, SW, {"S": ["d", "ck"], "N": ["q"]},
                         {"d": [0.54, 32.4], "ck": [33.12, 33.42], "q": [0.54, 34.02]}, [], SRC_STN,
                         f"qfd_c_b16_dv fabric station: one {w_}-b register stage (x{52 if w_ == 516 else 83} per cluster)"))
    rows.append(spec("qfd_c_xstn", SW, XH, {"S": ["b_d", "ck", "rst_n", "sidx"], "N": ["a_d"], "E": ["tap_d"]},
                     {"b_d": [0.54, 31.32], "ck": [31.86, 32.16], "rst_n": [32.52, 32.82], "sidx": [33.18, 34.02],
                      "a_d": [0.54, 34.02], "tap_d": [round(TAP_LO, 3), round(TAP_HI, 3)]}, ["rst_n"], SRC_X,
                     "qfd_c_b16_dv column station (qfd_xcst_n logic), tap on the E face (columns 0 / 2; x8 per cluster)"))
    rows.append(spec("qfd_c_xstnw", SW, XH, {"S": ["b_d", "ck", "rst_n", "sidx"], "N": ["a_d"], "W": ["tap_d"]},
                     {"b_d": [3.24, 34.02], "ck": [2.4, 2.7], "rst_n": [1.74, 2.04], "sidx": [0.54, 1.38],
                      "a_d": [0.54, 34.02], "tap_d": [round(TAP_LO, 3), round(TAP_HI, 3)]}, ["rst_n"], SRC_X,
                     "qfd_c_b16_dv column station, tap on the W face (columns 1 / 3; x8 per cluster)"))
    for s in rows:
        p = out / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print(p)


if __name__ == "__main__":
    main()
