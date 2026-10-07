"""Launcher integration tests: fake Docker, real subprocesses and git source pin."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'tools/qwen_dietop_launch.py'
FAKE_DOCKER = r'''#!/usr/bin/env python3
import json, os, pathlib, sys
args=sys.argv[1:]; root=pathlib.Path(os.environ['FAKE_DOCKER_ROOT'])
scenario=os.environ.get('SCENARIO', 'pass')
with (root/'calls').open('a') as f: f.write(json.dumps(args)+'\n')
image='sha256:'+'a'*64
if args[:2] == ['image','inspect']:
 print(image); sys.exit(0)
if args[0]=='create':
 labels=dict(x.split('=',1) for i,x in enumerate(args) if i and args[i-1]=='--label')
 phase=labels['opentallas.phase']
 if scenario=='conflict' or (scenario=='pdn_conflict' and phase=='pdn'):
  print('Conflict: name already in use by foreign live container',file=sys.stderr);sys.exit(125)
 cid=('b' if phase=='placement' else 'c')*64
 mounts=[x for i,x in enumerate(args) if i and args[i-1]=='-v']
 work=next(x.split(':')[0] for x in mounts if x.endswith(':/work'))
 assert not (pathlib.Path(work)/'floorplan.odb').exists() if phase=='placement' else True
 assert len([x for x in mounts if x.endswith(':ro')])==9
 for mount in mounts[1:]:
  assert pathlib.Path(mount.split(':')[0]).stat().st_mode & 0o222 == 0
 data={'Id':cid,'Image':image,'Config':{'Labels':labels},'State':{'Status':'created','Running':False,'ExitCode':0,'OOMKilled':False,'FinishedAt':'0001-01-01T00:00:00Z'},'work':work}
 (root/cid).write_text(json.dumps(data)); print(cid);sys.exit(0)
if args[0]=='inspect':
 data=json.loads((root/args[1]).read_text())
 if scenario=='wrong_identity' and data['State']['Status']=='exited':data['Id']='d'*64
 print(json.dumps([data]));sys.exit(0)
if args[:2]==['start','--attach']:
 cid=args[2];data=json.loads((root/cid).read_text());phase=data['Config']['Labels']['opentallas.phase']
 if scenario=='start_failure':sys.exit(125)
 data['State'].update(Status='exited',ExitCode=17 if scenario=='container_failure' else 0,FinishedAt='2026-10-07T06:00:00Z')
 (root/cid).write_text(json.dumps(data))
 work=pathlib.Path(data['work'])
 if phase=='placement':
  print('OT_LEGAL instances=17729 overlaps=0 outside=0\nOT_ASSERT PASS\nOT_PA DONE')
  if scenario=='physical_failure':print('OT_PA FAIL blocked pins')
  if scenario=='still_running':
   data['State'].update(Status='running',Running=True)
   (root/cid).write_text(json.dumps(data))
  if scenario!='missing_odb':(work/'floorplan.odb').write_text('owned placement')
 else:
  assert (work/'floorplan.odb').read_text()=='owned placement'
  print('OT_PDN PASS special_shapes=123\nOT_PGCHECK VDD PASS\nOT_PGCHECK VSS PASS')
  if scenario=='pdn_failure':print('OT_PGCHECK VSS FAIL disconnected grid')
  (work/'floorplan_pdn.odb').write_text('owned pdn')
 sys.exit(0)
raise AssertionError(args)
'''


@pytest.fixture
def campaign(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    subprocess.run(['git', 'init', '-q', str(source)], check=True)
    (source / 'producer.py').write_text('# pinned fixture producer\n')
    subprocess.run(['git', '-C', str(source), 'add', 'producer.py'], check=True)
    subprocess.run(['git', '-C', str(source), '-c', 'user.name=Test', '-c',
                    'user.email=test@example.invalid', 'commit', '-qm', 'fixture'], check=True)
    sha = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    inputs = tmp_path / 'generated'
    inputs.mkdir()
    for name in ('run.tcl', 'run_pdn.tcl', 'die.v', 'elements.lef', 'phy_ew.lef',
                 'snap.tcl', 'place.tcl', 'pdn.tcl'):
        (inputs / name).write_text('fixture '+name+'\n')
    (inputs / 'manifest.json').write_text(json.dumps({'execution_order':['run.tcl','run_pdn.tcl']}))
    # Old outputs/markers and a foreign live-container sentinel must remain intact.
    for name in ('case.done', 'run.log.exit', 'floorplan.odb'):
        (inputs / name).write_text('old failure evidence')
    fake = tmp_path / 'fake'
    fake.mkdir()
    (fake / 'foreign_live').write_text('running; must not be touched')
    (fake / 'docker').write_text(FAKE_DOCKER)
    (fake / 'docker').chmod(0o755)
    guard = fake / 'admit.sh'
    guard.write_text('#!/bin/sh\nshift\n[ "$1" = -- ] || exit 1\nshift\nexec "$@"\n')
    guard.chmod(0o755)
    env = dict(os.environ, PATH=str(fake)+os.pathsep+os.environ['PATH'], FAKE_DOCKER_ROOT=str(fake))
    dest = tmp_path / 'run'
    argv = [sys.executable, str(RUNNER), '--inputs', str(inputs), '--run', str(dest),
            '--source-root', str(source), '--source', sha, '--admit', str(guard), '--peak-gib', '0.01']
    return argv, env, dest, inputs, fake


def launch(campaign, scenario):
    argv, env, dest, inputs, fake = campaign
    result = subprocess.run(argv, env=dict(env, SCENARIO=scenario), capture_output=True, text=True)
    for name in ('case.done', 'run.log.exit', 'floorplan.odb'):
        assert (inputs / name).read_text() == 'old failure evidence'
    assert (fake / 'foreign_live').read_text() == 'running; must not be touched'
    return result, [json.loads(x) for x in (fake / 'calls').read_text().splitlines()]


@pytest.mark.parametrize('scenario', ['conflict', 'start_failure', 'container_failure',
                                     'physical_failure', 'missing_odb', 'wrong_identity', 'still_running'])
def test_placement_failure_never_launches_pdn_or_completes(campaign, scenario):
    result, calls = launch(campaign, scenario)
    dest = campaign[2]
    assert result.returncode != 0, result.stderr
    assert (dest / 'failure.json').exists()
    assert not (dest / 'complete.json').exists()
    assert not (dest / 'placement.complete.json').exists()
    assert not (dest / 'pdn.create.json').exists()
    assert sum(c[0]=='create' for c in calls)==1
    assert not any(c[0] in ('rm','stop','kill') for c in calls)
    if scenario=='conflict':
        assert not any(c[0] in ('start','inspect') for c in calls)
        assert not (dest / 'work/run.log').exists()


def test_success_uses_exact_ids_and_reuse_is_rejected(campaign):
    result, calls = launch(campaign, 'pass')
    dest = campaign[2]
    assert result.returncode == 0, result.stderr
    assert json.loads((dest/'placement.complete.json').read_text())['container_id']=='b'*64
    assert json.loads((dest/'pdn.complete.json').read_text())['container_id']=='c'*64
    assert (dest/'complete.json').exists()
    starts = [c for c in calls if c[0]=='start']
    assert starts==[['start','--attach','b'*64],['start','--attach','c'*64]]
    before={str(p):p.read_bytes() for p in dest.rglob('*') if p.is_file()}
    again, new_calls = launch(campaign, 'pass')
    assert again.returncode != 0
    assert new_calls == calls
    assert before=={str(p):p.read_bytes() for p in dest.rglob('*') if p.is_file()}


def test_pdn_create_conflict_keeps_placement_but_not_case_completion(campaign):
    result, calls = launch(campaign, 'pdn_conflict')
    dest = campaign[2]
    assert result.returncode != 0
    assert (dest/'placement.complete.json').exists()
    assert not (dest/'pdn.complete.json').exists()
    assert not (dest/'complete.json').exists()
    assert len([c for c in calls if c[0]=='start'])==1


def test_legacy_positional_entrypoint_fails_without_touching_inputs(campaign):
    _, env, _, inputs, fake = campaign
    result = subprocess.run(['bash', str(ROOT/'tools/qwen_rom_fulldie_run_case.sh'),
        str(inputs), 'run.tcl', 'run.log', '16', '300'], env=env, capture_output=True)
    assert result.returncode != 0
    assert not (fake/'calls').exists()
    assert (inputs/'run.log.exit').read_text()=='old failure evidence'


def test_pdn_physical_failure_is_not_completion(campaign):
    result, _ = launch(campaign, 'pdn_failure')
    dest = campaign[2]
    assert result.returncode != 0
    assert (dest/'placement.complete.json').exists()
    assert not (dest/'pdn.complete.json').exists()
    assert not (dest/'complete.json').exists()


def test_dirty_source_is_rejected_before_claim_or_docker(campaign):
    argv, env, dest, inputs, fake = campaign
    (inputs.parent/'source/producer.py').write_text('# changed')
    result = subprocess.run(argv, env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'not clean' in result.stderr
    assert not dest.exists()
    assert not (fake/'calls').exists()


@pytest.mark.parametrize('available_gib,accepted', [(150, False), (203, True)])
def test_admission_reserve_uses_host_total_not_job_peak(monkeypatch, available_gib, accepted):
    import importlib.util
    spec = importlib.util.spec_from_file_location('qwen_launch', RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # 1 TiB host, 100 GiB job: required 202.4 GiB. The erroneous job-based
    # reserve would accept 150 GiB (100 + max(10,32)).
    monkeypatch.setattr(module.Path, 'read_text', lambda _: (
        f'MemTotal: {1024*1024*1024} kB\nMemAvailable: {available_gib*1024*1024} kB\n'))
    calls=[]
    monkeypatch.setattr(module.subprocess, 'call', lambda argv: calls.append(argv) or 0)
    assert module.admitted_start('b'*64, 100)==(0 if accepted else 75)
    assert bool(calls)==accepted
