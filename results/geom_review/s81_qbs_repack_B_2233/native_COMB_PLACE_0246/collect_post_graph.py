from pathlib import Path
import sys,json
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
sys.path.insert(0,'/home/ubuntu/coord/tmp/codex-hist-anchor-2100');from exact_cones import endpoints,physical_port_map
P=Path(sys.argv[1]);D=G.Design(P/'actual_geom.tsv');C=json.load(open(P/'actual_macro_ports.json'));M=physical_port_map(C);r=G.r2r_metrics(D);mx=0;fm=0;bad=[];fb=[]
xy=lambda cid:tuple(round(v*1000)for v in G.ctr(D.cells[cid]))
for cid,c in D.cells.items():
 if c[0]!='S':continue
 p=xy(cid)
 for fwd in(True,False):
  ss,ms=endpoints(D,cid,fwd)
  for sc in ss:
   q=xy(sc);d=sum(abs(a-b)for a,b in zip(p,q));fm=max(fm,d)
   if d>405000:fb.append([c[6],D.cells[sc][6],d])
  for k in ms:
   for x,y,n in M[k]:
    q=(round(x*1000),round(y*1000));d=sum(abs(a-b)for a,b in zip(p,q));mx=max(mx,d)
    if d>405000:bad.append([c[6],n,d])
J=dict(scope='ACTUAL saved comb PLACE128019-net graph; no CTS/GRT',FF=sum(c[0]=='S'for c in D.cells.values()),r2r=r,FF_max_DBU=fm,FF_pairs_gt405000=len(fb),FF_bad=fb[:20],macro_max_DBU=mx,macro_gt405000=len(bad),macro_bad=bad[:20],DBU_per_um=1000)
(P/'actual_endpoint_census.json').write_text(json.dumps(J,indent=2)+'\n');print(J)
J=G.demand_metrics(D,max_layer='M5',min_layer='M2');(P/'actual_placed_demand_M2M5.json').write_text(json.dumps(J,indent=2)+'\n');print('DEMAND',J)
