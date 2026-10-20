#!/usr/bin/env python3
"""S81-TILES-E (10-20) COLL lane kits dscoll_lane_{w,e}_s7 (TritonCTS) / _s7k (k-means regional CTS, K=16):
structural successor of s6c (S81.STA.LKTO.2).

s6c terminal: W clock_rule FAIL (TT pin-flop spread 83.9 ps, one 16,342-sink root); E gate WARN but the actual GRT
native reach audit (Codex 08:13, codex/s81-terminal-collect-1020 coll6_e) FAILS: 5,403 sequential pairs > 405 um,
max 756.8 um.  Classes: 5,108 = receive control (u_ep c_diff / c_crc_ok / xp_v) placed beside the gearbox at the
link face -> the 18 RX FIFO address groups (count_r / wp_r / valid_r) beside the RX FIFO banks at the core face
(~520-650 um, one cycle); 194 = rx pin / lr_f landing -> gearbox; 150 = lo_d pin -> credit-rx landing d_q; 51 misc.
The macro map is right (s6c: FIFO at the core face for the q -> li path); the RTL had no forwarded hop on the
link-face -> core-face direction, so the placer had to stretch one single-cycle cone across the tile.

s7 = RTL top dsfd_coll_lane_{w,e}_safe7 (ot_s81ph_coll_lane_safe4 REACH = 1): rx landing 2 stages, RX_STAGES 3 -> 5
(two forwarded frame hops; receive control sits beside the FIFO), reverse ACK frame relay 2 stages back to the
gearbox, core landing lo_v/lo_d +1 stage at the core face.  Same outline, macro map, pins, PDN, layer contract as s6c.
s7k adds the k-means regional clock split (physical/common_flow/clock_split_km.tcl, K=16) against the 83.9 ps W
spread (parallel route, owner 10-19: bind the first that closes).
"""
import copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BR = "claude/s81-coll7-1020"
BENCH = "results/rtl/s81_coll_native32_1020/reach7/bench"


def bench(m, expect, regex_fail=None):
    b = {"name": f"lane_reach7_m{m}",
         "cmd": f"OT_COLL_NATIVE32=1 OT_COLL_NATIVE32_OFF=1 bash tools/xdie_s81/coll_reach7.sh {{RUN}}/reach{m} {m}",
         "expect": expect, "threads": 4, "peak_ram_gb": 8, "needs": ["verilator"],
         "pass_regex": "^COLL_REACH7 PASS received=\\d+"}
    if expect == "pass":
        b["pass_witness"] = f"{BENCH}/m{m}.log"
    else:
        b["fail_regex"] = regex_fail or "^COLL_REACH7 FAIL errors="
        b["fail_witness"] = f"{BENCH}/m{m}.log"
    return b


def make(side, km):
    s = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_{side}_s6c/spec.json").read_text())
    name = f"dscoll_lane_{side}_s7" + ("k" if km else "")
    s["name"] = name
    s["top"] = f"dsfd_coll_lane_{side}_safe7"
    if km:
        s["pre_cts_extra"] = ["physical/common_flow/clock_split_km.tcl"]
        s["orfs_vars"] = dict(s.get("orfs_vars", {}), OT_CKKM_K="16", OT_CKKM_PORT="ck")
    s["structural_change"] = __doc__.strip()
    s["fill_reason"] = {"pin_bound": "lattice/channel-bound (checklist 6): 55 bank64 SRAMs 62,002 um2 on the 43.2 lattice "
                        "with >= 20 um channels force 86.4 um pitch; W/E faces carry ~1,200 bus pins each (<= 3.6/um). "
                        "s7 keeps the s6c row set (all core rows; the s5 band hook is NOT sourced -- s6c place.tcl never "
                        "sourced it, so cells sit in the channels beside their macros); the low overall fill is channel area"}
    s["pin_regs"]["reason"] = (s["pin_regs"]["reason"] + " s7 (REACH=1): rx lands in 2 flops (lr -> lr2) and lo_v/lo_d "
                               "in an extra core-face flop before the credit-rx landing; these are the forwarded hops "
                               "(+1 rx, +1 core->link edges, priced in the kit README), not ref_tile pin_regs.")
    j = s["job"]
    old = [b for b in j["benches"] if b["name"].startswith("lane_miter_v8_m") and b["name"] != "lane_miter_v8_m0"]
    j["benches"] = [bench(0, "pass"), bench(5, "fail"), bench(6, "fail"), bench(7, "fail")] + old
    j["extra_paths"] = sorted(set(j["extra_paths"]) | {BENCH})
    j.update(owner="Claude:S81-TILES-E", branch=BR, tag="s7k" if km else "s7",
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             purpose="S81-COLL s7: REACH=1 forwarded relay hops (rx 2-stage landing, RX_STAGES 5, reverse ACK relay 2, "
                     "core landing +1) for the s6c native reach FAIL (5,403 pairs > 405 um)"
                     + ("; k-means regional CTS K=16 for the s6c W spread 83.9" if km else "") + ". SAFE checklist in kit README.")
    return name, s


if __name__ == "__main__":
    for side in ("w", "e"):
        for km in (False, True):
            name, s = make(side, km)
            d = ROOT / "physical/ref_tile" / name
            d.mkdir(parents=True, exist_ok=True)
            (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
            print("wrote", d / "spec.json")
