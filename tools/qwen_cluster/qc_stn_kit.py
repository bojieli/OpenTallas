#!/usr/bin/env python3
"""Q-CLUSTER3 (2026-10-17, coordinator decision HANDOFF 0de+5): ref_tile specs of the qfd_c_b16_dv fabric STATION masters
(rtl/physical/qcluster/qfd_c_stn.sv), one hardened master per width class, replicated at the qc_gen.py stage sites:

  qfd_c_stn516  51.84 x 51.84  column-run relay / pin register (bc -> bco), 52 per cluster
  qfd_c_stn514  51.84 x 51.84  tree leg / rs exit / rs_i -> rs_o relay, 83 per cluster (MX where the word flows south)
  qfd_c_xstn    56.16 x 86.4   column station (qfd_xcst_n logic) with the 508-b tap to its A0 tile on the E face (x8);
  qfd_c_xstnw   56.16 x 86.4   the same with the tap on the W face (x8; a mirrored master would put the S / N M3 / M5 pins
                               off the track lattice, as qfd_xcst_n_my showed); tap pins on the E face at exactly the A0 tap y range (437.184..485.856 above
                               the A0 origin, xstn origin = A0 row origin + 414.72), so tap wires are straight 8.64-um stubs

Geometry (Q-CLUSTER4): stn 51.84 x 51.84, xstn 56.16 x 86.4, so every data face is >= 0.096 um/bit (516 b on 49.86 um);
the L / R strips grow 43.2 -> 86.4 to hold them (qc_gen.py).  Data in on S (flop-first), data out on N (flop-last), on
M3 + M5 alternating (pin_balance; xcst_n precedent).  ck (and rst_n / sidx) on the S face E end.  Leaf tile layer cap M5
(PG M5 stripes = pins; the cluster straps M6, cluster signals M6 / M7 over the station).  Recipe 4, hold_budget die,
pin_regs off (the RTL is one register stage: every data pin is a flop D or a flop Q).

    qc_stn_kit.py      -> tools/ref_tile/specs_qcluster/qfd_c_{stn516,stn514,xstn,xstnw}.json
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Q-CLUSTER4 (coordinator 0de+6 (3)): the data faces meet the relay pin rule <= 0.096 um/bit (<= ~10.4 pins/um over
# M3 + M5) instead of 16 pins/um: 516 b need >= 49.5 um of face -> stn 51.84 (12 x 4.32); the xstn S face also holds
# ck / rst_n / sidx -> 56.16 (13 x 4.32).  Was 34.56 for both (Q-CLUSTER3).
SW = 51.84          # stn516 / stn514 width = height
XW = 56.16          # xstn / xstnw width
XH = 86.4           # xstn height
TAP_LO, TAP_HI = 437.184 - 414.72, 485.856 - 414.72   # A0 tap range relative to the xstn origin (qc_gen XSTN_DY)
SRC_STN = ["rtl/physical/qcluster/qfd_c_stn.sv"]
SRC_X = SRC_STN + ["rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/hdc/ot_hdc_delay.sv"]
BENCH = [dict(name="qcluster_lockstep", cmd="bash tools/qwen_cluster/bench_lockstep.sh bench_out", expect="pass",
              pass_regex="LOCKSTEP_EXIT 0", threads=8, peak_ram_gb=12)]
# S-QSTN (2026-10-18): per-master behavioural bench + one-fault mutant (rtl/test/tb_qfd_c_stn.sv, qfd_c_stn_mut_tile.sv),
# with the committed pass / fail witnesses from the fleet run.
EXTRA = ["tools/qwen_cluster/bench_stn.sh", "results/arch/qwen_cluster_1017/cluster_contract_dv.json", "rtl/test/tb_qfd_c_stn.sv", "rtl/test/qfd_c_stn_mut_tile.sv",
         "rtl/qwen_sys/dvm_20261014/ot_qfd_xslice.sv", "rtl/hdc/ot_hdc_delay.sv", "results/rtl/qcluster_stn_1018"]


def stn_benches(m):
    return BENCH + [
        dict(name="stn_exact", cmd=f"bash tools/qwen_cluster/bench_stn.sh pass {m} {{RUN}}/stn_p", expect="pass",
             pass_regex=f"STN_BENCH PASS {m} 0 errors in 20000 cycles" + (" .*hold_loads=[1-9]" if "xstn" in m else ""),
             threads=4, peak_ram_gb=4, needs=["verilator"], pass_witness=f"results/rtl/qcluster_stn_1018/run_pass_{m}.log"),
        dict(name="stn_mutant", cmd=f"bash tools/qwen_cluster/bench_stn.sh mut {m} {{RUN}}/stn_m", expect="fail",
             fail_regex=f"STN_BENCH FAIL {m} [1-9]\\d* errors in 20000 cycles", threads=4, peak_ram_gb=4,
             needs=["verilator"], fail_witness=f"results/rtl/qcluster_stn_1018/run_mut_{m}.log")]
WHY = ("Q-CLUSTER3 (coordinator 0de+5): qfd_c_b16_dv 8-root gates failed the clock rule (TritonCTS 1.5-1.9 ns insertion, "
       "400-530 ps spread; spine 4.1 ns) because ~78k loose fabric flops sat at 282 stage sites over the whole cluster; "
       "the stations are hardened as small replicated tiles with their own clock pin and local tree, and the cluster "
       "clock reaches only child clock pins.")


def spec(name, w, h, pins, ranges, reset, src, purpose):
    return dict(
        name=name, top=name, kind="tile", sources=src, params={}, clock_port="ck", reset_ports=reset,
        outline=dict(w=w, h=h, exact=True), layer_cap="M5", pins=pins, pin_ranges=ranges,
        route=dict(pd=0.5, threads=8, peak_ram_gb=16, pin_h="M4", pin_v="M5", hold_margin_ns=0.03, macro_halo_um=5.4,
                   pin_balance=dict(group_max=1, h="M4", v="M3 M5"), io_hold_margin_ns=0.0),
        macros=[], children=[], inter=[], recipe=4, io_flop_at_pins=False, hold_budget="die", inhold=False, outhold=False,
        pin_regs=dict(enable=False, reason="the RTL is one register stage: every data input pin drives a flop D "
                                           "(flop-first) and every data output pin is a flop Q (flop-last)"),
        structural_change=WHY,
        job=dict(owner="Claude:S-QSTN", branch="claude/qstn-1018", tag="s0", purpose=purpose, submit=False,
                 benches=stn_benches(name), extra_paths=EXTRA))


def main():
    out = ROOT / "tools/ref_tile/specs_qcluster"
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for w_ in (516, 514):
        n = f"qfd_c_stn{w_}"
        rows.append(spec(n, SW, SW, {"S": ["d", "ck"], "N": ["q"]},
                         {"d": [0.54, 50.4], "ck": [50.94, 51.24], "q": [0.54, 51.3]}, [], SRC_STN,
                         f"qfd_c_b16_dv fabric station: one {w_}-b register stage (x{52 if w_ == 516 else 83} per cluster)"))
    rows.append(spec("qfd_c_xstn", XW, XH, {"S": ["b_d", "ck", "rst_n", "sidx"], "N": ["a_d"], "E": ["tap_d"]},
                     {"b_d": [0.54, 50.4], "ck": [51.0, 51.3], "rst_n": [51.66, 51.96], "sidx": [52.32, 53.16],
                      "a_d": [0.54, 55.62], "tap_d": [round(TAP_LO, 3), round(TAP_HI, 3)]}, ["rst_n"], SRC_X,
                     "qfd_c_b16_dv column station (qfd_xcst_n logic), tap on the E face (columns 0 / 2; x8 per cluster)"))
    rows.append(spec("qfd_c_xstnw", XW, XH, {"S": ["b_d", "ck", "rst_n", "sidx"], "N": ["a_d"], "W": ["tap_d"]},
                     {"b_d": [5.76, 55.62], "ck": [2.4, 2.7], "rst_n": [1.74, 2.04], "sidx": [0.54, 1.38],
                      "a_d": [0.54, 55.62], "tap_d": [round(TAP_LO, 3), round(TAP_HI, 3)]}, ["rst_n"], SRC_X,
                     "qfd_c_b16_dv column station, tap on the W face (columns 1 / 3; x8 per cluster)"))
    for s in rows:
        p = out / f"{s['name']}.json"
        p.write_text(json.dumps(s, indent=1) + "\n")
        print(p)


if __name__ == "__main__":
    main()
