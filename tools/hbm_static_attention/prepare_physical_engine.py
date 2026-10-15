#!/usr/bin/env python3
"""Full instantiated 16-head production geometry, independent chunk8 golden."""
import argparse,sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(Path(__file__).resolve().parent))
import rtl_hdc_v41x_attn_campaign as C
from physical_calendar import schedule
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261015)
jobs=[C.random_job(rng,16,512,T,min(128,T),'coarse') for T in (128,640)]
counts,stats=C.write_jobs(a.out,jobs,16,512,32)
for j,T in enumerate((128,640)):
 for mode in ('qk','pv'):
  s=schedule(T=T,mode=mode);words=s['words']+[0]*(512-len(s['words']))
  (a.out/f'{mode}{T}.hex').write_text(''.join(f'{w:02x}\n' for w in words))
(a.out/'vectors.json').write_text(json.dumps(dict(counts=counts,stats=stats,H=16,D=512,TD=32,NL=2,T=[128,640],seed=20261015,golden='hdc_golden_v41 chunk8; exact FP8/FP4 stored codes and golden rounding',sha256={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.glob('*.hex')}),indent=2)+'\n')
print('PREPARED full16heads D512 T128/640 actual-golden vectors')
