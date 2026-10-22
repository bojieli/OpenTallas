#!/usr/bin/env python3
"""Scoped source4 local transport/control target cut; no production epoch."""
import hashlib,json,subprocess,sys
from pathlib import Path
root=Path.cwd();out=root.parent/'run_r3';out.mkdir(exist_ok=False);images=out/'images';images.mkdir()
sys.path.insert(0,str(root/'tools/s81_dv'))
from layer_prog.pv_so_calendar import control_frames
from layer_prog.lower_svc import hdr
owner=0x92345;position=777;se=0x31;so=0x67
params=[sum((0x40000000^(p*1000+l))<<(32*l) for l in range(16)) for p in range(5)]
for name,lf in [('control',78),('control_early',77)]:
 f=control_frames(owner,position,se,so,lf,403,params)
 words=f['CFG']+f['PARAM']+f['LAUNCH'];assert len(words)==8
 (images/(name+'.hex')).write_text(''.join(f'{w:0128x}\n' for w in words))
expected=[hdr(9,5,owner&255,spec=1|(5<<1)|(so<<5),pos=position,user=(owner>>8)&1023)]+params
for h in range(16):
 expected.append(hdr(9,32,owner&255,spec=(5<<1)|(so<<5)|(1<<13)|((1<<h)<<14),pos=position,user=(owner>>8)&1023))
 for row in range(32):expected.append(sum((0x3f000000^(h<<17)^((16*row+l)*101))<<(32*l) for l in range(16)))
assert len(expected)==534
(images/'expected.hex').write_text(''.join(f'{w:0128x}\n' for w in expected))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
readset=json.loads((root/'READSET.json').read_text())
for p,d in readset['source_sha256'].items():assert sha(root/p)==d,('source drift',p)
rtl=[p for p in readset['source_sha256'] if p.endswith(('.sv','.v')) and not p.endswith('dsdv_svc_rs_pvso_entry.sv')]
rtl+=['tools/s81_dv/pv_local_target_2250/tb_local_target.sv']
book=json.loads((root/'relative_transport_book.json').read_text())
assert book['die_sha256']=='629c0209bb0f1247ce9b6738e34918427822a4bfd622947a6067f83d75c403a8'
assert book['local_pv_pin_availability_edges']==18 and book['local_pv_half_join_sampled_edges']==19
assert book['source_reset_total']==4 and not book['physical_epoch_qualified']
identity=dict(schema='opentallas.s81.local_target_cut.v1',run_id=readset['run_id'],source_readset=readset,readset_sha256=sha(root/'READSET.json'),die_relative_book_sha256=sha(root/'relative_transport_book.json'),
 reuse_source4_ring_receipt='3519f6369:results/rtl/s81_g9f_source_1021/source4/receipt.json',
 bench_sha256=sha(root/rtl[-1]),runner_sha256=sha(__file__),images={p.name:sha(p) for p in images.iterdir()},
 native_clock_domain='scoped_common_frequency_component_epoch',source_epoch_edge=0,target_epoch_edge=0,
 forwarding_delay_ps=dict(clock=115,data=115),attempt=3,
 physical_epoch_mapping=None,peer_flight_qualified=False,scope='Changed local ring -> exact program/join/ingress components. Synthetic component payloads reuse existing target fixture; no SM arithmetic/SOT/full-entry execution.')
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
cmd=['iverilog','-g2012','-s','tb_local_target','-o',str(out/'sim')]+rtl
(out/'argv.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'build.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit(r.returncode)
identity['binary_sha256']=sha(out/'sim');cases={}
for mut in (0,1):
 with (out/f'run{mut}.log').open('w') as f:r=subprocess.run(['vvp','-n',str(out/'sim'),f'+DIR={images}',f'+mut={mut}'],stdout=f,stderr=subprocess.STDOUT)
 text=(out/f'run{mut}.log').read_text();ok=r.returncode==0 and ('LOCAL_TARGET_PASS' if mut==0 else 'LOCAL_TARGET_CAUGHT') in text
 cases[str(mut)]=dict(expected_outcome_met=ok,exit=r.returncode,log_sha256=sha(out/f'run{mut}.log'))
 print(mut,ok,text[-1200:],flush=True)
 if not ok:break
status='PASS' if len(cases)==2 and all(c['expected_outcome_met'] for c in cases.values()) else 'FAIL'
(out/'identity.json').write_text(json.dumps(identity,indent=2)+'\n')
(out/'result.json').write_text(json.dumps(dict(status=status,identity=identity,cases=cases,
 production_enabled=False,calendar_qualified=False,physical_epoch_mapping=None,peer_flight_qualified=False),indent=2)+'\n')
raise SystemExit(0 if status=='PASS' else 1)
