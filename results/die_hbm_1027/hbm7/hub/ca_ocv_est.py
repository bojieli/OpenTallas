#!/usr/bin/env python3
"""DIE-HBM-7 ESTIMATE: unshared clock + OCV-widened CA window per crossing of a hub slice map (hub_locality.py out),
with the APPROVED clk_aocv table (0.21 %/mm, tools/die_plan/clk_aocv_table_g021.json) + droop 5.1 % when the two
ends are in different droop regions. Branch model (UNCHECKED): repeated clock wire 100.2 ps/stage (table mu_stage TT)
at one stage per 450 um -> 0.2227 ns/mm, plus core latency 250 TT on each side (class B). Two LCA cases:
 'mid' = a plan tree node at the crossing midpoint (clock follows data, 12.13), 'root' = die clock root (today's form).
Window test: ocv_setup + ocv_hold + 60 (setup U) + 25 (hold U) must fit in 833 ps for a count-aligned crossing.
Usage: ca_ocv_est.py <repo tools/die_plan> loc.json out.json"""
import sys,json,math,collections
sys.path.insert(0,sys.argv[1]);import clk_aocv as CA
T=CA.load(sys.argv[1]+"/clk_aocv_table_g021.json");L=json.load(open(sys.argv[2]))
PS_PER_UM=100.239/450.0;CORE=250.0;PER=833.0
def branch(corner,len_um):
  A=T["classes"]["A"][corner];B=T["classes"]["B"][corner];fc=A["cell_share"]
  arr=len_um*PS_PER_UM;nB=max(1,round(CORE/B["mu_stage_ps"]))
  return dict(cell_ps=fc*arr+B["cell_share"]*CORE,net_ps=(1-fc)*arr+(1-B["cell_share"])*CORE,stages={"A":max(0,round(len_um/450)),"B":nB})
out={}
for tn,r in L["types"].items():
  root=r["root_xy"];res={}
  for case in ("mid","root"):
    rows=[];bad=0;badbits=0;mx=0;hist=collections.Counter()
    for x in r["crossings"]:
      pa,pb=x["pa"],x["pb"];d=x["eff_um"]
      if case=="mid": la=lb=d/2;dd=d
      else:
        la=abs(pa[0]-root[0])+abs(pa[1]-root[1])+ (x["eff_um"]-x["dist_um"])/2;lb=abs(pb[0]-root[0])+abs(pb[1]-root[1])+(x["eff_um"]-x["dist_um"])/2
        dd=max(d,math.dist(pa,root)+math.dist(pb,root))
      same=d<1500  # one regional mesh/droop region spans adjacent slices (UNCHECKED)
      su=CA.branch_pessimism(T,"TT",branch("TT",la),branch("TT",lb),dd/1000.0 if False else dd,same,"setup")
      ho=CA.branch_pessimism(T,"FF",branch("FF",la),branch("FF",lb),dd,same,"hold")
      su=su if isinstance(su,(int,float)) else su.get("total_ps",su.get("ps",0))
      ho=ho if isinstance(ho,(int,float)) else ho.get("total_ps",ho.get("ps",0))
      tot=su+ho+60+25;mx=max(mx,tot);hist[int(tot//100)*100]+=x["bits"]
      unshared=(la+lb)*PS_PER_UM+2*CORE
      if tot>PER: bad+=1;badbits+=x["bits"]
      rows.append(dict(a=x["a"],b=x["b"],bits=x["bits"],unshared_ps=round(unshared),ocv_setup=round(su,1),ocv_hold=round(ho,1),window_used_ps=round(tot)))
    rows.sort(key=lambda z:-z["window_used_ps"])
    res[case]=dict(crossings=len(rows),fail_window=bad,fail_bits=round(badbits),max_window_used_ps=round(mx),
                   max_unshared_ps=max(z["unshared_ps"] for z in rows),hist_bits_by_window_ps=dict(sorted(hist.items())),worst=rows[:6])
  out[tn]=res;print(tn,json.dumps({c:{k:v for k,v in res[c].items() if k!="worst"} for c in res}));print("  worst root",res["root"]["worst"][:3]);print("  worst mid",res["mid"]["worst"][:3])
json.dump(out,open(sys.argv[3],"w"),indent=1)
