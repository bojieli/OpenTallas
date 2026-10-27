"""count FT bank cells overlapping clock die islands per class, for all slots; usage PLAN [types...]"""
import json,sys
from collections import Counter
p=json.load(open(sys.argv[1])); pref=sys.argv[2:]
c=Counter(); tot=Counter()
for k,t in p["partition_types"].items():
    if pref and not any(k==q or k.startswith(q+"__cl") for q in pref): continue
    isl=(t.get("clock") or {}).get("die_islands_um") or []
    for s in t["ft_slots"]:
        cw,ch=s.get("bit_site_cell_um",[1.404,.27])
        for bank in s.get("bit_sites_um",[]):
            for x,y in bank:
                tot[k]+=1
                if any(x<r[2]-1e-6 and x+cw>r[0]+1e-6 and y<r[3]-1e-6 and y+ch>r[1]+1e-6 for r in isl): c[(k,s["name"])]+=1
print(sum(c.values()),"of",sum(tot.values())); 
for k,v in sorted(c.items()): print(v,k)
