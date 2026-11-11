#!/usr/bin/env python3
"""STATION-FIX-HBM 11-11 stationfix_1111: HBM native-OUT relay station chains written face -> core (COORD S7 class,
station_lint INVERTED, same class as KV phyrev_1111).

The TYPE-SAFE-2 11-08 relay event (ts_relay_event.py) wrote 13 OUT-bus internal_stations face first: from_um on the
face, regs_um[0] next to the face, launch = core pin, capture = 'face flop'.  kit_istations sites station k (the k-th
register after the launch) at regs_um[k], so in the kit stage 0 sits next to the face and the last stage next to the
core: the chain zig-zags core -> face -> ... -> core -> face (placed kits: NE_io L8006_o last hop 862 um, q_spb0 L722_o
first and last hop ~730 um, NW_io L8007_o last hop 2577 um).
Fix: on exactly these 13 entries, keyed (type, bus, index), swap from_um / to_um and reverse regs_um.  Same sites,
same register count, same launch / capture / note, no cycle change: EQ by construction.  Idempotent: an entry already
written core -> face (to_um on the outline, from_um inside) is left as is.
Pair: tools/die_plan/native_istations.py face_first() (same branch).  These buses are native OUT buses
(asbuilt internal_stations_buses); native_istations now reverses only an entry still written face first, so the
native source entries, the bind's native_topology digest and the bound RTL are identical before and after this event.

NW_io: apply on top of VIS-TRIAGE-HBM form h (NW_io_formh_plan.json fb858a44): its L8007_o entry (index 58) keeps
its form-h sites and is flipped the same way.  L52_o (index 22, flagged on 29333b2b) is NOT changed: its 13 entries
are planner face-first rows launched 'face bus L52_o' which kit_istations already reverses (KW-FIX-27) and merges
into one bits-weighted chain (placed NW_io a11: leaf -> 232,1341 -> 412,1311 -> face, monotone); form h re-sites
them and station_lint reports 0 flags on L52_o there.

usage (repo root or anywhere): event.py PLAN_IN PLAN_OUT [RECEIPT.json]
"""
import copy
import hashlib
import json
import sys

# (type, bus, internal_stations index, launch) -- STATION-LINT-1111.tsv rows of plan p11t 29333b2b (NW_io L52_o excluded)
TARGETS = (
    ("root", "L1237_o", 91, "u_col_idx.prm"),
    ("root", "L1258_o", 92, "u_col_idx.prm"),
    ("root", "L202_o", 93, "u_col_idx.prm"),
    ("root", "L202m_o", 94, "u_col_idx.prm"),
    ("root", "L5062_o", 95, "u_col_idx.prm"),
    ("root", "L8000_o", 96, "u_col_idx.prm"),
    ("root", "L8008_o", 97, "u_host_cp_rxs.ep_rx_arm_bank"),
    ("q_spb0", "L722_o", 10, "u_ep_S0.fault"),
    ("q_spb0", "L723_o", 11, "u_ep_S0.rx_pin_flit"),
    ("q_spb0__physical_v1", "L722_o", 10, "u_ep_S0.fault"),
    ("q_spb0__physical_v1", "L723_o", 11, "u_ep_S0.rx_pin_flit"),
    ("NW_io", "L8007_o", 58, "u_ep_N0.fault_cause"),
    ("NE_io", "L8006_o", 14, "u_ep_N2.fault_cause"),
)
TOL = 2.0


def _edge(p, o):
    return min(p[0], p[1], o[0] - p[0], o[1] - p[1]) <= TOL


def _state(e, o):
    """'face_first' (from_um on the outline, to_um inside), 'core_first' (the reverse) or None."""
    a, z = _edge(e["from_um"], o), _edge(e["to_um"], o)
    return "face_first" if a and not z else "core_first" if z and not a else None


def apply(plan, targets=TARGETS):
    """flip the target entries in place on a deep copy; returns (plan, rows)."""
    orig, plan = plan, copy.deepcopy(plan)
    rows = []
    for tn, bus, i, launch in targets:
        t = plan["partition_types"][tn]
        st = t["internal_stations"]
        e = st[i] if i < len(st) else None
        if e is None or e.get("conn") != "bus:" + bus:
            hits = [k for k, x in enumerate(st) if x.get("conn") == "bus:" + bus]
            raise SystemExit(f"stationfix_1111: {tn}[{i}] is not bus:{bus} (bus:{bus} at {hits}); plan differs from the lint base")
        b = next(x for x in t["buses"] if x["name"] == bus)
        if b.get("dir") != "out" or e.get("capture") != "face flop" or e.get("launch") != launch:
            raise SystemExit(f"stationfix_1111: {tn}[{i}] {bus}: expected an out bus launched at {launch}, captured at the face flop")
        s = _state(e, t["outline_um"])
        if s is None:
            raise SystemExit(f"stationfix_1111: {tn}[{i}] {bus}: neither end alone on the outline ({e['from_um']}, {e['to_um']})")
        if s == "face_first":
            e["from_um"], e["to_um"] = e["to_um"], e["from_um"]
            e["regs_um"] = list(reversed(e["regs_um"]))
        rows.append(dict(type=tn, bus=bus, index=i, action="flipped" if s == "face_first" else "already_core_first",
                         regs=len(e["regs_um"]), from_um=e["from_um"], to_um=e["to_um"]))
    check_eq(orig, plan, targets)
    return plan, rows


def check_eq(a, b, targets=TARGETS):
    """only the target entries' from_um / to_um / regs_um order may differ; same sites, same counts."""
    keys = {(tn, i) for tn, _, i, _ in targets}
    assert {k: v for k, v in a.items() if k != "partition_types"} == {k: v for k, v in b.items() if k != "partition_types"}
    assert a["partition_types"].keys() == b["partition_types"].keys()
    for tn, t in a["partition_types"].items():
        u = b["partition_types"][tn]
        if not any(k[0] == tn for k in keys):
            assert t == u, tn
            continue
        assert {k: v for k, v in t.items() if k != "internal_stations"} == {k: v for k, v in u.items() if k != "internal_stations"}
        assert len(t["internal_stations"]) == len(u["internal_stations"])
        for i, (e, f) in enumerate(zip(t["internal_stations"], u["internal_stations"])):
            if (tn, i) not in keys:
                assert e == f, (tn, i)
                continue
            fixed = ("from_um", "to_um", "regs_um")
            assert {k: v for k, v in e.items() if k not in fixed} == {k: v for k, v in f.items() if k not in fixed}
            assert sorted(map(tuple, e["regs_um"])) == sorted(map(tuple, f["regs_um"])), (tn, i)
            assert sorted([tuple(e["from_um"]), tuple(e["to_um"])]) == sorted([tuple(f["from_um"]), tuple(f["to_um"])])


def main(a):
    if len(a) not in (2, 3):
        raise SystemExit(__doc__)
    raw = open(a[0], "rb").read()
    text = raw.decode()
    plan, rows = apply(json.loads(text))
    out = json.dumps(plan, indent=1) + ("\n" if text.endswith("\n") else "")
    if json.dumps(json.loads(text), indent=1) + ("\n" if text.endswith("\n") else "") != text:
        raise SystemExit("stationfix_1111: input is not json.dumps(indent=1) text; refusing to re-serialise")
    open(a[1], "w").write(out)
    rec = dict(event="stationfix_1111", plan_in=a[0], plan_in_sha256=hashlib.sha256(raw).hexdigest(),
               plan_out=a[1], plan_out_sha256=hashlib.sha256(out.encode()).hexdigest(), entries=rows,
               eq="EQ_BY_CONSTRUCTION: same registers, same sites, same launch/capture/note; order of regs_um and "
                  "from_um/to_um only")
    if len(a) == 3:
        open(a[2], "w").write(json.dumps(rec, indent=1) + "\n")
    print("stationfix_1111:", sum(r["action"] == "flipped" for r in rows), "flipped,",
          sum(r["action"] != "flipped" for r in rows), "already core-first;", rec["plan_out_sha256"])


if __name__ == "__main__":
    main(sys.argv[1:])
