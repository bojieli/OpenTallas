# WHAT-IF (diagnostic, not a gate input): credit each early core tap clk_c<k> with its declared core insertion beyond
# the die common latency (schema.core_tap_early_ps: TT insertion_ps-250, FF insertion_ff_ps-202.5), since the
# die_sta_related declared-budget block model puts the same common latency on both sides of every pair.
import json,sys
sys.path.insert(0,sys.argv[3]); import schema as S
src,dst=sys.argv[1],sys.argv[2]
P=json.load(open("/srv/opentallas-scratch2/claude/die-s81-10/plan/plan_s10.json"))
PT=P["partition_types"]; parts={p["name"]:p["type"] for p in P["partitions"]}
class PP: pass
lat={"TT":250.0,"FF":202.5}
early={}
for pn,tn in parts.items():
    t=PT[tn] if isinstance(PT,dict) else None
    if not t or t.get("clock",{}).get("core_taps")!="early": continue
    k=0
    for tp in t["clock"].get("taps",[]):
        if tp.get("kind")!="core": continue
        for C in ("TT","FF"):
            early[(f"t_{pn}__clk_c{k}",C)]=max(0.0,S.core_tap_insertion_ps(tp,C)-lat[C])
        k+=1
st={}
for C in ("TT","FF"):
    d=json.load(open(f"{src}/tap_arrivals_{C}.json")); n=0
    for t in d["taps"]:
        e=early.get((t["port"],C))
        if e is None: continue
        n+=1
        for a in ("late_ps","early_ps","abs_late_ps","abs_early_ps"):
            if a in t: t[a]+=e
    d["whatif"]="early core taps + declared core insertion beyond common latency; DIE-S81-14 diagnostic"
    json.dump(d,open(f"{dst}/tap_arrivals_{C}.json","w")); st[C]=n
print(st, len(early)//2)
