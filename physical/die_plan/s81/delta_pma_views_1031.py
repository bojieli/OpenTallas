#!/usr/bin/env python3
"""S81-SERDES-PHY-1 10-31: one metadata event: place the S81 SerDes analog PMA abstracts in the serdes plan types.

The bound serdes RTL has no whole-PHY instance: u_core = ot_pdie_serdes_col = real KP4 digital + two analog leaves
u_ptx / u_prx (ot_s81_pma_txm / rxm).  OWNER 10-29 09:05: the PMA lies with its long side along the shore, stacked tx/rx
when the shore holds only one (2246.4 x 259.2), no re-aspect, no whole-PHY shim.  Views: tools/mem_compiler/s81_pma_gen.py
--form ew.  u_phy keeps its module/origin/outline (the logical PHY lot, die IO footprint) and gains physical_parts.

Pair placed against the lot's outer edge, centred along it, both MX (pad face on the outer side, digital face inward);
tx outer, rx inner.  A window whose lot cannot hold the pair is left unchanged, so its kit keeps failing closed:
that is a plan-geometry item, listed in the receipt, never hidden here.  Refuses a second run.

    python3 physical/die_plan/s81/delta_pma_views_1031.py PLAN_IN PLAN_OUT RECEIPT
"""
import hashlib
import json
import math
import sys
from pathlib import Path

W, H = 2246.4, 129.6
GAP = 10.8          # tx digital face to rx pad face: >= the kit_preflight macro_channels interior channel (10.8 um)
X_GRID, Y_GRID = 0.432, 1.08    # multiples of the M5 pitch 0.048 / the row height 0.27
X_TRACK = 0.024     # S81-SERDES-PHY-2: the view's M5 pin centres sit on 0.048 multiples, the kit M5 tracks at 0.024 + k 0.048
VIEWS = "physical/asap7_memory_macros"
LEAVES = (("u_bound.u_core.u_ptx", "ot_s81_pma_txm"), ("u_bound.u_core.u_prx", "ot_s81_pma_rxm"))


def part(inst, master, x, y):
    return {"physical_inst": inst, "physical_master": master, "lef": f"{VIEWS}/{master}/{master}.lef",
            "lib": f"{VIEWS}/{master}/{master}_tt.lib", "origin_um": [x, y], "outline_um": [W, H], "orient": "MX",
            "obs_max": "M5"}


def place(lot_xy, lot_wh):
    """(x, y_tx, y_rx) of the pair at the lot's top edge, or None when it does not fit."""
    (x0, y0), (w, h) = lot_xy, lot_wh
    if w < W or h < 2 * H + GAP:
        return None
    x = round(math.floor((x0 + (w - W) / 2) / X_GRID) * X_GRID + X_TRACK, 3)
    y_tx = round(math.floor((y0 + h - H) / Y_GRID) * Y_GRID, 3)
    y_rx = round(math.floor((y_tx - H - GAP) / Y_GRID) * Y_GRID, 3)
    return x, y_tx, y_rx if y_rx >= y0 else None


def main(src, dst, receipt):
    text = Path(src).read_text()
    plan = json.loads(text)
    rows, edits = [], []
    for tn, t in sorted(plan["partition_types"].items()):
        for c in t.get("contents", []):
            if c.get("module") != "ot_pdie_serdes":
                continue
            orig = json.loads(json.dumps(c))
            if c.get("physical_parts"):
                raise SystemExit(f"{tn}: physical_parts already present (second run refused)")
            got = place(c["origin_um"], c["outline_um"]) if "origin_um" in c and "outline_um" in c else None
            if got is None or got[2] is None:
                rows.append(dict(type=tn, placed=False, lot=[c.get("origin_um"), c.get("outline_um")]))
                continue
            x, y_tx, y_rx = got
            c["physical_parts"] = [part(*LEAVES[0], x, y_tx), part(*LEAVES[1], x, y_rx)]
            c["note"] = c.get("note", "") + ("; S81-SERDES-PHY-1 10-31: physical form = PMA abstracts u_ptx/u_prx (EW form, "
                                             "long side along the shore, OWNER 10-29); origin/outline stay the logical lot")
            edits.append((tn, orig, c))
            rows.append(dict(type=tn, placed=True, x=x, y_tx=y_tx, y_rx=y_rx))
    # the plan file keeps each contents[] record on ONE compact line (identical records recur across types): rewrite
    # exactly that line inside the type's own block of partition_types, nothing else
    lines = text.split("\n")
    keys = {ln[3:ln.index('"', 3)]: i for i, ln in enumerate(lines)
            if ln.startswith('  "') and not ln.startswith('   ') and ln.endswith('": {')}
    starts = sorted(keys.values())
    for (tn, old, new) in edits:
        i0 = keys[tn]
        i1 = next((i for i in starts if i > i0), len(lines))
        line = "    " + json.dumps(old, separators=(",", ":"))
        hit = [i for i in range(i0, i1) if lines[i].rstrip(",") == line]
        if len(hit) != 1:
            raise SystemExit(f"{tn}: u_phy record is not one compact line in its type block ({len(hit)})")
        k = hit[0]
        lines[k] = "    " + json.dumps(new, separators=(",", ":")) + ("," if lines[k].endswith(",") else "")
    out = "\n".join(lines)
    if json.loads(out) != plan:
        raise SystemExit("textual rewrite does not equal the edited plan")
    Path(dst).write_text(out)
    sha = lambda s: hashlib.sha256(s.encode()).hexdigest()[:12]
    Path(receipt).write_text(json.dumps(dict(kind="S81_PMA_VIEWS_1031", plan_in=sha(text), plan_out=sha(out), rows=rows,
                                             unchanged="outlines, pins, buses, clock, PG domains, cycles"), indent=1) + "\n")
    print(json.dumps(dict(plan_in=sha(text), plan_out=sha(out), placed=[r["type"] for r in rows if r["placed"]],
                          not_placed=[r["type"] for r in rows if not r["placed"]])))


if __name__ == "__main__":
    main(*sys.argv[1:4])
