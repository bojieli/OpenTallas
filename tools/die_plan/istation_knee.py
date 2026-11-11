#!/usr/bin/env python3
"""KNEE-1 (DIE-QC-97 11-10): Python mirror of the kit per_bit internal-station rule (kit_istations.TCL_HEAD
is_bits / is_knee_site), for planners and a die-wide plan check.

The kit places the n stations of a per_bit bus on each bit's own Manhattan route between the leaf point and the bit's
face pin, with ONE integer stage split shared by the whole bus, sized on the bounding box of ALL of the bus's pins:
  normal = farthest pin from the leaf across the face, along = farthest pin from the leaf along the face,
  out bus: first = along, second = normal;  in bus: first = normal, second = along;  edges = n + 1,
  worst = min over split j of max(first / j, second / (edges - j))  (one leg zero: leg / edges).
The kit stops 3_3_place_gp at worst > 403 um ("internal station knee needs a plan depth change").  The leaf point is
shifted toward the face by max(0, min(15, leaf_box / 2 - 2)) um (opposite-face corridor offset).  A straight
L1 / (n + 1) per-bit estimate is NOT this rule: integer splits and the shared bbox make the worst hop longer
(sle_fw_v3 st_eo: L1/3 = 355 um, kit 442.99 um).

  istation_knee.py SRC PLAN OUT_TSV [--limit 403] [--margin 400] [--fix OUT_PLAN REPORT_JSON]
replays every per_bit chain of PLAN (pins from gen_phys.type_pins, the records io.tcl is written from), prints the
chains over the limit / inside the margin, and with --fix adds the fewest stations that bring each failing chain to
<= margin (regs_um re-spaced with the planner rule of its direction) and sets lane fixed_cycles = source out-station
count + destination in-station count on every lane through a changed type.
"""
import copy, hashlib, json, re, sys

KIT_LIMIT_UM = 403.0
PLAN_MARGIN_UM = 400.0


def knee(first, second, edges):
    """kit is_knee_site: (worst ideal hop um, split) for legs first/second over `edges` hops"""
    if first < 1e-8:
        return second / edges, 0
    if second < 1e-8:
        return first / edges, edges
    if edges < 2:
        return float("inf"), -1
    return min((max(first / j, second / (edges - j)), j) for j in range(1, edges))


def leaf_offset(t, bus_rec):
    """kit_istations: the leaf content's half box (minus 2 um, capped 15 um) toward the face"""
    leaf = next((c for c in t.get("contents", []) if c["inst"] == bus_rec.get("leaf", "").split(".")[0]), {})
    box = leaf.get("outline_um", [0, 0])
    return max(0.0, min(15.0, box[0 if bus_rec["face"] in "EW" else 1] / 2.0 - 2.0))


def legs(face, direction, leaf, pts, offset=0.0):
    """(first, second) knee legs of a per_bit chain: leaf (x, y), pin points pts, bus face / dir"""
    lx, ly = leaf
    lx += {"W": -offset, "E": offset}.get(face, 0.0)
    ly += {"S": -offset, "N": offset}.get(face, 0.0)
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    if face in "EW":
        normal = max(abs(min(xs) - lx), abs(max(xs) - lx))
        along = max(abs(min(ys) - ly), abs(max(ys) - ly))
    else:
        normal = max(abs(min(ys) - ly), abs(max(ys) - ly))
        along = max(abs(min(xs) - lx), abs(max(xs) - lx))
    return (normal, along) if direction == "in" else (along, normal)


def worst_hop(face, direction, leaf, pts, n, offset=0.0):
    first, second = legs(face, direction, leaf, pts, offset)
    return knee(first, second, n + 1)[0]


def stations_needed(face, direction, leaf, pts, n=0, limit=PLAN_MARGIN_UM, offset=0.0, cap=30):
    """fewest stations >= n whose kit worst ideal hop is <= limit"""
    first, second = legs(face, direction, leaf, pts, offset)
    while knee(first, second, n + 1)[0] > limit and n < cap:
        n += 1
    return n


def replay(P, raw, type_pins):
    """rows (dict) for every per_bit internal station chain of raw; type_pins(P, tn) -> [(bus, bit, layer, x, y, f)]"""
    rows = []
    for tn in sorted(raw["partition_types"]):
        t = raw["partition_types"][tn]
        ents = [e for e in (t.get("internal_stations") or []) if e.get("bit_route") == "per_bit"]
        if not ents:
            continue
        pins = {}
        for bus, bit, ln, x, y, f in type_pins(P, tn):
            pins.setdefault(bus, {})[int(bit)] = (x, y)
        for e in ents:
            bus = e["conn"].split(":", 1)[1]
            b = next((x for x in t["buses"] if x["name"] == bus), None)
            bp = pins.get(bus) or {}
            n = len(e["regs_um"])
            if b is None or len(bp) not in (int(b["width"]), int(b["width"]) + 1):   # payload (+ epoch) bits
                rows.append(dict(type=tn, bus=bus, dir="?", stations=n, worst=None, entry=e))
                continue
            off = leaf_offset(t, b)
            first, second = legs(b["face"], b["dir"], e["leaf_um"], list(bp.values()), off)
            w, split = knee(first, second, n + 1)
            rows.append(dict(type=tn, bus=bus, dir=b["dir"], face=b["face"], stations=n, worst=round(w, 2),
                             split=split, first=round(first, 1), second=round(second, 1), offset=off,
                             need_limit=stations_needed(b["face"], b["dir"], e["leaf_um"], list(bp.values()), n,
                                                        KIT_LIMIT_UM, off),
                             need_margin=stations_needed(b["face"], b["dir"], e["leaf_um"], list(bp.values()), n,
                                                         PLAN_MARGIN_UM, off),
                             entry=e, legs=(first, second)))
    return rows


def respace(e, direction, m):
    """planner station sites: out (j+1)/(m+1) from_um -> to_um, in (j+2)/(m+2) ring -> consumers"""
    a, b = e["from_um"], e["to_um"]
    k0 = 1 if direction == "out" else 2
    return [[round(a[0] + (b[0] - a[0]) * (j + k0) / (m + k0), 3),
             round(a[1] + (b[1] - a[1]) * (j + k0) / (m + k0), 3)] for j in range(m)]


def main(argv):
    src, plan, out_tsv = argv[1:4]
    argf = lambda k, d: float(argv[argv.index(k) + 1]) if k in argv else d
    global KIT_LIMIT_UM, PLAN_MARGIN_UM
    KIT_LIMIT_UM, PLAN_MARGIN_UM = argf("--limit", KIT_LIMIT_UM), argf("--margin", PLAN_MARGIN_UM)
    fix = argv[argv.index("--fix") + 1: argv.index("--fix") + 3] if "--fix" in argv else None
    sys.path.insert(0, src + "/tools/die_plan")
    import schema as S
    import gen_phys as G
    rb = open(plan, "rb").read()
    raw = json.loads(rb)
    P = S.Plan(copy.deepcopy(raw), path=plan)
    rows = replay(P, raw, G.type_pins)
    changed = set()
    if fix:
        for r in rows:
            if r["worst"] is not None and r["need_margin"] > r["stations"]:
                e, m = r["entry"], r["need_margin"]
                e["regs_um"] = respace(e, r["dir"], m)
                r["fixed_to"], r["worst_after"] = m, round(knee(*r["legs"], m + 1)[0], 2)
                e["note"] = re.sub(r"\+\d+ pin cycles", f"+{m} pin cycles", e.get("note", "")) + \
                    f" | KNEE-1 11-10: {r['stations']}->{m} stations, kit knee worst {r['worst']}->{r['worst_after']} um"
                changed.add(r["type"])
    cols = ["type", "bus", "dir", "face", "stations", "worst", "split", "first", "second", "offset", "need_limit",
            "need_margin", "fixed_to", "worst_after"]
    with open(out_tsv, "w") as fh:
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    fail = [r for r in rows if r["worst"] is not None and r["worst"] > KIT_LIMIT_UM]
    marg = [r for r in rows if r["worst"] is not None and PLAN_MARGIN_UM < r["worst"] <= KIT_LIMIT_UM]
    miss = [r for r in rows if r["worst"] is None]
    print(f"chains {len(rows)} types {len({r['type'] for r in rows})} FAIL>{KIT_LIMIT_UM:g}: {len(fail)} "
          f"margin({PLAN_MARGIN_UM:g},{KIT_LIMIT_UM:g}]: {len(marg)} unchecked: {len(miss)}")
    for r in fail + marg + miss:
        print("  ", {c: r.get(c) for c in cols if c in r})
    if not fix:
        return 1 if (fail or miss) else 0
    out_plan, rep = fix
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n"):
        if f(json.loads(rb)).encode() == rb:
            dump = f
            break
    else:
        raise SystemExit("plan json style unknown")
    PT = raw["partition_types"]
    cnt = lambda tn, bus: sum(len(x["regs_um"]) for x in PT.get(tn, {}).get("internal_stations", [])
                              if x.get("conn") == "bus:" + bus)
    lanes_changed = {}
    for ln in (raw["lanes"] if isinstance(raw["lanes"], list) else list(raw["lanes"].values())):
        a, b = P.ports[ln["ports"][0]], P.ports[ln["ports"][-1]]
        st, dt = P.parts.get(a["src"]["part"], {}).get("type"), P.parts.get(b["dst"]["part"], {}).get("type")
        if not ({st, dt} & changed):
            continue
        want = (cnt(st, a["src"]["bus"]) if st else 0) + (cnt(dt, b["dst"]["bus"]) if dt else 0)
        old = int(ln.get("fixed_cycles", 0))
        if want != old:
            ln["fixed_cycles"] = want
            lanes_changed[ln["id"]] = [old, want]

    def lat(r):
        Q = S.Plan(copy.deepcopy(r), path=plan)
        o = {}
        for l in Q.lanes:
            try:
                o[l] = Q.lane_latency(l)["cycles"]
            except Exception:
                pass
        return o
    L0, L1 = lat(json.loads(rb)), lat(raw)
    delta = {l: [L0.get(l), L1.get(l)] for l in set(L0) | set(L1) if L0.get(l) != L1.get(l)}
    errs = S.validate(raw) if hasattr(S, "validate") else []
    open(out_plan, "w").write(dump(raw))
    sha = hashlib.sha256(open(out_plan, "rb").read()).hexdigest()
    json.dump(dict(limit_um=KIT_LIMIT_UM, margin_um=PLAN_MARGIN_UM, changed_types=sorted(changed),
                   chains=[{k: v for k, v in r.items() if k not in ("entry", "legs")} for r in rows],
                   fixed_cycles_set=lanes_changed, lane_latency_delta=delta, validate_errors=len(errs or []),
                   sha256=sha), open(rep, "w"), indent=1, sort_keys=True)
    print("FIX types", sorted(changed), "lanes", lanes_changed, "latency", delta, "validate", len(errs or []),
          "sha", sha[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
