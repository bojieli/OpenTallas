import datetime, hashlib, json, pathlib, subprocess
base=pathlib.Path('/srv/opentallas-scratch/claude/ref_gate')
out={'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'runs':[]}
for tile,suffix,stamp,pid in [('grp','sq2','113454',507086),('grp','sq3','113455',507087),('grp_h','sq2','113454',507085),('grp_h','sq3','113456',507088)]:
    name=f'qkd_kvs_{tile}_{suffix}-20261019-{stamp}'; d=base/name
    snap=json.load(open(str(d)+'.source_snapshot.json'))
    container='gate_cts_'+name
    ins=json.loads(subprocess.check_output(['docker','inspect',container]))[0]
    latest=[x for x in (d/'cts.log').read_text().splitlines() if '-74.905' in x][-4:]
    top=subprocess.check_output(['docker','top',container,'-eo','pid,ppid,etime,pcpu,args'],text=True)
    hashes={str(p.relative_to(d/'src')):hashlib.sha256(p.read_bytes()).hexdigest() for p in (d/'src/physical/ref_tile'/f'qkd_kvs_{tile}_{suffix}').glob('*') if p.is_file()}
    out['runs'].append(dict(run=name,path=str(d),local_client_pid=pid,source_commit=snap['start_commit'],manifest_sha256=snap['manifest_sha256'],archive_sha256=snap['archive_sha256'],container=container,container_id=ins['Id'],container_pid=ins['State']['Pid'],mounts=ins['Mounts'],processes=top,latest_hold=latest,kit_hashes=hashes))
print(json.dumps(out,indent=2))
