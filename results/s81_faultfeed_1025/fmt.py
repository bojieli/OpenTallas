import json,sys
src,dst=sys.argv[1],sys.argv[2]
p=json.load(open(src)); slots={}
for tn,t in p["partition_types"].items():
  for key in ("hard_cores","ft_slots"):
    fs=t.get(key)
    if fs:
        for i,s in enumerate(fs):
            k="@@FT%d@@"%len(slots); slots[k]=json.dumps(s,separators=(",",":")); fs[i]=k
txt=json.dumps(p,indent=1)
for k,v in slots.items(): txt=txt.replace(json.dumps(k),v,1)
open(dst,"w").write(txt+("\n" if open(src).read().endswith("\n") else ""))
assert json.load(open(dst))==json.load(open(src))
