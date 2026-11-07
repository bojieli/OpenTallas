"""Opt-in handoff controls; real tiny LEC exercises the completed-result transport.

The fake unadmitted child is our own sleeping process. Only its guard-unit tests
use age=0/flat=0 with an isolated admission lock; CLI defaults stay2h/60s.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import pytest

sys.path.insert(0,str(Path(__file__).parent))
import lec_pending_handoff as H
HERE=Path(__file__).parent


def kit(tmp_path):
    k=tmp_path/'source';(k/'rtl').mkdir(parents=True)
    fx=HERE/'examples/lec_csa31'
    for src,dst in [('lec_bbx.v','lec_bbx.v'),('lec_t1_fix.sv','lec_t1.sv')]:shutil.copy2(fx/src,k/'rtl'/dst)
    n=k/'run/results/asap7/lec_t1/base/1_2_yosys.v';n.parent.mkdir(parents=True);shutil.copy2(fx/'netlist_fix.v',n)
    for name in ('lec.py','lec_async.sh','lec_pending_handoff.py'):shutil.copy2(HERE/name,k/name)
    (k/'freeze.json').write_text('{}')
    (k/'config.mk').write_text('export DESIGN_NAME = lec_t1\nexport PLATFORM = asap7\nexport VERILOG_FILES = /work/rtl/lec_bbx.v /work/rtl/lec_t1.sv\nexport VERILOG_INCLUDE_DIRS = /work/rtl\nexport VERILOG_DEFINES = -DSYNTHESIS\nexport SYNTH_HDL_FRONTEND = slang\nexport SYNTH_BLACKBOXES = lec_bbx\n')
    (k/'lec_async.ready').write_text('1\npython3 -I /work/lec.py /work --netlist /work/run/results/asap7/lec_t1/base/1_2_yosys.v --out /work/lec\n')
    env=H.proof_env()
    (k/'lec_async.source_identity').write_text(H.identity(k,'source',env)+'\n')
    (k/'lec_async.identity').write_text(H.identity(k,'all',env)+'\n')
    return k


@pytest.fixture
def pending(tmp_path,monkeypatch):
    monkeypatch.setenv('OT_LEC_HANDOFF','1')
    k=kit(tmp_path)
    script=tmp_path/'ot-heavy'
    # Keep bash as the observed child; it has never launched a tool/container.
    script.write_text('#!/bin/bash\nsleep60 &\nwait\n'.replace('sleep60','sleep 60'))
    p=subprocess.Popen(['bash',str(script)],start_new_session=True)
    try:
        H.register(k,os.getpid(),p.pid,'fixture-owner','openroad/orfs:asap7lock',4,1)
        yield k,p,tmp_path
    finally:
        try:os.killpg(p.pid,15)
        except ProcessLookupError:pass
        p.wait()


def prepare(pending):
    k,p,tmp=pending;dest=tmp/'destination'
    H.request(k,H.host(),str(dest))
    return k,p,tmp,dest


def test_legacy_rejected(tmp_path):
    k=tmp_path/'legacy';k.mkdir()
    with pytest.raises(FileNotFoundError):H.request(k,H.host(),str(tmp_path/'to'))


def test_default_age_guard_keeps_unstarted_child(pending):
    k,p,tmp,dest=prepare(pending)
    with pytest.raises(ValueError,match='2h'):H.accept(k,os.getpid(),p.pid,lock=str(tmp/'admit.lock'))
    assert p.poll() is None


def test_admitted_child_refused(pending):
    k,p,tmp,dest=prepare(pending)
    (tmp/f'res.oth-fixture-{p.pid}-1').write_text('admitted')
    with pytest.raises(ValueError,match='already admitted'):
        H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'))
    assert p.poll() is None


def test_wrong_source_identity_keeps_child(pending):
    k,p,tmp,dest=prepare(pending)
    (k/'rtl/lec_t1.sv').write_text('// changed\n')
    with pytest.raises(ValueError,match='identity changed'):
        H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'))
    assert p.poll() is None


def test_wrong_destination_host_rejected_before_tool(pending):
    k,p,tmp,dest=prepare(pending)
    packet=H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'));p.wait()
    shutil.copytree(k,dest);packet['destination_host']='wrong-host.invalid';H.atomic(dest/H.PACKET,packet)
    with pytest.raises(ValueError,match='host/path'):H.worker(dest,dest/H.PACKET)
    assert not (dest/'lec_handoff_worker.log').exists()


def test_real_lec_and_result_import(pending):
    k,p,tmp,dest=prepare(pending)
    before=(k/'lec_async.identity').read_bytes();owner=H.read(k/H.STATE)['watcher']
    H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'));p.wait()
    shutil.copytree(k,dest)
    assert H.worker(dest,dest/H.PACKET)==0
    assert H.read(dest/'lec/lec.json')['verdict']=='EQUIVALENT'
    H.import_result(k,dest)
    assert (k/'lec_async.unit_rc').read_text().strip()=='0'
    assert (k/'lec_async.identity').read_bytes()==before
    assert H.read(k/H.STATE)['watcher']==owner
    assert H.read(k/H.STATE)['phase']=='returned'
    assert H.read(k/'lec/lec.json')['verdict']=='EQUIVALENT'


def test_worker_tool_failure_is_no_verdict(pending):
    k,p,tmp,dest=prepare(pending)
    packet=H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'));p.wait()
    shutil.copytree(k,dest)
    H.atomic(dest/H.RESULT,dict(schema=H.VERSION,packet_sha=H.digest(packet),host=H.host(),kit=str(dest.resolve()),rc=125,report_sha=None))
    H.import_result(k,dest)
    assert (k/'lec_async.unit_rc').read_text().strip()=='143'
    assert not (k/'lec/lec.json').exists()
    assert H.read(k/'lec_async.handoff.returned.json')['result_class']=='NO_VERDICT'


def test_metadata_presence_change_rejected_before_worker(pending):
    k,p,tmp,dest=prepare(pending)
    H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'));p.wait()
    shutil.copytree(k,dest)
    (dest/'constraint.sdc').write_text('create_clock -period1 clk\n')
    with pytest.raises(ValueError,match='identity changed'):H.worker(dest,dest/H.PACKET)
    assert not (dest/'lec_handoff_worker.log').exists()


def test_copied_netlist_change_rejected_before_worker(pending):
    k,p,tmp,dest=prepare(pending)
    H.accept(k,os.getpid(),p.pid,min_age=0,flat_seconds=0,lock=str(tmp/'admit.lock'));p.wait()
    shutil.copytree(k,dest)
    net=dest/'run/results/asap7/lec_t1/base/1_2_yosys.v'
    net.write_text(net.read_text()+'\n// exact bytes changed\n')
    with pytest.raises(ValueError,match='identity changed'):H.worker(dest,dest/H.PACKET)
    assert not (dest/'lec_handoff_worker.log').exists()
