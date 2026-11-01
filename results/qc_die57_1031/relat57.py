# DIE-QC-57: recompute plan latency.lanes with main gen.latency_table (same as `gen.py latency --inplace`) after the
# count_aligned_cycles +1 event, keeping the plan file format (json.dumps + newline). Checks the base table reproduces.
import json,sys
sys.path.insert(0,"tools/die_plan")
import gen, schema as S
plan=sys.argv[1]; s=open(plan).read(); raw=json.loads(s); assert json.dumps(raw)+"\n"==s
errs=S.validate(raw); assert not errs, errs[:5]
P=S.Plan(raw); sk=P.landed_skew(); assert not sk, sk[:5]
tab=gen.latency_table(P); old=raw["latency"]["lanes"]
assert set(tab)==set(old)
ch={l:(old[l]["cycles"],tab[l]["cycles"]) for l in tab if tab[l]!=old[l]}
other=[l for l in ch if {k for k in tab[l] if tab[l][k]!=old[l].get(k)}-{"cycles","clock_landing"}]
print("lanes",len(tab),"changed",len(ch),"deltas",sorted({b-a for a,b in ch.values()}),"non-cycle field changes",len(other))
if len(sys.argv)>2 and sys.argv[2]=="--write":
    raw["latency"]["lanes"]=tab; open(plan,"w").write(json.dumps(raw)+"\n"); print("written")
