import json,collections,sys
d=json.load(open("physical/die_plan/qwen_kvsys/die_plan.json"))
P={p["name"]:p for p in d["partitions"]}
CH=[(0,17.28),(233.28,336.96),(552.96,656.64),(872.64,976.32),(1192.32,1278.72)]
CAP=0.25*(1/0.048+1/0.064)   # die GRT share V (M5+M7) per um
out={"cap_per_um_die_share":round(CAP,2),"boundaries":{}}
for col,x0 in (("hg",1900.8),("hgi",3179.52)):
  for r in range(0,8):
    a=f"{col}_WN_{r}"; 
    b=f"{col}_WN_{r+1}" if r<7 else None
    per=collections.Counter(); slots=collections.defaultdict(list)
    for pr in d["ports"]:
        ps={pr["src"]["part"],pr["dst"]["part"]}
        if a not in ps or pr["face"] not in "NS": continue
        other=(ps-{a}) and (ps-{a}).pop()
        if b and other!=b: continue
        if not b and other.startswith(col+"_WN"): continue
        w0,w1=sorted(pr["window_um"]); m=(w0+w1)/2-x0
        k=next((i for i,(u,v) in enumerate(CH) if u-1<=m<=v+1),-1)
        per[k]+=pr["width"]; slots[k].append((pr["src"]["bus"],pr["width"],round(w0-x0,1),round(w1-x0,1)))
    out["boundaries"][f"{a}|{b or 'S-nbr'}"]={str(k):{"bits":v,"chan_um":(CH[k] if k>=0 else None),"util_vs_die_share":(round(v/((CH[k][1]-CH[k][0])*CAP),2) if k>=0 else None),"slots":slots[k]} for k,v in sorted(per.items())}
json.dump(out,open(sys.argv[1],"w"),indent=1)
for k,v in out["boundaries"].items():
    print(k,{c:(x["bits"],x["util_vs_die_share"]) for c,x in v.items()})
