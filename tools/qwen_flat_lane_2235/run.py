#!/usr/bin/env python3
"""One selected current flat lane: source-frozen arithmetic and TLS causal proof."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np

root=Path.cwd();out=root.parent/'run_r1';out.mkdir(exist_ok=False)
sys.path.insert(0,str(root/'tools'));import hdc_golden as G
model=json.loads((root/'MODEL.json').read_text())
expected_params=dict(WR=16,AW=24,NW=18,LANE=0,KV_FP8=1,ML=1,TLS=1,QLA=3,QLM=3,SFH=0)
assert model['params']==expected_params
pins=model['source_files']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for p,s in pins.items():assert sha(root/p)==s,(p,'selected source drift')
rtl=[p for p in pins if not p.endswith('_bb.v')]
mem='physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v'
rtl += [mem,'tools/qwen_flat_lane_2235/tb_flat_lane.sv']
images=out/'images';images.mkdir()
a=np.zeros(160,dtype=np.float32);b=np.zeros_like(a);c=np.zeros_like(a);gold=np.zeros_like(a)
for cls in range(5):
 ix=slice(32*cls,32*cls+16);n=np.arange(16,dtype=np.float32)
 a[ix]=(n+2)/8 if cls in (2,3) else (n-7)/8
 b[ix]=(n+3)/8;c[ix]=(19-n)/16
 y=a[ix] if cls==0 else G.exp(a[ix]) if cls==1 else G.reciprocal(a[ix]) if cls==2 else G.rsqrt(a[ix]) if cls==3 else G.reciprocal(G.add(G.exp(a[ix]),G.F(1)))
 gold[ix]=G.mul(G.mul(y,c[ix]),b[ix])
for name,v in [('a',a),('b',b),('c',c),('expected',gold)]:
 (images/(name+'.hex')).write_text(''.join(f'{int(x):08x}\n' for x in G.bits(v)))
identity=dict(schema='opentallas.qwen.flat_lane_functional.v1',selected_source_commit='1f7a4aedb',params=expected_params,
 physical_source_sha256=pins,simulation_source_sha256={p:sha(root/p) for p in rtl},
 reference_sha256=sha(root/'tools/hdc_golden.py'),runner_sha256=sha(__file__),
 image_sha256={p.name:sha(p) for p in images.iterdir()},clock='single actual native lane clock',
 memory_model='ML1 two-sampled-edge response; actual128x256 TLS macro',
 scope='Single lane0 source component, five SFU classes and dirty-history reset; no selected die/native/physical closure.')
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
results={}
for mut in (0,1):
 obj=out/f'obj_m{mut}';v=str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
 cmd=[v,'--binary','--timing','-O1','-Wno-fatal','-Wno-WIDTH','-Wno-TIMESCALEMOD','--top-module','tb_flat_lane','-Mdir',str(obj),'-j','2','-CFLAGS','-O1']
 if mut:cmd+=['-DOT_TLS_MUT']
 cmd += rtl
 (out/f'argv_m{mut}.json').write_text(json.dumps(cmd,indent=2)+'\n')
 with (out/f'build_m{mut}.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise SystemExit(r.returncode)
 guard_path=Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
 sys.path.insert(0,str(guard_path));import verilator_nba_guard as NG
 guard=NG.scan(str(obj));(out/f'nba_guard_m{mut}.json').write_text(json.dumps(guard,indent=2)+'\n')
 if guard['findings']:raise SystemExit(86)
 with (out/f'run_m{mut}.log').open('w') as f:r=subprocess.run([str(obj/'Vtb_flat_lane'),f'+DIR={images}'],stdout=f,stderr=subprocess.STDOUT)
 text=(out/f'run_m{mut}.log').read_text()
 passed=(r.returncode==0 and 'FLAT_LANE_PASS values=96' in text) if not mut else (r.returncode!=0 and 'OUTPUT_MISMATCH' in text and 'FLAT_LANE_FAIL' in text)
 results[str(mut)]=dict(expected_outcome_met=passed,exit=r.returncode,binary_sha256=sha(obj/'Vtb_flat_lane'),log_sha256=sha(out/f'run_m{mut}.log'))
 print('mutation',mut,'expected_outcome_met',passed,'exit',r.returncode,text[-900:],flush=True)
 if not passed:break
assert all(sha(root/p)==s for p,s in pins.items())
result=dict(status='PASS' if len(results)==2 and all(r['expected_outcome_met'] for r in results.values()) else 'FAIL',
 identity=identity,cases=results,native_qualified=False,physical_parent_bound=False,
 expected_retire_deltas=dict(NONE=19,EXP=68,RECIP=47,RSQRT=56,SIGM=99),
 expected_vm_write_delta='retire +1; source sampled issue edge, post-edge output observation',
 calendar_projection=None)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
raise SystemExit(0 if result['status']=='PASS' else 1)
