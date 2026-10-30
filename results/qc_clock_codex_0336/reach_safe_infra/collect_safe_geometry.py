import json,hashlib,sys,collections,math
from pathlib import Path
r=Path("/srv/opentallas-scratch2/claude/codex-qc-clock-0336");p=r/"reach_safe/out/kit/clock/tree.json";t=json.load(open(p));sites=t["sites"]
rows=[]
for c,pa in t["parent_of"].items():
 a,b=sites[c],sites[pa];rows.append((sum(abs(x-y)for x,y in zip(a,b)),pa,c))
badx={k:xy for k,xy in sites.items()if abs(xy[0]/.054-round(xy[0]/.054))>1e-5}
bady={k:xy for k,xy in sites.items()if abs(xy[1]/.54-round(xy[1]/.54))>1e-5}
rec={"scope":"Reach-safe generation geometry estimate only. PHY native-entry/body contract and final target/island/PG qualification pending; never frozen physical PASS.","tree_sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"tree_keys":list(t),"nodes":len(t.get("nodes",{})),"clock_cells":len(sites),"clock_edges":len(rows),"max_actual_origin_manhattan_um":max(x[0]for x in rows),"over405":sum(d>405+1e-6 for d,_,_ in rows),"over400":sum(d>400+1e-6 for d,_,_ in rows),"off_54nm_x":len(badx),"off_540nm_R0_y":len(bady),"longest_edges":sorted(rows,reverse=True)[:25],"offsite_examples":{"x":list(badx.items())[:5],"y":list(bady.items())[:5]}}
for k,v in t.items():
 if k not in["nodes","sites","parent_of","taps","node_buf","edges","tap_driver","tap_load","wire_segments"]and isinstance(v,(int,float,str,bool,type(None))):rec[k]=v
rec["model_metadata_keys"]={k:list(v)[:20]for k,v in t.items()if isinstance(v,dict)and k not in["sites","nodes","parent_of","node_buf","tap_driver","tap_load"]}
(r/"reach_safe/geometry_summary.json").write_text(json.dumps(rec,indent=1)+"\n");print(json.dumps(rec,indent=1))
