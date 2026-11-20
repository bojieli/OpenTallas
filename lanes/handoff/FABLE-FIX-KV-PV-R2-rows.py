#!/usr/bin/env python3
"""FABLE-FIX-KV-PV-R2 rows for KV D27: pv near-pair pin edge out of the 25.9-um join strip.

Every kv3_pv* type stacks, per group, pair / pair / join / pair / pair.  All 1,670 signal pins of kv3_pv_pair sit on ONE long
edge (M5).  The lower near pair faces the join over a 77.76-um strip; the upper near pair (origin y 803.52) faces it over
25.92 um (join top 777.6).  That strip must carry the pair's 1,024 ts outputs, its ~630 pad-tail inputs with their last
delay stages, the far pair's 1,024-bit bus to the join W/E face and the T/Q relay + station traffic: about 2x its tracks
(v8j CTS DB: 2,779 / 2,172 net edges leave the g2 strip E / W + 390 through; D23H / D25e3 GRT: the top overflow tiles).

Row: flip the upper near pair about its x axis (R0 -> MX, MY -> R180; same origin, same outline, same tap xy = core centre).
Its pin edge then faces the 103.68-um channel it shares with the far pair; the ts bus reaches the join N face over the
pair's own porous M5/M7.  0 cycles, 0 lanes, no RTL, no core re-shape, no core move, die clock taps unchanged.

usage: rows_R2.py PLAN_C.json [--check] [--types kv3_pv_v8,...] [--station-um 300] [--reserved-rows P3_SEL.json]
  --check          report only
  --no-flip        skip the flip (control arm of a private A/B)
  --station-um N   also set budgets.r_dly_spread_station_um[kv3_pv] = N   (D26 R3 row; private kits on older plans)
  --reserved-rows  also replace clock.reserved_sites_um of the types present in that file (private kits only)
"""
import json, sys, os, tempfile

FLIP = {"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"}
JOIN_GAP_MAX_UM = 40.0     # a pin edge closer than this to its join is "in the strip"
PIN_EDGE_LOW = {"R0": True, "MY": True, "MX": False, "R180": False}   # kv3_pv_pair fMX view: pins on the y-low edge at R0 / MY


def near_strip_pairs(t):
    """[(core, gap_um)] of kv3_pv_pair cores whose pin edge faces a join across less than JOIN_GAP_MAX_UM."""
    joins = [h for h in t.get("hard_cores", []) if h.get("module") == "ot_qwen_tp8_pv_join_t"]
    out = []
    for h in t.get("hard_cores", []):
        if h.get("module") != "kv3_pv_pair":
            continue
        x0, y0 = h["origin_um"]; w, hh = h["outline_um"]
        low = PIN_EDGE_LOW[h.get("orient", "R0")]
        for j in joins:
            jx0, jy0 = j["origin_um"]; jw, jh = j["outline_um"]
            if jx0 + jw <= x0 or jx0 >= x0 + w:
                continue                                  # not over this join
            gap = (y0 - (jy0 + jh)) if low else (jy0 - (y0 + hh))
            if 0 <= gap < JOIN_GAP_MAX_UM:
                out.append((h, round(gap, 3)))
    return out


def main(argv):
    if len(argv) < 2:
        print(__doc__); return 2
    path = argv[1]; check = "--check" in argv
    def opt(name):
        return argv[argv.index(name) + 1] if name in argv else None
    only = set(opt("--types").split(",")) if opt("--types") else None
    plan = json.load(open(path))
    types = plan["partition_types"]
    n = 0
    for tn in sorted(types):
        if not tn.startswith("kv3_pv") or (only and tn not in only):
            continue
        hits = [] if "--no-flip" in argv else near_strip_pairs(types[tn])
        for h, gap in hits:
            old = h.get("orient", "R0"); new = FLIP[old]
            print(f"R2-FLIP {tn} {h['inst']} origin {h['origin_um']} {old} -> {new} (pin edge {gap} um from the join)")
            if not check:
                h["orient"] = new
                h["note"] = (h.get("note", "") + " | FABLE-FIX-KV-PV-R2 11-20: pin edge turned to the 103.68-um pair channel "
                             f"({old} -> {new}; was {gap} um from the join)").strip(" |")
            n += 1
        if not hits:
            print(f"R2-FLIP {tn}: no pair pin edge inside {JOIN_GAP_MAX_UM} um of a join")
    st = opt("--station-um")
    if st:
        b = plan.setdefault("budgets", {}).setdefault("r_dly_spread_station_um", {})
        print(f"R2-STATION budgets.r_dly_spread_station_um kv3_pv {b.get('kv3_pv')} -> {st}")
        if not check:
            b["kv3_pv"] = int(st)
    rr = opt("--reserved-rows")
    if rr:
        sel = json.load(open(rr))
        for tn, rows in sel.items():
            if tn in types and (not only or tn in only) and "clock.reserved_sites_um" in rows:
                old = types[tn].get("clock", {}).get("reserved_sites_um", [])
                print(f"R2-RSV {tn} clock.reserved_sites_um {len(old)} -> {len(rows['clock.reserved_sites_um'])} rects (split form)")
                if not check:
                    types[tn]["clock"]["reserved_sites_um"] = rows["clock.reserved_sites_um"]
    print(f"R2 rows: {n} cores flipped" + (" (check only)" if check else ""))
    if not check:
        d = os.path.dirname(os.path.abspath(path))
        fd, tmp = tempfile.mkstemp(dir=d, prefix=".plan_c.", suffix=".tmp")
        with os.fdopen(fd, "w") as f:
            json.dump(plan, f, indent=1); f.write("\n")
        os.replace(tmp, path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
