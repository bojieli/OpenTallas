#!/usr/bin/env python3
"""S81-GEAR-1 (DIE-S81-87, 2026-11-12): composer stage for the BUS-GEAR-1 S81 x feed 2:1 plan delta.

Same transformation as results/arch/bus_gear_1112/gear_delta.py (claude/bus-gear-1-1112@f39a5c4f69, die s81), applied to the
event plan instead of the old svc_prov_v5 pgr1 plan: every lane with a port on an x_i*/x_o*/xo_i*/xo_o* bus goes 1104 -> 556 on
all its ports, on the endpoint type buses and ft slots (FF sites follow the respaced pins).
Fail-closed: the set of lanes/ports must equal the BUS-GEAR-1 delta (--delta), every changed width must be 1104, and only
ports[].width, lanes[].note, partition_types[*].buses[].width, ft_slots[].width/bit_sites_um/face_bit_sites_um change.
Latency (+1 word edge per geared lane) is NOT written (plan schema has no gear key; S81-ARCH-RTL-2 owns the landing K/E change).
usage: apply_xgear_1112.py IN OUT REPORT --delta s81_gear_delta.json [--extra-lanes-file F]
"""
import argparse, json, sys

X = ("x_i", "x_o", "xo_i", "xo_o")
OLD, NEW = 1104, 556


def sub(sites, old, new):
    return [sites[round(k * (old - 1) / (new - 1))] for k in range(new)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--delta", required=True)
    ap.add_argument("--extra-lanes-file", default=None, help="one lane id per line to gear in addition (e.g. xring lanes if ruled)")
    a = ap.parse_args()
    d = json.load(open(a.inp))
    dl = json.load(open(a.delta))
    P = {p["id"]: p for p in d["ports"]}
    ptype = {p["name"]: p["type"] for p in d["partitions"]}
    extra = set()
    if a.extra_lanes_file:
        extra = {x.strip() for x in open(a.extra_lanes_file) if x.strip()}
    rule = set()
    for l in d["lanes"]:
        if l["id"] in extra or any(P[i][e]["bus"].startswith(X) for i in l["ports"] for e in ("src", "dst")):
            rule.add(l["id"])
    want_l = {x["lane"] for x in dl["lanes"]} | extra
    want_p = {x["port"] for x in dl["ports"]}
    if rule != want_l:
        sys.exit(f"FAIL lanes differ from BUS-GEAR-1 delta: only_plan={sorted(rule-want_l)[:10]} only_delta={sorted(want_l-rule)[:10]}")
    ports_done = []
    tb, fsl = {}, {}
    for l in d["lanes"]:
        if l["id"] not in rule:
            continue
        for i in l["ports"]:
            p = P[i]
            if p["width"] != OLD:
                sys.exit(f"FAIL port {i} width {p[width]} != {OLD}")
            p["width"] = NEW
            ports_done.append(i)
            for e in ("src", "dst"):
                t = ptype.get(p[e]["part"])
                T = d["partition_types"].get(t) if t else None
                if T is None:
                    continue
                for b in T["buses"]:
                    if b["name"] == p[e]["bus"] and b["width"] == OLD:
                        tb[(t, b["name"])] = 1
                        b["width"] = NEW
                for f in T.get("ft_slots", []):
                    if p[e]["bus"] in (f["name"] + "_i", f["name"] + "_o") and f["width"] == OLD:
                        fsl[(t, f["name"])] = 1
                        f["width"] = NEW
                        if "bit_sites_um" in f:
                            f["bit_sites_um"] = [sub(st[:OLD], OLD, NEW) + st[OLD:] if len(st) == OLD + 1 else st
                                                 for st in f["bit_sites_um"]]
                        fb = f.get("face_bit_sites_um")
                        if isinstance(fb, list) and len(fb) in (OLD, OLD + 1):
                            f["face_bit_sites_um"] = sub(fb[:OLD], OLD, NEW) + fb[OLD:]
        l["note"] = (l.get("note", "") + " | BUS-GEAR-1 2:1").strip(" |")
    if set(ports_done) != want_p | {x for l in d["lanes"] if l["id"] in extra for x in l["ports"]}:
        sys.exit("FAIL port set differs from BUS-GEAR-1 delta")
    # leftovers: any remaining 1104 on x buses?
    left = [(t, b["name"]) for t, T in d["partition_types"].items() for b in T["buses"]
            if b["name"].startswith(X) and b["width"] == OLD]
    json.dump(d, open(a.out, "w"), indent=1)
    want_tb = {(x["type"], x["bus"]) for x in dl["type_buses"]}
    want_fs = {(x["type"], x["slot"]) for x in dl["ft_slots"]}
    rep = dict(lanes=len(rule), ports=len(ports_done), type_buses=len(tb), ft_slots=len(fsl),
               type_buses_not_in_delta=sorted(map(list, set(tb) - want_tb))[:40],
               type_buses_missing_vs_delta=sorted(map(list, want_tb - set(tb)))[:40],
               ft_slots_not_in_delta=sorted(map(list, set(fsl) - want_fs))[:40],
               ft_slots_missing_vs_delta=sorted(map(list, want_fs - set(fsl)))[:40],
               leftover_x_buses_at_1104=left[:40],
               bits_saved_on_ports=len(ports_done) * (OLD - NEW),
               latency_note="+1 word edge per geared lane NOT written to plan.latency; S81-ARCH-RTL-2 owns landing K/E")
    json.dump(rep, open(a.report, "w"), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if isinstance(v, int)}))

if __name__ == "__main__":
    main()
