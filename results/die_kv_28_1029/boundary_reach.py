#!/usr/bin/env python3
"""DIE-KV-28 diagnostic: START/reset BOUNDARY hops on the Codex KV all-cell proposal (codex-provider-import-1029/proposal_kv6,
22671 cells incl 12141 comb, placed) against the event27 FINAL native pin sites (plan_e27f provider boundary edges, die um).
Conservative: max Manhattan distance between the pin point and every corner of the actual placed endpoint cell bbox.
 in-edges (part pin -> stage): endpoints = proposal reach.json 'unresolved' FF D cells of that stage (boundary-sourced arcs)
   and, as an upper bound, every placed cell of that stage.
 out-edges (stage -> part pin): endpoint = the provider output inverter (inventory outputs.source_inst) and its launch FF.
usage: boundary_reach.py BOUNDARY_EDGES PLACEMENTS REACH INVENTORY OUT"""
import json, sys, collections
be, pl, rc, inv, out = sys.argv[1:6]
E = json.load(open(be)); P = json.load(open(pl)); R = json.load(open(rc)); I = json.load(open(inv)); D = P["dbu"]
cell = {c["inst"]: c for c in P["cells"]}; bystage = collections.defaultdict(list)
for c in P["cells"]: bystage[c["stage"]].append(c)
def far(pt, c):
    x0, y0, x1, y1 = [v / D for v in c["bbox_dbu"]]
    return max(abs(pt[0] - x) + abs(pt[1] - y) for x in (x0, x1) for y in (y0, y1))
unres = collections.defaultdict(list)
for u in R["unresolved"]:
    st = next((s for s in bystage if f"u_st_{s}." in u["dst_inst"] or f"u_rst_{s}." in u["dst_inst"]), None)
    unres[st].append(cell[u["dst_inst"]])
outs = {(o["stage"], o["dst_part"]): o for o in I["outputs"]}
rows = []
for e in E:
    pt = e["src_rect_um"][:2] if "dst_stage" in e else e["dst_rect_um"][:2]
    if "dst_stage" in e:
        st = e["dst_stage"]; kind = "reset_in" if e.get("signal") == "reset" else "start_in"
        ff = [far(pt, c) for c in unres.get(st, [])]
        allc = [far(pt, c) for c in bystage[st]]
        rows.append(dict(kind=kind, part=e["part"], pin=e["pin"], stage=st, d_ff_um=round(max(ff), 3) if ff else None, n_ff=len(ff), d_stage_any_um=round(max(allc), 3)))
    else:
        st = e["src_stage"]; o = outs[(st, e["part"])]
        rows.append(dict(kind="start_out", part=e["part"], pin=e["pin"], stage=st, d_inv_um=round(far(pt, cell[o["source_inst"]]), 3),
                         d_launch_um=round(far(pt, cell[o["launch_inst"]]), 3)))
k = lambda r: r.get("d_ff_um") or r.get("d_inv_um") or 0
s = dict(edges=len(rows), by_kind=dict(collections.Counter(r["kind"] for r in rows)),
         in_missing_ff=sum(1 for r in rows if r["kind"] != "start_out" and not r["n_ff"]),
         max_endpoint_um=max(k(r) for r in rows), over405_endpoint=sum(1 for r in rows if k(r) > 405),
         max_in_stage_any_um=max(r["d_stage_any_um"] for r in rows if "d_stage_any_um" in r),
         max_out_launch_um=max(r["d_launch_um"] for r in rows if "d_launch_um" in r),
         over405_upper=sum(1 for r in rows if max(r.get("d_stage_any_um", 0), r.get("d_launch_um", 0), k(r)) > 405),
         worst=sorted(rows, key=k)[-3:])
json.dump(dict(summary=s, rows=rows), open(out, "w"), indent=1); print(json.dumps(s, indent=1))
