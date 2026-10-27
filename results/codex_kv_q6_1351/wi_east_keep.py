"""Route large Wi bundles through the free E corridor; retain two legal tiny chains.
Counts/cycles fixed. Existing ft30/31 FF footprints are reserved before allocation.
"""
import json,sys,copy
from pathlib import Path
import numpy as np
R=Path(sys.argv[1]);sys.path.insert(0,str(R/'tools/die_plan'));sys.path.insert(0,str(R))
import schema as S,ft_corridor as F
src=R/'pd/hm_r26q6_hgi128.json';raw=json.load(open(src));P=S.Plan(raw,src);tn='kv3_hub_Wi';ty=P.types[tn]
keep={s['name']:copy.deepcopy(s) for s in ty['ft_slots'] if s['name'] in ['ft30','ft31']};assert len(keep)==2
fixed=[]
for s in keep.values():
 w,h=s['bit_site_cell_um']
 for stage in s['bit_sites_um']:
  for x,y in stage:fixed.append((x,y,x+w,y+h))
allocator=F.RowAllocator
F.RowAllocator=lambda *a,**kw:allocator(*a,**dict(kw,blocked=list(kw.get('blocked',[]))+fixed))
place=F.place_slot

def kept(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kw):
 if slot['name'] not in keep:return place(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kw)
 s=keep[slot['name']];sites=[np.array(q)+np.array(s['bit_site_cell_um'])/2 for q in s['bit_sites_um']];chain=[a]+sites+[b];hops=[float(np.abs(y-x).sum(axis=1).max()) for x,y in zip(chain,chain[1:])];assert max(hops)<=405,(s['name'],hops)
 return sites,[p.mean(axis=0) for p in sites],[q.mean(axis=0) for q in chain],dict(stations=s['stations'],len_um=round(sum(hops),2),hops_um=hops,retained_legal_chain=True,max_alloc_disp_um=0,proj_mean_um=[])
F.place_slot=kept;F.LANE_UM_PER_BIT=.08;F.LANE_PACK='bin'
jogs={f'{tn}/ft5':1220.,f'{tn}/ft4':1160.,f'{tn}/ft6':640.}
ledger=F._place_type(P,tn,405.,1.,jogs,{})
for name,s in keep.items():
 q=next(q for q in ty['ft_slots'] if q['name']==name);assert q['stations']==s['stations'] and q['bit_sites_um']==s['bit_sites_um']
(R/'pd/hm_r26q6_wi_keep.json').write_text(json.dumps(raw,indent=1)+'\n');(R/'wi_keep_ledger.json').write_text(json.dumps(ledger,indent=1)+'\n');print('WI_DONE',len(ledger),len(fixed),'fixed tiny FF bodies')
