#!/usr/bin/env python3
"""KV-BIND 10-24: re-derive the PV W request-lane pads for kv44 from the KV-P7 kv41 boot compile (image_kv41/
vport_dq_pads.json) and the RT rule (kv_param_rules_v36 'RT (boot cfg_age)': RT = 9 + max_g(D(vq_g) + D(rs_g)), D = landed
stages of vport.vq[01]_* -> slg_*.vreq and slg_*.rsp -> vport) measured on the kv41 and kv44 landing records.
Plan v3.8x lengthened slg <-> vport lanes (+1 on rsp for all 16 ports, +1 on vq for 10), so RT and hence DQ move:
    L_k = 4 + W_k + RT_k = RL41 - DQu41_k;  L44_k = L_k + dRT_k (+ dW_k, W from pr_t landed bound);  RL44 = max L44
    DQu44_k = RL44 - L44_k;  pad_k = max(0, DQu44_k - 15)
    kv_wreq_dq44.py KV41_BG(.gz) KV44_BG VPORT_DQ_PADS_KV41.json OUT.json"""
import collections, gzip, json, re, sys


def rt(f):
    d = json.load(gzip.open(f) if f.endswith(".gz") else open(f))
    vq, rs, w = collections.defaultdict(dict), collections.defaultdict(dict), {}
    for g in d["landing"]:
        for m in g["members"]:
            src = m["source"]
            if g["sink"].startswith("slg_") and re.match(r"vport_\w+\.vq[01]_", src):
                k = (src.split(".")[0], g["sink"])
                vq[k[0]][k[1]] = max(vq[k[0]].get(k[1], 0), m["landed_stages"])
            if g["sink"].startswith("vport_") and re.match(r"slg_\w+\.rsp$", src):
                rs[g["sink"]][src.split(".")[0]] = max(rs[g["sink"]].get(src.split(".")[0], 0), m["landed_stages"])
            if g["sink"].startswith("vport_") and m["sink_port"] == "pr_t":
                w[g["sink"]] = m["bound_stages"]
    out = {}
    for v in sorted(set(vq) | set(rs)):
        s = set(vq[v]) & set(rs[v])
        out[v] = 9 + max(vq[v][x] + rs[v][x] for x in s)
    return out, w, {v: sorted(set(vq[v]) & set(rs[v])) for v in vq}


r41, w41, p41 = rt(sys.argv[1])
r44, w44, p44 = rt(sys.argv[2])
B = json.load(open(sys.argv[3]))
dqu, RL = B["dq_unpadded"], B["RL"]
L44 = {k: RL - dqu[k] + (r44[k] - r41[k]) + (w44[k] - w41[k]) for k in dqu}
RL44 = max(L44.values())
dq44 = {k: RL44 - L44[k] for k in dqu}
pads = {k: max(0, v - 15) for k, v in dq44.items()}
doc = dict(note=__doc__, RT_kv41=r41, RT_kv44=r44, dRT={k: r44[k] - r41[k] for k in r41}, dW={k: w44[k] - w41[k] for k in w41},
           partners_kv44=p44, RL41=RL, RL44=RL44, dq_unpadded_kv44=dq44, pad_stages=pads,
           pad_flops=15 * sum(pads.values()), kv42_pad_stages=B["pad_stages"])
json.dump(doc, open(sys.argv[4], "w"), indent=1)
print(json.dumps({k: doc[k] for k in ("RT_kv41", "RT_kv44", "RL44", "dq_unpadded_kv44", "pad_stages", "pad_flops")}))
