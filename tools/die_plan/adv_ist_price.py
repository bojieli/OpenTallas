"""adv_ist_price.py -- PRECHECK ADV-IST-PRICE (COORD 11-23 20:3x): every lane's native + ft + source station count against its priced cycles.

KV A3c passed PRE, then the strict bind stopped on 'native stations exceed priced lane depth' (native_istations.annotate:
L['cycles'] < 2 + sum(ft stations) + clock_landing + source stations): GROWHOPS had added ft stations the latency table did
not price.  A2g died the same way (lane L415).  The bind reads the STORED latency table (plan latency.lanes) for the priced
cycles but recounts ft stations / landing live from the slots, so a table not refreshed after a plan edit shows up only
2-4 h later.  This check does the same comparison for ALL lanes (native-source or not), from the plan alone:

  STALE-TABLE   stored latency stations / clock_landing differ from the live count (schema.lane_natural): bind LANE_LATENCY /
                LANE_LANDING_LATENCY errors
  PRICE-SHORT   stored cycles < 2 + live ft stations + live landing + source station depth of the lane's OUT bus
                (kit_istations depth + hard-core cycles, LANE_ASBUILT UNPRICED_KIT_STATIONS; native: 'native stations exceed
                priced lane depth')
  FIXED-SPLIT   (needs the as-built: kw asbuilt= / plan_advisory --asbuilt) native-source lane whose fixed_cycles != source
                station regs + max destination regs (bind: 'native stations L415: fixed_cycles must equal source 6 + destination 5');
                the A2f strict refusal that PRICE-SHORT cannot see, since it is about the table's fixed split, not the ft count
  OUT-LANES     (needs the as-built) native source bus of a partition with 0 or >1 outgoing lanes (bind: 'native stations <part>.<bus>:
                expected one outgoing lane', KV A2g pc_EN_7.o_efault_pc_Q_N_fault: an R8 clone lost its lane)
Fix: refresh the latency table (the compose's latency step / reprice) or fixed_cycles += delta (pre-approved).
findings(raw, plan_path, tree=None, **kw) -> WARN lines (advisory in plan_advisory, never raises).
"""
import sys
from pathlib import Path

CHECK = "ADV-IST-PRICE"
MAX_LINES = 20


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def lane_rows(P, LA, schema, types):
    """yield (lane, stored, live_stations, live_landing, src_depth, boundary) for every lane with ports; boundary = the lane's live boundary
    flops (schema.lane_natural: 2 between partitions, 1 for a die-IO end, which has no partition flop)"""
    lat = (P.raw.get("latency") or {}).get("lanes") or {}
    for lid, ln in sorted(P.lanes.items()):
        ports = [P.ports[q] for q in ln.get("ports", []) if q in P.ports]
        if not ports:
            continue
        nat = P.lane_natural(lid)
        a = ports[0]["src"]
        depth = 0
        if a["part"] != schema.DIE_PART and a["part"] in P.parts:
            bus, core = LA.kit_depth(types.get(P.parts[a["part"]]["type"]), a["bus"])
            depth = bus + core
        yield lid, lat.get(lid), int(nat.get("stations", 0)), int(nat.get("clock_landing", 0)), depth, int(nat.get("boundary", 2))


def judge(row, st, land, depth, boundary=2):
    """reasons a lane's STORED latency row (dict stations/clock_landing/cycles) is short of the live counts.
    ISTPRICE-IO-1124: the base is the lane's boundary flops, not a fixed 2: a die-IO lane (din / dout of tiny_plan, boundary 1, cycles 1)
    was PRICE-SHORT '1 < 2' since 11d45bef39d made ISTPRICE a FAIL class (test_publish_gate's 2 failures)."""
    why = []
    if int(row.get("stations", st)) != st:
        why.append(f"STALE-TABLE stations table {row.get('stations')} != live ft stations {st}")
    if int(row.get("clock_landing", 0)) != land:
        why.append(f"STALE-TABLE clock_landing table {row.get('clock_landing', 0)} != live {land}")
    need = boundary + st + land + depth
    if int(row.get("cycles", 0)) < need:
        why.append(f"PRICE-SHORT priced cycles {row.get('cycles')} < {boundary} + ft {st} + landing {land} + source stations {depth} = {need}")
    return why


def native_fixed(P, schema, types, ab, tree_dir):
    """-> {lane: (fixed, source regs, destination regs)} for native-source lanes violating fixed == source + destination"""
    import adv_stn_conflict as S
    bad = {}
    for lid, ln in sorted(P.lanes.items()):
        ports = [P.ports[q] for q in ln.get("ports", []) if q in P.ports]
        if not ports:
            continue
        a, b = ports[0]["src"], ports[-1]["dst"]
        if a["part"] == schema.DIE_PART or a["part"] not in P.parts or b["part"] == schema.DIE_PART or b["part"] not in P.parts:
            continue
        stn, dtn = P.parts[a["part"]]["type"], P.parts[b["part"]]["type"]
        scope = S.native_scope(ab, stn)
        if scope is None or (scope and a["bus"] not in scope):
            continue
        rows = [e for e in (types.get(stn) or {}).get("internal_stations") or [] if isinstance(e, dict) and e.get("conn") == "bus:" + a["bus"]]
        if not rows:
            continue
        src = len(rows[0].get("regs_um") or [])
        dst = max((len(e.get("regs_um") or []) for e in (types.get(dtn) or {}).get("internal_stations") or []
                   if isinstance(e, dict) and e.get("conn") == "bus:" + b["bus"]), default=0)
        fixed = int(ln.get("fixed_cycles", 0))
        if fixed != src + dst:
            bad[lid] = (fixed, src, dst)
    return bad


def native_out_lanes(P, schema, types, ab):
    """-> [(part, bus, n lanes)] native source buses (as-built scope) whose partition has != 1 outgoing lane on that bus"""
    import adv_stn_conflict as S
    cnt = {}
    for lid, ln in P.lanes.items():
        ports = [P.ports[q] for q in ln.get("ports", []) if q in P.ports]
        if ports:
            a = ports[0]["src"]
            cnt[(a["part"], a["bus"])] = cnt.get((a["part"], a["bus"]), 0) + 1
    bad = []
    for part, pr in sorted(P.parts.items()):
        tn = pr["type"]
        scope = S.native_scope(ab, tn)
        t = types.get(tn) or {}
        if scope is None:
            continue
        outs = {b.get("name") for b in t.get("buses") or [] if isinstance(b, dict) and b.get("dir") == "out"}
        rows = {str(e.get("conn", ""))[4:] for e in t.get("internal_stations") or []
                if isinstance(e, dict) and str(e.get("conn", "")).startswith("bus:")}
        for bus in sorted((outs & rows) if not scope else (outs & rows & scope)):
            n = cnt.get((part, bus), 0)
            if n != 1:
                bad.append((part, bus, n))
    return bad


def _findings(raw, plan_path, tree=None, **_kw):
    sys.path.insert(0, str(Path(tree) / "tools" / "die_plan") if tree and (Path(tree) / "tools" / "die_plan" / "schema.py").is_file()
                    else str(Path(__file__).resolve().parent))
    import schema
    import lane_asbuilt_latency as LA
    P = schema.Plan(raw, plan_path)
    types = raw.get("partition_types") or {}
    hits, n, stale, short, notab = [], 0, 0, 0, 0
    for lid, row, st, land, depth, bnd in lane_rows(P, LA, schema, types):
        n += 1
        if not row:
            notab += 1
            continue
        why = judge(row, st, land, depth, bnd)
        if why:
            stale += any(x.startswith("STALE") for x in why)
            short += any(x.startswith("PRICE") for x in why)
            hits.append((-max(2 + st + land + depth - int(row.get("cycles", 0)), 0), _w(f"lane {lid}:", "; ".join(why),
                         "(bind: native stations exceed priced lane depth / LANE_LATENCY); fix: refresh the latency table or fixed_cycles +delta")))
    ab = _kw.get("asbuilt")
    if isinstance(ab, str):
        import json
        with open(ab) as f:
            ab = json.load(f)
    fixed_bad = 0
    if isinstance(ab, dict):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        try:
            for lid, (fx, src, dst) in native_fixed(P, schema, types, ab, tree).items():
                fixed_bad += 1
                hits.append((-1000, _w(f"lane {lid}: FIXED-SPLIT fixed_cycles {fx} != native source stations {src} + destination {dst} "
                                       f"(bind: native stations {lid}: fixed_cycles must equal source {src} + destination {dst}); fix: fixed_cycles = {src + dst}")))
            for part, bus, nl in native_out_lanes(P, schema, types, ab):
                fixed_bad += 1
                hits.append((-999, _w(f"{part}.{bus}: OUT-LANES native source bus has {nl} outgoing lane(s) (bind: native stations {part}.{bus}: "
                                      f"expected one outgoing lane); an R8/param clone or split lost its lane, or the lane is not planned")))
        except ImportError as e:
            hits.append((-1, _w(f"FIXED-SPLIT not checked: {e}")))
    hits.sort(key=lambda h: h[0])
    out = [m for _, m in hits[:MAX_LINES]]
    nr = "" if isinstance(ab, dict) else "NOT-RUN: FIXED-SPLIT and OUT-LANES (no as-built given: pass the integrator's current as-built, plan_advisory --asbuilt) -- "
    out.append(_w("summary", f"{nr}{len(hits)} of {n} lanes flagged ({short} PRICE-SHORT, {stale} STALE-TABLE, {fixed_bad} FIXED-SPLIT/OUT-LANES); {notab} lanes without a latency row"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None,
                       asbuilt=sys.argv[3] if len(sys.argv) > 3 else None):
        print(ln)
