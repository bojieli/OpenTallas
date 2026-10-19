"""ROOT-authorized one-time graceful stop; refuses any changed identity."""
import datetime, hashlib, json, pathlib, subprocess
root=pathlib.Path(__file__).parent
receipt=json.loads((root/'live_runs.json').read_text())
out={'reason':'ROOT authorization via KV coordinator: unregistered aliases, >32 logical fanout and illegal macro contacts cannot qualify through hold repair','evidence_commit':'f90a7b45c','started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stopped':[]}
if (root/'stop_receipt.json').exists():
    out=json.loads((root/'stop_receipt.json').read_text())
for run in receipt['runs']:
    if any(x['id']==run['container_id'] for x in out['stopped']):
        assert subprocess.run(['docker','inspect',run['container_id']],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
        continue
    d=pathlib.Path(run['path'])
    snap=json.loads(pathlib.Path(str(d)+'.source_snapshot.json').read_text())
    assert snap['start_commit']==run['source_commit']
    assert snap['manifest_sha256']==run['manifest_sha256']
    current=json.loads(subprocess.check_output(['docker','inspect',run['container']]))[0]
    assert current['Id']==run['container_id']
    assert current['State']['Pid']==run['container_pid']
    assert current['State']['Running']
    assert sorted(current['Mounts'],key=lambda m:m['Destination'])==sorted(run['mounts'],key=lambda m:m['Destination'])
    for p,h in run['kit_hashes'].items():
        assert hashlib.sha256((d/'src'/p).read_bytes()).hexdigest()==h,p
    result=subprocess.run(['docker','stop','--time','30',run['container_id']],capture_output=True,text=True)
    probe=subprocess.run(['docker','inspect',run['container_id']],capture_output=True,text=True)
    after=json.loads(probe.stdout)[0] if probe.returncode==0 else None
    out['stopped'].append(dict(container=run['container'],id=run['container_id'],pid=run['container_pid'],rc=result.returncode,stdout=result.stdout,stderr=result.stderr,running_after=after['State']['Running'] if after else False,utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    (root/'stop_receipt.json').write_text(json.dumps(out,indent=2)+'\n')
    assert result.returncode==0
print(json.dumps(out))
