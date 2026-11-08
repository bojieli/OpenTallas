"""Partitions use the existing released final-GRT policy before entering DRT."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import gen_phys as G
import legacy_gate as L


def test_actual_partition_descriptor_uses_declared_partition_references(tmp_path):
    raw=json.loads((HERE/'examples/tiny_plan.json').read_text())
    G.write_phys(raw,tmp_path/'out',types=['mid'],trial=True,skip_ir=True)
    kit=tmp_path/'out/mid'; cfg=(kit/'config.mk').read_text()
    for name in ('legacy_gate.py','core_clock_band.py','clock_binding.json','signoff.py'):
        assert (kit/name).is_file(),name
    assert not (kit/'core.json').exists()  # retain the actual partition descriptor
    settings={key:next(x.split('=',1)[1].strip() for x in cfg.splitlines()
                       if x.startswith('export '+key+' ='))
              for key in ('OT_VCLK_TT','OT_VCLK_FF','LAYER_PARASITICS_FILE')}
    base=kit/'run/results/asap7/fixture/base';base.mkdir(parents=True)
    disc,ctx,policy=L.policy_context(kit,base,settings)
    assert ctx['insertion_ff_ps']==202.5
    assert policy['ff_vclk']=='rebind' and policy['insertion_bound']['ff']==202.5
    context=json.loads((kit/'sdc_lint.json').read_text())
    context.pop('insertion_ff_ps');(kit/'sdc_lint.json').write_text(json.dumps(context))
    with pytest.raises(ValueError,match='no declared per-corner FF'):
        L.policy_context(kit,base,settings)


@pytest.mark.parametrize('goal,margin,code',[
    ('route',None,0),('route',10,0),('finish',None,0),('finish',10,0),
    ('route',10,1),('finish',None,1),('cts',10,0)])
def test_exported_runner_checks_final_policy_before_drt(tmp_path,goal,margin,code):
    kit=tmp_path/'kit';kit.mkdir();bin=tmp_path/'bin';bin.mkdir()
    flow=tmp_path/'flow';flow.mkdir();(flow/'env.sh').write_text('')
    # config.mk before the results: a newer config.mk is the RESYNTH-GUARD refusal case (KW-FIX-32)
    (kit/'config.mk').write_text('' if margin is None else f'export OT_HOLD_FF_MARGIN = {margin}\n')
    result=kit/'run/results/asap7/fixture/base';result.mkdir(parents=True)
    for name in ('1_synth.odb','1_2_yosys.v','4_cts.odb','4_cts.sdc','5_1_grt.odb','6_final.odb'):
        (result/name).touch()
    def exe(name,text):
        p=bin/name;p.write_text(text);p.chmod(0o755)
    exe('python3',r'''#!/usr/bin/python3
import json,os,sys
if any(x.endswith('/legacy_gate.py') for x in sys.argv):
 with open(os.environ['EVENTS'],'a') as f:f.write(json.dumps(['policy',*sys.argv[1:]])+'\n')
 sys.exit(int(os.environ['POLICY_RC']))
''')
    exe('make',r'''#!/usr/bin/python3
import json,os,sys
with open(os.environ['EVENTS'],'a') as f:f.write(json.dumps(['make',*sys.argv[1:]])+'\n')
''')
    exe('openroad','#!/bin/sh\necho "OT_POSTCTS_GATE TEST PASS"\n')
    exe('chown','#!/bin/sh\nexit 0\n')
    exe('docker',r'''#!/usr/bin/python3
import os,sys,subprocess
a=sys.argv[1:]
if 'bash' not in a:sys.exit(0)
i=a.index('bash');assert a[i+1]=='-lc'
e=os.environ.copy()
for j,x in enumerate(a[:-1]):
 if x=='-e' and '=' in a[j+1]:k,v=a[j+1].split('=',1);e[k]=v
cmd=a[i+2].replace('/OpenROAD-flow-scripts',e['FAKE_FLOW']).replace('/work',e['FAKE_KIT'])
sys.exit(subprocess.run(['bash','-c',cmd],env=e).returncode)
''')
    runner=tmp_path/'run.sh';runner.write_text(G.RUN_KIT)
    env=dict(os.environ,PATH=str(bin)+':'+os.environ['PATH'],OT_LEC_ASYNC='0',
             EVENTS=str(tmp_path/'events.jsonl'),POLICY_RC=str(code),
             FAKE_FLOW=str(flow),FAKE_KIT=str(kit))
    p=subprocess.run(['bash',str(runner),str(kit),goal,'16','8'],env=env,capture_output=True,text=True)
    assert p.returncode==(6 if code else 0),p.stdout+p.stderr+(kit/f'run_{goal}.log').read_text()
    events=[json.loads(x) for x in (tmp_path/'events.jsonl').read_text().splitlines()]
    policies=[i for i,e in enumerate(events) if e[0]=='policy']
    if goal=='cts':
        assert not policies
        return
    assert len(policies)==1
    gi=[i for i,e in enumerate(events) if e[0]=='make' and 'grt' in e]
    assert len(gi)==1 and gi[0]<policies[0]
    later=[i for i,e in enumerate(events) if e[0]=='make' and goal in e]
    if code:
        assert not later
        assert 'final GRT released TT/FF policy' in (kit/'FAIL_POSTCTS').read_text()
    else:
        assert len(later)==1 and policies[0]<later[0]
