#!/usr/bin/env python3
"""DIE-KV-13 10-28 (COORD TOK-ALL-13r): KV R8 write-group rule.  A write group (r8/write_groups.json) = the enable,
address and data ports of one sink write port that the producer emits on ONE source edge.  R8 keeps the as-built relative
offsets of a bus (r8.py rule 3); the historical as-built reference of the dcal boot-config port had the WE strobes one
stage short of addr/data (5 vs 6), so generic R8 landed WE one edge early (STALE write, native calendar FAIL).  This prep
step gives every member of a declared group ONE as-built reference = the group's latest stage (its source event), with
the raw value kept as `asbuilt_lane_stages` (r8.py keeps member ids on it, as for landed bundles); generic r8.py pads then
lands the whole group on one edge.  `check` asserts it on an R8 landing table (fails closed: group missing / partial /
unequal landing).

    r8_write_groups.py prep  BUS_GROUPS_IN.json BUS_GROUPS_OUT.json [--groups write_groups.json]
    r8_write_groups.py check R8_LANDING.json [--groups write_groups.json]
    r8_write_groups.py bindview R8_LANDING.json R8_LANDING_BIND.json [--groups write_groups.json]
`bindview` (DIE-KV-13 step-5 bind2, R8_STALE on dcal rx_we/tx_we): the strict binder checks each crossing bit against
the table's as-built depth (bind.py R8_STALE: bind as-built 5, table 6); the bind sees the RAW lane depth.  The bind copy
of the table therefore carries as-built = the raw lane (`asbuilt_lane`, group event depth kept as `asbuilt_group`),
bound / pad / landed unchanged, so the group still lands on ONE edge (check passes on both files).
Run prep after r8_invariant_split.py (and after r8_rebase.py when used), just before r8.py pads / gen.py --fold-r8."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_groups(p):
    d = json.load(open(p))
    assert d.get("schema") == "opentallas.kv.r8_write_groups.v1", p
    return d["groups"]


def _match(gr, sink, src_part):
    return re.search(gr["sink"], sink) and re.search(gr["src_part"], src_part)


def prep(bg, groups):
    out = json.loads(json.dumps(bg))
    rep = []
    for gr in groups:
        hits = []
        for g in out["landing"]:
            if not _match(gr, g["sink"], g["src_part"]):
                continue
            ms = [m for m in g["members"] if m["sink_port"] in gr["ports"] and m.get("lane") != "spine"]
            if ms:
                hits.append((g, ms))
        if not hits:
            raise SystemExit(f"write group {gr['name']}: no landing group matches")
        for g, ms in hits:
            got = sorted({m["sink_port"] for m in ms})
            if got != sorted(gr["ports"]):
                raise SystemExit(f"write group {gr['name']} {g['sink']}<-{g['src_part']}: ports {got} != {gr['ports']}")
            raw = [m.get("asbuilt_lane_stages", m["asbuilt_stages"]) for m in ms]
            ev = max(m["asbuilt_stages"] for m in ms)
            for m in ms:
                m.setdefault("asbuilt_lane_stages", m["asbuilt_stages"])
                m["asbuilt_stages"] = ev
                m["write_group"] = gr["name"]
            rep.append(dict(group=gr["name"], sink=g["sink"], src_part=g["src_part"], raw_asbuilt=dict(zip([m["sink_port"] for m in ms], raw)),
                            event_stage=ev))
    return out, rep


def check(r8, groups):
    bad, rows = [], []
    for gr in groups:
        by = {}
        for m in r8["members"]:
            if m["sink_port"] in gr["ports"] and _match(gr, m["sink"], m.get("src_part", "")):
                by.setdefault((m["sink"], m["sink_part"]), []).append(m)
        if not by:
            bad.append(f"{gr['name']}: no members in the R8 table")
        for (sink, sp), ms in sorted(by.items()):
            land = {m["sink_port"]: m["landed"] for m in ms}
            ok = sorted(land) == sorted(gr["ports"]) and len(set(land.values())) == 1
            rows.append(dict(group=gr["name"], sink=sink, sink_part=sp, landed=land, ok=ok))
            if not ok:
                bad.append(f"{gr['name']} {sink} ({sp}): landed {land} (one write group must land on ONE edge)")
    return bad, rows


def bindview(r8, groups):
    out = json.loads(json.dumps(r8))
    n = 0
    for gr in groups:
        for m in out["members"]:
            if m["sink_port"] in gr["ports"] and _match(gr, m["sink"], m.get("src_part", "")) \
                    and "asbuilt_lane" in m and m["asbuilt_lane"] != m["asbuilt"]:
                m["asbuilt_group"], m["asbuilt"] = m["asbuilt"], m["asbuilt_lane"]
                n += 1
    return out, n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["prep", "check", "bindview"]); ap.add_argument("inp"); ap.add_argument("out", nargs="?")
    ap.add_argument("--groups", default=str(HERE / "write_groups.json"))
    a = ap.parse_args(argv)
    groups = load_groups(a.groups)
    if a.mode == "prep":
        out, rep = prep(json.load(open(a.inp)), groups)
        Path(a.out).write_text(json.dumps(out, indent=0) + "\n")
        print(json.dumps(dict(write_groups=rep)))
        return 0
    if a.mode == "bindview":
        out, n = bindview(json.load(open(a.inp)), groups)
        bad, _ = check(out, groups)
        if bad:
            raise SystemExit(f"bindview: {bad}")
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
        print(json.dumps(dict(bindview_members=n)))
        return 0
    bad, rows = check(json.load(open(a.inp)), groups)
    print(json.dumps(dict(write_groups=rows, errors=bad)))
    for b in bad:
        print("ERROR", b, file=sys.stderr)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
