#!/usr/bin/env python3
"""MESO-INTEG-1: re-price the KV v39r lane-class token model (LAND-KV-1 tok/kv_v39r_price_land_q5c39.json) with the
count-aligned per-crossing schedule latency (count_align_bind.py) instead of +3 per landed crossing.
    kv_ca_price.py PRICE.json LANE_DELTA.json BIND.json [--out OUT.json]
Lane deltas: KV plan port ids are <lane>_<hop>, so a lane's CA delta = sum of its crossings' sched_lat (checked: every
priced lane's old delta == 3 x its crossings).  Classes priced exactly as the source record: per attention request
(max d2d_rx bundle + max kvs_attn tx) x requests/token, per token embed (d2d_rx + px_hop + worst pc chain + emb_tx_slot
+ row_tx, serial sum).  Chains = hub_Xo -> pc_X_7 .. pc_X_0 lanes of each est/tep/tok family (old chain = 27 = 6 + 7x3)."""
import argparse, json, re
from collections import defaultdict

ap = argparse.ArgumentParser(); ap.add_argument("price"); ap.add_argument("lane_delta"); ap.add_argument("bind"); ap.add_argument("--out")
a = ap.parse_args()
P, LD, B = (json.load(open(f)) for f in (a.price, a.lane_delta, a.bind))
ca, n = defaultdict(int), defaultdict(int)
for p, c in B["ports"].items():
    ca[p.rsplit("_", 1)[0]] += c["sched_lat"]; n[p.rsplit("_", 1)[0]] += 1
lanes = {l["lane"]: l for l in LD["lanes"]}
for l in LD["lanes"]:
    if l["delta"] and l["delta"] != 3 * n[l["lane"]]:
        raise SystemExit(f"lane {l['lane']}: old delta {l['delta']} != 3 x {n[l['lane']]} crossings")
def new(l): return ca[l] if lanes[l]["delta"] else 0
def old(l): return lanes[l]["delta"]
def by(src, dst): return [k for k, l in lanes.items() if re.fullmatch(src, l["src"]) and re.fullmatch(dst, l["dst"])]
ar = P["per_attention_request"]
res = {}
for tag, f in (("old", old), ("ca", new)):
    d2d = max(f(l) for l in ar["d2d_rx_lanes"]); tx = max(f(l) for l in ar["kvs_attn_tx_lanes"])
    chains = {}
    for fam, pat in (("embgw_est", "embgw_est"), ("kvs_emb_px_tep", "kvs_emb_px_tep"), ("kvs_emb_px_tok", "kvs_emb_px_tok")):
        for q in ("EN", "ES", "WN", "WS"):
            h = "hub_Wo" if q[0] == "W" else "hub_Eo"
            ls = by(rf"{h}\.o_{pat}(_d1)?", rf"pc_{q}_7\.i_{pat}") + [x for i in range(7, 0, -1) for x in by(rf"pc_{q}_{i}\.o_{pat}", rf"pc_{q}_{i-1}\.i_{pat}")]
            if len(ls) != 8: raise SystemExit(f"chain {fam}:{q} has {len(ls)} lanes")
            chains[f"{fam}:{q}"] = sum(f(l) for l in ls)
    px = max(f(l) for l in by(r"hub_Wi\.o_kvs_emb_px_t(ep|ok)_d1", r"hub_Wo\.i_kvs_emb_px_t(ep|ok)"))
    slot = f(by(r"sys_c\.o_dNd_kv_emb_tx_slot", r".*")[0])
    row = max(f(l) for l in by(r"hub_Wi\.o_kvs_emb_rowtx__emb_tx_.*", r"sys_c\..*"))
    emb = d2d + px + max(chains.values()) + slot + row
    added = ar["requests_per_token"] * (d2d + tx) + emb
    cyc = P["priced"]["ar"]["base_cycles"] + added
    res[tag] = dict(d2d_rx_max=d2d, kvs_attn_tx_max=tx, per_request=d2d + tx, px_hop=px, worst_chain=max(chains.values()),
                    chains=chains, emb_tx_slot=slot, row_tx=row, embed=emb, added_cycles=added, cycles=cyc,
                    tok_s=round(1.2e9 / cyc, 1), loss_pct=round(100 * added / cyc, 3))
assert res["old"]["added_cycles"] == P["priced"]["ar"]["added_cycles"], (res["old"]["added_cycles"], P["priced"]["ar"])
up = sorted(((l, old(l), new(l)) for l in lanes if old(l) and new(l) > old(l)), key=lambda x: x[2] - x[1])
res["lanes_ca_above_old"] = dict(count=len(up), worst=up[-5:])
res["source"] = dict(price=a.price, lane_delta=a.lane_delta, bind=a.bind,
                     label="UNCHECKED: lane-class model; interior families (vport/pv/ahub/seq/acal) unpriced as in the source")
print(json.dumps({k: (v if k != "old" and k != "ca" else {x: y for x, y in v.items() if x != "chains"}) for k, v in res.items()}, indent=1))
if a.out: json.dump(res, open(a.out, "w"), indent=1)
