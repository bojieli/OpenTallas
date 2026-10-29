"""One principle-level source-locality estimate on original macros, <=M7.

Section3 dominates the measured original/M7 hot corner. This is only a
connectivity/area estimate; it does not change a kit or route anything.
"""
import sys,json
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch2/claude/hbm-cores-kits-5/aptools')
from geom_rules import Design,ctr,demand_metrics,r2r_metrics
d=Design('/srv/opentallas-scratch2/claude/hbm-cores-kits-5/geom/ot_hbm_su_static_qcore_r13/geom.tsv')
box=[116.64,120.96,220.32,181.44]
ids=[i for i,c in d.cells.items()if c[6].replace('\\','').startswith('u_fcore.g_sec[3].u_s/')]
assert len(ids)>12000
xs=[ctr(d.cells[i])[0]for i in ids];ys=[ctr(d.cells[i])[1]for i in ids]
xmin,xmax,ymin,ymax=min(xs),max(xs),min(ys),max(ys)
area=sum((d.cells[i][4]-d.cells[i][2])*(d.cells[i][5]-d.cells[i][3])for i in ids)
for i in ids:
 k,m,x0,y0,x1,y1,n=d.cells[i];x,y=(x0+x1)/2,(y0+y1)/2
 nx=box[0]+2+(x-xmin)/(xmax-xmin)*(box[2]-box[0]-4)
 ny=box[1]+2+(y-ymin)/(ymax-ymin)*(box[3]-box[1]-4)
 d.cells[i]=(k,m,nx-(x1-x0)/2,ny-(y1-y0)/2,nx+(x1-x0)/2,ny+(y1-y0)/2,n)
out={'status':'AFFINE_GROUP_ESTIMATE_NOT_LEGAL_PLACEMENT','guide_section':3,'guide_um':box,
 'cells':len(ids),'cell_area_um2':area,'guide_fill':area/((box[2]-box[0])*(box[3]-box[1])),
 'demand':demand_metrics(d,max_layer='M7'),'reach':r2r_metrics(d),
 'all_guided_to_any_original_core_point_bound_um':393.12,
 'limits':'Original macros/pins/islands. M7 permission and typed legal-placement/GRT proof still required. Affine model may compress local clusters.'}
Path('/srv/opentallas-scratch2/claude/codex-qcore-1028/m7_local_estimate.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
