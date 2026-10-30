"""An admission failure does not own a previously completed physical input."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import pytest
import autopilot as AP


@pytest.mark.parametrize('kind,goal', [('preflight','route'),('admission-tools','route'),
                                      ('infra-lost','route'),('proof-oom','route'),('flow-error','post')])
def test_nonphysical_failure_never_requests_bulk_delete(monkeypatch,kind,goal):
    monkeypatch.setattr(AP,'tsv_append',lambda *a,**k:None)
    monkeypatch.setattr(AP,'log',lambda *a,**k:None)
    monkeypatch.setattr(AP,'failed_notice',lambda *a,**k:None)
    monkeypatch.setattr(AP,'set_status',lambda st,j,status,*a:j.update(status=status))
    monkeypatch.setattr(AP,'rpy',lambda *a,**k:pytest.fail('nonphysical failure attempted deletion'))
    j=dict(status='STRUCTURAL',id='owned',die='s81',type='t',src='rev',host='intel1',
           kit='k',path='/kit',kind=kind,goal=goal,chain_version=2,started=time.time())
    AP.record_failure({},j)
    assert j['data_deleted'] is False and j['delete_pending'] is False
    assert j['status']=='DONE-STRUCTURAL'


def test_probe_preserves_prior_checkpoint_but_fresh_dead_probe_cleanup_stays_eligible():
    # Execute the real remote probe against this test's own temporary kit, dry-run only.
    root=Path('/srv/opentallas-scratch/claude')
    with tempfile.TemporaryDirectory(prefix='cleanup-control-',dir=root) as td:
        kit=Path(td);(kit/'config.mk').write_text('# own fixture')
        odb=kit/'run/results/asap7/t/base/5_1_grt.odb';odb.parent.mkdir(parents=True);odb.write_text('prior checkpoint')
        bins=kit/'bin';bins.mkdir();docker=bins/'docker';docker.write_text('#!/bin/sh\nexit 0\n');docker.chmod(0o755)
        started=time.time();os.utime(odb,(started-30,started-30))
        def probe(cutoff):
            run=subprocess.run([sys.executable,'-c',AP.PROBE_DELETE,json.dumps(dict(kit=str(kit),dry=True,preserve_before=cutoff))],
                               env=dict(os.environ,PATH=str(bins)),capture_output=True,text=True,check=True)
            return json.loads(run.stdout.removeprefix('AP_JSON '))
        old=probe(started)
        assert old['preserved']==[str(odb)] and old['deleted']==[]
        assert odb.read_text()=='prior checkpoint'
        fresh=probe(started-60)
        assert 'preserved' not in fresh and fresh['deleted']
        assert odb.exists()  # dry-run ordinary cleanup retains the fixture too
