#!/usr/bin/env python3
"""TYPE-SAFE-1 11-08 (OWNER 04:58 "add the missing registers or relays immediately to make sure all types are safe by
construction"; OWNER 05:03 approved (A) hold-safe hops and (B) macro congestion budget): ONE plan event per die that
CONSTRUCTS the type rules from the existing plan machinery.  A constructor, not a gate: it only adds, never blocks.

  rule 2  reach <= 405 um per hop:
          (a) ft slots: opt-in --ft (ft_reach.resize, macrofree_only False).  Default OFF: on the 11-08 wave plans every
              slot it would raise already has FIRM regs_um / bit_sites_um that pass the G0C hop check (resize counts
              pin-to-pin length / reach, not the sited hops, and breaks the regs_um == stations - 1 schema rule);
          (b) tap-tree forward legs (fwd_reach.py audit) over reach get FIRM internal_stations (conn bus:<out>, regs_um
              on the L path, kit_istations realises them).
          Added stations are register stages: the pin-cycle delta per lane comes from schema.Plan.lane_latency before
          and after (gen.py latency recomputes the table the compiler reads).
  rule 3  launch and capture on matched taps: clock.tap_pair_affinity {} (QC-TYPES-6 form, proven by QC qc52t:
          reg2reg < -40 ps 1161 -> 12) on every type with >= 2 tap ports that lacks it; bounds checked by
          gen_phys.tap_pair_affinity_exports.  Clock pins only, no RTL change.
  rule 4  reset relays <= 405 um: reset_tree relay_um default 405 already; recorded, not changed.
  (A)/(B) and rule 1 core-face stages: reported per type (lockup candidates, faces > 70 %, channels) for the
          per-hop / per-core steps; not applied by this event.

    python3 tools/die_plan/type_safe_event.py BASE_PLAN OUT_PLAN EVENT_JSON [--skip-types a,b] [--ft] [--no-fwd] [--no-tap]

The output keeps the base file's JSON style; every key outside the edits is asserted byte-identical."""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S  # noqa: E402
import gen_phys  # noqa: E402
import ft_reach  # noqa: E402

REACH = 405.0


def _style(raw_bytes, P):
    for f in (lambda p: json.dumps(p, separators=(",", ":")) + "\n", lambda p: json.dumps(p) + "\n",
              lambda p: json.dumps(p, indent=1) + "\n", lambda p: json.dumps(p, indent=2) + "\n",
              lambda p: json.dumps(p, separators=(",", ":")), lambda p: json.dumps(p)):
        if f(P).encode() == raw_bytes:
            return f
    return lambda p: json.dumps(p, separators=(",", ":")) + "\n"


def lane_cycles(raw):
    P = S.Plan(copy.deepcopy(raw))
    out = {}
    for lid in P.lanes:
        try:
            out[lid] = P.lane_latency(lid)["cycles"]
        except Exception:      # noqa: BLE001 - a lane the model cannot time stays unreported, never fails the event
            continue
    return out


def tap_pair(raw, skip):
    added, refused = [], []
    for tn, t in raw["partition_types"].items():
        if tn in skip or t.get("hard"):
            continue
        ck = t.get("clock")
        if not isinstance(ck, dict) or len(ck.get("taps") or []) < 2 or "tap_pair_affinity" in ck:
            continue
        ck["tap_pair_affinity"] = {}
        try:
            gen_phys.tap_pair_affinity_exports(t)
            added.append(tn)
        except ValueError as e:
            del ck["tap_pair_affinity"]
            refused.append(dict(type=tn, reason=str(e)))
    return added, refused


def fwd_stations(raw, plan_path, skip):
    import fwd_reach
    import check as C
    P = S.Plan(copy.deepcopy(raw), path=Path(plan_path).resolve())
    reach = C.station_max(P)
    tree = {}
    for lid, ln in P.lanes.items():
        nt = str(ln.get("note", ""))
        if nt.startswith("tap_tree"):
            tree[lid] = nt.split("|")[0].strip()
    from collections import defaultdict
    ins, outs = defaultdict(lambda: defaultdict(set)), defaultdict(lambda: defaultdict(set))
    for pid, pr in P.ports.items():
        lid = pid.rsplit("_", 1)[0]
        if lid not in tree:
            continue
        for side, acc in (("src", outs), ("dst", ins)):
            e = pr[side]
            if e["part"] in P.parts:
                acc[P.parts[e["part"]]["type"]][tree[lid]].add(e["bus"])
    added = []
    for tn in sorted(set(ins) & set(outs)):
        t = raw["partition_types"][tn]
        if tn in skip or t.get("hard"):
            continue
        have = {e.get("conn") for e in t.get("internal_stations", [])}
        bt = C._bus_targets(P, tn)
        for net in sorted(set(ins[tn]) & set(outs[tn])):
            for ib in sorted(ins[tn][net]):
                for ob in sorted(outs[tn][net]):
                    if ib.startswith("ft") or ob.startswith("ft") or ib not in bt or ob not in bt:
                        continue
                    if f"bus:{ob}" in have:
                        continue
                    pa, pb = bt[ib][1], bt[ob][1]
                    d = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
                    if d <= reach + 1e-6:
                        continue
                    n = max(1, math.ceil(d / (reach * .98)) - 1)
                    e = dict(conn=f"bus:{ob}", from_um=[round(v, 3) for v in pa], to_um=[round(v, 3) for v in pb],
                             regs_um=fwd_reach.stations_on_L(pa, pb, n), launch="face flop", capture="face flop",
                             note=f"TYPE-SAFE-1 11-08 fwd leg {ib} -> {ob} ({net}) {d:.0f} um > {reach:g}")
                    t.setdefault("internal_stations", []).append(e)
                    have.add(f"bus:{ob}")
                    added.append(dict(type=tn, in_bus=ib, out_bus=ob, dist_um=round(d, 1), stations=n))
    return added


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base")
    ap.add_argument("out")
    ap.add_argument("event")
    ap.add_argument("--skip-types", default="")
    ap.add_argument("--ft", action="store_true", help="also run ft_reach.resize (see rule 2a)")
    ap.add_argument("--no-fwd", action="store_true")
    ap.add_argument("--no-tap", action="store_true")
    a = ap.parse_args(argv)
    raw_b = Path(a.base).read_bytes()
    P0 = json.loads(raw_b)
    style = _style(raw_b, P0)
    skip = {s for s in a.skip_types.split(",") if s}
    Q = copy.deepcopy(P0)
    before = lane_cycles(P0)
    taps, refused = ([], []) if a.no_tap else tap_pair(Q, skip)
    ft = [] if not a.ft else [r for r in ft_reach.resize(Q, reach_um=REACH, margin=.98, macrofree_only=False)
                             if r["type"] not in skip]
    if skip and a.ft:      # undo resizes on skipped types (resize has no skip list)
        for tn in skip:
            if tn in Q["partition_types"]:
                Q["partition_types"][tn] = copy.deepcopy(P0["partition_types"][tn])
    fwd = [] if a.no_fwd else fwd_stations(Q, a.base, skip)
    after = lane_cycles(Q)
    deltas = {lid: [before[lid], after[lid]] for lid in after if lid in before and after[lid] != before[lid]}
    # preservation: only partition_types changed, and only on the listed types
    for k in P0:
        if k not in ("partition_types",) and json.dumps(P0[k], sort_keys=True) != json.dumps(Q[k], sort_keys=True):
            raise AssertionError(f"top-level key {k} changed")
    touched = set(taps) | {r["type"] for r in ft} | {r["type"] for r in fwd}
    for tn, v in P0["partition_types"].items():
        if tn not in touched and json.dumps(v, sort_keys=True) != json.dumps(Q["partition_types"][tn], sort_keys=True):
            raise AssertionError(f"type {tn} changed but is not listed")
    errs = S.validate(copy.deepcopy(Q))
    if errs:
        raise SystemExit("type_safe_event: output plan fails schema validation: " + "; ".join(map(str, errs[:5])))
    data = style(Q).encode()
    Path(a.out).write_bytes(data)
    lanes = S.Plan(copy.deepcopy(Q)).lanes
    by_type = {}
    for lid, (c0, c1) in deltas.items():
        ln = lanes.get(lid, {})
        by_type.setdefault(lid, dict(lane=lid, cycles=[c0, c1], delta=c1 - c0, src=ln.get("src"), dst=ln.get("dst")))
    rec = dict(schema="opentallas.type_safe_event.v1", tool="tools/die_plan/type_safe_event.py",
               owner="OWNER 2026-11-08 04:58 + 05:03 (A)(B); lane TYPE-SAFE-1",
               base_plan=str(a.base), base_plan_sha256=hashlib.sha256(raw_b).hexdigest(),
               plan_output=str(a.out), plan_output_sha256=hashlib.sha256(data).hexdigest(),
               rule3_tap_pair_types=taps, rule3_refused=refused, rule2_ft_resized=ft, rule2_fwd_stations=fwd,
               pin_cycle_deltas=sorted(by_type.values(), key=lambda r: r["lane"]), skipped_types=sorted(skip),
               touched_types=sorted(touched),
               preservation="every top-level key except partition_types and every untouched type byte-identical "
                            "(sort_keys compare); RTL, outlines, pins and hard cores unchanged")
    Path(a.event).write_text(json.dumps(rec, indent=1) + "\n")
    print(f"tap_pair {len(taps)} (+{len(refused)} refused), ft slots resized {len(ft)}, fwd legs {len(fwd)}, "
          f"lanes with pin-cycle delta {len(deltas)}, touched types {len(touched)}")


if __name__ == "__main__":
    main()
