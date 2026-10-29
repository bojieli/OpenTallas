# DIE-S81-26: exact 1:1 check, every CLK pin of the run 1_synth.v vs the slice (leaf sinks + planned original gates); FAIL on any delta
import json,re,sys,collections
sys.path.insert(0,sys.argv[3]); import core_sink_census as C
sl=json.load(open(sys.argv[1])); text=open(sys.argv[2]).read()
pin=re.compile(r"\.CLK\(\s*(\\\S+\s|[^)\s]+)\s*\)")
act={}
for m in C.INST.finditer(text):
    if m.group(1) in ("module","input","output","wire","assign","inout","reg"): continue
    p=pin.search(m.group(3))
    if p: act[C._net(m.group(2))]=m.group(1)
t=sl["core_tree"]; planned=collections.Counter()
for leaf in t["leaves"]:
    for s in leaf.get("sinks",[]):
        if s.endswith("/CLK"): planned[C.plain(s)]+=1
for g in t.get("gates") or []:
    if "clone_of" not in g: planned[g["inst"].replace("\\","")]+=1
dup=[k for k,v in planned.items() if v>1]
miss=sorted(set(act)-set(planned)); extra=sorted(set(planned)-set(act))
r=dict(actual_clk_pins=len(act),planned=sum(planned.values()),dup=len(dup),missing=len(miss),extra=len(extra),missing_first=miss[:8],extra_first=extra[:8],
       gates=len(t.get("gates") or []),copies=sum(1 for g in t.get("gates") or [] if "clone_of" in g),leaves=len(t["leaves"]),masters=collections.Counter(act.values()).most_common(5))
r["verdict"]="PASS" if not (dup or miss or extra) else "FAIL"
print(json.dumps(r,indent=1)); sys.exit(0 if r["verdict"]=="PASS" else 3)
