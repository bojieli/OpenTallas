#!/usr/bin/env python3
"""PATH-KV-BIND 10-25: KV plan dead-lane cleanup from as-built evidence (KV pin delta; lane cycles of live lanes unchanged).

A plan lane whose SOURCE bus carries planned OUT stations but on which the bound as-built die drives NO bit (bind
bind_latency.json has no crossing for (src part, bus)) is a dead plan port: the binder cannot realise its stations at the
source (native_istations P1 guard: "expected one outgoing lane") and a kit would get pins / stations nothing drives.
This tool REMOVES such lanes (never weakens the guard): the lane, its hop ports, its latency entry, its references in
latency_groups, and then every bus / internal-station record / ft slot of a partition type that no remaining lane of
any instance of that type uses.  A live lane narrower than planned (the as-built source drives fewer bits than the plan
bus, e.g. KV pv row-0 vo_d1: 48 forwarded bits on a 396-bit plan bus) is NARROWED to its live width: hop ports, source
and receiver bus, and every ft slot it crosses (bit sites truncated to the first W + the epoch site), but only when
every lane using that bus / slot (all instances of the type) narrows to the same width -- else it is reported only.
Lanes whose source bus matches --keep REGEX are reported, not narrowed (KV: the hroot->ectl cfg daisy
o_kvs_hroot_Q_o_cN, whose live width differs per position -- the S-class hg_v1 split, ectl ID-strap proposal).

usage: live_width_cleanup.py PLAN BIND_LATENCY_JSON OUT_PLAN REPORT_JSON [--keep REGEX]
"""
import collections
import gzip
import json
import sys
from pathlib import Path


def out_station_buses(t):
    buses = {b["name"]: b for b in t.get("buses", [])}
    return {e["conn"][4:] for e in t.get("internal_stations", [])
            if e.get("conn", "").startswith("bus:") and buses.get(e["conn"][4:], {}).get("dir") == "out"}


def main(argv):
    keep_re = None
    if "--keep" in argv:
        i = argv.index("--keep")
        keep_re = argv[i + 1]
        del argv[i:i + 2]
    plan_p, lat_p, out_p, rep_p = argv
    p = json.loads(Path(plan_p).read_text())
    lat = json.loads(gzip.decompress(Path(lat_p).read_bytes()) if lat_p.endswith(".gz") else Path(lat_p).read_text())["buses"]
    T = p["partition_types"]
    ptype = {x["name"]: x["type"] for x in p["partitions"]}
    ports = {x["id"]: x for x in p["ports"]}
    crossed = collections.defaultdict(list)
    for b in lat:
        crossed[(b["src"], b["bus_out"])].append(b)
    dead, narrow = [], []
    for ln in p["lanes"]:
        a = ports[ln["ports"][0]]
        sp, sb = a["src"]["part"], a["src"]["bus"]
        if sb not in out_station_buses(T[ptype[sp]]):
            continue
        m = crossed.get((sp, sb), [])
        if not m:
            dead.append(dict(lane=ln["id"], src=f"{sp}.{sb}", dst=f'{ports[ln["ports"][-1]]["dst"]["part"]}.'
                             f'{ports[ln["ports"][-1]]["dst"]["bus"]}', width=a["width"],
                             cycles=p.get("latency", {}).get("lanes", {}).get(ln["id"], {}).get("cycles")))
        elif m[0]["width"] < a["width"]:
            narrow.append(dict(lane=ln["id"], src=f"{sp}.{sb}", live=m[0]["width"], planned=a["width"]))
    gone = {d["lane"] for d in dead}
    gone_ports = {q for ln in p["lanes"] if ln["id"] in gone for q in ln["ports"]}
    p["lanes"] = [ln for ln in p["lanes"] if ln["id"] not in gone]
    p["ports"] = [x for x in p["ports"] if x["id"] not in gone_ports]
    for k in gone:
        p.get("latency", {}).get("lanes", {}).pop(k, None)
    groups_touched = []
    for g in p.get("latency_groups", []):
        if any(x in gone for x in g.get("lanes", [])):
            g["lanes"] = [x for x in g["lanes"] if x not in gone]
            groups_touched.append(g.get("name"))
    p["latency_groups"] = [g for g in p.get("latency_groups", []) if g.get("lanes", True)]
    # bus / station / ft-slot usage over all instances of each type, from the remaining lanes
    used_bus = collections.defaultdict(set)
    for x in p["ports"]:
        used_bus[ptype[x["src"]["part"]]].add(x["src"]["bus"])
        used_bus[ptype[x["dst"]["part"]]].add(x["dst"]["bus"])
    removed = collections.defaultdict(lambda: dict(buses=[], internal_stations=0, ft_slots=[]))
    touched_types = set()
    old_ports = json.loads(Path(plan_p).read_text())["ports"]
    for x in old_ports:
        if x["id"] in gone_ports:
            touched_types.add(ptype[x["src"]["part"]])
            touched_types.add(ptype[x["dst"]["part"]])
    for tn in sorted(touched_types):
        t = T[tn]
        keep = []
        for b in t.get("buses", []):
            if b["name"] in used_bus[tn] or b.get("kind") in ("clock", "reset"):
                keep.append(b)
            else:
                removed[tn]["buses"].append(b["name"])
        drop = set(removed[tn]["buses"])
        t["buses"] = keep
        n0 = len(t.get("internal_stations", []))
        if "internal_stations" in t:
            t["internal_stations"] = [e for e in t["internal_stations"] if e.get("conn", "")[4:] not in drop]
            removed[tn]["internal_stations"] = n0 - len(t["internal_stations"])
        if t.get("ft_slots"):
            fs = []
            for f in t["ft_slots"]:
                if any(u.rsplit("_", 1)[0] == f["name"] for u in used_bus[tn]):
                    fs.append(f)
                else:
                    removed[tn]["ft_slots"].append(f["name"])
            t["ft_slots"] = fs
        if not any(removed[tn].values()):
            removed.pop(tn, None)
    # narrow live lanes (consistent per type bus / ft slot), see docstring
    import re
    ports = {x["id"]: x for x in p["ports"]}
    lanes = {ln["id"]: ln for ln in p["lanes"]}
    want = {}
    for n in narrow:
        if keep_re and re.fullmatch(keep_re, n["src"].split(".", 1)[1]):
            n["action"] = "kept (--keep)"
            continue
        want[n["lane"]] = n["live"]
    uses = collections.defaultdict(set)      # (type, bus or ft slot) -> {(lane, width)}
    for ln in p["lanes"]:
        for q in ln["ports"]:
            x = ports[q]
            for side in ("src", "dst"):
                key = (ptype[x[side]["part"]], x[side]["bus"])
                uses[key].add((ln["id"], want.get(ln["id"])))
    def slot(bus):
        m = re.fullmatch(r"(ft\d+)_[io]", bus)
        return m.group(1) if m else None
    ok = {}
    for lid, w in want.items():
        keys = {(ptype[ports[q][s]["part"]], ports[q][s]["bus"]) for q in lanes[lid]["ports"] for s in ("src", "dst")}
        ok[lid] = all({u[1] for u in uses[k]} == {w} for k in keys)
    narrowed = []
    for n in narrow:
        lid = n["lane"]
        if lid not in want:
            continue
        if not ok[lid]:
            n["action"] = "reported (bus/slot shared with lanes of another width)"
            continue
        w = want[lid]
        for q in lanes[lid]["ports"]:
            x = ports[q]
            x["width"] = w
            for side in ("src", "dst"):
                t = T[ptype[x[side]["part"]]]
                bn = x[side]["bus"]
                fs = slot(bn)
                if fs and any(f["name"] == fs for f in t.get("ft_slots", [])):
                    f = next(f for f in t["ft_slots"] if f["name"] == fs)
                    if f["width"] != w:
                        f["width"] = w
                        f["bit_sites_um"] = [ss[:w] + ss[-1:] for ss in f["bit_sites_um"]]
                for b in t.get("buses", []):
                    if b["name"] == bn:
                        b["width"] = w
        n["action"] = f"narrowed to {w}"
        narrowed.append(lid)
    p["note"] = (p.get("note", "") + f" | PATH-KV-BIND 10-25 live-width cleanup: {len(dead)} dead plan lanes "
                 f"(OUT-stationed source bus with no as-built bit) removed with their buses/stations/ft slots; "
                 f"{len(narrowed)} narrow live lanes narrowed to their as-built width, {len(narrow) - len(narrowed)} reported")
    Path(out_p).write_text(json.dumps(p, indent=1, ensure_ascii=False) + "\n")
    rep = dict(schema="opentallas.kv.live_width_cleanup.v1", plan_in=plan_p, evidence=lat_p, dead_lanes=dead,
               removed=dict(removed), latency_groups_touched=groups_touched, narrow=narrow,
               live_lane_cycles_changed=0)
    Path(rep_p).write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps(dict(dead=len(dead), narrow=len(narrow), types=sorted(removed))))


if __name__ == "__main__":
    main(sys.argv[1:])
