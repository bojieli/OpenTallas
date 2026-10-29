#!/usr/bin/env python3
"""DIE-HBM-15 10-29: top-down per-port face re-pin of hard cores whose port groups face away from their partners.

check.py core_faces (G0C) FAILs a core port when the mean, over its pins, of the best cosine between the pin's face
normal and the direction to a partner is < FACE_AWAY_COS.  core_pins_orient.py fixes the case where a whole core
was mirrored; this tool fixes the per-port case (the plan moved a partner after the pin table was written, e.g. HBM
hub vmb dq on S with its vmdel to the N).  It uses the SAME check.py model (check_core_faces(collect=...)), adds no
check, and changes only pin tables: core outline, origin, orient and clock/reset/island pins are unchanged.

Per pin table (pins_file; every instance of every type that uses it is scored together, so one table stays one
design view) and per data port with at least one FAILing instance: the new face F (core frame) minimises
(#instances still < FACE_AWAY_COS, #instances < FACE_WARN_COS, -sum of instance scores); the port moves only when the
FAIL count drops.  Moved pins go, in bit order, to the free tracks of F nearest the partners' projection on F:
layer = the layer the table already uses on F (else on the opposite face), track lattice = the residue of the
table's existing pins on that face/layer (so every placed orientation stays on track exactly as before), depth = the
face's existing pin depth, spacing = 2 tracks (1 track only if the face is full).  New tables are written as
<stem>__fr15.json next to the old ones; the plan's hard_cores[].pins_file is repointed.

    core_face_repin.py PLAN_IN PLAN_DIR PLAN_OUT REPORT [--types a,b] [--suffix fr15] [--per-orient]
Opt-in plan delta; re-kit + GEOM review are owed for every core whose table changes (pins only).
"""
import argparse, collections, copy, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check as C   # noqa: E402
import schema as S  # noqa: E402
from core_pins_orient import CLKRST  # noqa: E402

FACES = "NSEW"
OPP = dict(N="S", S="N", E="W", W="E")
MARGIN = 2.16
EDGE = 1.0          # a face pin sits within 1 um of its edge (pin depth 0.096); deeper pins are interior


def type_face(o, f):
    """face in the type frame of core-frame face f after orient o (check._core_face convention)."""
    if o in ("MX", "R180") and f in "NS":
        f = OPP[f]
    if o in ("MY", "R180") and f in "EW":
        f = OPP[f]
    return f


def core_dir(o, ux, uy):
    """type-frame direction -> core frame."""
    if o in ("MX", "R180"):
        uy = -uy
    if o in ("MY", "R180"):
        ux = -ux
    return ux, uy


def pin_face(p, cw, ch, edge=None):
    """nearest face; with `edge` (um), None unless the pin is within `edge` of it (interior clock/island pins)."""
    d, f = min([(p["x"], "W"), (cw - p["x"], "E"), (p["y"], "S"), (ch - p["y"], "N")])
    return f if edge is None or d <= edge else None


def base(nm):
    return re.sub(r"\[\d+\]$", "", nm)


def bit(nm):
    m = re.search(r"\[(\d+)\]$", nm)
    return int(m.group(1)) if m else -1


def score_face(recs, f):
    """(fails, warns, -sum) of putting the whole port on core face f, over its instance records."""
    sc = []
    for r in recs:
        tf = type_face(r["orient"], f)
        n = C._NORMAL[tf]
        sc.append(max(n[0] * ux + n[1] * uy for _, ux, uy in r["dirs"]))
    return (sum(s < C.FACE_AWAY_COS for s in sc), sum(s < C.FACE_WARN_COS for s in sc), -sum(sc)), sc


def place(pins, moved, f, cw, ch, layers, tangent, hc):
    """move pins `moved` (list of dicts, in place) to core face f; returns (layer, step, n_slots_free)."""
    keep = [p for p in pins if not any(p is q for q in moved)]
    onf = [p for p in keep if pin_face(p, cw, ch, EDGE) == f]
    pool = onf or [p for p in keep if pin_face(p, cw, ch, EDGE) == OPP[f]]
    want_dir = "V" if f in "NS" else "H"
    lays = collections.Counter(p["layer"] for p in pool if layers.get(p["layer"], {}).get("dir") == want_dir)
    if not lays:        # no pins on this face pair: the table's own layer of that direction, else M5 / M4
        pool = [p for p in keep if pin_face(p, cw, ch, EDGE)]
        lays = collections.Counter(p["layer"] for p in pool if layers.get(p["layer"], {}).get("dir") == want_dir) \
            or collections.Counter({"M5" if want_dir == "V" else "M4": 1})
    lay = lays.most_common(1)[0][0]
    pitch = layers[lay]["pitch_um"]
    ax, L = ("x", cw) if f in "NS" else ("y", ch)
    rs = collections.Counter(round(p[ax] % pitch, 4) for p in pool if p["layer"] == lay)
    if rs:      # same lattice as the table's existing pins of that layer (on track in every placed orient as before)
        res = rs.most_common(1)[0][0]
    else:       # computed from the first instance (R0/MX keep the axis, MY/R180 mirror it)
        o = hc.get("orient", "R0")
        org = hc["origin_um"][0 if ax == "x" else 1] + (hc.get("track_offset_um") or [0, 0])[0 if ax == "x" else 1]
        flip = (o in ("MY", "R180")) if ax == "x" else (o in ("MX", "R180"))
        off = layers[lay]["offset_um"]
        res = round(((org + L - off) if flip else (off - org)) % pitch, 4)
    dep = collections.Counter(round(dict(N=ch - p["y"], S=p["y"], E=cw - p["x"], W=p["x"])[f], 4)
                              for p in onf).most_common(1)
    depth = dep[0][0] if dep else 0.096
    assert depth <= EDGE, (f, depth)
    occ = {round((p[ax] - res) / pitch) for p in onf if p["layer"] == lay}
    k0 = int((MARGIN - res) // pitch) + 1
    k1 = int((L - MARGIN - res) // pitch)
    centre = 0.5 * L * (1 + max(-0.9, min(0.9, tangent)))
    n = len(moved)
    for step in (2, 1):
        free = [k for k in range(k0, k1 + 1)
                if all((k + j) not in occ for j in range(-(step - 1), step))
                and (step == 1 or k % 2 == (k0 % 2))]
        if len(free) >= n:
            break
    else:
        raise ValueError(f"face {f}: {len(free)} free tracks < {n} pins")
    pick = sorted(sorted(free, key=lambda k: abs(res + k * pitch - centre))[:n])
    for p, k in zip(sorted(moved, key=lambda p: bit(p.get("name", ""))), pick):
        v = round(res + k * pitch, 6)
        p["layer"] = lay
        if ax == "x":
            p["x"], p["y"] = v, round(ch - depth if f == "N" else depth, 6)
        else:
            p["y"], p["x"] = v, round(cw - depth if f == "E" else depth, 6)
    return lay, step, len(free)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("plan_dir"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--types")
    ap.add_argument("--suffix", default="fr15")
    ap.add_argument("--per-orient", action="store_true",
                    help="one table per (pins_file, plan orient) -- COORD CLOCK-KV-R13 form, at most 1 view/orient")
    a = ap.parse_args()
    pd = Path(a.plan_dir)
    raw = json.loads(Path(a.plan).read_text())
    P = S.Plan(copy.deepcopy(raw), pd / "die_plan.json")
    types = set(a.types.split(",")) if a.types else None
    col = []

    def key(hc):            # one table per pins_file, or per (pins_file, orient) with --per-orient
        return (hc["pins_file"], hc.get("orient", "R0") if a.per_orient else "")
    C.check_core_faces(P, C.Report(True), str(pd), None, collect=col)
    hcs = {(tn, hc["inst"]): hc for tn, t in raw["partition_types"].items() for hc in t.get("hard_cores", [])}
    groups = collections.defaultdict(list)       # (pins_file, port) -> instance records
    for r in col:
        hc = hcs[(r["type"], r["inst"])]
        if not hc.get("pins_file") or CLKRST.match(r["port"]):
            continue
        groups[(key(hc), r["port"])].append(dict(r, orient=hc.get("orient", "R0")))
    users = collections.defaultdict(list)
    for k, hc in hcs.items():
        if hc.get("pins_file"):
            users[key(hc)].append(k)
    moves = collections.defaultdict(dict)        # pins_file -> {port: (face, recs)}
    rep = dict(moves=[], skipped=[], tables={})
    for (tk, port), recs in sorted(groups.items()):
        pf = tk[0]
        if not any(r["mean"] < C.FACE_AWAY_COS for r in recs):
            continue
        if types and not all(tn in types for tn, _ in users[tk]):
            rep["skipped"].append(dict(pins_file=pf, port=port, why="table used outside --types"))
            continue
        old = (sum(r["mean"] < C.FACE_AWAY_COS for r in recs), sum(r["mean"] < C.FACE_WARN_COS for r in recs),
               -sum(r["mean"] for r in recs))
        best = min(FACES, key=lambda f: score_face(recs, f)[0])
        new, sc = score_face(recs, best)
        if new[0] >= old[0]:
            rep["skipped"].append(dict(pins_file=pf, orient=tk[1], port=port, why=f"no face lowers the FAIL count {old[0]}",
                                       insts=[f"{r['type']}/{r['inst']}" for r in recs]))
            continue
        moves[tk][port] = (best, recs)
        rep["moves"].append(dict(pins_file=pf, orient=tk[1], port=port, to_face=best, insts=len(recs), fails=[old[0], new[0]],
                                 scores_after=[round(s, 2) for s in sc]))
    layers = P.layers
    for tk, ports in sorted(moves.items()):
        pf, ori = tk
        src = pd / pf
        js = json.loads(src.read_text())
        pins = js["pins"] if isinstance(js, dict) else js
        tn0, ci0 = users[tk][0]
        cw, ch = hcs[(tn0, ci0)]["outline_um"]
        by = collections.defaultdict(list)
        for p in pins:
            nm = p.get("name") or f"{p['bus']}[{p.get('bit', 0)}]"
            by[base(nm)].append(p)
        trep = {}
        for port, (f, recs) in sorted(ports.items(), key=lambda kv: -len(by[kv[0]])):
            moved = [p for p in by[port] if not CLKRST.match(p.get("name") or "")]
            if not moved:
                continue
            tang = []
            for r in recs:
                for _, ux, uy in r["dirs"]:
                    cx, cy = core_dir(r["orient"], ux, uy)
                    tang.append(cx if f in "NS" else cy)
            t = sum(tang) / len(tang) if tang else 0.0
            old_faces = collections.Counter(pin_face(p, cw, ch) for p in moved)
            lay, step, nfree = place(pins, moved, f, cw, ch, layers, t, hcs[(tn0, ci0)])
            trep[port] = dict(pins=len(moved), from_faces=dict(old_faces), to_face=f, layer=lay, track_step=step,
                              free_tracks=nfree)
        stem = re.sub(r"\.json$", "", pf)
        dst = f"{stem}__{a.suffix}{'_' + ori if ori else ''}.json"
        if isinstance(js, dict):
            js["source"] = f"{js.get('source', '')} | DIE-HBM-15 core_face_repin: {len(trep)} ports re-faced"
        (pd / dst).write_text(json.dumps(js, indent=0) + "\n")
        for k in users[tk]:
            hcs[k]["pins_file"] = dst
        rep["tables"][dst] = dict(old=pf, cores=[f"{tn}/{ci}" for tn, ci in users[tk]], ports=trep)
    raw["note"] = "DIE-HBM-15 core_face_repin (per-port face re-pin, check.py core_faces model) <- " + \
        raw.get("note", "")[:200]
    Path(a.out).write_text(json.dumps(raw) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"{len(rep['moves'])} ports re-faced in {len(rep['tables'])} tables; {len(rep['skipped'])} skipped")


if __name__ == "__main__":
    main()
