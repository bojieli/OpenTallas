#!/usr/bin/env python3
"""S81-COLL8 (10-20) COLL lane kits dscoll_lane_{w,e}_s8 (TritonCTS) / dscoll_lane_e_s8k (k-means regional CTS, K=16):
structural fallback of s7 (S81.STA.LKTO.2), gated in parallel with the running s7 routes.

s7 E gates WARN (GRT0, spread 73.3/67.9 and 67.2/65.3) and route, but the actual GRT native reach audit on the s7 E
gate ODB (scratch/s81-tilesf/reach_e_s7) still FAILS: 5,379 pairs > 405 um, max 765 um; 4.8k of them are ONE cone:
u_ep c_diff / c_crc_ok / xp_v (receive decision, placed by the gearbox at the link face) -> the 18 RX FIFO address
groups (g_fifo_safe g_address[].count_r / wp_r) and u_m g_slice[].valid_r beside the 18 RX FIFO banks at the core
face, in one cycle (W s7 gate placement TT reg->reg -246 ps at g_address[5].wp_r).  The REACH = 1 frame hops did not
move the decision: the placer keeps it by the gearbox.

s8 = RTL top dsfd_coll_lane_{w,e}_safe8 (ot_s81ph_coll_lane_safe4 REACH = 2 = REACH 1 + ot_s81ph_link_ep_safe4
WRL = 2): RX FIFO write LANDING.  c_acc -> 3 kept copies (edge 1, one per 6 groups) -> 18 per-group kept copies
(edge 2, each on its group's reset leaf) beside the banks; write data 2 reset-free stages; logical occupancy (fill,
c_full / overflow) still counts c_acc at once, physical occupancy (fillw / tail / drain) counts the landed write.
No single-cycle wire from the decision to the FIFO groups; +2 receive edges (credits return 2 edges later).
Same outline, macro map, pins, PDN, layer contract as s7.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BR = "claude/s81-coll8-1020"
BENCH = "results/rtl/s81_coll_native32_1020/reach8/bench"


def bench(m, expect):
    b = {"name": f"lane_reach8_m{m}",
         "cmd": f"OT_COLL_NATIVE32=1 OT_COLL_NATIVE32_OFF=1 OT_COLL_REACH8=1 bash tools/xdie_s81/coll_reach7.sh {{RUN}}/reach{m} {m}",
         "expect": expect, "threads": 4, "peak_ram_gb": 8, "needs": ["verilator"],
         "pass_regex": "^COLL_REACH7 PASS received=\\d+"}
    if expect == "pass":
        b["pass_witness"] = f"{BENCH}/m{m}.log"
    else:
        b["fail_regex"] = "(^COLL_REACH7 FAIL errors=|COLL FIFO group state differs|COLL WRL )"
        b["fail_witness"] = f"{BENCH}/m{m}.log"
    return b


def make(side, km):
    src = f"dscoll_lane_{side}_s7" + ("k" if km else "")
    s = json.loads((ROOT / f"physical/ref_tile/{src}/spec.json").read_text())
    name = f"dscoll_lane_{side}_s8" + ("k" if km else "")
    s["name"] = name
    s["top"] = f"dsfd_coll_lane_{side}_safe8"
    s["structural_change"] = __doc__.strip()
    s["fill_reason"]["pin_bound"] = s["fill_reason"]["pin_bound"].replace("s7 keeps", "s8 (as s7) keeps")
    j = s["job"]
    old = [b for b in j["benches"] if b["name"].startswith("lane_miter_v8_m")]
    j["benches"] = [bench(0, "pass"), bench(5, "fail"), bench(6, "fail"), bench(7, "fail"), bench(8, "fail")] + old
    j["extra_paths"] = sorted(set(j["extra_paths"]) | {BENCH})
    j.update(owner="Claude:DRIVE-S81-COLL", branch=BR, tag="s8k" if km else "s8",
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             purpose="S81-COLL s8: REACH=2 = s7 hops + RX FIFO write landing (c_acc -> 3 -> 18 kept per-group copies, "
                     "data 2 stages) for the s7 GRT native reach FAIL (5,379 pairs > 405 um, 4.8k = c_diff -> FIFO groups)"
                     + ("; k-means regional CTS K=16" if km else "") + ". SAFE checklist in kit README.")
    return name, s


if __name__ == "__main__":
    for side, km in (("w", False), ("e", False), ("e", True)):
        name, s = make(side, km)
        d = ROOT / "physical/ref_tile" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", d / "spec.json")
