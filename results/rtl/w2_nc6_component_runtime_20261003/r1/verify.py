#!/usr/bin/env python3
"""Read-only terminal/source/case verification; never rebuilds or launches."""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent
ROOT=D.parents[3]
PIN='526c760682f111e2f0261bdf811a7eab10e49d1b'

def verify(record=None,text=None,terminal=None):
    r=json.loads((D/'record.json').read_text()) if record is None else record
    t=(D/'runtime.log').read_text() if text is None else text
    end=json.loads((D/'terminal.json').read_text()) if terminal is None else terminal
    assert r['source_commit']==PIN and r['worktree_clean'] and r['frozen_inputs_match'] and r['toolchain_matches_enrolled_hashes']
    assert r['compile_launched'] and r['runtime_launched']
    assert r['compile_returncode']==r['runtime_returncode']==0
    assert r['verdict']=='PASS_COMPONENT_FUNCTIONAL_ONLY'
    assert r['process_caps']=='NONE; affinity allocation only'
    assert r['headroom']['admitted'] and len(set(r['headroom']['allocated_cpus']))==2
    assert r['compiler_version'].startswith('Verilator 5.050 ')
    command=r['compile_command']
    assert command[:3]==['taskset','-c',','.join(map(str,r['headroom']['allocated_cpus']))]
    assert command[command.index('-j')+1]=='2'
    assert command[command.index('--top-module')+1]=='tb'
    assert command[-2].endswith('/rtl/experimental/w2_nc6_completion_20261003/ot_hdc_qwen_pc_exact_completion.sv')
    assert command[-1].endswith('/rtl/test/w2_nc6_completion_20261003/tb.sv')
    for name,digest in r['source_pins'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest
    expected=json.loads((D/'expected_cases.json').read_text())
    cases=re.findall(r'^CASE_PASS ([^ ]+) cycle=(\d+)$',t,re.M)
    assert len(cases)==18 and len({name for name,cycle in cases})==18 and {name for name,cycle in cases}==set(expected)
    assert [int(c) for n,c in cases]==sorted(int(c) for n,c in cases)
    assert 'COMPONENT_PASS cases=18 cycles=320 NC6 MAX16 period_ps1000' in t
    assert not end['runner_proc_present'] and end['source_worktree_clean']
    assert end['binary_sha256']==r['binary_sha256'] and end['runtime_returncode']==0
    return dict(verdict=r['verdict'],source_commit=PIN,case_count=18,fixture_cycles=320,
        binary_sha256=r['binary_sha256'],compile_seconds=r['compile_seconds'],allocated_cpus=r['headroom']['allocated_cpus'],
        functional_clock_period_ps=1000,mutable_protection_qualified=False,SS_FF_qualified=False,
        R14_connected_qualified=False,native_caller_qualified=False,physical_WR_visibility_qualified=False,
        global_reset_ABA_qualified=False,production_rate_qualified=False,full_token_qualified=False)

if __name__=='__main__':
    for row in json.loads((D/'manifest.json').read_text()):
        assert hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest()==row['sha256']
    print(json.dumps(verify(),indent=2,sort_keys=True))
