#!/usr/bin/env python3
"""DIE-HBM-90-ISTA 11-07: plan event that drops type internal_stations on buses the type no longer has.

Cause: the die_hbm_1029 lane re-route events (results/die_hbm_1029/hbm2{2,3,8}/replan_event*.py, lane_add.Builder)
removed the dropped lanes, their ports and their endpoint buses, but kept type internal_stations "by name".  The
stations of the removed lanes stayed in 25 HBM types (1255 entries on 164 bus names in d44v), and kit_istations.py
stops the kit on them ("internal station on unknown bus").

An entry is DEAD in type T, and is dropped, only when all of these hold for its bus B (conn "bus:B"):
  1. B is not in partition_types[T].buses and is not an ft slot port of T (<slot>_i / <slot>_o);
  2. no die port (ports[].src / ports[].dst) on a partition of type T names B;
  3. the bound RTL module of T (--bound-rtl DIR: <module>__<T>.sv or hbm_arch_<T>.sv or <module>.sv) has no
     identifier B, B_q, B_eq, B_pad<j>, B_is<j>_q, u_bin_B, u_bout_B, u_ist_B_<j>.
A stale entry that fails 2 or 3 is not dropped: the tool fails closed (exit 1, nothing written).
A dead entry is not remapped to a current bus: the current lanes are priced without these internal stations
(latency.lanes stations 0 on their face hop) and the bound RTL has no pad stage for them, so a remap would add
unpriced cycles.  Entries on live buses and core<->core entries are kept byte for byte; nothing else changes.

    drop_dead_istations.py PLAN_IN PLAN_OUT LEDGER --bound-rtl DIR [--types T1,T2]
"""
import argparse
import json
import re
import sys
from pathlib import Path


def stale_entries(raw, tn):
    """[(index, bus)] of bus: entries whose bus is not a bus or ft slot port of the type."""
    t = raw["partition_types"][tn]
    have = {b["name"] for b in t.get("buses", [])}
    for s in t.get("ft_slots", []):
        have |= {s["name"] + "_i", s["name"] + "_o"}
    out = []
    for i, e in enumerate(t.get("internal_stations", []) or []):
        c = str(e.get("conn", ""))
        if c.startswith("bus:") and c[4:] not in have:
            out.append((i, c[4:]))
    return out


def die_port_buses(raw, tn):
    parts = {p["name"] for p in raw.get("partitions", []) if p.get("type") == tn}
    out = set()
    for q in raw.get("ports", []):
        for end in ("src", "dst"):
            e = q.get(end) or {}
            if e.get("part") in parts and e.get("bus"):
                out.add(e["bus"])
    return out


def bound_rtl_file(rtl_dir, raw, tn):
    mod = raw["partition_types"][tn].get("module", "")
    for name in (f"{mod}__{tn}.sv", f"hbm_arch_{tn}.sv", f"{mod}.sv"):
        f = Path(rtl_dir) / name
        if f.is_file():
            return f
    return None


def rtl_mentions(txt, bus):
    b = re.escape(bus)
    pat = rf"\b(?:u_bin_|u_bout_|u_ist_)?{b}(?:_q|_eq|_pad\d+|_is\d+_q|_is\d+_eq|_t\w+|_\d+)?\b"
    return len(re.findall(pat, txt))


def classify(raw, tn, rtl_txt):
    """(dead [(index, bus)], live [(bus, why)]) for the stale entries of one type."""
    ports = die_port_buses(raw, tn)
    dead, live = [], []
    for i, bus in stale_entries(raw, tn):
        why = []
        if bus in ports:
            why.append("die port")
        if rtl_txt is None:
            why.append("no bound RTL")
        elif rtl_mentions(rtl_txt, bus):
            why.append("bound RTL")
        (live.append((bus, ",".join(why))) if why else dead.append((i, bus)))
    return dead, live


def apply(raw, rtl_dir, types=None):
    """Returns (new raw, ledger).  Raises SystemExit when a stale entry is not provably dead."""
    T = raw["partition_types"]
    todo = [tn for tn in sorted(T) if stale_entries(raw, tn) and (not types or tn in types)]
    ledger = dict(schema="opentallas.drop_dead_istations.v1", types={}, entries=0, buses=0)
    bad = []
    plan = {}
    for tn in todo:
        f = bound_rtl_file(rtl_dir, raw, tn)
        txt = f.read_text() if f else None
        dead, live = classify(raw, tn, txt)
        if live:
            bad.extend(f"{tn}: bus {b} is not in the type but is live ({w})" for b, w in sorted(set(live)))
            continue
        plan[tn] = dead
        ist = T[tn]["internal_stations"]
        by = {}
        for i, b in dead:
            by.setdefault(b, []).append(dict(stages=len(ist[i].get("regs_um", [])), bits=ist[i].get("bits"),
                                             capture=ist[i].get("capture"), launch=ist[i].get("launch")))
        ledger["types"][tn] = dict(bound_rtl=str(f), before=len(ist), dropped=len(dead), after=len(ist) - len(dead),
                                   buses={b: v for b, v in sorted(by.items())})
    if bad:
        raise SystemExit("drop_dead_istations: fail closed, nothing written:\n  " + "\n  ".join(bad))
    for tn, dead in plan.items():
        drop = {i for i, _ in dead}
        t = T[tn]
        t["internal_stations"] = [e for i, e in enumerate(t["internal_stations"]) if i not in drop]
        if not t["internal_stations"]:
            t.pop("internal_stations")
        ledger["entries"] += len(dead)
        ledger["buses"] += len({b for _, b in dead})
    return raw, ledger


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_in")
    ap.add_argument("plan_out")
    ap.add_argument("ledger")
    ap.add_argument("--bound-rtl", required=True)
    ap.add_argument("--types", default="")
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan_in))
    types = set(x for x in a.types.split(",") if x)
    raw, ledger = apply(raw, a.bound_rtl, types)
    note = (f"DIE-HBM-90-ISTA drop_dead_istations ({ledger['entries']} dead entries on {ledger['buses']} type buses, "
            f"{len(ledger['types'])} types)")
    raw["note"] = note + " <- " + raw.get("note", "") if raw.get("note") else note
    Path(a.plan_out).write_text(json.dumps(raw))
    Path(a.ledger).write_text(json.dumps(ledger, indent=1, sort_keys=True) + "\n")
    print(note)
    return 0


if __name__ == "__main__":
    sys.exit(main())
