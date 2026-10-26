"""Shift the SYS_C PHY/corridor together into the 200um shoreline envelope.
No pins, station counts, outline or programmed latency change from approved SYS_C2.
"""
import copy,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[4]/"tools/die_plan"))
import schema as S
import gen_phys as G
import taps as TP

def apply(raw,io,shift=43.2):
 old=copy.deepcopy(raw);t=raw["partition_types"]["kv3_sys_c"]
 m=next(c for c in t["contents"] if c["module"]=="ot_qkvd_ucie_x64_phy")
 assert abs(m["origin_um"][1]-17.28)<1e-5,"expected approved SYS_C2 input, not an already shifted plan"
 m["origin_um"][1]=round(m["origin_um"][1]+shift,4)
 for d in raw["die"]["pg"]["domains"]:
  if d["name"]=="phy_sys_c_ucie":
   d["rect_um"][1]=round(d["rect_um"][1]+shift,4);d["rect_um"][3]=round(d["rect_um"][3]+shift,4)
   if d.get("bumps",{}).get("rect_um"):
    d["bumps"]["rect_um"][1]=round(d["bumps"]["rect_um"][1]+shift,4);d["bumps"]["rect_um"][3]=round(d["bumps"]["rect_um"][3]+shift,4)
 for b in t["clock"]["keepouts_um"]:b[1]=round(b[1]+shift,4);b[3]=round(b[3]+shift,4)
 s=next(v for v in t["ft_slots"] if v["name"]=="ft1")
 for j in [3,4,5,6]:
  for q in s["bit_sites_um"][j]:q[1]=round(q[1]+shift,4)
 s["note"]+="; SYS_C3 PHY shoreline +43.2um, north-corridor stages3..6 shifted equally; pins/counts/cycles unchanged"
 for e in t["internal_stations"]:
  if e["conn"]=="bus:o_host_link_rst_n":
   for q in e["regs_um"]:
    if abs(q[1]-816.48)<1e-5:q[1]=round(q[1]+shift,4)
   e["note"]+="; SYS_C3 trunk shifted equally to859.68um"
 part=next(p for p in raw["partitions"] if p["type"]=="kv3_sys_c");ox,oy=part["origin_um"];x,y=m["origin_um"];w,h=m["outline_um"]
 for a in io:
  if a["name"]=="io_sys_c_ucie_rom":a["rect_um"]=[ox+x,oy+y,ox+x+w,oy+y+h]
 P=S.Plan(raw);pins={(n,i):(x,y) for n,i,l,x,y,f in G.type_pins(P,"kv3_sys_c")}
 cw,ch=s["bit_site_cell_um"];maxhop=0;near=[]
 for i in range(s["width"]+1):
  q=[pins["ft1_i",i]]+[(a[i][0]+cw/2,a[i][1]+ch/2) for a in s["bit_sites_um"]]+[pins["ft1_o",i]]
  maxhop=max(maxhop,max(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(q,q[1:])))
  for a in s["bit_sites_um"]:
   xx,yy=a[i];assert not(x<xx+cw and xx<x+w and y<yy+ch and yy<y+h),("PHY overlap",i,xx,yy)
  for e in t["internal_stations"]:
   for xx,yy in e["regs_um"]:
    for a in s["bit_sites_um"]:
     px,py=a[i]
     if px-1.5<xx<px+cw+1.5 and py-0.3<yy<py+ch+0.3:near.append((e["conn"],i,xx,yy,px,py))
 assert maxhop<=405,maxhop
 edge=raw["die"]["outline_um"][1]-(oy+y+h);assert edge<=200,edge
 assert t["outline_um"]==old["partition_types"]["kv3_sys_c"]["outline_um"]
 assert {k:v for k,v in t.items() if k in ["buses","clock_root","reset_root"]}=={k:v for k,v in old["partition_types"]["kv3_sys_c"].items() if k in ["buses","clock_root","reset_root"]}
 return {"shift_um":shift,"edge_um":edge,"max_ft_hop_um":maxhop,"ft_fwd_near":near,"new_phy":m["origin_um"],"added_cycles_from_sysc2":0,"taps":len(S.tap_grid(P,"kv3_sys_c"))}
if __name__=="__main__":
 p,ip,out,ioo,rep=map(Path,sys.argv[1:]);r=json.loads(p.read_text());io=json.loads(ip.read_text());report=apply(r,io);out.write_text(json.dumps(r,indent=1)+"\n");ioo.write_text(json.dumps(io,indent=1)+"\n");rep.write_text(json.dumps(report,indent=1)+"\n");print(json.dumps(report))
