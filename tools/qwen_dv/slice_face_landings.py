#!/usr/bin/env python3
"""QW-SLICE4 10-19: the 182 slice<->slice landings owed INSIDE the receiving qfd_dv_slice2_{e,w} face (QW-GEN3 NOTICE).

Abutted dv_slice2 pairs (0-um gap) have no die site for a landing, so each landed bus of the dv chain (families n_dv_ch,
n_dv_st, n_dv_l9, n_dv_x0_*) lands in the RECEIVER's face: ring written on the sender's forwarded region clock (one new
ck_s input per landed face port group), read on the receiver's root.  Static, fixed latency, no backpressure.

Inputs
  --landing-list  results/arch/qw_dieclk2_1019/landing_list.json (QW-DIECLK2 / QW-GEN3; default: read from
                  origin/claude/qw-gen3-1019 with git show)
  --relay-stages  the GEN's relay_stages.json (dv2f19g3r p2/relay_stages.json): gives the receiver PORT of every bus,
                  whose suffix (_wi / _ei / _ni / _si) is the receiving face.  Without it the face is "not derivable".
Masters (CLOSED views on origin/main, read with git show):
  bits <= 32 : the LAND8 hop-0 D8 masters qfd_landh0d8_{1,3,10,32}_EW_* (physical/ref_tile/qfwd_landh0d8_*;
               ICG main, qfd_landh0d8n_* no-ICG fallback); width rounded up to the next closed width.
               Latency L is die-chosen so that the write->read age (L-1) T + phi lies in the D8 window [1.25 T, 4.125 T]
               (rtl/qwen_split/qfd_land8.sv): nominal L = 3 (+3 edges), the same as the E=2 halves.
  bits >  32 : ceil(bits / 258) pairs qfd_c_land_w258_narrow + qfd_c_land_r258_narrow (514-bit buses: the 257 pair),
               E = K = 2, +3 edges.
Output: results/arch/qw_slice4_1019/slice_face_landings.json
"""
from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAIN = "origin/main"
LL_REF = "origin/claude/qw-gen3-1019:results/arch/qw_dieclk2_1019/landing_list.json"
LAND8 = {1: ("qfwd_landh0d8_1_ew_16x16", "qfd_landh0d8_1_EW_16x16"), 3: ("qfwd_landh0d8_3_ew_17x17", "qfd_landh0d8_3_EW_17x17"),
         10: ("qfwd_landh0d8_10_ew_19x19", "qfd_landh0d8_10_EW_19x19"), 32: ("qfwd_landh0d8_32_ew_28x26", "qfd_landh0d8_32_EW_28x26")}
NARROW = {258: ("qfd_c_land_w258_narrow", "qfd_c_land_r258_narrow"), 257: ("qfd_c_land_w257_narrow", "qfd_c_land_r257_narrow")}
D8_SLOTS = 8
ADDED_EDGES = 3          # E = K = 2 halves: +E+1; LAND8 nominal L = 3 (die-chosen in the D8 window)
FACE = {"_wi": "W", "_ei": "E", "_ni": "N", "_si": "S"}


def git_show(ref: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), "show", ref], check=True, capture_output=True, text=True, timeout=60).stdout


def view(tile: str) -> dict:
    """closed-view facts of one master on main: outline, measured clock sinks (TT insertion census 'all' n)"""
    spec = json.loads(git_show(f"{MAIN}:physical/ref_tile/{tile}/spec.json"))
    top = spec["top"]
    ins = json.loads(git_show(f"{MAIN}:physical/ref_tile/{tile}/views/{top}/insertion.json"))
    tt = ins["tt"] if isinstance(ins["tt"], dict) else ast.literal_eval(ins["tt"])
    w, h = float(spec["outline"]["w"]), float(spec["outline"]["h"])
    return dict(tile=tile, top=top, w=w, h=h, area_um2=round(w * h, 1), sinks=int(tt["all"]["n"]),
                tt_insertion_ps=[tt["all"]["min"], tt["all"]["max"]])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--landing-list")
    ap.add_argument("--relay-stages")
    ap.add_argument("--out", default=str(ROOT / "results/arch/qw_slice4_1019/slice_face_landings.json"))
    a = ap.parse_args()
    ll_text = Path(a.landing_list).read_text() if a.landing_list else git_show(LL_REF)
    ll = json.loads(ll_text)
    rows = [l for l in ll["links"] if str(l["src_master"]).startswith("qfd_dv_slice2") and
            str(l["dst_master"]).startswith("qfd_dv_slice2")]
    ports = collections.defaultdict(list)
    rs_sha = None
    if a.relay_stages:
        rs_text = Path(a.relay_stages).read_text()
        rs_sha = hashlib.sha256(rs_text.encode()).hexdigest()
        for b in json.loads(rs_text)["buses"]:
            ports[(b.get("bid"), b["src"]["inst"], b["dst"]["inst"])].append((b["dst"]["port"], int(b["width"]), b["src"]["port"]))
    l8 = {w: view(t) for w, (t, _) in LAND8.items()}
    nw = {k: (view(wt), view(rt)) for k, (wt, rt) in NARROW.items()}

    links, groups = [], collections.defaultdict(lambda: dict(links=0, bits=0, ck_s=set(), faces=set()))
    for l in rows:
        bits = int(l["bits"])
        bp = ports.get((l["bus"][2:] if l["bus"].startswith("n_") else l["bus"], l["src"], l["dst"]), [])
        faces = sorted({FACE.get(p[-3:], "?") for p, _, _ in bp}) if bp else []
        face = faces[0] if len(faces) == 1 else ("/".join(faces) if faces else "not derivable (no relay_stages port)")
        if bits <= 32:
            w = min(k for k in LAND8 if k >= bits)
            v = l8[w]
            masters = [dict(master=v["top"], count=1, fallback=v["top"].replace("landh0d8_", "landh0d8n_"),
                            closed_view=f"physical/ref_tile/{v['tile']}/views/{v['top']}")]
            ff_ck = v["sinks"]
            ff_cks = D8_SLOTS * w + 2          # D8 bank + en_s0/en_icg on ck_s (model; the view census counts ck only)
            ff, area = ff_ck + ff_cks, v["area_um2"]
            basis = f"LAND8 D8 hop-0 W{w}: ck sinks {ff_ck} measured + ck_s bank {ff_cks} (model 8*W+2)"
        else:
            k = 257 if bits == 514 else 258
            n = math.ceil(bits / k)
            wv, rv = nw[k]
            masters = [dict(master=wv["top"], count=n, closed_view=f"physical/ref_tile/{wv['tile']}/views/{wv['top']}"),
                       dict(master=rv["top"], count=n, closed_view=f"physical/ref_tile/{rv['tile']}/views/{rv['top']}")]
            ff, area = n * (wv["sinks"] + rv["sinks"]), round(n * (wv["area_um2"] + rv["area_um2"]), 1)
            basis = f"{n} x narrow pair {k} (measured sinks {wv['sinks']} + {rv['sinks']})"
        gkey = (l["dst_master"], l["dst"], l["src"])
        g = groups[gkey]
        g["links"] += 1
        g["bits"] += bits
        g["ck_s"].update(l["ck_s"])
        g["faces"].add(face)
        links.append(dict(bus=l["bus"], family=l["family"], bits=bits, src=l["src"], src_master=l["src_master"],
                          dst=l["dst"], dst_master=l["dst_master"], face=face,
                          dst_ports=[dict(port=p, width=w_, src_port=sp) for p, w_, sp in bp],
                          ck_s_group=f"{l['dst']}<-{l['src']}", ck_s=l["ck_s"], ck=l["ck"], masters=masters,
                          flops=ff, flops_basis=basis, area_um2=area, added_edges=ADDED_EDGES,
                          list_ff=l.get("ff"), list_area_um2=l.get("area_um2")))

    # per receiving MASTER: one master serves every instance of its column, so it carries the UNION of the landed face
    # port groups over its instances (bus names stripped of the instance index).
    per_master = {}
    for m in sorted({x["dst_master"] for x in links}):
        mine = [x for x in links if x["dst_master"] == m]
        union = {}
        for x in mine:
            key = (x["face"], re.sub(r"_[EW]\d", "", x["bus"]), x["bits"])
            union.setdefault(key, x)
        face_groups = sorted({x["face"] for x in mine})
        per_inst = collections.Counter(x["dst"] for x in mine)
        per_master[m] = dict(
            instances=dict(sorted(per_inst.items())),
            links=len(mine), bits=sum(x["bits"] for x in mine),
            flops_all_instances=sum(x["flops"] for x in mine),
            area_um2_all_instances=round(sum(x["area_um2"] for x in mine), 1),
            per_face={f: dict(links=sum(1 for x in mine if x["face"] == f), bits=sum(x["bits"] for x in mine if x["face"] == f))
                      for f in face_groups},
            master_landing_set=[dict(face=k[0], bus=k[1], bits=k[2], masters=v["masters"], flops=v["flops"],
                                     area_um2=v["area_um2"]) for k, v in sorted(union.items())],
            master_flops=sum(v["flops"] for v in union.values()),
            master_area_um2=round(sum(v["area_um2"] for v in union.values()), 1),
            new_ck_s_ports=len(face_groups),
            new_ck_s_port_names=[f"ck_s_{f.lower()}i" for f in face_groups],
            extra_face_pins=2 * len(face_groups),
            extra_face_pins_basis="per landed face group: ck_s (sender forwarded region clock) + en_s (sender released reset, "
                                  "the LAND8 en / narrow-writer rsi); data pins unchanged (the bus pins already exist); "
                                  "LAND8 K straps k0..k3 are tied inside the master by the face generator from the die's L")
    hops = sorted({(x["src"], x["dst"]) for x in links})
    price = ll.get("price", {})
    # the dv chain is a LINE of slices (a reduction pass runs one way along it, the result pass the other way): the serial
    # landed hops of one pass = the undirected chain edges (E0<->E1 share one root, pll_r95: no landing there)
    und = sorted({tuple(sorted(h)) for h in hops})
    n_hops = len(und)
    layers = int(price.get("layers", 36))
    per_layer = n_hops * ADDED_EDGES
    out = dict(
        schema="opentallas.qwen_compute.slice_face_landings.v1",
        lane="QW-SLICE4 (LEAD3-QW) 10-19",
        inputs=dict(landing_list=a.landing_list or LL_REF, landing_list_sha256=hashlib.sha256(ll_text.encode()).hexdigest(),
                    relay_stages=a.relay_stages, relay_stages_sha256=rs_sha, masters_ref=MAIN),
        rule=("receiver-face landing: ring on the sender's forwarded region clock ck_s (one ck_s input per landed face "
              "port group = per (src instance, dst instance) pair), read on the receiver root; <=32 b -> LAND8 D8 hop-0, "
              ">32 b -> ceil(bits/258) narrow pairs (514 b -> 257 pair); +3 edges; static, no backpressure"),
        totals=dict(links=len(links), bits=sum(x["bits"] for x in links), flops=sum(x["flops"] for x in links),
                    area_um2=round(sum(x["area_um2"] for x in links), 1),
                    land8_links=sum(1 for x in links if x["bits"] <= 32),
                    narrow_links=sum(1 for x in links if x["bits"] > 32),
                    narrow_pairs=sum(x["masters"][0]["count"] for x in links if x["bits"] > 32),
                    face_port_groups=len(groups), by_face=dict(collections.Counter(x["face"] for x in links))),
        face_port_groups=[dict(dst_master=k[0], dst=k[1], src=k[2], links=v["links"], bits=v["bits"],
                               ck_s=sorted(v["ck_s"]), faces=sorted(v["faces"])) for k, v in sorted(groups.items())],
        per_master=per_master,
        price=dict(serial_slice_hops_per_layer=n_hops, directed_hops=len(hops), hops=[f"{s}->{d}" for s, d in hops],
                   chain_edges=[f"{s}<->{d}" for s, d in und], added_edges_per_hop=ADDED_EDGES,
                   added_cycles_per_layer=per_layer, layers=layers, added_cycles_per_token=per_layer * layers,
                   clock_ghz=1.2, added_us_per_token=round(per_layer * layers / 1.2e3, 3),
                   note=("one pass along the chain (every landed slice edge serial once); the list's worst case dv_chain_hops "
                         f"{price.get('serial_landings_per_layer', {}).get('dv_chain_hops')} (+{3 * int(price.get('serial_landings_per_layer', {}).get('dv_chain_hops') or 0)}/layer) is 1 more (likely E0<->E1, today one shared root pll_r95, not landed; +3 if it splits); both are inside the list's "
                         f"{price.get('added_cycles_per_layer')} cycles/layer, not additional to it")),
        masters=dict(land8={str(k): v for k, v in l8.items()},
                     narrow={str(k): dict(w=v[0], r=v[1]) for k, v in nw.items()}),
        links=links)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    t = out["totals"]
    print(f"{t['links']} links {t['bits']} b {t['flops']} ff {t['area_um2']} um2 by_face {t['by_face']}; "
          f"hops {n_hops} -> +{per_layer}/layer +{per_layer * layers}/token {out['price']['added_us_per_token']} us")
    for m, v in per_master.items():
        print(m, v["instances"], "master set", len(v["master_landing_set"]), "ff", v["master_flops"], "um2", v["master_area_um2"],
              "ck_s", v["new_ck_s_port_names"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
