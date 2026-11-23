"""ADV-LANE-STATIONS (COORD 11-22, estimator, never a gate): kit / relay stations per lane against the latency table, before bind.

QC V4 l1a (OPUS-FIX-QC-V4-R2 23:01): static G0 passed with 0 errors, but the strict bind (2-4 h later) found
sl_W4_fw__arm_wo_arm_ei and sl_W4_fw__arv_wo_arv_ei delivering 12 against table 8 (LANE_ASBUILT UNPRICED_KIT_STATIONS +4): the
kit inserts internal_stations chains on both end buses (src arm_wo 4 + dst arm_ei 4) and the lane's fixed_cycles 4 priced only
half of them.  The strict bind's lane_asbuilt_latency counts the bound RTL; this check predicts the same delivered count from
the plan alone, with the bind's own kit_depth() (kit_istations chain depth of bus:<bus>, + core pin-face chain):

  the bind prices the lane by its receiver pad: u_lpad D = fixed_cycles + R8 pad - kit(src bus_out) (kit_source_station_pricing),
  and a packed u_lpad absorbs the receiver's kit IN stations.  So the lane is long only when the source kit eats the whole budget
  (D <= 0, no pad): delivered = boundary + ft stations + landing + kit(src) + kit(dst bus_in)
  table     = schema lane_latency(lane).cycles (= boundary + ft stations + fixed_cycles + landing + pad), the value the bind
              writes into the table (a composed plan's stored latency.lanes may be stale until the latency refresh)

WARN per lane where delivered > table (the bind would fail UNPRICED_KIT_STATIONS); the fix is fixed_cycles += delta (pre-approved
+cycles) or fewer planned stations.  Not modelled (the bind sees them): bound native u_ist / pads already in the RTL (they only
lower kit), registered hard-pin ends.  One summary line, then the worst lanes.
"""
import sys
from pathlib import Path

CHECK = "ADV-LANE-STATIONS"
MAX_LINES = 20


def _w(*parts):
    return " ".join(["WARN", CHECK] + [str(p) for p in parts])


def estimate(nat, pad, ksrc, kdst):
    """-> delivered cycles predicted for a lane: nat = schema lane_natural dict (cycles, fixed, ...), pad = R8 pad"""
    fixed = int(nat.get("fixed", 0))
    table = int(nat["cycles"]) + pad
    if fixed + pad - ksrc > 0:
        return table                                                # receiver u_lpad D > 0 absorbs the IN stations
    return int(nat["cycles"]) - fixed + ksrc + kdst                # boundary + ft + landing + both kit chains


def _findings(raw, plan_path, tree=None, **_kw):
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    import schema
    import lane_asbuilt_latency as LA
    P = schema.Plan(raw, plan_path)
    types = raw.get("partition_types") or {}
    pads = P.lane_pads()
    hits, n = [], 0
    for lid, ln in sorted(P.lanes.items()):
        ports = [P.ports[q] for q in ln.get("ports", []) if q in P.ports]
        if not ports:
            continue
        n += 1
        a, b = ports[0]["src"], ports[-1]["dst"]

        def k(end):
            if end["part"] == schema.DIE_PART or end["part"] not in P.parts:
                return 0
            bus, core = LA.kit_depth(types.get(P.parts[end["part"]]["type"]), end["bus"])
            return bus + core
        ksrc, kdst = k(a), k(b)
        nat = P.lane_natural(lid)
        pad = int(pads.get(lid, 0) or 0)
        est = estimate(nat, pad, ksrc, kdst)
        t = int(nat["cycles"]) + pad
        if est > t:
            hits.append((est - t, lid, est, t, ksrc, kdst, int(nat.get("fixed", 0)), a, b))
    if not hits:
        return []
    hits.sort(key=lambda h: (-h[0], h[1]))
    out = [_w(f"{len(hits)} of {n} lane(s) deliver more cycles than the latency table once the kit inserts its planned stations "
              f"(strict bind would fail LANE_ASBUILT UNPRICED_KIT_STATIONS); fix fixed_cycles or the station rows")]
    for d, lid, est, t, ks, kd, fx, a, b in hits[:MAX_LINES]:
        out.append(_w(f"{lid}: delivered ~{est} vs table {t} (+{d}): kit stations src {a['part']}.{a['bus']} {ks} + dst "
                      f"{b['part']}.{b['bus']} {kd} vs fixed_cycles {fx}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import json
    p = sys.argv[1]
    for line in findings(json.loads(Path(p).read_text()), p):
        print(line)
