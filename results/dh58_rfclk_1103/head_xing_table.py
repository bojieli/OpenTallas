#!/usr/bin/env python3
"""DH58-RFCLK (11-03): the ONE HEAD crossing latency table for RE-FORM batch l48rf (COORD 06:14 scope (c)).

Every die-level crossing of the plan (plan ports) gets: lane, src/dst partition + type, width, FORM, cycles
(plan latency.lanes breakdown + count-aligned K), the hold/setup evidence of its form, and the RE-FORM added
cycles (DH58-RFRTL --added JSON).  Forms:
  landed_ca   fixed-latency count-aligned (mesochronous) crossing; evidence = die_sta_related CA rows (margin lo/hi)
  seam_latch  same-region zero-logic seam: registered face + launch-side negative-level lockup latch (0 extra cycles)
The schedule / LEC / tok re-baseline reads lanes[*].total_cycles.  Read-only on its inputs.
--added schema: {"lanes": {LANE: {"cycles": int, "reason": str}}, "ports": {PORT: {"cycles": int, "reason": str}}}
(a port entry adds to that port's lane)."""
import argparse, collections, hashlib, json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:12]


def build(plan, ca_rows, ca_cycles, added=None, est=None):
    added = added or {}
    ty = {x["name"]: x["type"] for x in plan["partitions"]}
    lane_of = {pid: l["id"] for l in plan["lanes"] for pid in l["ports"]}
    lat = plan.get("latency", {}).get("lanes", {})
    est = est or {}
    port_add = collections.defaultdict(int)
    for pid, a in added.get("ports", {}).items():
        port_add[lane_of.get(pid, pid)] += int(a["cycles"])
    ports = []
    for x in plan["ports"]:
        pid = x["id"]; s, d = x["src"]["part"], x["dst"]["part"]
        row = dict(port=pid, lane=lane_of.get(pid), src=s, dst=d, src_type=ty.get(s, s), dst_type=ty.get(d, d),
                   width=x["width"], kind=x["kind"])
        if pid in ca_rows.get("TT", {}):
            tt, ff = ca_rows["TT"][pid], ca_rows["FF"][pid]
            row.update(form="landed_ca", ca_K=ca_cycles.get(pid),
                       margin_lo_ps=dict(TT=tt["margin_lo_ps"], FF=ff["margin_lo_ps"]),
                       margin_hi_ps=dict(TT=tt["margin_hi_ps"], FF=ff["margin_hi_ps"]))
        else:
            row.update(form="seam_latch", ca_K=None)
            if pid in est:
                e = est[pid]
                row.update(est_ff_hold_latch_ps=e["hold_latch_ff"], est_tt_setup_latch_ps=e["setup_latch_tt"],
                           est_ff_hold_plain_ps=e["hold_plain_ff"])
        if pid in added.get("ports", {}):
            row["added_cycles"] = int(added["ports"][pid]["cycles"]); row["added_reason"] = added["ports"][pid]["reason"]
        ports.append(row)
    lanes = {}
    for l in plan["lanes"]:
        b = dict(lat.get(l["id"], {}))
        a = int(added.get("lanes", {}).get(l["id"], {}).get("cycles", 0)) + port_add.get(l["id"], 0)
        lanes[l["id"]] = dict(ports=l["ports"], plan=b, plan_cycles=b.get("cycles"), added_cycles=a,
                              added_reason=added.get("lanes", {}).get(l["id"], {}).get("reason"),
                              total_cycles=(b["cycles"] + a) if "cycles" in b else None,
                              forms=sorted({p["form"] for p in ports if p["lane"] == l["id"]}))
    by = collections.defaultdict(lambda: dict(ports=0, bits=0))
    for p in ports:
        by[p["form"]]["ports"] += 1; by[p["form"]]["bits"] += p["width"]
    lo = [p["margin_lo_ps"][c] for p in ports if p["form"] == "landed_ca" for c in ("TT",)]
    summary = dict(by_form=dict(by), lanes=len(lanes), lanes_with_added=sum(1 for v in lanes.values() if v["added_cycles"]),
                   added_cycles_total=sum(v["added_cycles"] for v in lanes.values()),
                   ca_worst_lo_ps=dict(TT=min((p["margin_lo_ps"]["TT"] for p in ports if p["form"] == "landed_ca"), default=None),
                                       FF=min((p["margin_lo_ps"]["FF"] for p in ports if p["form"] == "landed_ca"), default=None)),
                   ca_worst_hi_ps=dict(TT=min((p["margin_hi_ps"]["TT"] for p in ports if p["form"] == "landed_ca"), default=None),
                                       FF=min((p["margin_hi_ps"]["FF"] for p in ports if p["form"] == "landed_ca"), default=None)))
    return dict(ports=ports, lanes=lanes, summary=summary)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True); ap.add_argument("--gate", required=True, help="die_sta_related.json (CA rows)")
    ap.add_argument("--added"); ap.add_argument("--est", help="xing_taps_*.json nearest-tap estimate rows")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    plan = json.loads(Path(a.plan).read_text()); gate = json.loads(Path(a.gate).read_text())
    ca_rows = {c: {r["port"]: r for r in gate["count_aligned"][c]["rows"]} for c in ("TT", "FF")}
    ca_cycles = plan["clock"].get("landing_network", {}).get("count_aligned_cycles", {})
    added = json.loads(Path(a.added).read_text()) if a.added else {}
    est = {r["port"]: r for r in json.loads(Path(a.est).read_text())["rows"]} if a.est else {}
    t = build(plan, ca_rows, ca_cycles, added, est)
    t = dict(schema="opentallas.head_crossing_latency_table.v1", plan=a.plan, plan_sha256=sha(a.plan), gate=a.gate,
             added=a.added, added_sha256=sha(a.added) if a.added else None, **t)
    Path(a.out).write_text(json.dumps(t, indent=1) + "\n")
    print("XING_TABLE", json.dumps(t["summary"]))


if __name__ == "__main__":
    main()
