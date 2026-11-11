#!/usr/bin/env python3
"""HBM-VSN-XTAP 11-11 (COORD 04:18 ruling, S7 generator class fix; vsN4 forms B and C both failed the cross-tap
half-cycle latch leg): an ft hop k -> k+1 of a type on clock.ft_hop_lockup whose launch and capture stations hang on
DIFFERENT clock taps gets a FULL-CYCLE hop flop (ot_dp_st, instance u_fx_*, reset-less, data + epoch) plus ONE pin
cycle in place of the transparent-low lockup latch u_fl_*.  Same-tap hops keep the latch (T/2 leg, CRPR on one tap).

Why: the latch -> capture leg has T/2 - W - skew of setup.  On vsN4 (form C) a latch on clk_t5 (420 ps tree) fed
u_ft_L9mx2_o_2 on clk_t12 (269 ps tree, -160 window): 106 ps left for 152 ps of data + 34 ps setup.  The hop flop
sits on the LAUNCH station's tap (clock_taps.tcl hop pass, as the latch), at the hop midpoint (face_flops.tcl), so
the flop -> capture leg has T - W - skew (~520 ps) and hold buffers fit in it.

The hop set is PLAN DATA (explicit, reviewable, EQ-visible):
    clock.ft_hop_lockup.xtap_flop = {type: {slot: [k, ...]}}   (k = launch station index, 0 <= k < stations - 1)
read by schema.ft_hop_xtap (lane_natural counts each listed hop as one register stage, so gen.py latency, the bind
lane pads and the compiler table see the cycle) and by the RTL emitters (bind.py / gen_rtl.py).

This tool PREDICTS the hops from the plan geometry, the way the kit assigns clock sinks (clock_taps.tcl nearest pass,
Manhattan distance to the type's grid taps S.tap_grid): station j >= 1 bit b at its bit site (bit_sites_um[j-1][b])
or its regs_um site, station 0 (the in-face register) at its in-port pin (gen_phys.type_pins) or the projection of
station 1 onto the in face.  A hop is cross-tap when ANY bit's two stations have different nearest taps.  The cap /
merge passes of the kit can still move sinks; a hop predicted same-tap keeps its latch (the 11-06 form) and a hop
predicted cross-tap pays one cycle even if the kit later lands it on one tap (safe direction).

    ft_xtap.py predict PLAN [--types T ...] [--json OUT]
    ft_xtap.py event PLAN OUT_PLAN RECEIPT [--types T ...] [--note N]
        event: writes the map for every lockup type with >= 1 cross-tap hop (or only --types), recomputes
        latency.lanes (gen.latency_table, the compiler's LAT ABI) when the plan carries one, asserts every other key
        byte-identical, and records per type/slot the hops and per lane the cycle delta.
"""
import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import gen_rtl  # noqa: E402

FACE_AXIS = {"S": ("y", 0), "N": ("y", 1), "W": ("x", 0), "E": ("x", 1)}


def _nearest(taps, x, y):
    best, bd = None, None
    for name, tx, ty in taps:
        d = abs(x - tx) + abs(y - ty)
        if bd is None or d < bd:
            best, bd = name, d
    return best


def _in_pins(P, tn, slot):
    """{bit: (x, y)} of the slot's in port pins in the type frame ({} when the plan has no instance / ports)."""
    try:
        import gen_phys
        pins = gen_phys.type_pins(P, tn)
    except Exception:
        return {}
    want = gen_rtl.sv_id(slot + "_i")
    return {int(b): (float(x), float(y)) for bn, b, _l, x, y, _f in pins if gen_rtl.sv_id(bn) == want}


def station_sites(P, tn, s):
    """[[(x, y) per bit] per station] for ft slot s of type tn (type frame, um); bits = the slot's planned sites."""
    t = P.types[tn]
    w, h = t["outline_um"]
    n = int(s.get("stations", 1))
    bs = s.get("bit_sites_um") or []
    regs = s.get("regs_um") or []
    nb = int(s.get("width", 1))
    st = [None] * n
    for j in range(1, n):
        if len(bs) == n - 1 and bs[j - 1]:
            st[j] = [tuple(map(float, p)) for p in bs[j - 1]]
        elif len(regs) == n:
            st[j] = [tuple(map(float, regs[j]))]
    if n >= 1:
        pins = _in_pins(P, tn, s["name"])
        if pins:
            st[0] = [pins[b] for b in sorted(pins)]
        elif len(regs) == n:
            st[0] = [tuple(map(float, regs[0]))]
        elif n > 1 and st[1]:
            ax, side = FACE_AXIS.get(s.get("in_face", "W"), ("x", 0))
            lim = (h if ax == "y" else w) * side
            st[0] = [(x, lim) if ax == "y" else (lim, y) for x, y in st[1]]
    # bit lists of unequal length (pins carry the epoch bit, sites may not): compare bit b with min(b, len - 1)
    return st, nb


def predict_slot(P, tn, s, taps):
    """[k] cross-tap hops of slot s; None for a hop whose sites are unknown counts as cross-tap (safe direction)."""
    st, _ = station_sites(P, tn, s)
    out = []
    for k in range(len(st) - 1):
        a, b = st[k], st[k + 1]
        if not a or not b:
            out.append(k)
            continue
        m = max(len(a), len(b))
        ta = [_nearest(taps, *a[min(i, len(a) - 1)]) for i in range(m)]
        tb = [_nearest(taps, *b[min(i, len(b) - 1)]) for i in range(m)]
        if any(x != y for x, y in zip(ta, tb)):
            out.append(k)
    return out


def predict(P, types=None):
    """{type: {slot: [k]}} for every type on ft_hop_lockup with >= 2 grid taps (types with no cross-tap hop omitted)."""
    res = {}
    for tn in sorted(P.types):
        if types and tn not in types:
            continue
        if not gen_rtl.ft_hop_lockup(P.raw, tn):
            continue
        taps = S.tap_grid(P, tn)
        if len(taps) < 2:
            continue
        d = {}
        for s in P.types[tn].get("ft_slots", []):
            if int(s.get("stations", 1)) < 2:
                continue
            hops = predict_slot(P, tn, s, taps)
            if hops:
                d[s["name"]] = hops
        if d:
            res[tn] = d
    return res


def _sha(o):
    return hashlib.sha256(json.dumps(o, sort_keys=True).encode()).hexdigest()


def event(raw, types=None, note=None):
    import gen
    P0 = S.Plan(raw)
    xt = predict(P0, types)
    new = copy.deepcopy(raw)
    lk = dict(new["clock"]["ft_hop_lockup"])
    lk["xtap_flop"] = xt
    if note:
        lk["note"] = note
    new["clock"]["ft_hop_lockup"] = lk
    lat0 = {lid: P0.lane_latency(lid)["cycles"] for lid in P0.lanes}
    P1 = S.Plan(new)
    lat1 = {lid: P1.lane_latency(lid)["cycles"] for lid in P1.lanes}
    stale = []
    if "latency" in raw and "lanes" in (raw.get("latency") or {}):
        # only the lanes the hop flops lengthen change; every other row stays byte-identical (a base row that differs
        # from the plan computation -- a pre-existing G0 latency finding -- is shifted by the delta, never recomputed)
        t0, t1 = gen.latency_table(P0), gen.latency_table(P1)
        tab = copy.deepcopy(raw["latency"]["lanes"])
        for lid in lat0:
            if lat1[lid] == lat0[lid] and t0.get(lid) == t1.get(lid):
                continue
            old = tab.get(lid)
            if old is not None and old == t0.get(lid):
                tab[lid] = t1[lid]
            elif old is not None:
                stale.append(lid)
                nd = dict(old)
                for k in ("cycles", "stations", "natural", "pad", "word_cycles"):
                    if k in nd and k in t0[lid] and k in t1[lid]:
                        nd[k] = nd[k] + t1[lid][k] - t0[lid][k]
                tab[lid] = nd
        new["latency"] = {**raw["latency"], "lanes": tab}
    for k in raw:
        if k not in ("clock", "latency"):
            assert _sha(raw[k]) == _sha(new[k]), k
    ca = {k: v for k, v in raw["clock"].items() if k != "ft_hop_lockup"}
    cb = {k: v for k, v in new["clock"].items() if k != "ft_hop_lockup"}
    assert _sha(ca) == _sha(cb)
    oa = {k: v for k, v in raw["clock"]["ft_hop_lockup"].items() if k not in ("xtap_flop", "note")}
    ob = {k: v for k, v in lk.items() if k not in ("xtap_flop", "note")}
    assert _sha(oa) == _sha(ob)
    dl = {lid: lat1[lid] - lat0[lid] for lid in lat0 if lat1[lid] != lat0[lid]}
    rows = []
    for tn, d in sorted(xt.items()):
        for sl, hops in sorted(d.items()):
            s = next(x for x in P0.types[tn]["ft_slots"] if x["name"] == sl)
            rows.append(dict(type=tn, slot=sl, stations=int(s.get("stations", 1)), width=s.get("width"),
                             xtap_hops=hops, latch_hops=[k for k in range(int(s.get("stations", 1)) - 1) if k not in hops]))
    rec = dict(event="HBM-VSN-XTAP-1111", tool="tools/die_plan/ft_xtap.py", rule="cross-tap ft hop: flop + 1 cycle; same-tap: latch",
               plan_in_sha256=_sha(raw), plan_out_sha256=_sha(new), types=sorted(xt), slots=rows,
               hop_flops=sum(len(r["xtap_hops"]) for r in rows), hop_latches_kept=sum(len(r["latch_hops"]) for r in rows),
               lane_cycle_delta=dl, lanes_changed=len(dl), max_lane_delta=max(dl.values(), default=0),
               stale_base_rows_shifted=stale,
               latency_table_rewritten="latency" in raw and "lanes" in (raw.get("latency") or {}))
    return new, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("predict")
    a.add_argument("plan")
    a.add_argument("--types", nargs="*")
    a.add_argument("--json")
    b = sub.add_parser("event")
    b.add_argument("plan")
    b.add_argument("out")
    b.add_argument("receipt")
    b.add_argument("--types", nargs="*")
    b.add_argument("--note")
    x = ap.parse_args(argv)
    raw = json.loads(Path(x.plan).read_text())
    if x.cmd == "predict":
        r = predict(S.Plan(raw), x.types)
        txt = json.dumps(r, indent=1, sort_keys=True)
        (Path(x.json).write_text(txt + "\n") if x.json else print(txt))
        return 0
    new, rec = event(raw, x.types, x.note)
    Path(x.out).write_text(json.dumps(new, indent=1) + "\n")
    Path(x.receipt).write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(f"types {len(rec['types'])} slots {len(rec['slots'])} hop flops {rec['hop_flops']} latches kept "
          f"{rec['hop_latches_kept']} lanes +cycles {rec['lanes_changed']} (max +{rec['max_lane_delta']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
