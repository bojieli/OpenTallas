#!/usr/bin/env python3
"""S81 plan event helpers (DIE-S81-56/PLAN 11-04): repo plan text and reset tree publishing, shared by the event deltas."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/die_plan"))
import pin_template as PT  # noqa: E402


def plan_text(P):
    """repo plan format with one line per collector_tree relay row (results/rf_eg_1104/compact_relays.py: 45 MB, not 106 MB)"""
    txt = PT.dumps(P)
    dec, res, last = json.JSONDecoder(), [], 0
    for m in re.finditer(r'(?m)^( +)"relays": \[', txt):
        i = m.end() - 1
        v, e = dec.raw_decode(txt, i)
        pad = m.group(1) + " "
        body = "[]" if not v else "[\n" + ",\n".join(pad + json.dumps(r, separators=(",", ":")) for r in v) + "\n" + m.group(1) + "]"
        res += [txt[last:i], body]
        last = e
    res.append(txt[last:])
    new = "".join(res)
    assert json.loads(new) == P, "whitespace edit changed the plan"
    return new


def publish_tree(lc, st, tree, rep):
    """write a re-solved reset tree to the plan landing contract and the sidecar type; collector sources name taps of the
    published tree, so re-pick them like clock_landing_plan (nearest tap to the pin, else band centre)."""
    tapxy = {r["q"]: r["xy"] for r in tree["relays"] if r["q"].startswith("rst_n_t")}
    near_tap = lambda xy: min(tapxy, key=lambda q: abs(tapxy[q][0] - xy[0]) + abs(tapxy[q][1] - xy[1]))
    dist = lambda q, xy: abs(tapxy[q][0] - xy[0]) + abs(tapxy[q][1] - xy[1])
    for holder, skey, ckey in ((lc, "collector_local_sources", "collector_children"), (st, "local_sources", "children")):
        for row in holder.get(skey) or ():
            if row.get("tap") is None:
                continue
            pin = row.get("pin_xy_um") or row["xy_um"]
            q = near_tap(pin)
            rect = (row.get("band") or {}).get("rect_um")
            if dist(q, pin) > 405 and rect:
                pin = [round((rect[0] + rect[2]) / 2, 3), round((rect[1] + rect[3]) / 2, 3)]
                q = near_tap(pin)
            row["tap"], row["xy_um"] = int(q.split("rst_n_t")[1]), pin
            rep["max_source_hop_um"] = round(max(rep.get("max_source_hop_um", 0), dist(q, pin)), 1)
        for kid in holder.get(ckey) or ():
            if "node" in kid:
                kid["node"] = near_tap(kid["xy_um"])
                rep["max_source_hop_um"] = round(max(rep.get("max_source_hop_um", 0), dist(kid["node"], kid["xy_um"])), 1)
    if lc.get("collector_tree"):
        lc["collector_tree"] = tree
    if st.get("tree"):
        st["tree"] = tree
