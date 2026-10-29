#!/usr/bin/env python3
"""QC-IMPORT-1: QC plan of record = native h800 plan + START provider/reset_source (candidate2) + form (a) tap pin growth."""
import hashlib,json,sys
C,G,B,OUT=sys.argv[1:5]
sha=lambda p:hashlib.sha256(open(p,"rb").read()).hexdigest()
b,c,g=(json.load(open(p)) for p in (B,C,G))
assert sha(B)=="0ff4c77a67b2dd0df1d51a53b3f2a1b5c7633529dfa5a3b31928ff9374135c12"
assert sha(G)=="bddfe45dadd71636740d278a5b32adebc2f3e4e957d38b4cdf3846054853d8b4"
n=0
for tn,t in g["partition_types"].items():
    h=t.get("clock",{}).get("tap_pin_heights_um")
    if h is not None and h!=b["partition_types"][tn].get("clock",{}).get("tap_pin_heights_um"):
        c["partition_types"][tn]["clock"]["tap_pin_heights_um"]=h; n+=1
json.dump(c,open(OUT,"w"),indent=1)
print(json.dumps(dict(types_grown=n,base=sha(B),candidate2=sha(C),growth=sha(G),out=sha(OUT))))
