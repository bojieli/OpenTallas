"""R30 check: row overlaps + macro/island hits on ALL FT bank cells, and adjacent-bank hop (same bit index) for moved bits."""
import json,sys
from collections import defaultdict
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import schema as S
p=json.load(open(sys.argv[2])); led=json.load(open(sys.argv[3]))
def hit(x,y,cw,ch,r): return x<r[2]-1e-6 and x+cw>r[0]+1e-6 and y<r[3]-1e-6 and y+ch>r[1]+1e-6
ov=0;hits=0
for k,t in p["partition_types"].items():
    isl=(t.get("clock") or {}).get("die_islands_um") or []; boxes=list(S.placed_macro_boxes(t,halo=0.).values())
    rows=defaultdict(list)
    for s in t["ft_slots"]:
        cw,ch=s.get("bit_site_cell_um",[1.404,.27])
        for bank in s.get("bit_sites_um",[]):
            for x,y in bank:
                rows[round(y/.27)].append((x,x+cw))
                if any(hit(x,y,cw,ch,r) for r in isl+boxes): hits+=1
    for ints in rows.values():
        ints.sort(); ov+=sum(1 for a,b in zip(ints,ints[1:]) if b[0]<a[1]-1e-6)
worst=(0,None)
for m in led["move_list"]:
    s=[s for s in p["partition_types"][m["cls"]]["ft_slots"] if s["name"]==m["slot"]][0]; B=s["bit_sites_um"]; j=m["bank"]-1; i=m["bit"]
    for jj in (j-1,j+1):
        if 0<=jj<len(B) and i<len(B[jj]):
            d=abs(B[jj][i][0]-B[j][i][0])+abs(B[jj][i][1]-B[j][i][1])
            if d>worst[0]: worst=(d,(m["cls"],m["slot"],j+1,jj+1,i))
print(dict(row_overlaps=ov,island_or_macro_hits=hits,max_adjacent_bank_hop_of_moved_bits_um=round(worst[0],3),at=worst[1]))
