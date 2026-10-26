#!/usr/bin/env python3
"""Full H16 instantiated arithmetic fixture with canonical logical H1 data."""
import argparse,sys,json,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools'))
import rtl_hdc_v41x_attn_campaign as A
sys.path.insert(0,str(Path(__file__).resolve().parent));from physical_calendar import schedule
p=argparse.ArgumentParser();p.add_argument('--eb-dir',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(20261015);jobs=[A.random_job(rng,16,512,T,min(128,T),'coarse') for T in (128,640)]
for j,T in zip(jobs,(128,640)):
 eb=np.asarray([int(x,16) for x in (a.eb_dir/f'EB{T}.hex').read_text().split()],dtype=np.uint32).reshape(16,T)
 j.q[1:,:]=np.float32(0);j.p[:,:]=np.float32(0);j.p[0,:]=eb.view(np.float32)[0,:]
counts,stats=A.write_jobs(a.out,jobs,16,512,32)
for T in (128,640):
 for mode in ("qk","pv"):
  words=schedule(T,mode)["words"];(a.out/f"{mode}{T}.hex").write_text("".join(f"{w:02x}\n" for w in words+[0]*(512-len(words))))
record={'scope':'H1 logical golden fixture for unchanged fullyinstantiated H16 arithmetic binary. Inactive slots explicitzero; actualprefetch SRAM initialization has separate proof. Notnative source/producer/calendar/physical qualification.','active_hardware_head':0,'hardware_H':16,'D':512,'TD':32,'NL':2,'T':[128,640],'counts':counts,'stats':stats,'eb_input_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.eb_dir.glob('EB*.hex')},'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.glob('*.hex')}}
(a.out/'fixture.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS prepared H1 logical data on fullH16 unchanged arithmetic shapes')
