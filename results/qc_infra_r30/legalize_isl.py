"""INFRA-FIRST-QC-R30: move FT bank cells that overlap a clock die island (or macro) to the nearest free legal
site of the same type (row grid 0.27, site grid 0.054), searching y rows first then neighbouring 2.16-um bank columns.
Deterministic; ledger of every move; max displacement reported (hop-length change <= displacement, Manhattan).
usage: legalize_isl.py REPO PLAN_IN PLAN_OUT"""
import json,sys,hashlib,math
from collections import defaultdict
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import schema as S
p=json.load(open(sys.argv[2])); out=sys.argv[3]
def hit(x,y,cw,ch,r): return x<r[2]-1e-6 and x+cw>r[0]+1e-6 and y<r[3]-1e-6 and y+ch>r[1]+1e-6
moves=[];fails=[]
for k,t in sorted(p["partition_types"].items()):
    isl=(t.get("clock") or {}).get("die_islands_um") or []
    if not isl: continue
    w,hh=t["outline_um"]; boxes=list(S.placed_macro_boxes(t,halo=0.).values())
    occ=defaultdict(list)
    for s in t["ft_slots"]:
        cw,ch=s.get("bit_site_cell_um",[1.404,.27])
        for bank in s.get("bit_sites_um",[]):
            for x,y in bank: occ[round(y/.27)].append([x,x+cw])
    def free(x,y,cw,ch):
        if x<0 or y<0 or x+cw>w+1e-6 or y+ch>hh+1e-6: return False
        if any(hit(x,y,cw,ch,r) for r in isl) or any(hit(x,y,cw,ch,b) for b in boxes): return False
        for rr in range(round(y/.27), round(y/.27)+max(1,round(ch/.27))):
            if any(x<b-1e-6 and x+cw>a+1e-6 for a,b in occ[rr]): return False
        return True
    for s in t["ft_slots"]:
        cw,ch=s.get("bit_site_cell_um",[1.404,.27])
        for j,bank in enumerate(s.get("bit_sites_um",[])):
            for i,(x,y) in enumerate(bank):
                if not (any(hit(x,y,cw,ch,r) for r in isl) or any(hit(x,y,cw,ch,b) for b in boxes)): continue
                rr=round(y/.27); occ[rr]=[iv for iv in occ[rr] if not (abs(iv[0]-x)<1e-9)]  # release own site
                cands=[]
                for dx in (0,-2.16,2.16,-4.32,4.32):
                    for dy in range(-12,13):
                        nx,ny=round(x+dx,4),round(y+dy*.27,4)
                        cands.append((abs(dx)+abs(dy*.27),dx!=0,abs(dy),nx,ny))
                cands.sort()
                for d,_,_,nx,ny in cands:
                    if free(nx,ny,cw,ch):
                        bank[i]=[nx,ny]; occ[round(ny/.27)].append([nx,nx+cw])
                        moves.append(dict(cls=k,slot=s["name"],bank=j+1,bit=i,frm=[x,y],to=[nx,ny],disp_um=round(d,4))); break
                else:
                    occ[rr].append([x,x+cw]); fails.append(dict(cls=k,slot=s["name"],bank=j+1,bit=i,xy=[x,y]))
json.dump(p,open(out,"w"),indent=0)
rep=dict(moves=len(moves),fails=len(fails),max_disp_um=max([m["disp_um"] for m in moves] or [0]),
         plan_sha256=hashlib.sha256(open(out,"rb").read()).hexdigest(),move_list=moves,fail_list=fails)
json.dump(rep,open(out.replace(".json","_legalize.json"),"w"),indent=1)
print({k:v for k,v in rep.items() if not k.endswith("_list")})
