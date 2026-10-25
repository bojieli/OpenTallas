#!/usr/bin/env python3
"""CORE-HBM core re-pin v3 (PROPOSAL for the HBM plan owner; the published plan pins stay pins_plan v2 until adopted).

v2 (pins_plan_v2.spread) put every face's pins in ONE block at 0.096-um pitch centred on the face (10.4 pins/um in
every 10-um window; an SM native column used 7% of each face), connectivity-blind.  v3 keeps the v2 pin set, port
order and (unless overridden) face, and spreads each face over its whole usable span:
  - plan tracks: E/W faces M4 (y = 0.024 + k*0.048), N/S faces M5 (x = 0.024 + k*0.048), centre inset 0.019 (as v2);
  - M5 tracks under the core / partition M5 PG stripes (x mod 4.32 in [1.932, 2.196]) are skipped (a v2 pin there
    shorts to the stripe);
  - corner keep-out 2.16 um; pins evenly spaced in port order (buses contiguous).
Overrides (--rules JSON {type_id: {"outline_um": [w, h]?, "faces": [[regex, face], ...]}}): a regex sends matching
ports to a face (first match wins; non-matching keep the v2 face).  Faces over 5 pins/um are reported, not hidden.

    python3 repin_v3.py --plan PLAN.json --census census.json --out DIR [--rules rules.json] [--types t1,t2]
"""
import argparse
import collections
import json
import math
import re
from pathlib import Path

PITCH, OFF, INSET, KEEP = 0.048, 0.024, 0.019, 2.16
PG_PITCH, PG_LO, PG_HI = 4.32, 1.932, 2.196
CAP_PER_UM, BALANCE = 4.5, True


def face_of(x, y, w, h):
    return min([(x, "W"), (w - x, "E"), (y, "S"), (h - y, "N")])[1]


def tracks(L, layer):
    k0 = math.ceil((KEEP - OFF) / PITCH)
    k1 = math.floor((L - KEEP - OFF) / PITCH)
    ks = []
    for k in range(k0, k1 + 1):
        a = OFF + k * PITCH
        if layer == "M5" and PG_LO <= (a % PG_PITCH) <= PG_HI:
            continue
        ks.append(round(a, 4))
    return ks


def spread(names, L, layer):
    tr = tracks(L, layer)
    n = len(names)
    if n > len(tr):
        raise ValueError(f"{n} pins > {len(tr)} free tracks on a {L:g}-um {layer} face")
    out = {}
    for j, nm in enumerate(names):
        out[nm] = tr[min(len(tr) - 1, int((j + 0.5) * len(tr) / n))]
    return out


def bitkey(n):
    m = re.match(r"^(.*)\[(\d+)\]$", n)
    return (m.group(1), int(m.group(2))) if m else (n, -1)


def repin(pins, w, h, rules):
    faces = collections.defaultdict(list)
    for p in pins:
        f = face_of(p["x"], p["y"], w, h)
        for rx, rf in rules.get("faces", []):
            if re.match(rx, p["name"]):
                f = rf
                break
        faces[f].append(p["name"])
    if rules.get("balance", BALANCE):
        # faces over CAP_PER_UM spill their tail (port order, buses kept contiguous as far as possible) to the face
        # with the most spare capacity (adjacent faces first); the v2 face order is otherwise kept
        cap = {f: int(CAP_PER_UM * (h if f in "EW" else w)) for f in "NSEW"}
        adj = dict(N="EWS", S="EWN", E="NSW", W="NSE")
        for f in "NSEW":
            names = sorted(faces.get(f, []), key=bitkey)
            extra = names[cap[f]:] if len(names) > cap[f] else []
            faces[f] = names[:len(names) - len(extra)]
            for nm in extra:
                g = max(adj[f], key=lambda g: (cap[g] - len(faces.get(g, [])), -adj[f].index(g)))
                faces.setdefault(g, []).append(nm)
    out, st = [], {}
    for f, names in faces.items():
        if not names:
            continue
        L = h if f in "EW" else w
        layer = "M4" if f in "EW" else "M5"
        names = sorted(names, key=bitkey)
        pos = spread(names, L, layer)
        for nm, a in pos.items():
            if f in "EW":
                out.append(dict(name=nm, layer=layer, x=INSET if f == "W" else round(w - INSET, 4), y=a))
            else:
                out.append(dict(name=nm, layer=layer, x=a, y=INSET if f == "S" else round(h - INSET, 4)))
        st[f] = dict(pins=len(names), per_um=round(len(names) / L, 2), layer=layer)
    return sorted(out, key=lambda p: p["name"]), st


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--census", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--rules")
    ap.add_argument("--types")
    a = ap.parse_args()
    root = Path(a.plan).resolve().parent
    cen = json.load(open(a.census))["types"]
    rules = json.load(open(a.rules)) if a.rules else {}
    want = set(a.types.split(",")) if a.types else None
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    summ = {}
    for r in cen:
        tid = r["type_id"]
        if want and tid not in want:
            continue
        ru = rules.get(tid, {})
        w, h = ru.get("outline_um", r["outline_um"])
        v2 = json.load(open(root / r["pins_file"]))
        try:
            pins, st = repin(v2, w, h, ru)
        except ValueError as e:
            summ[tid] = dict(error=str(e), outline_um=[w, h], pins=len(v2))
            continue
        fn = f"{r['module']}__{w:g}x{h:g}.json"
        (out / fn).write_text(json.dumps(pins) + "\n")
        worst = max(v["per_um"] for v in st.values())
        summ[tid] = dict(pins_file=fn, outline_um=[w, h], pins=len(pins), faces=st, worst_per_um=worst,
                         face_rule="PASS" if worst <= 5.0 else ("WARN" if worst <= 6.0 else "FAIL"),
                         outline_changed=[w, h] != r["outline_um"], rules=bool(ru))
    (out / "summary.json").write_text(json.dumps(summ, indent=1) + "\n")
    c = collections.Counter(v.get("face_rule", "ERROR") for v in summ.values())
    print(json.dumps(dict(c)))


if __name__ == "__main__":
    main()
