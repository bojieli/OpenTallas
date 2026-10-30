import json,sys
sys.path.insert(0,sys.argv[1]); import schema as S, reset_tree as RT
from pathlib import Path
P=S.Plan(json.load(open(sys.argv[2])),Path(sys.argv[2]))
M=(17.28,54.0,17.28+1848.96,54.0+972.0)
out={}
for tn in ("kv3_sys_SD","kv3_sys_SD_v1"):
    T=RT.for_type(P,tn)
    on=[r["q"] for r in T["relays"] if M[0]<r["xy"][0]<M[2] and M[1]<r["xy"][1]<M[3]]
    out[tn]=dict(summary=RT.summary(T),relays_on_macro=on,consumers=len(RT.consumer_taps(P,tn)))
    try: RT.verify(T); out[tn]["verify"]="PASS"
    except Exception as e: out[tn]["verify"]=str(e)
    RT.render(P,tn,f"{sys.argv[3]}/reset_tree_{tn}.png")
print(json.dumps(out,indent=1))
