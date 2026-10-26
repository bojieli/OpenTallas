from pathlib import Path
import sys,json,math
R=Path("/srv/opentallas-scratch2/claude/codex-aux-pg-1026");sys.path.insert(0,str(R/"code/tools/die_plan"));import infra_pg as I;import infra_pg_domains as X
p=R/"s81/src/physical/die_plan/s81/die_plan_phyfit_proto.json";P=I.S.Plan(I.S.load(p),p);m=I.load_model(P,p.parent,core_watts=53.5,phy_w_per_macro=4.37);rg=next(q for q in m["regions"]if q["name"]=="io_lk_WS0_u_phy");r=rg["rect_um"];domain=next(q for q in P.die["pg"]["domains"]if q["name"]=="phy_lk_WS0")
pg=dict(grid=P.die["pg"]["grid"],bump_pitch_um=130,phy_w_per_macro=4.37,core_w_mm2=m["core_w_mm2"])
# Literal candidate rows at45um: select9 of every20 rows forPG (~45%); reserve all other sites for signals/control/unassigned.
nx=int((r[2]-r[0])//45);ny=int((r[3]-r[1])//45);ox=(r[0]+r[2]-(nx-1)*45)/2;oy=(r[1]+r[3]-(ny-1)*45)/2;bumps=[];reserved=[]
for j in range(ny):
 for i in range(nx):
  pt=[round(ox+i*45,6),round(oy+j*45,6)]
  if (j*9//20)!=((j+1)*9//20):bumps.append(["VDD"if(i+j)%2==0 else"VSS",*pt])
  else:reserved.append(pt)
window=dict(window=rg["name"],window_um=[max(0,r[0]-60),max(0,r[1]-300),min(P.W,r[2]+60),min(P.H,r[3]+300)])
meta=X.make(P,p.parent,pg,window,R/"s81/native_rows/psm",8.64,bumps,domain["grid"])
d=dict(plan=str(p),plan_sha256=__import__("hashlib").sha256(p.read_bytes()).hexdigest(),window=window,phy_rect_um=r,phy_power_w=rg["power_w"],core_watts_proxy=53.5,grid=pg["grid"],phy_grid=domain["grid"],bumps=bumps,reserved_sites=reserved,site_pitch_um=45,pg_sites=len(bumps),field_sites=nx*ny,qualification="PREPARATORY row candidate only: literal45um lattice with9/20PG rows, remaining sites reserved; signal map and assignment unfinalized;53.5W historical coreproxy,4.37W SerDes; no vendor or die signoff")
(R/"s81/native_rows/geometry.json").write_text(json.dumps(d,indent=1)+chr(10));print(d["qualification"],len(bumps),nx*ny)
