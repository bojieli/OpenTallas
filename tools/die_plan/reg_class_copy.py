# S81-SLICE-J9 11-24 class row (FABLE-RC-ALL ee2fb1d2): reg_reach_census.py json -> relay_split + relay_sites plan ops for one
# type (every register of the class, no names in code).  usage: reg_class_copy.py CENSUS.json PLAN.json TYPE OPS_OUT [PLAN_OUT]
# SPLIT: >= 2 movable sinks spread over more than REACH -> k_cover clusters (radius REACH/2), the cluster nearest the flop
#        keeps the original, every other cluster gets a copy K__rs<n> seated at its L1 centre (same D/clock/reset, 0 cycles).
# SEAT : >= 4 sinks inside one REACH box but the flop is far -> original seated at the sink centre (0 cycles).
# HOP  : 1..3 sinks in one box, far: a copy cannot shorten it -> reported, no row.
import sys, json, hashlib, collections, re, os
cj, pj, tn, oo = sys.argv[1:5]; po = sys.argv[5] if len(sys.argv) > 5 else None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reset_leg_plan import l1, centre, k_cover
C = json.load(open(cj)); R = C["reach"]; raw = open(pj, "rb").read(); P = json.loads(raw); t = P["partition_types"][tn]
bad = re.compile(r"[{}\\\s]")
names = collections.Counter(r["flop"] for r in C["rows"])
split, sites, hop, skip = [], {}, [], collections.Counter()
for r in sorted(C["rows"], key=lambda r: r["flop"]):
    f = r["flop"]
    if names[f] > 1 or bad.search(f): skip["dup/badname"] += 1; continue
    if not r.get("direct"): skip["no-direct"] += 1; hop.append((f, r["reach_l1"], r["n_sinks"])); continue
    mv = {k: (v[0], v[1]) for k, v in r["direct"].items() if not bad.search(k)}
    fixed = r["fixed"] + len(r["direct"]) - len(mv)
    if mv:
        xs = [v[0] for v in mv.values()]; ys = [v[1] for v in mv.values()]
        r["sink_side"] = max(max(xs) - min(xs), max(ys) - min(ys))
    wide = [k for k, v in r["direct"].items() if v[2] > R]
    if wide: skip["wide-repeater-load"] += 1
    if len(mv) >= 2 and r["sink_side"] > R:
        cl = k_cover(list(mv.items()), R / 2)
        if len(cl) < 2: skip["one-cluster"] += 1; continue
        cl.sort(key=lambda c: l1(centre([x[1] for x in c]), r["xy"]))
        clones = []
        for n, c in enumerate(cl[1:]):
            nm = f"{f}__rs{n}"; clones.append({"name": nm, "sinks": sorted(x[0] for x in c)})
            x, y = centre([x[1] for x in c]); sites[nm] = [round(x, 2), round(y, 2)]
        split.append({"flop": f, "clones": clones, **({"unbuffer": True} if r.get("unbuf") else {})})
    elif len(mv) >= 4 and not fixed:
        x, y = centre(list(mv.values())); sites[f] = [round(x, 2), round(y, 2)]
    else:
        hop.append((f, r["reach_l1"], r["n_sinks"]))
nseat = sum(1 for k in sites if not re.search(r"__rs\d+$", k)); nc = sum(len(s["clones"]) for s in split)
ops = []
old = t.get("relay_split"); new = list(old or []) + split
ops.append({"path": f"partition_types.{tn}.relay_split", "old": old, "value": new})
olds = t.get("relay_sites"); news = dict(olds or {}); clash = [k for k in sites if k in news]; news.update({k: v for k, v in sites.items() if k not in news})
ops.append({"path": f"partition_types.{tn}.relay_sites", "old": olds, "value": dict(sorted(news.items()))})
json.dump({"schema": "opentallas.plan_ops.v1", "base": pj, "base_sha": hashlib.sha256(raw).hexdigest()[:12], "row": os.environ.get("ROW", "CLASSCOPY"), "ops": ops}, open(oo, "w"), indent=1)
if po:
    t["relay_split"] = new; t["relay_sites"] = ops[1]["value"]; open(po, "w").write(json.dumps(P, indent=1) + "\n")
hg = collections.Counter(re.sub(r"\[\d+\]$", "", h[0]) for h in hop)
print(f"CLASS_ROW flagged {len(C['rows'])} split {len(split)} copies {nc} seat {nseat} hop {len(hop)} skip {dict(skip)} clash {len(clash)}")
sg = collections.Counter(re.sub(r"\[\d+\]$", "", s["flop"]) for s in split)
print("split groups", sg.most_common(12)); print("hop groups", hg.most_common(12))
