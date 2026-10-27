cd $1; for f in $(ls *.gate.json 2>/dev/null); do python3 - $f <<'P'
import json,sys
n=sys.argv[1][:-10]
d=json.load(open(sys.argv[1]))
g=d["gates"]; p=g.get("P_asbuilt",{})
if not p: print(n,"partial"); sys.exit()
print(n, d.get("verdict"), "".join(k[:2]+v["verdict"][0]+" " for k,v in g.items()), "TT",p.get("TT",{}).get("mean"),"w",p.get("TT",{}).get("window"),"FFe",p.get("FF_early",{}).get("mean"),"w",p.get("FF_early",{}).get("window"), "trunk", (d.get("entry_trunk") or {}).get("pred_with_trunk"), "G5n",len(g["G5_sram_structure"]["nodes_in_pin_column"]),"x",len(g["G5_sram_structure"]["legs_across_sram"]),"G4f",len(g["G4_detour_sites"]["failures"]), g["G4_detour_sites"]["repeaters_per_edge"])
P
done
