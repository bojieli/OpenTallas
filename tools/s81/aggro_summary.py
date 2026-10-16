#!/usr/bin/env python3
"""S81-AGGRO roll-up: more-dies knee (allocator) + hub shapes (actual faces) + gcell screen + token-rate deltas."""
import json, sys
from pathlib import Path
D = Path(sys.argv[1])
knee = json.loads((D / "knee_summary.json").read_text())
hub = json.loads((D / "hub_vm_centred.json").read_text())
grt = {r["key"]: r for r in json.loads((D / "hub_grt_screen.json").read_text())["results"]}
# % e2e per added edge on every node of the class (accepted_cost.rom_loss on results/arch/token_path_20261009)
PER = dict(ar=dict(su=0.130, field=0.035, coll=0.021), mtp=dict(su=0.114, field=0.030, coll=0.019))
CROSS = {"SU-VM": 4}      # two serial VM read round trips per SU job (su_gate --lvm), each crossing twice
def edges(L):
    e = dict(su=0, field=0, coll=0)
    for f in L["flows"]:
        e[f["cls"] if f["cls"] in e else "su"] += f["relays"] * CROSS.get(f["name"], 1)
    return e
base = [l for l in hub["layouts"] if l["key"] == "c5"][0]
eb = edges(base)
def tree_link(key):
    """field-phase tree edges (max collect + max broadcast hub hops) and die-link hub hops from the gcell screen;
    C5's link route is a screen artifact (0) -> C5 takes vmc's link hops"""
    h = grt.get(key, {}).get("hub_hops") or {}
    if not h:
        return None
    t = max(h.get("collect-W", 0), h.get("collect-E", 0)) + max(h.get("bcast-W", 0), h.get("bcast-E", 0))
    lk = h.get("link", 0) if key != "c5" else grt["vmc"]["hub_hops"]["link"]
    return t, lk
tb = tree_link("c5")
rows = []
for L in hub["layouts"]:
    e = edges(L)
    d = {wl: round(sum((e[c] - eb[c]) * PER[wl][c] for c in e), 3) for wl in PER}
    tl = tree_link(L["key"])
    dt = None
    if tl:
        dt = {wl: round(d[wl] + (tl[0] - tb[0]) * PER[wl]["field"] + (tl[1] - tb[1]) * PER[wl]["coll"], 3) for wl in PER}
    g = grt.get(L["key"], {})
    rows.append(dict(key=L["key"], name=L["name"], order=L["order"], checks=L["checks"], bbox_um=L["bbox_um"],
                     roads_um=L["roads_um"], road_cut=L["road_cut"], structural_turns=L["structural_turns"],
                     worst_flow_cut=L["worst_flow_cut"], hub_relays_all=L["relays_all"],
                     relay_edges_by_class=e, e2e_loss_delta_vs_c5_pct=d,
                     tree_edges_and_link_hops=tl, e2e_loss_delta_vs_c5_incl_trees_links_pct=dt,
                     tok_s_rm5_89st=None if dt is None else dict(MTP=round(4209.6 / (1 + dt["mtp"] / 100), 0),
                                                               AR=round(1433.8 / (1 + dt["ar"] / 100), 0)),
                     grt_screen={k: g.get(k) for k in ("max_util", "p99_util", "edges_over_060", "overflow_edges", "hub_hops")},
                     flows=[{k: f.get(k) for k in ("name", "bits", "face_a", "face_b", "window_um", "gap_um", "cut", "relays", "status")} for f in L["flows"]],
                     rects=L["rects"]))
k = []
for r in knee["rows"]:
    if r["arrangement"] != "tier" or r["refill"] is True:
        continue
    k.append({x: r.get(x) for x in ("name", "refill", "removed_columns", "pairs", "stages", "dies", "d_dies_vs_today",
                                    "MTP_tok_s", "AR_tok_s", "silicon_vs_today", "chips_kW", "hub_width_um", "fits",
                                    "worst_road_cut", "whitespace")})
out = dict(schema="opentallas.s81.aggro.v2", date="2026-10-15", author="S81-AGGRO (Claude)",
           scope="PLANNING SCREEN: real canonical packer + real allocator stage counts; hub = actual outlines + actual closed-port faces; gcell maze screen (not OpenROAD GRT)",
           today=knee["today"], knee=k, hub=rows,
           vm_rows=dict(VM_RELAY="unchanged by hub shape: a2f_reach_price midcapd with SU on S face = write 9 / read 16 (same as W). Set by VM size: area x0.5 -> 17 edges, x0.75 -> 22, x1.25 -> 31, x1.5 -> 34 (0.205 % AR per edge).",
                        VM_READ="S-VM 23:xx: A2-F hop-1 = drop the b4 relay level: -2 cycles a round trip, -32 leaves, -0.54 mm2, no outline growth -> fits every candidate; the 41->85 row was measured on the legacy bgq28 leaf and must be re-priced with VM.RELAY on A2-F.",
                        VM_SIZE="S-VM: VM size is set by row width (128 banks x 128 b, 53 sources x 16,384 b), not layers/die; halving SRAM depth saves ~1 mm2 of 19.06 -> more dies do NOT shrink the VM."),
           per_edge_pct=PER)
(D / "s81_aggro.json").write_text(json.dumps(out, indent=1) + "\n")
for r in rows:
    print(r["key"], len(r["structural_turns"]), r["hub_relays_all"], r["relay_edges_by_class"], r["e2e_loss_delta_vs_c5_pct"], r["tree_edges_and_link_hops"], r["e2e_loss_delta_vs_c5_incl_trees_links_pct"], r["tok_s_rm5_89st"], r["grt_screen"]["max_util"], r["grt_screen"]["overflow_edges"])
for r in k: print(r)
