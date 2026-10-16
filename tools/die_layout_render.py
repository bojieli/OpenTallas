#!/usr/bin/env python3
"""die_layout_render.py -- die-level layout pictures (OWNER principle 2026-10-15: look at the layout).

For a die revision (GEN, GRT, STA) or a PLANNED set of homes (no die job needed -- 'render now'):
  die_floorplan.png   block outlines + names (colour by block family)
  die_buses.png       every inter-block bus as a line, thickness ~ log2(bit width), colour = relay stages
                      (green 0 .. yellow 2 .. orange 4 .. red >= 6)
  die_congestion.png  GRT congestion heatmap (when a congestion report / dump is given)

Sources (adapters):
  --hbm DIR        HBM compact plan dir (compact.P.json homes + compact.graph.json links; grt/congestion_final.txt)
  --qwen HOMES     Qwen globalfp homes (…-homes-pins.json 'homes') with the bus graph --graph SOURCE.json (insts/buses)
  --s81 PLAN       S81 canonical wide-hub plan (rm*_p*.json: hard_fixed_boxes, hcp_homes, field columns + root frames)
  --dump DUMP      a die .odb dumped by tools/ref_tile/layout_dump.tcl with OT_LAYOUT_LINKS=1 (blocks + block links)
Stages: a plan without explicit relay stages gets the ideal-reach model ceil(manhattan centre distance / --reach um)
(500 um, the per-hop budget of the die contracts); the legend says so.

    python3 tools/die_layout_render.py --hbm results/arch/hbm_die_v15/compact660_v5 --out DIR [--title T]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "ref_tile"))
import layout_png as LP  # noqa: E402


def _stages(a, b, reach):
    (ax0, ay0, ax1, ay1), (bx0, by0, bx1, by1) = a, b
    d = abs((ax0 + ax1) / 2 - (bx0 + bx1) / 2) + abs((ay0 + ay1) / 2 - (by0 + by1) / 2)
    return max(0, math.ceil(d / reach) - 1)


def _buses(blocks, links, reach):
    """links [(a, b, bits[, stages])] -> plan buses, merged per unordered block pair"""
    rect = {b[0]: b[1:5] for b in blocks}
    agg = {}
    for ln in links:
        a, b, bits = ln[0], ln[1], ln[2]
        if a == b or a not in rect or b not in rect:
            continue
        k = tuple(sorted((a, b)))
        st = ln[3] if len(ln) > 3 and ln[3] is not None else _stages(rect[a], rect[b], reach)
        prev = agg.get(k, [0, 0])
        agg[k] = [prev[0] + int(bits), max(prev[1], int(st))]
    return [[a, b, v[0], v[1]] for (a, b), v in agg.items()]


def grt_table(text):
    rows = re.findall(r"^(M\d+|Total)\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)", text or "", re.M)
    return [{"layer": r[0], "usage_pct": float(r[3]), "overflow": int(r[6])} for r in rows]


def from_hbm(d, reach):
    d = Path(d)
    P = json.loads((d / "compact.P.json").read_text())
    G = json.loads((d / "compact.graph.json").read_text())
    blocks = [[n, v["x"], v["y"], v["x"] + v["w"], v["y"] + v["h"]] for n, v in P.items() if isinstance(v, dict) and "w" in v]
    W = max(b[3] for b in blocks) + 20
    H = max(b[4] for b in blocks) + 20
    links = [(l["src"], l["dst"], l.get("bits", 1), l.get("stages")) for l in G.get("links", [])]
    plan = {"die": [0, 0, W, H], "blocks": blocks, "buses": _buses(blocks, links, reach)}
    cg = d / "grt" / "congestion_final.txt"
    if cg.exists():
        plan["grt"] = grt_table(cg.read_text())
    return plan


def from_qwen(homes, graph, reach):
    H = json.loads(Path(homes).read_text())
    hm = H["homes"]
    blocks = [[n, v["x"], v["y"], v["x"] + v["w"], v["y"] + v["h"]] for n, v in hm.items()]
    W, Hh = H.get("die_outline_um", [max(b[3] for b in blocks), max(b[4] for b in blocks)])
    links = []
    if graph:
        Gd = json.loads(Path(graph).read_text())
        for bus in Gd.get("buses", []):
            ends = [e[0] for e in bus.get("e", [])]
            for a, b in zip(ends, ends[1:]):
                links.append((a, b, bus.get("n", 1), None))
    return {"die": [0, 0, W, Hh], "blocks": blocks, "buses": _buses(blocks, links, reach)}


def from_s81(plan_path, reach, hub_layout=None):
    p = json.loads(Path(plan_path).read_text())
    W, H = p.get("die_outline_um", [33000, 26000])
    blocks = [[b[0], b[1], b[2], b[1] + b[3], b[2] + b[4]] for b in p.get("hard_fixed_boxes", [])]
    for h in p.get("hcp_homes", []):
        x, y = h["at_um"]
        blocks.append([h["name"], x, y, x + h["outline"]["w"], y + h["outline"]["h"]])
    cols = sorted(p.get("columns", []), key=lambda c: c["x_um"])
    for i, c in enumerate(cols):
        nxt = cols[i + 1]["x_um"] if i + 1 < len(cols) else c["x_um"] + 1100
        w = min(1100.0, max(200.0, (nxt - c["x_um"]) * 0.85))
        blocks.append([f"field_col{i}_r{c.get('roots')}", c["x_um"], c["y0_um"], c["x_um"] + w, c["y1_um"]])
    if hub_layout:
        # --s81-hub: the generator hub layout (tools/s81/wide_hub_layout.py) replaces the old hub boxes of the record
        hl = json.loads(Path(hub_layout).read_text())
        x0, x1 = p["wide_hub"]["hub_x_um"]
        blocks = [b for b in blocks if b[0] not in hl["blocks"]]
        for n, (x, y, w, h, *_r) in hl["blocks"].items():
            blocks.append([n, x, y, x + w, y + h])
        if hl.get("mix4_slot"):
            x, y, w, h = hl["mix4_slot"]
            blocks.append(["mix4", x, y, x + w, y + h])
        wd = hl.get("wide", {})
        for k in ("s14w", "s14e"):
            if k in wd:
                blocks.append([f"road_{k}", wd[k][0], 3214.0, wd[k][1], 22786.0])
        if "x_vch" in wd:
            blocks.append(["road_vch", wd["x_vch"], 3214.0, wd["x_vch"] + wd["vch"], 22786.0])
        by = {b[0]: b for b in blocks}
        links = [(a_, b_, n_, None) for a_, b_, n_ in S81_HUB_BUSES if a_ in by and b_ in by]
        return {"die": [0, 0, W, H], "blocks": blocks, "buses": _buses(blocks, links, reach),
                "note": "S81 wide-hub plan + generator hub layout; buses = the c21h die's hub buses (bits), stages = reach model"}
    return {"die": [0, 0, W, H], "blocks": blocks, "buses": [],
            "note": "S81 wide-hub plan: blocks only (the plan file carries no inter-block bus list; render the GEN die"
                    " dump with --dump for buses)"}


# c21h (src22) die hub buses, bits per block pair (die.v n_hb_* nets)
S81_HUB_BUSES = [("sp_capture", "sp_vm", 13376), ("sp_gather", "sp_capture", 6947), ("sp_hc_s", "sp_vm", 5402),
                 ("sp_hc_s", "sp_hc_t", 9168), ("sp_collective", "sp_vm", 2219), ("sp_collective", "sp_hc_s", 8193),
                 ("sp_vm", "sp_pq", 2069), ("sp_su_s", "sp_vm", 17128), ("sp_vm", "sp_wfc", 2647), ("sp_vm", "sp_gather", 523),
                 ("sp_collective", "sp_host", 592), ("sp_collective", "sp_wfc", 1028), ("sp_sseq", "sp_vm", 96),
                 ("sp_sseq", "sp_collective", 96), ("sp_sseq", "sp_su_s", 96), ("sp_sseq", "sp_hc_s", 96),
                 ("sp_sseq", "sp_gather", 96), ("mix4", "sp_vm", 2048)]


def from_dump(dump, reach):
    d = json.loads(Path(dump).read_text())
    blocks = [[b[0], *b[2:6]] for b in d.get("blocks", [])]
    links = [(a, b, n, None) for a, b, n in d.get("links", [])]
    plan = {"die": d["die"], "blocks": blocks, "buses": _buses(blocks, links, reach)}
    if d.get("congestion"):
        plan["congestion"] = d["congestion"]
    return plan


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--hbm"); src.add_argument("--qwen"); src.add_argument("--s81"); src.add_argument("--dump")
    ap.add_argument("--graph", help="Qwen bus graph (insts/buses) for --qwen")
    ap.add_argument("--s81-hub", help="S81 generator hub layout JSON (tools/s81/wide_hub_layout.py) for --s81")
    ap.add_argument("--reach", type=float, default=500.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="")
    a = ap.parse_args(argv)
    plan = (from_hbm(a.hbm, a.reach) if a.hbm else from_qwen(a.qwen, a.graph, a.reach) if a.qwen
            else from_s81(a.s81, a.reach, a.s81_hub) if a.s81 else from_dump(a.dump, a.reach))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    imgs = LP.render_die(plan, out, a.title)
    summary = {"blocks": len(plan["blocks"]), "buses": len(plan["buses"]),
               "bus_bits": sum(b[2] for b in plan["buses"]),
               "max_stages": max((b[3] for b in plan["buses"]), default=0), "grt": plan.get("grt"),
               "note": plan.get("note", ""), "stage_model": f"ceil(manhattan/{a.reach:g} um) - 1 where the plan gives none",
               "images": imgs}
    (out / "die_layout.json").write_text(json.dumps(summary, indent=1) + "\n")
    for k, p in imgs.items():
        print(f"OT_DIE_LAYOUT_PNG {k} {p}")
    print("OT_DIE_LAYOUT " + json.dumps({k: v for k, v in summary.items() if k != "images"})[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
