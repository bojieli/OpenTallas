#!/usr/bin/env python3
"""Native4-quarter district probe: source stages, actual C11 HCOL pins, fixed hub obstacles.
Does not edit or adopt a plan. All source f/r/g stages stay at their existing ages.
"""
import argparse,json,math,re,collections
from pathlib import Path
import matplotlib;matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
W,H=218.592,187.488;HP,CP,EY=224.64,449.28,1391.04
ROW=[0,267.84,483.84,751.68];BH=939.168;YBASE=8.64;XBASE=8.64
QW,QH=1808.352,2347.488

def rawpins(p):
 d=json.load(open(p));return d.get("pins",d) if isinstance(d,dict) else d

def named(ps,b):return {int(re.search(r"\[(\d+)\]",p["name"])[1]):p for p in ps if p["name"].startswith(b+"[")}
def point(p,e,c,k,h):return [XBASE+c*CP+h*HP+p["x"],YBASE+e*EY+ROW[k]+(H-p["y"] if k%2 else p["y"])]
def recthit(a,b):return a[0]<b[2]-1e-6 and b[0]<a[2]-1e-6 and a[1]<b[3]-1e-6 and b[1]<a[3]-1e-6

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--data",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);ap.add_argument("--align-shared-pins",action="store_true");a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 pins=[rawpins(a.data/f"pins_h{h}.json") for h in range(2)]
 pin_changes=[]
 if a.align_shared_pins:
  p0={p["name"]:p for p in pins[0]}
  for p in pins[1]:
   z=p0.get(p["name"]);
   if z and z["layer"]=="M5" and abs(z["y"]-(H-.019))<.1:
    if(p["x"],p["y"])!=(z["x"],z["y"]):pin_changes.append(dict(name=p["name"],old=[p["x"],p["y"]],new=[z["x"],z["y"]]))
    p["x"],p["y"]=z["x"],z["y"]
 qb=[named(p,"q_b")for p in pins];kp=[named(p,"key")for p in pins]
 qrank={j:i for i,j in enumerate(sorted(qb[0],key=lambda j:qb[0][j]["x"]))}
 cores=[];arcs=collections.defaultdict(list);bad=[];banks=[];clocks=[];ffpoints=[]
 def arc(kind,src,dst,tag):
  d=abs(src[0]-dst[0])+abs(src[1]-dst[1]);arcs[kind].append(d)
  if not kind.startswith("SRAM"):ffpoints.append(src)
  if "hcol"not in kind:ffpoints.append(dst)
  if d>405+1e-6:bad.append(dict(kind=kind,tag=tag,length_um=round(d,6),source=src,target=dst))
 def bank(name,x,y,w=100,h=8.64):banks.append(dict(name=name,rect_um=[x-w/2,y-h/2,x+w/2,y+h/2]))
 for e in range(2):
  for c in range(4):
   for k in range(4):
    for hf in range(2):
     x=XBASE+c*CP+hf*HP;y=YBASE+e*EY+ROW[k];ori="MX"if k%2 else"R0"
     cores.append(dict(name=f"e{e}c{c}k{k}h{hf}",module=f"ot_hbm_idx_score_hcol_h{hf}",origin_um=[x,y],outline_um=[W,H],orient=ori))
     for p in pins[hf]:
      if p["name"].startswith("clk_pair"):
       pp=point(p,e,c,k,hf);clocks.append(dict(core=cores[-1]["name"],port=p["name"],pin_um=pp,island_um=[x+103.68,y+(88.128 if k%2 else 90.72),x+112.32,y+(96.768 if k%2 else 99.36)],common_clock="833ps",planned_stack_candidate_um=[x+104.544,y+95.04],qualification="ANALYTIC_PG_GAP_ONLY_NOT_ROUTED"))
   # Query: one source rq bit reaches all8 actual HCOL pins. f_q and g_q are independent existing banks.
   for j in range(568):
    qx=XBASE+c*CP+(qb[0][j]["x"]+qb[1][j]["x"]+HP)/2
    qy=YBASE+e*EY+469.584+((qrank[j]%12)-5.5)*.27
    rq=[qx,qy]
    if c==0:
     fx=XBASE+221.616+((qrank[j]%3)-1)*1.08
     delta=400-abs(fx-qx)
     fy=(qy+delta) if e==0 else(qy-delta)
     fq=[fx,fy]
     qrx=fx;qry=YBASE+1160.91-(qrank[j]//5)*.27
     arc("q_r_to_first_f_q",[qrx,qry],fq,f"e{e}b{j}")
    elif c==1:fq=[qx,YBASE+e*EY+(700 if e==0 else BH-700)]
    else:fq=[qx,qy]
    arc("f_q_to_rq",fq,rq,f"e{e}c{c}b{j}")
    for k in range(4):
     for hf in range(2):arc("rq_to_hcol_q_p",rq,point(qb[hf][j],e,c,k,hf),f"e{e}c{c}k{k}h{hf}b{j}")
    if c<3:
     nx=qx+CP
     if c==0:ny=YBASE+e*EY+(700 if e==0 else BH-700);g=[nx-216,ny];nf=[nx,ny]
     elif c==1:g=[qx+293.76,fq[1]];nf=[nx,YBASE+e*EY+469.584+((qrank[j]%12)-5.5)*.27]
     else:g=[qx+216,fq[1]];nf=[nx,fq[1]]
     arc("f_q_to_g_q",fq,g,f"e{e}c{c}b{j}");arc("g_q_to_next_f_q",g,nf,f"e{e}c{c}b{j}")
   bank(f"rq_e{e}c{c}",XBASE+c*CP+170, YBASE+e*EY+469.584,110)
   # Key routes use exactly kl_r(1), f_key(2+2c), rkey/g_key(3+2c), HCOLkey_p(4+2c).
   for k in range(4):
    def f_y(cc):
     if e==0:
      return ([706,718,730,742][k]if cc==0 else([463.32,475.2,730,742][k]if cc==1 else[205,237,730,742][k]))
     return ([203,215,227,239][k]if cc==0 else([203,215,463.32,475.2][k]if cc==1 else[203,215,704,736][k]))
    ry=([463.32,475.2,704,736]if e==0 else[205,237,463.32,475.2])[k]
    for j in range(544):
     kx=XBASE+c*CP+kp[0][j]["x"];jy=((qrank[j]%12)-5.5)*.27
     f=[kx,YBASE+e*EY+f_y(c)+jy];r=[kx+HP/2,YBASE+e*EY+ry+jy]
     arc("f_key_to_rkey",f,r,f"e{e}c{c}k{k}b{j}")
     for hf in range(2):arc("rkey_to_hcol_key_p",r,point(kp[hf][j],e,c,k,hf),f"e{e}c{c}k{k}h{hf}b{j}")
     if c==0:
      lane=e*4+k;kl=[194.4+((j%12)-5.5)*1.08,YBASE+[988,1008,1028,1048,1288,1308,1328,1348][lane]+((j//12)%64-31.5)*.27]
      arc("kl_r_to_first_f_key",kl,f,f"lane{lane}b{j}")
     if c<3:
      nf=[kx+CP,YBASE+e*EY+f_y(c+1)+jy];off=319.68 if abs(nf[1]-f[1])>100 else 216
      g=[kx+off,f[1]];arc("f_key_to_g_key",f,g,f"e{e}c{c}k{k}b{j}");arc("g_key_to_next_f_key",g,nf,f"e{e}c{c}k{k}b{j}")
    bank(f"rkey_e{e}c{c}k{k}",XBASE+c*CP+275,YBASE+e*EY+ry,104)
 # Soft17 SRAM compactcluster in engine boundary street; shared data slices keep source identity.
 sr=[]
 for j in range(17):
  row=j//2;x=8.64+(j%2)*198.72;y=950.4+row*43.2+(43.2 if row>=4 else 0)
  sr.append(dict(name=f"keybuf.gm[{j}].mem",origin_um=[x,YBASE+y],outline_um=[172.824,41.064],kind="SOFT_REAL_SRAM"))
 # Conservative source SRAM-output to kl_r bound: every possible edge pin is covered.
 for lane in range(8):
  for j in range(544):
   mm=sr[(lane*544+j)//256];xx,yy=mm["origin_um"];kl=[194.4+((j%12)-5.5)*1.08,YBASE+[988,1008,1028,1048,1288,1308,1328,1348][lane]+((j//12)%64-31.5)*.27]
   corner=max([[xx,yy],[xx+172.824,yy],[xx,yy+41.064],[xx+172.824,yy+41.064]],key=lambda z:abs(z[0]-kl[0])+abs(z[1]-kl[1]));arc("SRAM_rd_to_kl_r_corner_bound",corner,kl,f"lane{lane}b{j}")
 ctrl=[194.4,YBASE+1165.104]
 for mm in sr:
  xx,yy=mm["origin_um"]
  for q in [[xx,yy],[xx+172.824,yy],[xx,yy+41.064],[xx+172.824,yy+41.064]]:arc("control_window_to_SRAM_corner_bound",ctrl,q,mm["name"])
 # Two native hard-tail reservations. Their E-glue timing graph is a separate remaining check.
 tails=[dict(name=f"tail_e{e}",origin_um=[1581.12,YBASE+976.32+e*216],outline_um=[W,H],kind="NATIVE_TAIL_RESERVE")for e in range(2)]
 illegal=[]
 for pt in ffpoints:
  for ob in cores+sr:
   xx,yy=ob["origin_um"];ww,hh=ob["outline_um"]
   if xx+.02<pt[0]<xx+ww-.02 and yy+.02<pt[1]<yy+hh-.02:illegal.append(dict(point=pt,inside=ob["name"]));break
 # Real hub feasibility: fixed VM/FUSED positions untouched; movable collisions are a required re-plan, not accepted packing.
 plan=json.load(open(a.data/"base_c8b/die_plan.json"));hub=[];qx,qy=3974.4,829.44
 qr=[qx,qy,qx+QW,qy+QH]
 for tn in["q_hub_nw","q_hub_ne"]:
  fixed=[];move=[]
  for h in plan["partition_types"][tn]["hard_cores"]:
   if"keybuf"in h["module"]:continue
   x,y=h["origin_um"];w,hh=h["outline_um"];halo=h.get("halo_um",4.32);rr=[x-halo,y-halo,x+w+halo,y+hh+halo]
   if recthit(qr,rr):
    v=dict(inst=h["inst"],module=h["module"],rect_with_halo_um=rr,halo_um=halo)
    (fixed if any(s in h["module"] for s in["fused","vms_bank"])else move).append(v)
  hub.append(dict(type=tn,candidate_rect_um=qr,fixed_collisions=fixed,movable_collisions=move,adoption="NOT ADOPTED; source-aware relocation and reprice required"))
 # Stack candidates avoid nominal 8.64-pitch/0.48-width die PG stripes.
 # These are model clearance checks; actual parent die-grid offsets must be bound before route.
 stack_records=[]
 for z in clocks:
  sx,sy=z["planned_stack_candidate_um"];ix0,iy0,ix1,iy1=z["island_um"]
  clearance=lambda v:abs(((v-4.32+4.32)%8.64)-4.32)-.24
  stack_records.append(dict(core=z["core"],port=z["port"],stack_um=[sx,sy],inside_actual_island=ix0<=sx<=ix1 and iy0<=sy<=iy1,nominal_pg_edge_clearance_um=[round(clearance(sx),6),round(clearance(sy),6)],pin_to_stack_l1_um=round(abs(sx-z["pin_um"][0])+abs(sy-z["pin_um"][1]),6)))
 json.dump(stack_records,open(a.out/"clock_stack_candidates.json","w"),indent=2)
 summary=dict(schema="opentallas.native_quarter_geometry.v1",source="ef994fe770 /44a5cccc2d",added_cycles=0,hard_hcol=64,hard_tail=2,soft_sram=17,illegal_source_ff_points=illegal,soft_standard_cells=227684,outline_um=[QW,QH],clock_pair_count=len(clocks),stage_ages=dict(kl_r=1,f_key=[2,4,6,8],rkey=[3,5,7,9],HCOL_key_p=[4,6,8,10]),arcs={k:dict(count=len(v),max_um=round(max(v),6))for k,v in arcs.items()},reach_failures=bad,hub=hub,required_h1_pin_reorder=pin_changes,clock_stack_nominal_min_pg_clearance_um=min(min(z["nominal_pg_edge_clearance_um"])for z in stack_records),clock_stack_outside_actual_islands=sum(not z["inside_actual_island"]for z in stack_records),unclosed=["Native H1 outputs through b_w/e_bus and E-glue into exact tail pins", "Whole hub mover relocation with native connected-source reach", "Full soft cell placement/cut congestion/parent clock and reset distribution", "Actual die PG offsets, M8/M9 via geometries and hold/STA"],qualification="MODEL_ONLY; no plan edit, no P&R; clock stacks analytical candidates only")
 json.dump(summary,open(a.out/"summary.json","w"),indent=2);json.dump(dict(cores=cores,tails=tails,srams=sr,banks=banks,clock_sites=clocks),open(a.out/"layout.json","w"),indent=2)
 fig,ax=plt.subplots(figsize=(13,15))
 for h in cores:
  x,y=h["origin_um"];ax.add_patch(Rectangle((x,y),W,H,fc="#d9e5f2"if h["orient"]=="R0"else"#c7dcc7",ec="k",lw=.35));ax.text(x+3,y+H/2,h["name"]+" "+h["orient"],fontsize=5)
  edge=y if h["orient"]=="MX"else y+H;ax.plot([x+8.9,x+209.8],[edge,edge],color="#e59000",lw=2)
 for m in sr:
  x,y=m["origin_um"];ax.add_patch(Rectangle((x,y),172.824,41.064,fc="#b889bd",ec="k",lw=.4));ax.text(x+2,y+12,m["name"],fontsize=5)
 for t in tails:
  x,y=t["origin_um"];ax.add_patch(Rectangle((x,y),W,H,fc="#edba73",ec="k",lw=.6));ax.text(x+5,y+H/2,t["name"],fontsize=6)
 for b in banks:
  x,y,x1,y1=b["rect_um"];ax.add_patch(Rectangle((x,y),x1-x,y1-y,fc="#bb4422",alpha=.7))
 for e in range(2):
  for c in range(4):
   for off in [187.488,671.328]:
    yy=YBASE+e*EY+off+8.64
    for xx in[34.56,103.68,172.8,241.92,311.04,380.16]:ax.add_patch(Rectangle((XBASE+c*CP+xx-4.32,yy-4.32),8.64,8.64,fc="red",alpha=.8))
 ax.set_xlim(-10,QW+10);ax.set_ylim(-10,QH+10);ax.set_aspect("equal");ax.set_title(f"Nativequarter source-stage district:64HCOL,17SRAM; zero added cycles\nReach failures {len(bad)}; MODEL ONLY, no P&R");fig.savefig(a.out/"quarter.png",dpi=150,bbox_inches="tight")
 fig,axs=plt.subplots(2,1,figsize=(16,14))
 for ax,hn in zip(axs,hub):
  for h in plan["partition_types"][hn["type"]]["hard_cores"]:
   if"keybuf"in h["module"]:continue
   x,y=h["origin_um"];w,hh=h["outline_um"];fixed=any(s in h["module"]for s in["fused","vms_bank"]);ax.add_patch(Rectangle((x,y),w,hh,fc="#8899bb"if fixed else"#dddddd",ec="k",lw=.3))
  ax.add_patch(Rectangle((qx,qy),QW,QH,fc="#ffcc66",alpha=.45,ec="red",lw=2));ax.set_xlim(0,8216.64);ax.set_ylim(0,4320);ax.set_aspect("equal");ax.set_title("{} fixed collisions {} / movable {}".format(hn["type"],len(hn["fixed_collisions"]),len(hn["movable_collisions"])))
 fig.savefig(a.out/"hub_probe.png",dpi=130,bbox_inches="tight")
 print(json.dumps(dict(arc_counts={k:len(v)for k,v in arcs.items()},reach_failures=len(bad),illegal_points=len(illegal),worst=sorted(bad,key=lambda q:-q["length_um"])[:5],hub=[dict(type=h["type"],fixed=len(h["fixed_collisions"]),movable=len(h["movable_collisions"]))for h in hub])))
if __name__=="__main__":main()
