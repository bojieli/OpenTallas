#!/usr/bin/env python3
"""Cold-state theorem for the ONLY two replicated ORDER register originals.

The actual retained source connects each pair to the same literal D and CLK
nets. Independent initial QNs therefore converge on the first real clock edge,
for arbitrary shared D streams, independent of the entire SRAM/ASR state.
No async2sync transform or memory abstraction is used by this proof.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

sp=importlib.util.spec_from_file_location('tl','textbook_lint.py')
m=importlib.util.module_from_spec(sp);sys.modules['tl']=m;sp.loader.exec_module(m)
source=Path('qkd_hr_core_order_n32.sv').read_text()
record=json.loads(Path('qkd_hr_core_order_n32.json').read_text())
assert hashlib.sha256(source.encode()).hexdigest()==record['generated_sha256']
assert not re.search(r'\binitial\b|\binit\s*=',source),'selected source initializes state'
# The structural parser expects the module before any Verilog directive.
text=re.sub(r'^`timescale[^\n]*\n','',source,flags=re.M)
g,_=m.flatten(m.parse_verilog(text),record['top']);a=m.build(g,None)
byname={name:ci for ci,(_,name,_) in enumerate(g.cells)}
copied=[row for row in record['copied_cells'] if row['kind']=='ff']
assert len(copied)==2
lines=['module shared_d_proof(input wire ck,input wire d0,input wire d1,output wire equal);']
checks=[];pairs=[]
for i,row in enumerate(copied):
    assert row['copies']==2
    cells=[g.cells[byname[f'u{row["cell"]}_c{k}.u_cell']] for k in range(2)]
    assert cells[0][0]==cells[1][0]=='DFFHQNx1_ASAP7_75t_R'
    p0,p1=cells[0][2],cells[1][2]
    assert set(p0)==set(p1)=={'D','CLK','QN'}
    assert p0['D']==p1['D'] and p0['CLK']==p1['CLK']==[g.ports['ck_core'][1]]
    assert p0['QN']!=p1['QN']
    for k in range(2):
        lines+= [f'wire q{i}_{k};',f'DFFHQNx1_ASAP7_75t_R ff{i}_{k}(.CLK(ck),.D(d{i}),.QN(q{i}_{k}));']
    checks.append(f'(q{i}_0==q{i}_1)')
    pairs.append(dict(original=row['original'],instances=[c[1] for c in cells],
                      type=cells[0][0],same_literal_D=g.net_name[p0['D'][0]],clock='ck_core'))
lines+=['assign equal='+' & '.join(checks)+';','endmodule']
Path('shared_d_proof.v').write_text('\n'.join(lines)+'\n')
cmd=['read_verilog canonical_DFF_normalized.v','read_verilog shared_d_proof.v',
     'hierarchy -check -top shared_d_proof','flatten','proc','opt_expr','opt_clean',
     'write_json shared_d_pre.json','clk2fflogic','opt_clean','write_json shared_d_post.json']
sat='sat -seq 8 -prove equal 1 -prove-skip 1 -verify'
for t in range(1,9):sat+=f' -set-at {t} ck {(t+1)%2}'
cmd.append(sat);Path('shared_d_proof.ys').write_text('\n'.join(cmd)+'\n')
with Path('shared_d_proof.log').open('w') as log:rc=subprocess.run(['yosys','-s','shared_d_proof.ys'],stdout=log,stderr=subprocess.STDOUT).returncode
pre=json.loads(Path('shared_d_pre.json').read_text())['modules']['shared_d_proof']
assert not any('init' in d.get('attributes',{}) for d in pre['netnames'].values())
assert len([c for c in pre['cells'].values() if c['type']=='$dff'])==4,'physical state was merged'
post=json.loads(Path('shared_d_post.json').read_text())['modules']['shared_d_proof']
initial={n:d['attributes']['init'] for n,d in post['netnames'].items() if 'init' in d.get('attributes',{})}
physical_samples={n:dict(bits=d['bits'],init=d.get('attributes',{}).get('init'))
                  for n,d in post['netnames'].items()
                  if re.search(r'sample_data\$\\ff[01]_[01]\.QN#sampled\$',n)}
assert len(physical_samples)==4,physical_samples
assert len({tuple(d['bits']) for d in physical_samples.values()})==4,'physical samples merged'
assert all(d['init'] is None or set(d['init'])<=set('x') for d in physical_samples.values()),physical_samples
result=dict(passed=rc==0,source_sha256=record['generated_sha256'],
            canonical_DFF_model_sha256=hashlib.sha256(Path('canonical_DFF_normalized.v').read_bytes()).hexdigest(),
            copied_originals=pairs,physical_state_bits=4,independent_initial_states=True,
            opt_merge=False,async2sync=False,memory_abstraction=False,unconstrained_shared_D_streams=True,
            post_transform_initialization=initial,
            physical_sample_state=physical_samples,
            initialization_audit='All four distinct physical QN samples have no fixed initialization. Fixed previous-D and clock-edge history are transform auxiliaries, separate from physical state.',
            theorem='All additional physical FF copies equal their original after the first real ck_core edge, for arbitrary shared D, independent of SRAM and ASR state.',
            scope='Copied-state obligation only; actual complete primitive correspondence and native reset profile proved separately.')
Path('shared_d_result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
raise SystemExit(rc)
