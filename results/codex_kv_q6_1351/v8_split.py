"""Q6 v8: divide FT26's physical station sites over two channels, same RTL/stages."""
import sys,json,copy
from pathlib import Path
import numpy as np
R=Path(sys.argv[1]);sys.path.insert(0,str(R/'tools/die_plan'));sys.path.insert(0,str(R))
import schema as S,ft_corridor as F
raw=json.load(open(R/'pd/hm_r26q6_hgi128.json'));P=S.Plan(raw);tn='kv3_hgi_v8';orig=F.place_slot

def split(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kw):
 if slot['name']!='ft26':return orig(slot,a,b,fin,fout,w,h,boxes,alloc,budget,**kw)
 chunks=[(0,528,600.),(528,len(a),920.)];sol=[];ledgers=[]
 for lo,hi,jog in chunks:
  ss=copy.deepcopy(slot);ss['width']=hi-lo-1
  local=dict(kw,jog=jog,jog_lane=(hi-lo)*.08)
  sites,cents,path,led=orig(ss,a[lo:hi],b[lo:hi],fin,fout,w,h,boxes,alloc,budget,**local);sol.append(sites);ledgers.append(led)
 sites=[np.concatenate([q[j] for q in sol]) for j in range(slot['stations']-1)];chain=[a]+sites+[b];hops=[float(np.abs(y-x).sum(axis=1).max()) for x,y in zip(chain,chain[1:])];assert max(hops)<=403,(slot['name'],hops)
 ledger=dict(stations=slot['stations'],len_um=max(z['len_um'] for z in ledgers),hops_um=hops,max_alloc_disp_um=max(z['max_alloc_disp_um'] for z in ledgers),proj_mean_um=[],physical_bit_groups=[dict(lo=lo,hi=hi-1,jog_um=jog) for lo,hi,jog in chunks],cycles_added=0)
 return sites,[p.mean(axis=0) for p in sites],[q.mean(axis=0) for q in chain],ledger
F.place_slot=split;F.LANE_PACK='bin';F.LANE_UM_PER_BIT=.08
led=F._place_type(P,tn,405.,1.,{},{});(R/'pd/hm_r26q6_v8_split.json').write_text(json.dumps(raw,indent=1)+'\n');(R/'v8_split_ledger.json').write_text(json.dumps(led,indent=1)+'\n');print('V8_SPLIT_DONE',len(led))
