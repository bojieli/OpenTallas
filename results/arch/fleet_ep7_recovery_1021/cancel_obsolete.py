import os,json,time,fcntl,signal,glob
from pathlib import Path
rows=json.loads(Path('/tmp/codex-ep7-obsolete-waiters-1021.json').read_text())['waiters']
report={'start':time.strftime('%Y-%m-%d %H:%M:%S %Z'),'cancelled':[],'preserved':[]}
with open('/var/tmp/ot-heavy/admit.lock','a') as lock:
    deadline=time.monotonic()+60
    while True:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);break
        except BlockingIOError:
            if time.monotonic()>deadline:raise SystemExit('NO ACTION: admission lock busy')
            time.sleep(.01)
    report['lock_acquired']=time.strftime('%Y-%m-%d %H:%M:%S %Z')
    for r in rows:
        if not r['eligible']:continue
        p=r['pid']
        try:
            a=Path(f'/proc/{p}/cmdline').read_text().split('\0')[:-1]
            start=Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()[19]
            cg=Path(f'/proc/{p}/cgroup').read_text()
            if (start!=r['start'] or a[1:2]!=['/usr/local/bin/ot-heavy'] or
                '--tag' not in a or a[a.index('--tag')+1]!=r['tag'] or
                os.readlink(f'/proc/{p}/cwd')!=r['cwd'] or '/oth-' in cg or
                glob.glob(f'/var/tmp/ot-heavy/res.oth-ubuntu-{p}-*')):
                report['preserved'].append({'pid':p,'reason':'changed/admitted/reserved'});continue
            kids=Path(f'/proc/{p}/task/{p}/children').read_text().split()
            locked=[]
            for child in r['flock_children']:
                k=child['pid']
                if str(k) in kids and Path(f'/proc/{k}/stat').read_text().rsplit(')',1)[1].split()[19]==child['start'] and Path(f'/proc/{k}/comm').read_text().strip()=='flock' and Path(f'/proc/{k}/wchan').read_text().strip()=='locks_lock_inode_wait':locked.append(k)
            if not locked:
                report['preserved'].append({'pid':p,'reason':'not proven flock-blocked'});continue
            # Hold admission lock across identity validation and exact signals,
            # so these launchers cannot cross into an admitted build.
            os.kill(p,signal.SIGTERM)
            for k in locked:
                try:os.kill(k,signal.SIGTERM)
                except ProcessLookupError:pass
            report['cancelled'].append({'pid':p,'tag':r['tag'],'flock_children':locked,'cwd':r['cwd']})
        except (OSError,ValueError,IndexError):
            report['preserved'].append({'pid':p,'reason':'gone or changed; no action'})
report['end']=time.strftime('%Y-%m-%d %H:%M:%S %Z')
Path('/tmp/codex-ep7-obsolete-cancel-report-1021.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cancelled':len(report['cancelled']),'preserved':len(report['preserved']),'start':report['start'],'lock_acquired':report['lock_acquired'],'end':report['end']}))
