#!/usr/bin/env python3
"""Validate publication and replay unchanged r9 controls at the frozen real root.

Read-only archival input replay, not runtime admission. No ROOT patch, compiler,
make, simulation, service, configuration mutation or artifact reuse is invoked.
The clean frozen worker is an explicit external prerequisite.
"""
import json
import os
import subprocess
import sys
from pathlib import Path
import prepare_hbm_qwen_frontend_r9 as P

ROOT = Path(__file__).resolve().parents[1]
SOURCE = '575a9d988e444d38f9fdaef8a1004799319ab76d'
REL = Path('results/uarch/hbm_qwen_frontend_r9_20261002')


def worker_state(worker):
    head = subprocess.check_output(['git','rev-parse','HEAD'],cwd=worker,text=True).strip()
    if head != SOURCE:
        raise ValueError('recorded r9 worker must remain at frozen source commit')
    if subprocess.check_output(['git','status','--porcelain'],cwd=worker,text=True):
        raise ValueError('recorded r9 worker must remain clean')
    return head


def check_inputs(worker, proposal):
    pins = dict(proposal['source_sha256'], **proposal['gate_tool_sha256'])
    for bundle in ('frame.json','model.json','prospective_headroom.json','original_Qwen_prepared_gate.json','GO_template.json'):
        path = REL / bundle
        if (ROOT/path).read_bytes() != (worker/path).read_bytes():
            raise ValueError('main/worker input bytes differ: '+str(path))
    for path,pin in pins.items():
        if P.sha(ROOT/path) != pin or P.sha(worker/path) != pin:
            raise ValueError('main/worker source/tool pin mismatch: '+path)
    if (ROOT/REL/'prepared_gate.json').read_bytes() != (worker/REL/'prepared_gate.json').read_bytes():
        raise ValueError('main/worker proposal bytes differ')
    # Pure main derivation also verifies compiler files and original committed
    # GO/verdict/source/tool/frame provenance, without executing any old build.
    data=(json.dumps(P.review_prepare(),indent=2,sort_keys=True)+'\n').encode()
    if data != (ROOT/REL/'prepared_gate.json').read_bytes():
        raise ValueError('main review preparation bytes differ')
    return len(pins)


def validate_archive():
    worker=Path(P.load(P.OUT/'frame.json')['execution_root'])
    if ROOT == worker:
        raise ValueError('archival wrapper must run outside production worker')
    before=worker_state(worker)
    proposal=P.load(P.OUT/'prepared_gate.json')
    count=check_inputs(worker,proposal)
    try:
        P.prepare_target('Qwen')
    except ValueError as error:
        if str(error)!='reviewed Qwen execution root changed':
            raise
    else:
        raise ValueError('production ROOT guard failed to reject archival tree')
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    test=subprocess.run([sys.executable,'-B',str(ROOT/'tools/hbm_r9_archival_test_fixture.py')],cwd=worker,env=env,capture_output=True,text=True,timeout=60)
    if test.returncode:
        raise ValueError('unchanged real-root controls failed: '+test.stderr)
    replay='import sys,json;sys.path.insert(0,"tools");import prepare_hbm_qwen_frontend_r9 as P;print(json.dumps(P.prepare_target("Qwen"),indent=2,sort_keys=True))'
    raw=subprocess.check_output([sys.executable,'-B','-c',replay],cwd=worker,env=env,timeout=60)
    if raw != (ROOT/REL/'prepared_gate.json').read_bytes():
        raise ValueError('real-root prepare replay byte mismatch')
    check_inputs(worker,proposal)
    if worker_state(worker)!=before:
        raise ValueError('frozen worker changed during archival replay')
    return dict(schema='opentallas.H1.r9.archival-validation.v1',verdict='PASS_ARCHIVAL_REAL_ROOT_CONTROLS_AND_BYTE_PARITY',recorded_source_commit=before,recorded_source_root=str(worker),archival_root=str(ROOT),proposal_sha256=P.sha(P.OUT/'prepared_gate.json'),source_tool_pins=count,main_worker_proposal_bytes_equal=True,main_review_prepare_bytes_equal=True,real_root_prepare_bytes_equal=True,unchanged_production_ROOT_guard_refuses_archival_tree=True,real_root_test_stdout=test.stdout,real_root_test_stderr=test.stderr,external_resource_fixture=json.loads(test.stdout)['external_resource_fixture'],tests_run=json.loads(test.stdout)['tests_run'],scope='Archival inputs and original10 controls; external host-memory fixture only during mocked lifecycle case; no runtime admission or actual compile',worker_clean_before_after=True,launches=0,physical_credit=False,token_credit=False)


if __name__=='__main__':
    print(json.dumps(validate_archive(),indent=2,sort_keys=True))
