#!/usr/bin/env python3
"""Fail closed until the live protected half has real bench-gated views."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

SOURCE='3b90d75fa113add3ab6b8f1d21e58a18e6b1b206'
p=argparse.ArgumentParser();p.add_argument('--job-state',type=Path,required=True)
p.add_argument('--half-view',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();job=json.loads(a.job_state.read_text())
if job.get('status')!='CLOSED':raise SystemExit('PENDING_HALF_CLOSURE '+str(job.get('status')))
if job.get('commit_full')!=SOURCE:raise SystemExit('half source changed; reprice/re-gate the new source explicitly')
m=job.get('metrics',{})
for key in ['ss_ps','ff_ps']:
 if not isinstance(m.get(key),(int,float)) or not math.isfinite(m[key]) or m[key]<0:
  raise SystemExit('invalid half timing '+key)
if m.get('drc')!=0:raise SystemExit('half not DRC0')
expected={('bench_'+b['name']) for b in job['spec']['stages']['bench']}
if not expected or any(not job.get('benches',{}).get(k,{}).get('ok') for k in expected):
 raise SystemExit('half exact/negative gates incomplete')
lef=a.half_view/'ot_hcoll_port.lef';text=lef.read_text()
size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)\s*;',text)
if not size:raise SystemExit('half LEF missing size')
w,h=map(float,size.groups())
if not(w>0 and h>0):raise SystemExit('invalid dimensions')
names=set(re.findall(r'^\s*PIN\s+(\S+)',text,re.M))
for pin in ['clk','ckf','rst_n','qp_push','qr_push','sw_cr_ret','ph_tx_v','ph_rx_v','rb_v','rb_cr','stall','fault','ecc_ce']:
 if pin not in names:raise SystemExit('missing half ABI pin '+pin)
for bus,width in [('qp_din',545),('qr_din',545),('ph_rx_flit',545),('ph_tx_flit',545),('rb_d',545),('rx_ecc_drop',2)]:
 if any(f'{bus}[{b}]' not in names for b in range(width)):
  raise SystemExit('missing full-shape half bus '+bus)
files=[lef]+[a.half_view/f'ot_hcoll_port_{corner}.lib' for corner in ('tt','ff','ss')]
hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
result=dict(source=SOURCE,half_job=job['name'],half_status=job['status'],half_dimensions_um=[w,h],
 artifacts=hashes,half_instances=[dict(name='g_h[0].u_port',origin_um=[0,0]),
 dict(name='g_h[1].u_port',origin_um=[w+24,0])],composite_dimensions_um=[2*w+24,h],
 source_gates=sorted(expected),signal_seam_crossings=0,partition_added_cycles=0,
 composite_physical_closed=False,adopted=False,
 next_gate='paired-wrapper wiring gate plus composite/die clock-binding and placement lint')
a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
