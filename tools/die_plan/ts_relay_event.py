#!/usr/bin/env python3
"""TYPE-SAFE-2 11-08 (OWNER 11-08 04:58 "add the missing registers or relays immediately to make sure all types are
safe by construction"; OWNER 11-03 pin cycles are a lever): the RELAY constructor.  A plan event, run LAST on a die's
combined plan.  It never blocks; it only adds relay stages on face-bus <-> hard-core wiring that is longer than reach.

Why: the native bind joins face buses to hard-core ports through wiring only (concatenations, lane pads u_lpad_*,
kept transport chains u_d<k>_*).  The plan does not see that connectivity, so check.py R3-INTERNAL is blind and no
station is planned (S81 slice_C: ret/leaf lanes cross 1.3-2.4 mm inside the type with 0-1 stage).

For every type with a bound module (--bound TYPE=PATH, or --bound-list FILE of "TYPE<tab>PATH" lines):
  1. connectivity: core_conns_from_bind.trace (wiring only, no logic in between) -> (bus, dir, core.port) paths
  2. per bus: d = worst-bit Manhattan from the plan bus window centre to the core pins (plan pins_file, origin,
     track_offset, orient) over all cores the bus reaches; n = ceil(d / (405 * 0.98)) - 1 stages
  3. SLACK FIRST, then pin cycles, per lane of every instance of the type (schema.Plan.lane_latency):
       OUT buses first: native_istations realises source stations before u_bout and requires fixed == source +
                destination stations; s = max(n, fixed - destination need) so the lane's slack moves into the source
                (0 cycles); fixed = s + destination.  The type is listed in event.native_out_types for the bind
                recipe (asbuilt.internal_stations_types).
       IN  buses: the receiver pad (fixed - source stations) lands as reset-less stages u_lpad_<bus> right after
                the face flop; count = max(n, pad); fixed = source + count.  kit_istations packed_input_delay sites the
                u_lpad registers on the entry's regs_um (no new stage).
     PIN CYCLES = the fixed_cycles delta per lane (gen.py latency regenerates the table the compiler reads).
  4. buses that already have an internal_stations entry, COUNTED/SIGNED types (--skip-types) and buses whose lane is
     not found are reported, never touched.
Every key outside the edits is asserted byte-identical (sort_keys compare); the output passes schema validation.

    python3 -I tools/die_plan/ts_relay_event.py BASE OUT EVENT --pins-root DIR --bound T=P [--bound-list F]
                                                 [--skip-types a,b] [--only-types a,b]
"""
import argparse
import copy
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import core_conns_from_bind as CCB  # noqa: E402

REACH = 405.0
STEP = REACH * 0.98


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def on_L(a, b, n):
    """n points at equal Manhattan arc length on the L a -> (b.x, a.y) -> b"""
    tot, dx = man(a, b), abs(b[0] - a[0])
    out = []
    for k in range(1, n + 1):
        s = tot * k / (n + 1)
        if s <= dx:
            out.append([round(a[0] + math.copysign(s, b[0] - a[0]), 3), round(a[1], 3)])
        else:
            out.append([round(b[0], 3), round(a[1] + math.copysign(s - dx, b[1] - a[1]), 3)])
    return out


_PINS = {}


def core_port_pins(hc, root):
    f = Path(root) / hc["pins_file"] if hc.get("pins_file") else None
    raw = []
    if f is not None:
        if f not in _PINS:
            js = json.loads(f.read_text())
            js = js.get("pins", js) if isinstance(js, dict) else js
            _PINS[f] = [(q.get("name") or f"{q['bus']}[{q.get('bit', 0)}]", q["x"], q["y"]) for q in js]
        raw = list(_PINS[f])
    raw += [(p["name"], *p["xy"]) for p in hc.get("pins", [])]
    w, h = hc["outline_um"]
    ox, oy = hc["origin_um"]
    dx, dy = hc.get("track_offset_um", [0.0, 0.0])
    o = hc.get("orient", "R0")
    out = defaultdict(list)
    for nm, x, y in raw:
        if o in ("MY", "R180"):
            x = w - x
        if o in ("MX", "R180"):
            y = h - y
        out[nm.split("[")[0]].append((ox + dx + x, oy + dy + y))
    return out


def window_pt(t, b):
    w, h = t["outline_um"]
    m = 0.5 * sum(b["window_um"])
    return dict(N=(m, h), S=(m, 0.0), E=(w, m), W=(0.0, m))[b["face"]]


_IX = {}


def lanes_of(raw, tn, bus, dirn):
    """[(lane id, part)] of every instance of type tn whose lane enters (in) / leaves (out) on bus"""
    if id(raw) not in _IX:
        ports = {p["id"]: p for p in raw["ports"]}
        ptype = {p["name"]: p["type"] for p in raw["partitions"]}
        ix = defaultdict(list)
        for ln in raw["lanes"]:
            a, b = ports[ln["ports"][0]], ports[ln["ports"][-1]]
            for d, e in (("out", a["src"]), ("in", b["dst"])):
                if e.get("part") in ptype:
                    ix[(ptype[e["part"]], e["bus"], d)].append((ln["id"], e["part"]))
        _IX[id(raw)] = ix
    return list(_IX[id(raw)].get((tn, bus, dirn), []))


def _src_part(raw, lid):
    """(source part, source bus, dest part, dest bus) of lane lid"""
    if "_PX" not in _IX:
        ports = {p["id"]: p for p in raw["ports"]}
        _IX["_PX"] = {ln["id"]: (ports[ln["ports"][0]]["src"], ports[ln["ports"][-1]]["dst"]) for ln in raw["lanes"]}
    s, d = _IX["_PX"][lid]
    return s.get("part"), s.get("bus"), d.get("part"), d.get("bus")


def _entry(t, bus):
    return next((e for e in t.get("internal_stations", []) if e.get("conn") == f"bus:{bus}"), None)


def build(raw, bound, root, skip, only=None, native_base=()):
    """Two passes so every lane keeps native_istations' invariant fixed == source stations + destination stations:
    OUT buses first (source stations take the lane's slack: s = max(n_out, fixed - destination need)), then IN buses
    (receiver pad = fixed - source stations; count = max(n_in, pad); fixed = source + count).  Lane latency never
    shrinks; PIN CYCLES = final fixed - base fixed."""
    import schema as S
    Q = copy.deepcopy(raw)
    P0 = S.Plan(copy.deepcopy(raw))
    lane_by_id = {ln["id"]: ln for ln in Q["lanes"]}
    F0 = {lid: int(ln.get("fixed_cycles", 0)) for lid, ln in lane_by_id.items()}
    ptype = {p["name"]: p["type"] for p in Q["partitions"]}
    edits, reported, native_out = [], [], set()
    cand = {}                                   # (tn, dir, bus) -> (n, row, a)
    for tn, bpath in sorted(bound.items()):
        if tn in skip or (only and tn not in only) or tn not in Q["partition_types"]:
            continue
        t = Q["partition_types"][tn]
        if t.get("hard"):
            continue
        conns = CCB.trace(raw, tn, Path(bpath).read_text())
        hcs = {hc["inst"]: hc for hc in t.get("hard_cores", [])}
        pins = {ci: core_port_pins(hc, root) for ci, hc in hcs.items()}
        buses = {b["name"]: b for b in t.get("buses", [])}
        have_ist = {e.get("conn") for e in t.get("internal_stations", [])}
        per_bus = defaultdict(lambda: dict(d=0.0, far=None, ports=set()))
        for p in conns["paths"]:
            if "bus" not in p or p["bus"] not in buses:
                continue
            pp = pins.get(p["core"], {}).get(p["port"])
            if not pp:
                continue
            w = window_pt(t, buses[p["bus"]])
            d = max(man(xy, w) for xy in pp)
            a = per_bus[(p["dir"], p["bus"])]
            a["ports"].add(f"{p['core']}.{p['port']}")
            if d > a["d"]:
                cen = (sum(x for x, _ in pp) / len(pp), sum(y for _, y in pp) / len(pp))
                a.update(d=d, far=cen, win=w)
        for (dirn, bus), a in sorted(per_bus.items()):
            n = max(0, math.ceil(a["d"] / STEP) - 1)
            row = dict(type=tn, bus=bus, dir=dirn, d_um=round(a["d"], 1), need=n, ports=sorted(a["ports"]))
            if n == 0:
                continue
            if f"bus:{bus}" in have_ist:
                reported.append(dict(row, action="REPORT: bus already has internal_stations (owner's entry kept)"))
                continue
            if not lanes_of(Q, tn, bus, dirn):
                reported.append(dict(row, action="REPORT: no plan lane on this bus"))
                continue
            cand[(tn, dirn, bus)] = (n, row, a)
    native = set(native_base)

    def dest_need(lid):
        _, _, dp, db = _src_part(Q, lid)
        dt = ptype.get(dp)
        e = _entry(Q["partition_types"].get(dt, {}), db) if dt else None
        if e is not None:
            return len(e["regs_um"])
        c = cand.get((dt, "in", db))
        return c[0] if c else 0

    def src_count(lid):
        sp, sb, _, _ = _src_part(Q, lid)
        st = ptype.get(sp)
        if st not in native and st not in native_out:
            return 0
        e = _entry(Q["partition_types"][st], sb)
        return len(e["regs_um"]) if e else 0
    touched = []                                # (tn, dir, bus, n, row, count, lanes)
    for (tn, dirn, bus), (n, row, a) in sorted(cand.items(), key=lambda kv: kv[0][1] != "out"):
        t = Q["partition_types"][tn]
        lns = [lid for lid, _ in lanes_of(Q, tn, bus, dirn)]
        frm, to = a["win"], a["far"]
        if dirn == "out":
            count = max([n] + [F0[lid] - dest_need(lid) for lid in lns])
            for lid in lns:
                lane_by_id[lid]["fixed_cycles"] = count + dest_need(lid)
            ent = dict(conn=f"bus:{bus}", from_um=[round(v, 3) for v in frm], to_um=[round(v, 3) for v in to],
                       regs_um=on_L(frm, to, count), launch=sorted(a["ports"])[0], capture="face flop",
                       note=f"TYPE-SAFE-2 11-08 relay: {', '.join(sorted(a['ports'])[:3])} -> face {bus} "
                            f"{a['d']:.0f} um, {n} needed, {count} source stations (lane slack moved first)")
            native_out.add(tn)
        else:
            pads = {lid: int(lane_by_id[lid].get("fixed_cycles", 0)) - src_count(lid) for lid in lns}
            count = max([n] + list(pads.values()))
            for lid in lns:
                lane_by_id[lid]["fixed_cycles"] = src_count(lid) + count
            # the receiver pad u_lpad_<bus> (D = count) is realised by the bind; kit_istations packed_input_delay
            # sites its registers on these planned sites (no new stage)
            ent = dict(conn=f"bus:{bus}", from_um=[round(v, 3) for v in frm], to_um=[round(v, 3) for v in to],
                       regs_um=on_L(frm, to, count), launch="face flop", capture=sorted(a["ports"])[0],
                       note=f"TYPE-SAFE-2 11-08 relay: face {bus} -> {', '.join(sorted(a['ports'])[:3])} "
                            f"{a['d']:.0f} um, {n} needed, {count} receiver pad stages sited")
        t.setdefault("internal_stations", []).append(ent)
        touched.append((row, count, lns))
    for row, count, lns in touched:
        lat = {lid: P0.lane_latency(lid) for lid in lns}
        edits.append(dict(row, count=count, lanes={lid: dict(cycles=lat[lid]["cycles"],
                                                             delta=int(lane_by_id[lid]["fixed_cycles"]) - F0[lid])
                                                   for lid in lns}))
    # native_istations invariant on every touched lane whose source type realises OUT stations natively
    for row, count, lns in touched:
        for lid in lns:
            sp, sb, dp, db = _src_part(Q, lid)
            if ptype.get(sp) in native | native_out and _entry(Q["partition_types"][ptype[sp]], sb) is not None:
                e = _entry(Q["partition_types"].get(ptype.get(dp), {}), db)
                want = src_count(lid) + (len(e["regs_um"]) if e else 0)
                if int(lane_by_id[lid]["fixed_cycles"]) != want:
                    raise AssertionError(f"lane {lid}: fixed_cycles {lane_by_id[lid]['fixed_cycles']} != source + "
                                         f"destination stations {want}")
    for lid, ln in lane_by_id.items():
        if int(ln.get("fixed_cycles", 0)) < F0[lid]:
            raise AssertionError(f"lane {lid}: fixed_cycles would shrink {F0[lid]} -> {ln['fixed_cycles']}")
    return Q, edits, reported, sorted(native_out)


def _style(raw_bytes, P):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(P).encode() == raw_bytes:
            return f
    return lambda p: json.dumps(p, separators=(",", ":")) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("event")
    ap.add_argument("--pins-root", required=True)
    ap.add_argument("--bound", action="append", default=[])
    ap.add_argument("--bound-list")
    ap.add_argument("--skip-types", default="")
    ap.add_argument("--only-types", default="")
    ap.add_argument("--native-types", default="", help="base asbuilt internal_stations_types (their OUT entries are "
                    "realised as source stations by the bind)")
    a = ap.parse_args(argv)
    bound = dict(s.split("=", 1) for s in a.bound)
    if a.bound_list:
        for ln in Path(a.bound_list).read_text().splitlines():
            if ln.strip() and not ln.startswith("#"):
                k, v = ln.split("\t")[:2]
                bound[k] = v
    raw_b = Path(a.base).read_bytes()
    P0 = json.loads(raw_b)
    style = _style(raw_b, P0)
    skip = {s for s in a.skip_types.split(",") if s}
    only = {s for s in a.only_types.split(",") if s} or None
    Q, edits, reported, native_out = build(P0, bound, a.pins_root, skip, only,
                                           {s for s in a.native_types.split(",") if s})
    touched = {e["type"] for e in edits}
    touched_lanes = {lid for e in edits for lid in e["lanes"]}
    for k in P0:
        if k in ("partition_types", "lanes"):
            continue
        if json.dumps(P0[k], sort_keys=True) != json.dumps(Q[k], sort_keys=True):
            raise AssertionError(f"top-level key {k} changed")
    for tn, v in P0["partition_types"].items():
        if tn not in touched and json.dumps(v, sort_keys=True) != json.dumps(Q["partition_types"][tn], sort_keys=True):
            raise AssertionError(f"type {tn} changed but is not listed")
    for l0, l1 in zip(P0["lanes"], Q["lanes"]):
        if l0["id"] not in touched_lanes and json.dumps(l0, sort_keys=True) != json.dumps(l1, sort_keys=True):
            raise AssertionError(f"lane {l0['id']} changed but is not listed")
        if l0["id"] in touched_lanes:
            d0 = {k: v for k, v in l0.items() if k != "fixed_cycles"}
            d1 = {k: v for k, v in l1.items() if k != "fixed_cycles"}
            if json.dumps(d0, sort_keys=True) != json.dumps(d1, sort_keys=True):
                raise AssertionError(f"lane {l0['id']}: a key other than fixed_cycles changed")
    import schema as S
    # only errors the event introduces fail it (a base plan may carry keys newer than this tool tree's schema)
    base_errs = set(map(str, S.validate(copy.deepcopy(P0))))
    errs = [e for e in map(str, S.validate(copy.deepcopy(Q))) if e not in base_errs]
    if errs:
        raise SystemExit("ts_relay_event: output plan fails schema validation: " + "; ".join(map(str, errs[:5])))
    data = style(Q).encode()
    Path(a.out).write_bytes(data)
    pin = defaultdict(int)
    for e in edits:
        for lid, v in e["lanes"].items():
            pin[lid] = max(pin[lid], v["delta"])
    rec = dict(schema="opentallas.ts_relay_event.v1", tool="tools/die_plan/ts_relay_event.py",
               owner="OWNER 2026-11-08 04:58 relays + 2026-11-03 pin cycles; lane TYPE-SAFE-2",
               base_plan=str(a.base), base_plan_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_output=str(a.out), plan_output_sha256=hashlib.sha256(data).hexdigest(),
               bound=bound, skipped_types=sorted(skip), edits=edits, reported=reported,
               native_out_types=native_out,
               pin_cycle_deltas={k: v for k, v in sorted(pin.items()) if v},
               totals=dict(types=len(touched), buses=len(edits), lanes=len(touched_lanes),
                           lanes_with_pin_cycles=sum(1 for v in pin.values() if v),
                           pin_cycles_sum=sum(pin.values()), stations=sum(e["count"] for e in edits)),
               preservation="only partition_types[touched].internal_stations and lanes[touched].fixed_cycles change; "
                            "every other key byte-identical (sort_keys compare); RTL/outlines/pins/cores unchanged")
    Path(a.event).write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["totals"]))


if __name__ == "__main__":
    main()
