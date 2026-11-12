"""Apply the rx_bm3_rest taller form to a plan: outline 197.856x345.6 -> 197.856x483.84 (+138.24 up, same origin/orient),
pins_file -> cores/ot_pdie_serdes_rx_bm3_rest__197.856x483.84__hg7_modelA.json. usage: apply_rxtall.py in.json out.json"""
import json,sys
D=json.load(open(sys.argv[1])); n=0
for t in D["partition_types"].values():
    for h in t.get("hard_cores",[]):
        if h.get("module")=="ot_pdie_serdes_rx_bm3_rest" and h["outline_um"]==[197.856,345.6]:
            h["outline_um"]=[197.856,483.84]; h["obs_max"]="M7"
            h["pins_file"]="cores/ot_pdie_serdes_rx_bm3_rest__197.856x483.84__hg7_modelA.json"; n+=1
print("rewrote",n); json.dump(D,open(sys.argv[2],"w"),indent=1)
