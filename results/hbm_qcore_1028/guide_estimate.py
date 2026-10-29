"""Estimate source-group locality before a second same-outline placement."""
import sys,json
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/hbm-cores-kits-5/aptools')
from geom_rules import Design,ctr,demand_metrics,r2r_metrics
root=Path('/srv/opentallas-scratch2/claude/codex-qcore-1028')
d=Design(str(root/'geom_place/geom.tsv'))
guides={1:[8.64,82.08,108.,125.28],2:[116.64,82.08,216.,125.28]}
stats={}
for g,box in guides.items():
 ids=[i for i,c in d.cells.items() if c[6].replace('\\','').startswith(f'u_fcore.g_sec[{g}].u_s/')]
 assert len(ids)>12000
 xs=[ctr(d.cells[i])[0] for i in ids];ys=[ctr(d.cells[i])[1] for i in ids]
 xmin,xmax,ymin,ymax=min(xs),max(xs),min(ys),max(ys)
 area=sum((d.cells[i][4]-d.cells[i][2])*(d.cells[i][5]-d.cells[i][3])for i in ids)
 for i in ids:
  k,m,x0,y0,x1,y1,n=d.cells[i];x,y=(x0+x1)/2,(y0+y1)/2
  nx=box[0]+2+(x-xmin)/(xmax-xmin)*(box[2]-box[0]-4)
  ny=box[1]+2+(y-ymin)/(ymax-ymin)*(box[3]-box[1]-4)
  d.cells[i]=(k,m,nx-(x1-x0)/2,ny-(y1-y0)/2,nx+(x1-x0)/2,ny+(y1-y0)/2,n)
 stats[g]={'cells':len(ids),'area_um2':area,'guide':box}
out={'status':'AFFINE_GROUP_MODEL_NOT_LEGAL_PLACEMENT','groups':stats,
 'reach':r2r_metrics(d),'demand':demand_metrics(d),'any_guided_to_any_core_point_bound_um':332.64,
 'limits':'All group data/control/logic included. Affine distribution models locality only; placement/GRT decides.'}
(root/'guide_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
