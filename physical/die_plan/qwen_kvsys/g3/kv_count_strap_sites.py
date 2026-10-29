#!/usr/bin/env python3
"""DIE-KV-31-KITS 10-29: KV count-strap pin sites (plan delta on partition_types[*].count_straps ONLY).

Root cause it fixes: gen_phys.strap_pin_sites (9f6da9e92 / DIE-HEAD-5 TILEIO ec8508c91f) only emits strap pins,
port_bind_pins and straps.json for straps that carry plan `layer` + `sites_um`; the KV plan declared none, so every KV
kit with OWNER 12.15a count straps FAILed port_bind (extra = the strap bits).  This assigns, per type, one interior site
per strap bit in the HEAD form: rows parallel to the south edge (y = 4.32, 8.64, ...), x on the layer's preferred
(vertical) track, STEP_TRACKS tracks apart, on the type's own signal ceiling layer (kit MAX_ROUTING_LAYER; M7 here,
M5 for an M5-capped type).  A site is refused within PIN_CLEAR_UM of any existing plan pin, inside a hard content /
macro box grown by MACRO_CLEAR_UM, or inside a clock keepout / die island grown by ISLAND_CLEAR_UM.

Idempotent: a type whose count straps all carry layer + sites_um equal to the computed assignment is unchanged; a
type with a partial / different assignment fails closed.  Tie at the die top (12.15a) is a bind follow-up.

    kv_count_strap_sites.py PLAN_IN PLAN_OUT --type T=LAYER[:PLAN_PINS_JSON] ... [--report R.json]
"""
import argparse
import json
import math
import sys

TRACKS = {"M5": (0.024, 0.048), "M7": (0.032, 0.064)}   # (x_offset, x_pitch) um, kit make_tracks.tcl (vertical layers)
STEP_TRACKS = {"M5": 45, "M7": 34}                       # 2.16 / 2.176 um site pitch (M7 = the HEAD hd_tile form)
ROW_Y0, ROW_DY = 4.32, 4.32
X_MARGIN = 21.6
PIN_CLEAR_UM, MACRO_CLEAR_UM, ISLAND_CLEAR_UM = 1.0, 4.32, 2.0


def _grow(r, d):
    return (r[0] - d, r[1] - d, r[2] + d, r[3] + d)


def blockers(t):
    boxes = []
    for c in list(t.get("hard_cores", []) or []) + list(t.get("contents", []) or []):
        if c.get("origin_um") is not None and c.get("outline_um") is not None:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
                w, h = h, w
            boxes.append(_grow((x, y, x + w, y + h), MACRO_CLEAR_UM))
    ck = t.get("clock", {}) or {}
    for r in (ck.get("keepouts_um") or []) + (ck.get("die_islands_um") or []):
        boxes.append(_grow(tuple(r), ISLAND_CLEAR_UM))
    return boxes


def sites_for(t, layer, n, pins):
    if layer not in TRACKS:
        raise SystemExit(f"layer {layer}: no vertical track table")
    off, pitch = TRACKS[layer]
    step = STEP_TRACKS[layer] * pitch
    W, H = t["outline_um"]
    boxes = blockers(t)
    grid = {}
    for p in pins:
        if str(p["name"]).startswith("strap_"):
            continue
        grid.setdefault((int(p["x"] // 2), int(p["y"] // 2)), []).append((p["x"], p["y"]))

    def free(x, y):
        if any(b[0] <= x <= b[2] and b[1] <= y <= b[3] for b in boxes):
            return False
        for gx in (int(x // 2) - 1, int(x // 2), int(x // 2) + 1):
            for gy in (int(y // 2) - 1, int(y // 2), int(y // 2) + 1):
                if any(abs(px - x) < PIN_CLEAR_UM and abs(py - y) < PIN_CLEAR_UM for px, py in grid.get((gx, gy), ())):
                    return False
        return True

    out, y = [], ROW_Y0
    k0 = math.ceil((X_MARGIN - off) / pitch)
    while len(out) < n:
        if y > H / 2:
            raise SystemExit(f"no room for {n} strap sites below mid-height (got {len(out)})")
        k = k0
        while len(out) < n:
            x = round(off + k * pitch, 4)
            if x > W - X_MARGIN:
                break
            if free(x, y):
                out.append([x, round(y, 4)])
            k += STEP_TRACKS[layer]
        y = round(y + ROW_DY, 4)
    return out


def assign(plan, tn, layer, pins):
    t = plan["partition_types"][tn]
    cs = t.get("count_straps", []) or []
    n = sum(int(c["width"]) for c in cs)
    sites = sites_for(t, layer, n, pins)
    have = [("sites_um" in c or "layer" in c) for c in cs]
    i, rows = 0, []
    for c in cs:
        want = sites[i:i + int(c["width"])]
        i += int(c["width"])
        if any(have):
            if c.get("layer") != layer or c.get("sites_um") != want:
                raise SystemExit(f"{tn}: strap {c['name']} has a partial/different site assignment; refusing")
        c["layer"], c["sites_um"] = layer, want
        rows.append(dict(name=c["name"], width=c["width"]))
    xs = [s[0] for s in sites]
    return dict(type=tn, layer=layer, straps=len(cs), bits=n, changed=not all(have) if cs else False,
                rows_y=sorted({s[1] for s in sites}), x_span=[min(xs), max(xs)] if xs else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("--type", action="append", required=True, help="T=LAYER[:plan_pins.json]")
    ap.add_argument("--report")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan_in))
    rep = []
    for spec in a.type:
        tn, rest = spec.split("=", 1)
        layer, _, pj = rest.partition(":")
        pins = json.load(open(pj))["pins"] if pj else []
        rep.append(assign(plan, tn, layer, pins))
    json.dump(plan, open(a.plan_out, "w"), indent=1)
    if a.report:
        json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    sys.exit(main())
