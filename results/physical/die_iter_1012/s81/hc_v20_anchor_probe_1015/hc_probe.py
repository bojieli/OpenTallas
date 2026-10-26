#!/usr/bin/env python3
"""Build-only probe: canonical generator construction with a chosen contract; report HC slab boxes + legality."""
import argparse,json,sys,traceback
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools'));import dsrom_s81_fulldie as G
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('args',nargs=argparse.REMAINDER);a=ap.parse_args()
p=argparse.ArgumentParser();p.add_argument('mode');p.add_argument('--k',type=int,default=16);G.die_options(p);opts=p.parse_args(a.args);G.apply_options(opts)
rec={'contract':opts.contract,'HC_S_GROW_DOWN':G.HC_S_GROW_DOWN,'HC_V2_UM':G.HC_V2_UM,'HC_T_UM':G.HC_T_UM}
stop={}
old=G.buses_r8
def cap(m):
    stop['m']=m; raise SystemExit('PROBE_STOP_BEFORE_BUSES')
G.buses_r8=cap
try:
    G.build()
except SystemExit as e:
    rec['stopped']=str(e)
except Exception as e:
    rec['error']=repr(e);rec['traceback']=traceback.format_exc()
m=stop.get('m')
if m:
    I=m['insts']
    hc=[i for i in I if i.master in ('dsfd_sp_hc_c','dsfd_sp_hc_t') or i.name in ('sp_hc_s','sp_hc_t')]
    rec['hc']=[[i.name,i.master,i.x,i.y,i.w,i.h] for i in hc]
    ov=[]
    for h in hc:
        for i in I:
            if i is h: continue
            if i.x<h.x+h.w-1e-6 and i.x+i.w>h.x+1e-6 and i.y<h.y+h.h-1e-6 and i.y+i.h>h.y+1e-6:
                ov.append([h.name,i.name,i.master,i.x,i.y,i.w,i.h])
    rec['hc_overlaps']=ov
    rec['regions']=[r for r in m['regions'] if r['kind']!='field']
    try: rec['legality']=G.legality(m)
    except Exception as e: rec['legality_error']=repr(e)
    rec['n_insts']=len(I)
Path(a.out).write_text(json.dumps(rec,indent=1,default=str))
print(json.dumps({k:v for k,v in rec.items() if k not in('traceback',)},default=str)[:3000])
