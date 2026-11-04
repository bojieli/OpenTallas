#!/usr/bin/env python3
"""DIE-KV-64 11-03 (COORD 11:3x class 1): bind the KV pv_pair hard cores as native composites.

KIT_PREFLIGHT macro_instances failed on every kv3_pv* type: the plan places kv3_pv_pair macros pvgX_pY and joins
pv__u_gN_j, but the bind flattened the two pv slices of each pair into the partition (no kv3_pv_pair instance).
Same form as the hg head_eighth composites: one compose core per (pv partition, pv_pair hard core) whose members are
the pair's two as-built slices, port map = kv3_pv_pair_core.json port_decl (s0 = first slice, s1 = second; the signed
kv3_pv_pair clocks both slices from s1__clk, so s1__clk carries both clk terminals and s0__clk stays unbound), plus
the plan physical identity (u_bound.u_<pair>, u_bound.u_pv_u_gN_j).

usage: mk_pvcompose.py PLAN BIND_NAMES IN_COMPOSE OUT_COMPOSE OUT_PARTS   (plan edited in place)
"""
import gzip, json, re, sys

plan_p, names_p, cin, cout, parts_out = sys.argv[1:6]
P = json.load(open(plan_p))
B = json.load(open(names_p))
DECL = {"bc": 23, "bcx": 6, "pe2": 32, "pv2": 256, "fault": 1, "ts": 512, "rst_n": 1}
DIR = {"fault": "output", "ts": "output"}
spec = json.load(gzip.open(cin)) if cin.endswith(".gz") else json.load(open(cin))
spec["cores"] = [c for c in spec["cores"] if c["module"] != "kv3_pv_pair"]
parts = {}
for p in P["partitions"]:
    if not p["type"].startswith("kv3_pv"):
        continue
    for h in P["partition_types"][p["type"]]["hard_cores"]:
        if h["module"] != "kv3_pv_pair":
            continue
        locs = re.match(r"pv_pair: (\S+) \+ (\S+) \(", h["note"]).groups()
        mem = [B[p["name"] + ".u_pv_u_" + l[len("pv__u_"):]] for l in locs]
        ports = {}
        for s, m in enumerate(mem):
            for pn, w in DECL.items():
                ports[f"s{s}__{pn}"] = {"dir": DIR.get(pn, "input"), "indices": list(range(w)),
                                        "bits": [[{"member": m, "port": pn, "bit": i}] for i in range(w)]}
        ports["s1__clk"] = {"dir": "input", "indices": [0],
                            "bits": [[{"member": m, "port": "clk", "bit": 0} for m in mem]]}
        inst = f"native_composite_{p['name']}_{h['inst']}"
        spec["cores"].append({"inst": inst, "module": "kv3_pv_pair", "members": mem, "ports": ports})
        parts[inst] = [p["name"], h["inst"]]
for t, pt in P["partition_types"].items():
    if not t.startswith("kv3_pv"):
        continue
    for h in pt["hard_cores"]:
        if h["module"] == "kv3_pv_pair":
            h["physical_inst"], h["physical_master"] = "u_bound.u_" + h["inst"], "kv3_pv_pair"
        elif h["module"] == "ot_qwen_tp8_pv_join_t" and h["inst"].startswith("pv__"):
            h["physical_inst"], h["physical_master"] = "u_bound.u_pv_" + h["inst"][4:], h["module"]
txt = json.dumps(spec)
(gzip.open(cout, "wt") if cout.endswith(".gz") else open(cout, "w")).write(txt)
json.dump(parts, open(parts_out, "w"), indent=0)
s = json.dumps(P, indent=1)
s = re.sub(r'("id_straps_in_type_types": \[)([^\]]*)\]', lambda m: m.group(1) + " ".join(m.group(2).split()) + "]", s)
open(plan_p, "w").write(s + "\n")
print("pv cores", len(parts), "total cores", len(spec["cores"]))
