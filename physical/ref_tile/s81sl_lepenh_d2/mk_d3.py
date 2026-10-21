#!/usr/bin/env python3
"""DRIVE-S81-LEPENH 10-20: build the d3a / d3b DIAGNOSTIC stand-in parent kits of dsdv_slice_lepe_nh from d2.

d2b gate facts (ep7 run s81sl_lepenh_d2-20261020-050811, CTS stage):
  * all 16.6k parent flops sit in the 129.6-um slice|lep channel (x 1298..1500, y 2402..3322) -- the textbook_lint
    "10k flops over 2458 x 5784" warning is outline-based, NOT the placement;
  * exactly 3 flops are elsewhere: u_lpr_root (rst_n pin, E face y 2402), u_lpo_fault.q (fault pin, E face y 3322),
    u_lpo_fault r[0] (x 1976): the CTS sink boxes became 1150 x 700 um (ck_S_regs / ck_K_regs), path depth 20-23,
    avg sink wire 1.4-1.5 mm, TT insertion 1141..1941 (S) / 1094..2339 (K) -> 800 ps spread;
  * the channel was over-dense (density map red), 111k hold buffers (20k endpoints in margin), GRT congested
    (2nd round of 30 extra iterations after 12 h).
d3 structural changes (both variants):
  1. lep_nh stand-in at the REAL r5a size 475.2 x 561.6 (s81sl_lepnhwd_r5a, mirrored for the E end: ro/ri face W);
  2. channel 129.6 -> 172.8 um (lep x 1468.8, lep|lane gap 86.4 -> 43.2), lep y 2592 (centre kept);
  3. slice ro_e / ri_e re-ranged bit-aligned to the taller lep window; slice rst_n/clk/fault below them;
  4. lep sl_f on the S face at the channel corner, lep fault at the S-E corner; parent fault pin moved to the E face
     just below lane 0 (y 2500), rst_n beside ck_S, so the E-face flops sit as close to the channel as the faces allow.
  d3a: rst_n / fault port flops NOT anchored at their pins (OT_OFLOP_PORT_RE matches no port) -> the reset root and
       fault out_regs place with their loads, the CTS boxes stay on the channel; PD 0.45.
  d3b: d2 anchoring kept, TritonCTS recipe 24 sinks / 30 um / 15-um buffers / -balance_levels (dsfd_vm_direct_scatter
       cb3, LEPNH r5b) -- the clock-only fallback.
"""
import copy, json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
D2 = ROOT / "physical/ref_tile/s81sl_lepenh_d2"

LEP_X, LEP_Y, LEP_W, LEP_H = 1468.8, 2592.0, 475.2, 561.6
SL_Y = 43.2
INS = {"ot_s81sl_slice": "250,200,330", "ot_s81sl_lep_nh": "220,170,290", "dsfd_coll_lane_e": "419,347,537"}


def lep_standin():
    s = json.load(open(D2 / "standin/lep_nh.json"))
    s["outline"] = {"w": LEP_W, "h": LEP_H}
    # r5a (s81sl_lepnhwd_r5a): native W = lanes + clk/rst_n (272.8-288.8), E = ro, ri, S = sl_f, fault.  E end = MY.
    s["pins"] = {"W": ["ro", "ri"],
                 "E": ["lo0_v", "lo0_r", "lo0_d", "li0_v", "li0_r", "li0_d", "lo1_v", "lo1_r", "lo1_d",
                       "li1_v", "li1_r", "li1_d", "rxv", "l0_f", "l1_f", "clk", "rst_n"],
                 "S": ["sl_f", "fault"]}
    s["pin_ranges"] = {"ro": [4.0, 280.0], "ri": [282.0, 557.6], "clk": [272.8, 280.8], "rst_n": [280.8, 288.8],
                       "sl_f": [3.0, 10.0], "fault": [455.0, 472.0]}
    s["_note"] = ("DRIVE-S81-LEPENH d3 stand-in (DIAGNOSTIC, STANDIN_NOT_A_VIEW) at the real r5a outline 475.2 x 561.6, "
                  "drawn in the E-end (MY) orientation. Pin REQUEST for the real E-end lep_nh view: ro W 4-280, ri W 282-557.6 "
                  "(bit i meets slice ro_e/ri_e bit i across the 172.8-um landing channel), sl_f on S at the channel corner, "
                  "fault on S at the lane corner, clk/rst_n on the lane face as r5a.")
    return s


def slice_standin():
    s = json.load(open(D2 / "standin/slice.json"))
    off = LEP_Y - SL_Y          # slice-local y of the lep bottom
    pr = s["pin_ranges"]
    pr["ro_e"] = [round(off + 4.0, 3), round(off + 280.0, 3)]
    pr["ri_e"] = [round(off + 282.0, 3), round(off + 557.6, 3)]
    pr["rst_n"] = [off - 52.0, off - 48.0]
    pr["clk"] = [off - 44.0, off - 32.0]
    pr["fault"] = [off - 28.0, off - 24.0]
    s["_note"] = ("DRIVE-S81-LEPENH d3 stand-in (DIAGNOSTIC): PL-SLICE pin REQUEST, E face ro_e/ri_e bit-aligned with the "
                  "d3 lep_nh window (lep y 2592), rst_n/clk/fault just below it.")
    return s


def build(name, variant):
    kd = ROOT / "physical/ref_tile" / name
    (kd / "standin").mkdir(parents=True, exist_ok=True)
    stand = {"lep_nh.json": lep_standin(), "slice.json": slice_standin(),
             "lane_e.json": json.load(open(D2 / "standin/lane_e.json"))}
    for f, s in stand.items():
        json.dump(s, open(kd / "standin" / f, "w"), indent=1)
    views = {}
    for f, master in (("slice.json", "ot_s81sl_slice"), ("lep_nh.json", "ot_s81sl_lep_nh"), ("lane_e.json", "dsfd_coll_lane_e")):
        out = kd / "standin_views" / master
        subprocess.run([sys.executable, str(ROOT / "tools/qwen_dv/slice_standin.py"), "--ins", INS[master], "--master", master,
                        str(kd / "standin" / f), str(out.parent)], check=True, cwd=ROOT)
        views[master] = str(out.relative_to(ROOT))
    s = json.load(open(D2 / "spec.json"))
    s["name"] = name
    s["sources"] = [x.replace("s81sl_lepenh_d2/standin_views", f"{name}/standin_views") for x in s["sources"]]
    at = {"u_sl": [43.2, SL_Y], "u_lep": [LEP_X, LEP_Y], "u_ln0": [1987.2, 2548.8], "u_ln1": [1987.2, 2937.6]}
    for c in s["children"]:
        c["view"] = c["view"].replace("s81sl_lepenh_d2/", f"{name}/")
        c["at"] = at[c["inst"]]
    pr = s["pin_ranges"]
    pr["rst_n"] = [2436.0, 2440.0]
    pr["ck_S"] = [2444.0, 2456.0]
    pr["fault"] = [2500.0, 2504.0]
    s["route"]["peak_ram_gb"] = 128
    if variant == "a":
        s["route"]["pd"] = 0.45
        s.setdefault("orfs_vars", {})["OT_OFLOP_PORT_RE"] = "ot_no_port_anchor_x"
        s["io_flop_at_pins"] = dict(s["io_flop_at_pins"], allow_none=True)
    else:
        s["route"]["cts_sink"] = {"size": 24, "diameter_um": 30, "extra": "-distance_between_buffers 15 -balance_levels"}
    s["structural_change"] = (f"DRIVE-S81-LEPENH 10-20 {name} DIAGNOSTIC stand-in parent (never bindable), successor of "
                              "s81sl_lepenh_d2 (d2b CTS: all parent flops in the 129.6-um channel but 3 E-face port flops "
                              "stretched both CTS boxes to 1150x700 um, depth 20-23, TT spread 800 ps; channel over-dense, 111k "
                              "hold buffers, GRT congested). See mk_d3.py: real-size lep_nh (475.2x561.6), channel 172.8, "
                              "re-ranged line ports, fault/rst_n pins moved toward the channel; "
                              + ("d3a: port flops unanchored (place with their loads), PD 0.45."
                                 if variant == "a" else "d3b: anchors kept, CTS 24 sinks/30 um/15-um buffers/-balance_levels."))
    j = s["job"]
    j["owner"] = "Claude:DRIVE-S81-LEPENH"
    j["branch"] = "claude/s81-lepenh3-1020"
    j["tag"] = name.split("_")[-1]
    j["views_to"] = f"physical/ref_tile/{name}/views"
    j["record_to"] = f"results/rtl/ref_tile/{name}"
    sp = kd / "spec.json"
    json.dump(s, open(sp, "w"), indent=1)
    subprocess.run([sys.executable, str(ROOT / "tools/ref_tile/ref_tile.py"), "gen", str(sp.relative_to(ROOT))], check=True, cwd=ROOT)


if __name__ == "__main__":
    build("s81sl_lepenh_d3a", "a")
    build("s81sl_lepenh_d3b", "b")
