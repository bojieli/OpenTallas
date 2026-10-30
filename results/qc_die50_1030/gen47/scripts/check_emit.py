"""DIE-QC-50/gen47 (a) emission check: clock cells unchanged, one tap port per stage, actual stage-to-stage START reach."""
import json,sys,re,collections
sys.path.insert(0,sys.argv[1]+"/tools/die_plan")
import start_stage_emit as E
K,EM,PL,OUT=sys.argv[2:6]
old=E.ctree_cells(open(K+"/ctree.v").read(),open(K+"/ctree.tcl").read())
new=E.ctree_cells(open(EM+"/ctree.v").read(),open(EM+"/ctree.tcl").read())
same=old[0]==new[0] and old[1]==new[1]
doc=json.load(open(EM+"/start_stages.json"));st=doc["stages"]
v=open(EM+"/ctree.v").read()
ports=set(re.findall(r"\b(t_st_\w+__clk)\b",v))
miss=[s["clock_port"] for s in st if s["clock_port"] not in ports]
byreg={s["region"]:s for s in st}
plan=json.load(open(PL))
sp=json.load(open(sys.argv[6]))["start_ports"]
proof=json.load(open(sys.argv[7]));taps={t["port"]:t for t in proof["taps"]}
hops=[];bad=[]
def xy(region,tap):
  if region in byreg: r=byreg[region]["rect_um"];return (r[0],r[1])
  return tuple(taps[tap]["xy_um"])
for pid,c in sp.items():
  a=xy(c["src"],c.get("launch"));b=xy(c["dst"],c.get("capture"))
  h=abs(a[0]-b[0])+abs(a[1]-b[1]);hops.append(h)
  if h>405: bad.append((pid,round(h,1)))
stub=[s.get("clock_pin_xy_um") for s in st]
fl=collections.Counter(s["flops"] for s in st)
r=dict(clock_cells_identical=same,clock_cells=len(new[0]),stages=len(st),stage_ports_missing=len(miss),start_ports=len(sp),
 max_start_hop_um=round(max(hops),3),start_hops_over_405=len(bad),bad=bad[:10],flops=sum(s["flops"] for s in st),flop_hist=dict(fl),
 roots=[s["id"] for s in st if s["root"]],from_A=sum(s["clock_from"]=="A" for s in st),counts=doc["counts"])
json.dump(r,open(OUT,"w"),indent=1);print(json.dumps(r))
