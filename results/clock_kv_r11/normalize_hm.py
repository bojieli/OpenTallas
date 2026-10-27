"""CLOCK-KV-R11: normalize the 319.68 headmirror composed plan for G0 (no geometry change).
(a) every hard core: placed = origin_um + track_offset_um is kept; origin_um -> nearest grid_um lattice point,
    track_offset_um = placed - origin (|offset| < BASE_LATTICE_UM 2.16, else ERROR);
(b) a composed variant type (kv3_pv_v*n, kv3_hg_v1p*) with no cell estimate inherits `cells` from the type it was
    cloned from (same contents/cores, only core placement differs) -- recorded per type."""
import json, sys
src, dst, rep = sys.argv[1:4]
P = json.load(open(src))
G = float(P["die"].get("grid_um", 8.64)); B = 2.16
T = P["partition_types"]
moved, bad, cells = 0, [], {}
for tn, t in T.items():
    for c in t.get("hard_cores", []):
        off = c.get("track_offset_um") or [0.0, 0.0]
        placed = [round(a + b, 4) for a, b in zip(c["origin_um"], off)]
        org = [round(round(v / G) * G, 4) for v in placed]
        to = [round(p - o, 4) for p, o in zip(placed, org)]
        if max(abs(v) for v in to) >= B - 1e-9:
            bad.append([tn, c["inst"], placed]); continue
        if org != c["origin_um"] or to != list(off):
            moved += 1
        c["origin_um"], c["track_offset_um"] = org, to
for tn, t in T.items():
    has = "cells" in t or any("cells" in x for x in t.get("contents", []) if isinstance(x, dict))
    if has:
        continue
    base = tn[:-1] if tn.endswith("n") and tn[:-1] in T else (tn.rsplit("p", 1)[0] if "p" in tn.rsplit("_", 1)[-1] else None)
    if base in T and "cells" in T[base]:
        t["cells"] = T[base]["cells"]; cells[tn] = base
P["note"] = ("CLOCK-KV-R11 normalized 319.68 headmirror candidate (origins on the %g-um lattice + track_offset_um; "
             "variant cells inherited) <- " % G) + P["note"][:200]
json.dump(P, open(dst, "w"), indent=None)
json.dump(dict(cores_normalized=moved, offset_errors=bad, cells_inherited=cells), open(rep, "w"), indent=1)
print("normalized", moved, "offset errors", len(bad), "cells inherited", len(cells), sorted(cells.items())[:12])

# (c) pin-track quantum (G0 hard_cores): a core whose pins use vertical layers keeps its x displacement from the
#     on-track reference plan (argv[4]) a multiple of lcm(V pitches of its pins) (orient x-class unchanged); only
#     cores with no clock island (census: 0 islands) are snapped here; recorded per core.
if len(sys.argv) > 4:
    import math
    from fractions import Fraction
    REF = json.load(open(sys.argv[4]))["partition_types"]
    PITCH_V = {"M3": Fraction(36, 1000), "M5": Fraction(48, 1000), "M7": Fraction(64, 1000)}
    import os
    snaps = []
    pdir = os.path.dirname(os.path.abspath(sys.argv[1]))
    qcache = {}
    for tn, t in T.items():
        for c in t.get("hard_cores", []):
            if c["module"] != "ot_qwen_tp8_pv_join_t":
                continue
            base = tn[:-1] if tn not in REF and tn.endswith("n") else tn
            o = next((x for x in REF.get(base, {}).get("hard_cores", []) if x["inst"] == c["inst"]), None)
            if o is None or (o.get("orient", "R0") in ("MY", "R180")) != (c.get("orient", "R0") in ("MY", "R180")):
                continue
            pf = c.get("pins_file")
            if pf not in qcache:
                pins = json.load(open(os.path.join(pdir, pf))); pins = pins.get("pins", pins)
                ls = {p["layer"] for p in pins if p["layer"] in PITCH_V}
                q = Fraction(0)
                for l in ls:
                    q = PITCH_V[l] if q == 0 else Fraction(math.lcm(q.numerator * PITCH_V[l].denominator, PITCH_V[l].numerator * q.denominator), q.denominator * PITCH_V[l].denominator)
                qcache[pf] = float(q)
            q = qcache[pf]
            px = c["origin_um"][0] + c["track_offset_um"][0]
            ox = o["origin_um"][0] + (o.get("track_offset_um") or [0, 0])[0]
            dx = px - ox
            ndx = round(dx / q) * q
            if abs(ndx - dx) > 1e-6:
                npx = round(ox + ndx, 4)
                org = round(round(npx / G) * G, 4)
                c["origin_um"][0], c["track_offset_um"][0] = org, round(npx - org, 4)
                snaps.append([tn, c["inst"], round(dx, 4), round(ndx, 4), q])
    rp = json.load(open(rep)); rp["pin_quantum_snaps"] = snaps; json.dump(rp, open(rep, "w"), indent=1)
    json.dump(P, open(dst, "w"), indent=None)
    print("pin-quantum snaps", len(snaps), snaps[:3])
