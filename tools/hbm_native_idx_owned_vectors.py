#!/usr/bin/env python3
"""Independent canonical numerical inputs for full native2048-leaf parent arithmetic."""
from pathlib import Path
import argparse,json,hashlib
import numpy as np
import rtl_w11_idx_array as A
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
A.IW=20
r=np.random.default_rng(20261014)
tokens=A.random_tokens(r,181)+[A.normal_token(r,10944,refuse=7,cand_block=8,keep_p=.7,name='native.full10944'),A.normal_token(r,4100,refuse=3,cand_block=8,keep_p=.7,name='native.partial4100')]
jobs=[(t,A.reader_beats(len(t['keep']))) for t in tokens]
nt,ns=A.write_mems(a.out,jobs,4)
x={'scope':'Full NS16/NK4 arithmetic with2048 realhead-key leaves; canonical NumPy golden. Functional clock adapter, not physical/timing/real HBM source.','ntok':nt,'nslot':ns,'classes':[t['cls'] for t in tokens],'source_sha256':{f:hashlib.sha256(Path('tools',f).read_bytes()).hexdigest() for f in ['rtl_w11_idx_array.py','rtl_hdc_v41x_idx_campaign.py','hdc_golden_v41.py']},'vector_sha256':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in a.out.glob('*.mem')}}
(a.out/'metadata.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps({'ntok':nt,'nslot':ns}))
