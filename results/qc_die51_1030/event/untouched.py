import json,sys,collections
d="physical/die_plan/qwen_compute/plan_of_record/"
A=json.load(open(d+"plan_qc49.json"));B=json.load(open(d+"plan_qc52.json"))
inst=collections.Counter(p["type"] for p in B["partitions"])
same=[];chg={}
for tn,t in B["partition_types"].items():
    a=A["partition_types"].get(tn)
    if a is None: chg[tn]=["new"];continue
    ks=[k for k in ("outline_um","buses","ft_slots","hard_cores","contents") if json.dumps(a.get(k),sort_keys=True)!=json.dumps(t.get(k),sort_keys=True)]
    ck=[k for k in ("taps","tap_mode","landing_contract") if json.dumps(a.get("clock",{}).get(k),sort_keys=True)!=json.dumps(t.get("clock",{}).get(k),sort_keys=True)]
    if ks or ck: chg[tn]=ks+["clock."+k for k in ck]
    else: same.append(tn)
slots=collections.defaultdict(set)
for p in B["partitions"]:
    a=next((q for q in A["partitions"] if q["name"]==p["name"]),None)
    if a is None or json.dumps({k:a.get(k) for k in ("origin_um","orient","type")})!=json.dumps({k:p.get(k) for k in ("origin_um","orient","type")}): slots[p["type"]].add(p["name"])
for tn in list(same):
    if slots.get(tn): chg[tn]=["slot"]; same.remove(tn)
print("UNTOUCHED",len(same),[(t,inst[t]) for t in sorted(same)])
print("CHANGED",len(chg))
print(collections.Counter(tuple(v) for v in chg.values()).most_common(12))
print("nonslice changed",sorted(t for t in chg if not t.startswith(("sle_","slw_"))))
hc=collections.Counter()
for tn,t in B["partition_types"].items():
    for h in t.get("hard_cores",[]): hc[(h.get("module") or h.get("master") or h.get("inst"),h.get("pins_file"))]+=1
print("hardcores",len(hc)); [print(" ",k,v) for k,v in sorted(hc.items(),key=str)]
