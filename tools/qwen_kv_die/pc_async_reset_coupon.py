#!/usr/bin/env python3
"""Canonical semantic theorem for each source-audited one-plus-eight ASR bank.

Two stopped-clock phases, asynchronous assertion/reassertion, and exactly two
real destination rising edges are exercised from independent physical states.
Six real coupon-source defects must produce committed SAT failure witnesses.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

record=json.loads(Path('pc_async_source_graph_proof.json').read_text())
for path,digest in record['models'].items():
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==digest
ASR='DFFASRHQNx1_ASAP7_75t_R'
results=[]
mutations=['baseline','root_polarity','root_assert_value','first_D','clock','QN_polarity','stage_bypass']
for stopped in (0,1):
    # In both traces reset asserts/reasserts while the destination clock is
    # stopped. The initial state is unrestricted; the first step is not proved.
    if stopped==0:
        trace=[(0,1,0),(0,0,0),(0,0,0),(0,1,0),(1,1,0),(0,1,0),(1,1,1),
               (0,1,1),(0,0,0),(0,1,0),(1,1,0),(0,1,0),(1,1,1)]
    else:
        trace=[(1,1,0),(1,0,0),(1,0,0),(1,1,0),(0,1,0),(1,1,0),(0,1,0),(1,1,1),
               (1,0,0),(1,1,0),(0,1,0),(1,1,0),(0,1,0),(1,1,1)]
    for mutation in mutations:
        prefix=Path('coupon_stopped'+str(stopped)+'_'+mutation)
        lines=['module pc_async_coupon(input wire clk,rst_n,want,output wire ok,output wire [7:0] released);']
        for index in range(9):
            data="1'b1" if index==0 else '~q0'
            ck='clk';reset='rst_n';setn="1'b1"
            if index==0:
                if mutation=='root_polarity':reset='~rst_n'
                elif mutation=='root_assert_value':reset="1'b1";setn='rst_n'
                elif mutation=='first_D':data="1'b0"
            elif index==1:
                if mutation=='clock':ck='~clk'
                elif mutation=='QN_polarity':data='q0'
                elif mutation=='stage_bypass':data="1'b1"
            lines += [f'wire q{index};',f'{ASR} ff{index}(.CLK({ck}),.D({data}),.RESETN({reset}),.SETN({setn}),.QN(q{index}));']
        lines += ['assign released=~{q8,q7,q6,q5,q4,q3,q2,q1};',
                  'assign ok=released=={8{want}};','endmodule']
        prefix.with_suffix('.v').write_text('\n'.join(lines)+'\n')
        commands=['read_verilog canonical_ASR_normalized.v',
                  'read_verilog '+str(prefix.with_suffix('.v')),
                  'hierarchy -check -top pc_async_coupon','flatten','proc','opt_expr','opt_clean',
                  'write_json '+str(prefix.with_suffix('.pre.json')),
                  'clk2fflogic','opt_clean','write_json '+str(prefix.with_suffix('.post.json'))]
        sat=f'sat -seq {len(trace)} -prove ok 1 -prove-skip 1 -verify -show-inputs -show-outputs'
        for step,(ck,reset,want) in enumerate(trace,1):
            sat+=f' -set-at {step} clk {ck} -set-at {step} rst_n {reset} -set-at {step} want {want}'
        commands.append(sat);prefix.with_suffix('.ys').write_text('\n'.join(commands)+'\n')
        with prefix.with_suffix('.log').open('w') as out:
            rc=subprocess.run(['yosys','-s',str(prefix.with_suffix('.ys'))],stdout=out,stderr=subprocess.STDOUT).returncode
        log=prefix.with_suffix('.log').read_text()
        if mutation=='baseline':
            assert rc==0 and 'SUCCESS' in log,(prefix,rc)
            pre=json.loads(prefix.with_suffix('.pre.json').read_text())['modules']['pc_async_coupon']
            sequential=[c for c in pre['cells'].values() if c['type'] in ('$adff','$dff','$dffsr')]
            assert len(sequential)==9,'physical ASR bank states merged or pruned'
            assert not any('init' in d.get('attributes',{}) for d in pre['netnames'].values())
            post=json.loads(prefix.with_suffix('.post.json').read_text())['modules']['pc_async_coupon']
            # A later stage's previous-D history can itself be named ff0.QN
            # because its canonical next-state is first-stage QN. Those history
            # samplers initialize to zero and are NOT physical state. Exactly
            # one unconstrained sampled-Q exists per source ASR instance.
            physical={n:dict(bits=d['bits'],init=d.get('attributes',{}).get('init')) for n,d in post['netnames'].items()
                      if re.search(r'sample_data\$\\ff[0-8]\.QN#sampled\$',n)
                      and ('init' not in d.get('attributes',{}) or set(d['attributes']['init'])<=set('x'))}
            assert len(physical)==9,physical
            for index in range(9):
                assert len([n for n in physical if re.search(r'\\ff'+str(index)+r'\.QN#sampled\$',n)])==1,physical
            assert len({tuple(d['bits']) for d in physical.values()})==9,'physical sampled state merged'
            assert all(d['init'] is None or set(d['init'])<=set('x') for d in physical.values()),physical
            results.append(dict(stopped_clock=stopped,mutation=mutation,passed=True,rc=rc,
                                independent_physical_states=physical,trace=trace,
                                log_sha256=hashlib.sha256(log.encode()).hexdigest()))
        else:
            assert rc!=0 and 'proof did fail' in log,(prefix,rc,log[-500:])
            results.append(dict(stopped_clock=stopped,mutation=mutation,causally_failed=True,rc=rc,
                                fail_regex='proof did fail',fail_witness=str(prefix.with_suffix('.log')),
                                log_sha256=hashlib.sha256(log.encode()).hexdigest()))
packet=dict(schema='opentallas.pc.private_async_conditioner.canonical_coupon.v1',
            source_graph_proof_sha256=hashlib.sha256(Path('pc_async_source_graph_proof.json').read_bytes()).hexdigest(),
            model_hashes=record['models'],async2sync=False,opt_merge=False,ignore_unknown_cells=False,
            memory_abstraction=False,unconstrained_initial_physical_bank_bits=9,
            semantic_scope='Source-audited one-first/eight-final canonical ASR bank; source graph/cell/pin identities and every external consumer are bound separately.',
            assertion='Logical release is 0 after raw reset assertion with clock stopped at either level.',
            release='No asynchronous or one-edge release; all eight final logical releases become 1 exactly at the second real destination rising edge.',
            source_observer_scope='Existing ordinary-D logical release observers capture on their own subsequent destination edge; exact source graph records their clocks, not a masked/removed cycle.',
            baseline_passes=2,causal_mutant_failures=12,results=results)
Path('pc_async_coupon_proof.json').write_text(json.dumps(packet,indent=2)+'\n')
print(json.dumps(dict(baseline_passes=2,causal_mutant_failures=12,independent_bank_states=9,async2sync=False)))
