#!/usr/bin/env python3
"""Emit the reviewed LEP child geometry for the HEAD fix-only parent event.

Uses the current 55-SRAM child census and the existing RTL-header pin planner.
This is a fresh bank-wise macro arrangement, not an affine placement transform.
It emits no RTL or timing view and does not modify the supplied die plan.
"""
import argparse
import copy
import json
import re
from pathlib import Path

from head_lep_pair_pins import ROOT, SV, ports, build

OUTLINE = (777.6, 492.48)
K_PIN_SPAN = 397.44  # fresh S band: 556/558 pins at ~0.704 um, within one-hop reach
COLL_PIN_SPAN = 466.56
# GB SRAM readouts directly drive the W-face beat registers: they must stay
# near that face. EP FIFO/replay SRAMs form nine local 2x2 bank blocks. Their
# complete macro boxes fit inside one 395-um Manhattan control envelope.
EP_BANK = ((172.8,17.28,47.52), (267.84,17.28,47.52),
           (172.8,129.6,47.52), (267.84,129.6,47.52), (362.88,129.6,47.52),
           (155.52,241.92,47.52), (250.56,241.92,47.52), (345.6,241.92,51.84),
           (172.8,354.24,47.52))
SIZES = {"ot_sram_1r1w2c_256x64_m1": (34.584, 41.352),
         "ot_sram_1r1w2c_32x64_m1": (31.992, 17.304)}


def geometry(base):
    # Parent placement is owned by the die event. Do not carry the old parent
    # entries into a child-only output that another tool might apply wholesale.
    delta = dict(child_type=copy.deepcopy(base["child_type"]))
    child = delta["child_type"]
    child["outline_um"] = list(OUTLINE)
    seen = set()
    for c in child["contents"]:
        name = c["inst"]
        if c.get("kind") != "sram" or name in seen:
            raise ValueError("expected the unique 55 SRAM child census")
        seen.add(name)
        m = re.search(r"u_ep\.g_(fifo|rb)_safe.*g_bank\[(\d+)\]\.g_depth\[(\d+)\]", name)
        if m:
            role, bank, depth = m[1], int(m[2]), int(m[3])
            bx,by,depth_pitch=EP_BANK[bank]
            xy = (bx+depth_pitch*depth, by+(56.16 if role=="rb" else 0))
        elif ".u_gb.u_sf." in name:
            bank = int(re.search(r"g_bank\[(\d+)\]", name)[1])
            # The phase mux allows a GB bank to feed distant W beat bits.
            # All ten GB SRAMs therefore sit inside the intersection of the
            # 405-um reach envelopes of the whole W registered output band.
            xy = (34.56,146.88+30.24*bank) if bank < 6 else (82.08,177.12+30.24*(bank-6))
        elif ".u_ski.u_head." in name:
            bank = int(re.search(r"g_bank\[(\d+)\]", name)[1])
            xy = (34.56,21.6+30.24*bank) if bank < 4 else (82.08,21.6+30.24*(bank-4)) if bank < 8 else (34.56,336.96)
        else:
            raise ValueError("unclassified child SRAM: " + name)
        c.update(origin_um=[round(v,3) for v in xy], orient="R0")
        c["note"] = "LEP locality child v5: GB in common W-output reach envelope, SKI below/beside GB; EP FIFO/replay/depths in staggered local 2x2 bank blocks; clock/reset centre channel"
    if len(seen) != 55:
        raise ValueError(f"expected 55 child SRAMs, got {len(seen)}")
    boxes = []
    for c in child["contents"]:
        x, y = c["origin_um"]
        w, h = SIZES[c["module"]]
        if not (4.32 <= x and 4.32 <= y and x+w+4.32 <= OUTLINE[0] and y+h+4.32 <= OUTLINE[1]):
            raise ValueError("SRAM halo outside child: " + c["inst"])
        boxes.append((c["inst"], x, y, x+w, y+h))
    minimum_gap = float("inf")
    for i, a in enumerate(boxes):
        for b in boxes[i+1:]:
            xgap = max(b[1]-a[3], a[1]-b[3])
            ygap = max(b[2]-a[4], a[2]-b[4])
            if max(xgap, ygap) < 10.8:
                raise ValueError("SRAM channels below 10.8 um: " + a[0] + " / " + b[0])
            minimum_gap = min(minimum_gap, max(xgap, ygap))
    cx, cy = OUTLINE[0]/2, OUTLINE[1]/2
    assert not any(a[1]-4.32 <= cx <= a[3]+4.32 and a[2]-4.32 <= cy <= a[4]+4.32 for a in boxes)
    child["note"] = "Candidate only: fixed 777.6x492.48 outline, bank-wise macro plan, 0 RTL/cycle changes; actual placement/clock/route gates pending"
    return delta, boxes, minimum_gap


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", type=Path, default=ROOT/"results/die_head_1028/die_head_9_lep/lep_pair_plan_delta.json")
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    delta, boxes, gap = geometry(json.loads(a.base.read_text()))
    widths = ports((ROOT/SV).read_text())
    # The final landing chunk contains both low-index control and high-index
    # payload bits. Spreading those pins across 777.6 um makes the common
    # control/state delivery consume essentially two whole reach budgets.
    # A fresh 397.44-um S band keeps it local without changing pin count/layers.
    pins = build(widths, K_PIN_SPAN, COLL_PIN_SPAN)
    centre_reset = build(widths, *OUTLINE)[-1]
    pins[-1] = centre_reset
    view = dict(source=f"Fresh current RTL-header pin plan: {SV}; head_lep_child_resize.py", macro="ot_s81hd_lep_pair",
                outline_um=list(OUTLINE), excluded_pg=["VDD", "VSS"], excluded_clock=["clk"],
                faces=dict(W="coll_i M4 / coll_o M6, lower W band y2..464.56", S="K-side in M5 / out M7, SW band x2..395.44"), pins=pins)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out/"child_delta.json").write_text(json.dumps(delta, indent=1)+"\n")
    (a.out/"lep_pair_pins.json").write_text(json.dumps(view, indent=1)+"\n")
    estimate = dict(status="PLANNED_NOT_ROUTED", outline_um=list(OUTLINE), macros=len(boxes), pins=len(pins),
                    k_pin_band_um=[2.,K_PIN_SPAN-2.],
                    coll_pin_band_um=[2.,COLL_PIN_SPAN-2.],
                    minimum_macro_gap_um=round(gap, 3), centre_clock_reset_clear=True, added_cycles=0,
                    prior_trial7=dict(outline_um=[388.8,432.], channel_h=1.022, channel_v=1.595),
                    width_height_capacity_estimate=dict(channel_h=round(1.022*432/OUTLINE[1],3),
                                                       channel_v=round(1.595*388.8/OUTLINE[0],3)),
                    limits="Capacity estimate only; no inherited GRT or reach PASS. Full placed reach and per-bank/control fanout must pass before route.")
    (a.out/"estimate.json").write_text(json.dumps(estimate,indent=1)+"\n")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(13,8))
    ax.add_patch(Rectangle((0,0),*OUTLINE,fill=False,lw=1.5))
    for name,x,y,x1,y1 in boxes:
        color="tab:blue" if "g_fifo" in name else "tab:orange" if "g_rb" in name else "tab:green"
        ax.add_patch(Rectangle((x,y),x1-x,y1-y,facecolor=color,alpha=.5,edgecolor="black",lw=.5))
    for layer,color in (("M4","green"),("M6","cyan"),("M5","red"),("M7","brown")):
        pp=[p for p in pins if p["layer"]==layer]
        ax.scatter([p["x"] for p in pp],[p["y"] for p in pp],s=2,c=color,label=layer)
    ax.scatter([OUTLINE[0]/2],[OUTLINE[1]/2],marker="*",s=150,c="red",label="Clock/reset clear centre")
    ax.set(xlim=(-20,OUTLINE[0]+20),ylim=(-20,OUTLINE[1]+20),aspect="equal",xlabel="um",ylabel="um",
           title="LEP child v5: GB inside full W-output reach envelope; EP in local blocks\n55 SRAMs, 777.6 x 492.48 um; unchanged RTL/cycles; physical gates pending")
    ax.legend(loc="upper left",ncol=2,fontsize=8)
    fig.tight_layout();fig.savefig(a.out/"child_plan.png",dpi=140)
    print(json.dumps(estimate))


if __name__ == "__main__":
    main()
