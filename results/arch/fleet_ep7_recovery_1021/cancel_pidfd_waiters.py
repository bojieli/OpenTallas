import os,json,time,signal,glob
from pathlib import Path
rows=json.loads(Path('/tmp/codex-ep7-obsolete-waiters-1021.json').read_text())['waiters']
report={'start':time.strftime('%Y-%m-%d %H:%M:%S %Z'),'cancelled':[],'preserved':[]}
assert hasattr(os,'pidfd_open') and hasattr(signal,'pidfd_send_signal')
for r in rows:
    if not r['eligible']:continue
    p=r['pid'];fd=None;stopped=False;cancelled=False
    try:
        fd=os.pidfd_open(p)
        a=Path(f'/proc/{p}/cmdline').read_text().split('\0')[:-1]
        start=Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()[19]
        if start!=r['start'] or a[1:2]!=['/usr/local/bin/ot-heavy'] or '--tag' not in a or a[a.index('--tag')+1]!=r['tag']:
            report['preserved'].append({'pid':p,'reason':'identity changed'});continue
        signal.pidfd_send_signal(fd,signal.SIGSTOP);stopped=True
        for _ in range(100):
            if Path(f'/proc/{p}/stat').read_text().rsplit(')',1)[1].split()[0]=='T':break
            time.sleep(.001)
        else:raise RuntimeError('launcher did not stop')
        # With launcher stopped, it cannot execute admission or a build.
        # Re-read identity and scope/reservation proof after stopping.
        a=Path(f'/proc/{p}/cmdline').read_text().split('\0')[:-1]
        cg=Path(f'/proc/{p}/cgroup').read_text()
        if (a[1:2]!=['/usr/local/bin/ot-heavy'] or '--tag' not in a or a[a.index('--tag')+1]!=r['tag'] or
            os.readlink(f'/proc/{p}/cwd')!=r['cwd'] or '/oth-' in cg or
            glob.glob(f'/var/tmp/ot-heavy/res.oth-ubuntu-{p}-*')):
            report['preserved'].append({'pid':p,'reason':'admitted/reserved/changed after pause'});continue
        kids=Path(f'/proc/{p}/task/{p}/children').read_text().split();flocks=[]
        for child in r['flock_children']:
            k=child['pid']
            if str(k) in kids and Path(f'/proc/{k}/stat').read_text().rsplit(')',1)[1].split()[19]==child['start'] and Path(f'/proc/{k}/comm').read_text().strip()=='flock':
                cfd=os.pidfd_open(k);flocks.append((k,cfd))
        if not flocks:
            report['preserved'].append({'pid':p,'reason':'no proven flock child; resumed'});continue
        signal.pidfd_send_signal(fd,signal.SIGKILL);cancelled=True
        for k,cfd in flocks:
            try:signal.pidfd_send_signal(cfd,signal.SIGTERM)
            except ProcessLookupError:pass
            finally:os.close(cfd)
        report['cancelled'].append({'pid':p,'tag':r['tag'],'flock_children':[k for k,_ in flocks],'cwd':r['cwd'],'proof':'stopped exact ot-heavy; no reservation; not admitted scope; exact flock child'})
    except (OSError,ValueError,IndexError,RuntimeError) as e:
        report['preserved'].append({'pid':p,'reason':str(e)})
    finally:
        if fd is not None:
            if stopped and not cancelled:
                try:signal.pidfd_send_signal(fd,signal.SIGCONT)
                except ProcessLookupError:pass
            os.close(fd)
report['end']=time.strftime('%Y-%m-%d %H:%M:%S %Z')
Path('/tmp/codex-ep7-pidfd-cancel-report-1021.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'cancelled':len(report['cancelled']),'preserved':len(report['preserved']),'start':report['start'],'end':report['end']}))
