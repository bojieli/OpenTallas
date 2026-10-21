"""Model-only check that idx3 does not silently change the qualified field inventory."""
import sys,json,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent
sys.path.insert(0,str(D/'root/tools/s81_dv'))
import dv_plan as P
P.LAYOUT='p4';P.FRAME_W=1436.832;P.FRAME_PITCH=P.FRAME_W+8.7
P.SCOL_W=1000.;P.SLICE_W=950.;P.SLICE_H=4600.;P.UNIT_W=P.UNIT_WE=680.
P.LANE_DX=30.;P.PITCH=2*P.FRAME_PITCH+P.SCOL_W
P.COL_EXE[3]=120.;P.COL_EXW[4]=120.;P.DIE_W=600+8*P.PITCH+240
P.P4L=P.P4K=P.P4J=P.P4I=P.P4F=P.P4G=P.P4H=True
P.NO_MIX4=True;P.RET=70;P.MU=1;P.PATHFIX=True;P.TIER_W=276;P.LANES=4
P.BAND=1786.4;P.CTRL_VIEW_W=388.8;P.CTRL_H=324.
P.P4H_DROP=((2,'R'),(3,'L'),(3,'R'),(4,'L'),(4,'R'),(5,'L'))
P.SVC_FACE['up']=(16,P.SVC_FACE['up'][1],P.SVC_FACE['up'][2])
rows={}
for mode in (0,3):
 P.IDXRD=mode;p,f=P.build();frames=[b['name'] for b in p.blocks if b['kind']=='frame']
 rows[str(mode)]={'n_frames':len(frames),'frames':frames,'blocks':len(p.blocks),'links':len(p.links),'idx':f.get('idxrd')}
assert rows['0']['n_frames']==122,rows['0']['n_frames']
removed=sorted(set(rows['0']['frames'])-set(rows['3']['frames']))
out={'schema':'s81.mu7.idx3_field_inventory_model.v1','source_dv_plan_sha256':hashlib.sha256(Path(P.__file__).read_bytes()).hexdigest(),'variants':rows,'frames_removed':removed,'qualified_campaign_inventory':122,'idx3_capacity_compatible':rows['3']['n_frames']==122,'scope':'model only; no bind/route; no existing job modified','required_resolution':'repack idx3 while preserving122 frames, or recompile capacity at actual reduced inventory and allow more physical stages'}
(D/'idx3_frame_inventory.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
