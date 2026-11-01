import sys,json,copy,numpy as np,time
from pathlib import Path
R=Path("/srv/opentallas-scratch2/claude/codex-hbm-rootstations-1101");W=R
sys.path.insert(0,str(W/"tools/die_plan"));sys.path.insert(0,str(W))
import schema as S,ft_corridor as FC
from gen_phys import type_pins
from tools.die_trial.legal_sites import RowAllocator
raw=json.load(open(R/"base.json"));model=S.Plan(raw,None);bad=json.load(open(R/"failures.json"));ledger=[]
old_build=FC.build_path
def corridor_path(fin,fout,ca,cb,w,h,jog=None):
 if jog is None:return old_build(fin,fout,ca,cb,w,h,jog)
 ca,cb=np.asarray(ca),np.asarray(cb)
 if fin in "EW":return [ca,np.array([jog,ca[1]]),np.array([jog,cb[1]]),cb]
 return [ca,np.array([ca[0],jog]),np.array([cb[0],jog]),cb]
FC.build_path=corridor_path
for tn in ["root"]:
 t=model.types[tn];w,h=t["outline_um"];todo={x["slot"] for x in bad if x["type"]==tn};pins={(b,i):(x,y) for b,i,l,x,y,f in type_pins(model,tn)}
 boxes=list(S.placed_macro_boxes(t,halo=FC.KEEPOFF).values());al=RowAllocator((4.32,4.32,w-4.32,h-4.32),blocked=boxes,cell_size=FC.CELL,column_pitch=2.16,row_pitch=.27,origin=(4.32,4.32))
 for s in t.get("ft_slots",[]):
  if s["name"] in todo or not s.get("bit_sites_um"):continue
  cw,ch=s["bit_site_cell_um"]
  for st in s["bit_sites_um"]:
   for x,y in st:al.reserve_rectangle((x,y,x+cw,y+ch))
 for s in sorted([x for x in t["ft_slots"] if x["name"] in todo],key=lambda x:-x["width"]):
  name=s["name"];n=s["width"]+1;a=np.array([pins[(name+"_i",i)] for i in range(n)]);b=np.array([pins[(name+"_o",i)] for i in range(n)]);old=copy.deepcopy(s);used=set(al.used);success=None;trials=[]
  # No new cycles: try the normal Manhattan path and alternate channel jogs only.
  ext=w if s["in_face"] in "EW" else h
  axis=0 if s["in_face"] in "EW" else 1
  lo,hi=sorted([a.mean(0)[axis],b.mean(0)[axis]])
  opts=[(lo+hi)/2,lo+(hi-lo)*.75,lo+(hi-lo)*.25,ext*.5,ext*.75,ext*.25]
  for jog in opts:
   al.used=set(used);started=time.time()
   try:
    sites,cents,path,led=FC.place_slot(s,a,b,s["in_face"],s["out_face"],w,h,boxes,al,403.,jog=jog,step=12.,jog_lane=n*FC.LANE_UM_PER_BIT)
    success=(sites,cents,path,led);trials.append(dict(jog=jog,status="PASS",sec=round(time.time()-started,1)));break
   except Exception as e:
    trials.append(dict(jog=jog,status="FAIL",reason=str(e),sec=round(time.time()-started,1)));print(tn,name,"trial",trials[-1],flush=True)
  rec=dict(type=tn,slot=name,width=s["width"],old_stations=old["stations"],new_stations=old["stations"],added_cycles=0,trials=trials)
  if success:
   sites,cents,path,led=success;s["regs_um"]=[a.mean(0).round(4).tolist()]+[q.round(4).tolist() for q in cents];s["bit_site_cell_um"]=list(FC.CELL);s["bit_sites_um"]=[(q-np.array(FC.CELL)/2).round(6).tolist() for q in sites];s["note"]=(s.get("note","")+" | CODEX station reach repair: all per-bit hops <=403 um, cycles unchanged")
   rec.update(status="PASS",geometry=led,old_regs_um=old["regs_um"],new_regs_um=s["regs_um"]);print("PASS",tn,name,led.get("hops_um"),flush=True)
  else:
   al.used=set(used)
   # Failed old sites stay occupied so another repaired slot cannot reuse them.
   cw,ch=s["bit_site_cell_um"]
   for st in s["bit_sites_um"]:
    for x,y in st:al.reserve_rectangle((x,y,x+cw,y+ch))
   rec.update(status="UNRESOLVED",lower_bound_hops=int(np.ceil(abs(a-b).sum(1).max()/405.)))
   print("UNRESOLVED",tn,name,flush=True)
  ledger.append(rec);json.dump(ledger,open(R/"ledger.json","w"),indent=2)
 # Snapshot after each type; output is not consumed until DONE.
 with open(R/"repaired.json.tmp","w") as f:json.dump(raw,f,separators=(",",":"))
 (R/"repaired.json.tmp").replace(R/"repaired.json")
(R/"DONE").write_text("done\n")
print("DONE PASS",sum(x["status"]=="PASS" for x in ledger),"UNRESOLVED",sum(x["status"]!="PASS" for x in ledger),flush=True)
