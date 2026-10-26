import json,sys
R="/srv/opentallas-scratch2/claude/tok-sched/kvbind"; T=R+"/tree"
a=json.loads(open(T+"/physical/die_plan/qwen_kvsys/bind/kv45/asbuilt_mission_pass0.json").read().replace("/srv/opentallas-scratch2/claude/codex-kv-token-1309/tree",T))
a["map_file"]=T+"/physical/die_plan/qwen_kvsys/bind/asbuilt_map_binder2.json"
m=json.load(open(R+"/compose/composition_all_heads_map.json"))
mp=dict(a.get("map",{})); parts=dict(mp.get("parts",{}))
clash=[k for k in m if k in parts and parts[k]!=m[k]]
assert not clash, clash[:5]
parts.update(m); mp["parts"]=parts; a["map"]=mp
a["compose"]=R+"/compose/composition_all_heads.json"
a["straps"]=list(a["straps"])+[r"native_composite_.*\.strap_(hid|bsel)"]
a["internal_stations_types"]=["kv3_sys_c"]
a["pack_by_sink"]=True; a["type_canon"]=True
a["note"]="TOK-SCHED 10-25 strict bind: aef2 folded plan + main POR + CLOCK compose a65 + all-head composition + composite ID straps + SYS_C native istations + pack_by_sink/type_canon. Base recipe kv45/asbuilt_mission_pass0.json"
json.dump(a,open(R+"/recipe_b1.json","w"),indent=1)
print("parts",len(parts),"straps",len(a["straps"]))
