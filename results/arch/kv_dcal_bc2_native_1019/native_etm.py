#!/usr/bin/env python3
"""Read frozen routed exports; no STA rerun or modification of old run trees."""
import sys,json,pathlib,hashlib
r=pathlib.Path(__file__).resolve().parents[3];sys.path.insert(0,str(r/'tools/hier_contract'));import pinreg_audit as p
v=r/'physical/ref_tile/qkd_d2d_cal_seq_pin_bc/views/qkd_d2d_cal_seq_pin_bc';ins=json.loads((v/'insertion.json').read_text());out={}
for c in ['tt','ff','ss']:
 f=v/f'qkd_d2d_cal_seq_pin_bc_{c}.lib';l=p.parse_lib(f);refs=p.clock_refs(l,ins,c);m=p.pin_metrics(l,refs)
 launch=sorted([(x['out'],n) for n,x in m.items() if x['dir']=='output' and x['out'] is not None],reverse=True);capture=sorted([(x['inp'],n) for n,x in m.items() if x['dir']=='input' and x['inp'] is not None],reverse=True)
 out[c]=dict(clock_refs=refs,launch_max=launch[:1],capture_max=capture[:1],launch_over220=[x for x in launch if x[0]>220],capture_over190=[x for x in capture if x[0]>190],combinational_pins={n:x['comb'] for n,x in m.items() if x['comb']},metrics=m,lib_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
pathlib.Path(__file__).with_name('native_etm.json').write_text(json.dumps(out,indent=2)+'\n')
