import json,sys,math,copy,shutil
from pathlib import Path
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-s81-die-1351/tools/die_plan")
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/codex-s81-die-1351/tools/s81_dv")
import die_clock_mesh as D,die_clock as DC,schema as S
from graded_mesh_physical import cluster,blocked
B=Path("/srv/opentallas-scratch2/claude/codex-s81-graded-1351/p128_repaired");O=B.parent/"p128_bankrepair";O.mkdir(exist_ok=True)
P=S.Plan(S.load("/srv/opentallas-scratch2/claude/codex-s81-pd14-0818/die_plan_phy_contents.json"));C=json.load(open(B/"place.json"));N=json.load(open(B/"nets.json"));M=json.load(open(B/"mesh.json"));G=json.load(open(B/"graded_metal.json"));banks=json.load(open(B/"banks.json"));ko=list(DC.keepouts(P))+D.ft_halo_keepouts(P);recs=[]
incoming={ld:n["drv"] for n in N["nets"] for ld in n["loads"]};outgoing={n["drv"]:n["loads"] for n in N["nets"]}
for bad in D.hard_keepout_violations(P,C):
 name=bad["cell"]
 if C[name]["kind"]!="node":continue
 groups=[b for b in banks if b["parent"]==name];units=[u for b in groups for u in M["drivers"][b["site"]]["cells"]];omit=set(units+[name]);K=DC.KeepIndex(ko,die=(P.W,P.H))
 for nm,c in C.items():
  if nm not in omit:D.reserve_cell(K,nm,c)
 parent=incoming[name];px,py=D.C128.pin_xy(C,parent,"Y",D.ROW_Y);r=bad["keepout_um"];xoptions=[r[0]-6.48,r[2]+4.32];best=None
 for x in sorted(xoptions,key=lambda x:abs(x-C[parent]["x"])):
  x=D.snap(x,D.SITE_X)
  for dy in [0]+[v*4.32 for j in range(1,47) for v in (j,-j)]:
   y=D.snap(C[name]["y"]+dy,D.ROW_Y);node=dict(C[name],x=x,y=y)
   if D.hitf(K,(x+.81,y+.135)) or abs(px-(x+.162))+abs(py-(y+.135))>405:continue
   chosen=[];temp=[];ok=True
   for b in groups:
    found=None;bx,by=b["centre_um"];shift=b["shift_um"];strap=M["drivers"][b["site"]]["strap"];bx,by=(bx+shift,by) if strap=="M8" else (bx,by+shift)
    for sx in [0,4.32,-4.32,8.64,-8.64,17.28,-17.28,25.92,-25.92]:
     for sy in [0,4.32,-4.32,8.64,-8.64,17.28,-17.28]:
      for nc in [1,2,3,6]:
       cs=cluster(x+sx,by+sy,b["units"],nc)
       if any(D.hitf(K,(c["x"]+.81,c["y"]+.135)) for c in cs):continue
       if any(abs(x+1.728-(c["x"]+.162))+abs(y+.135-(c["y"]+.135))>405 for c in cs):continue
       trial={"n":node,**{str(i):c for i,c in enumerate(cs+temp)}}
       if D.placement_overlaps(trial):continue
       found=(cs,nc);break
      if found:break
     if found:break
    if not found:ok=False;break
    chosen.append((b,found[0],found[1]));temp+=found[0]
   if ok:best=(node,chosen);break
  if best:break
 if not best:recs.append(dict(cell=name,status="NO_JOINT_BANK_SITE"));print(recs[-1],flush=True);continue
 node,chosen=best;old=dict(C[name]);C[name]=node;record=dict(cell=name,old=old,new=node,banks=[])
 for b,cs,nc in chosen:
  names=M["drivers"][b["site"]]["cells"]
  for u,c in zip(names,cs):C[u]=c
  cx=sum(c["x"]+D.BUF_W/2 for c in cs)/len(cs);cy=sum(c["y"]+D.ROW_Y/2 for c in cs)/len(cs);oldc=b["centre_um"];b["centre_um"]=[cx,cy];b["shift_um"]=0;b["cols"]=nc;b["joint_node_relocation"]=True
  for a in G["attachments"]:
   if a["role"]=="driver" and a["units"]==names:
    # Explicit jog from moved bank to nearest physical rail; metal remains unencoded.
    xx=min(G["xs"],key=lambda v:abs(v-cx));yy=min(G["ys"],key=lambda v:abs(v-cy));layer="M8" if abs(yy-cy)<=abs(xx-cx) else "M9";a.update(layer=layer,xy_um=[cx,yy] if layer=="M8" else [xx,cy],bank_centre_um=[cx,cy],physical_jog_pending=True)
  M["drivers"][b["site"]]["physical_bank"].update(cols=nc,rows=math.ceil(len(cs)/nc),centre_um=[cx,cy],joint_node_relocation=True)
  record["banks"].append(dict(site=b["site"],old_centre=oldc,new_centre=[cx,cy],units=len(cs),cols=nc))
 recs.append(record);print(record,flush=True)
hard=D.hard_keepout_violations(P,C);hops=D.actual_clock_hop_violations(C,N["nets"],405);over=D.placement_overlaps(C);ft=D._body_keepout_violations(DC.KeepIndex(D.ft_halo_keepouts(P)),P.W,P.H,C)
report=dict(status="BLOCKED" if hard or hops or over or ft else "PLACEMENT_READY_PENDING_METAL",hardbody=len(hard),actual_pin_hops=len(hops),overlaps=len(over),ft_halos=len(ft),repairs=recs,qualified_timing=False)
M["meta"]["joint_bank_repair"]=report;M["clock_hard_keepout_violations"]=hard;M["clock_actual_hop_violations"]=hops
for fn,obj in [("REPAIR.json",report),("place.json",C),("mesh.json",M),("graded_metal.json",G),("banks.json",banks),("nets.json",N),("body_failures.json",hard),("hop_failures.json",hops)]: (O/fn).write_text(json.dumps(obj,separators=(",",":"))+"\n")
D.write_verilog(C,N["nets"],N["ports"],O/"ctree.v");print({k:v for k,v in report.items() if k!="repairs"},flush=True)
