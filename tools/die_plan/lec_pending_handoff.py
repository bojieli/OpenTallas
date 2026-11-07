"""Opt-in v1 transport of an UNADMITTED LEC child; the original watcher owns the verdict.

Legacy watchers are rejected. This API never launches physical work, changes a
proof command, or imports a proof into a different source/netlist identity.
The controller stages the COMPLETE kit and runs `worker` through normal ot-run.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
import uuid

VERSION = 'opentallas.pending_lec_handoff.v1'
STATE = 'lec_async.handoff.json'
PACKET = 'lec_async.handoff.packet.json'
RESULT = 'lec_async.handoff.result.json'


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    return h.hexdigest()


def digest(x):
    return hashlib.sha256(json.dumps(x, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def atomic(p, x):
    p = Path(p); tmp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.tmp')
    tmp.write_text(json.dumps(x, sort_keys=True, indent=2) + '\n'); os.replace(tmp, p)


def proc(pid):
    p = Path('/proc') / str(pid)
    fields = (p / 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(pid=int(pid), ppid=int(fields[1]), ticks=int(fields[11])+int(fields[12]),
                start=int(fields[19]), argv=(p/'cmdline').read_bytes().decode().split('\0')[:-1])


def host():
    return socket.gethostname()


def proof_env():
    return {k: v for k, v in os.environ.items() if k.startswith('OT_LEC_') and
            k not in ('OT_LEC_ASYNC', 'OT_LEC_ASYNC_POLL', 'OT_LEC_MEM_GB', 'OT_LEC_HANDOFF')}


def identity(k, mode, env):
    e = {a: b for a, b in os.environ.items() if not a.startswith('OT_LEC_')}; e.update(env)
    return subprocess.check_output(['bash', str(k/'lec_async.sh'), 'identity', str(k), mode], env=e, text=True).strip()


def snapshot(k, env):
    # A complete staged cohort is mandatory; reject external file aliases.
    names=('lec.py','lec_async.sh','lec_pending_handoff.py','config.mk','freeze.json',
           'lec_options.json','lec_hints.json','reset_contract.json','lec_async.ready',
           'core.json','constraint.sdc','straps.json','sdc_lint.json','pins.json',
           'lec_native_stub_metadata.json','native_stub_metadata.py')
    paths=[k/n for n in names if (k/n).is_file()]
    paths += [p for p in (k/'rtl').rglob('*') if p.is_file()]
    metadata={n:sha(k/n) if (k/n).is_file() else None for n in
              ('core.json','constraint.sdc','straps.json','sdc_lint.json','pins.json',
           'lec_native_stub_metadata.json','native_stub_metadata.py')}
    if any((k/n).is_symlink() for n in metadata):raise ValueError('typed metadata alias needs explicit closure')
    import shlex, re
    freeze=read(k/'freeze.json')
    for row in freeze.get('runtime_files',[]): paths.append(k/row['destination'])
    for line in (k/'config.mk').read_text().splitlines():
        if re.match(r'^(?:override )?export (?:VERILOG_FILES|ADDITIONAL_LIBS|TC_LIB_FILES)\s*=',line):
            for value in shlex.split(line.split('=',1)[1]):
                if value=='$(TC_NLDM_LIB_FILES)':continue # standard cells are image-owned
                if '$' in value:raise ValueError('explicit proof file requires resolved closure: '+value)
                if value.startswith('/OpenROAD-flow-scripts/'):continue # covered by exact image ID
                if value.startswith('/work/'):paths.append(k/value[6:])
                elif not Path(value).is_absolute():paths.append(k/value)
                else:raise ValueError('external proof file requires explicit closure: '+value)
    cmd = shlex.split('\n'.join((k/'lec_async.ready').read_text().splitlines()[1:]))
    net = cmd[cmd.index('--netlist')+1]
    if not net.startswith('/work/'): raise ValueError('netlist is not kit-local')
    paths.append(k/net[6:])
    if (k/'reset_contract.json').is_file():
        receipt = read(k/'reset_contract.json').get('proof',{}).get('receipt')
        if receipt: paths.append(k/(receipt[6:] if receipt.startswith('/work/') else receipt))
    rows = {}
    for p in paths:
        p.resolve().relative_to(k.resolve())
        if p.is_symlink(): raise ValueError('proof input symlink needs explicit closure: '+str(p))
        rows[str(p.relative_to(k))] = sha(p)
    for n in ('lec.py','lec_async.sh','lec_pending_handoff.py','config.mk','lec_async.ready'):
        if n not in rows: raise ValueError('missing protocol/proof input '+n)
    return dict(source=identity(k,'source',env), proof=identity(k,'all',env), files=rows, netlist=net, metadata=metadata)


def validate(k, packet):
    if packet.get('schema') != VERSION: raise ValueError('unsupported handoff protocol')
    if snapshot(k, packet['env']) != packet['fingerprint']: raise ValueError('proof input identity changed')


def register(k, watcher, child, owner, image, mem, cpus):
    if os.environ.get('OT_LEC_HANDOFF') != '1': raise ValueError('handoff is opt-in')
    w, c = proc(watcher), proc(child)
    if c['ppid'] != w['pid']: raise ValueError('not this watcher child')
    env = proof_env(); fp = snapshot(k,env)
    if (k/'lec_async.source_identity').read_text().strip()!=fp['source'] or (k/'lec_async.identity').read_text().strip()!=fp['proof']:
        raise ValueError('captured watcher identity differs')
    image_id=subprocess.check_output(['docker','image','inspect','-f','{{.Id}}',image],text=True).strip()
    state = dict(schema=VERSION, phase='queued', source_host=host(), watcher=w,
                 child=c, owner=owner, image=image, image_id=image_id, mem=int(mem), cpus=int(cpus),
                 env=env, fingerprint=fp, registered=time.time(), token=uuid.uuid4().hex)
    atomic(k/STATE,state)


def request(k, dest_host, dest_kit):
    s = read(k/STATE)
    if s.get('schema') != VERSION or s.get('phase') != 'queued': raise ValueError('not a v1 queued watcher')
    if s['source_host'] != host(): raise ValueError('request must run on bound source host')
    if not dest_host or not Path(dest_kit).is_absolute(): raise ValueError('explicit canonical destination host/path required')
    if proc(s['watcher']['pid'])['start'] != s['watcher']['start']: raise ValueError('watcher PID identity changed')
    validate(k,s)
    atomic(k/'lec_async.handoff.request.json',dict(token=s['token'],host=dest_host,kit=dest_kit,
           observed=time.time(),child=proc(s['child']['pid'])))


def accept(k, watcher, child, *, min_age=7200, flat_seconds=60, lock='/var/tmp/ot-heavy/admit.lock'):
    s = read(k/STATE); r = read(k/'lec_async.handoff.request.json')
    if s['source_host'] != host() or int(watcher) != s['watcher']['pid']: raise ValueError('wrong source watcher host/PID')
    if proc(watcher)['start'] != s['watcher']['start'] or int(child) != s['child']['pid']: raise ValueError('watcher/child identity changed')
    if r['token'] != s['token'] or s['phase'] != 'queued': raise ValueError('wrong request/session')
    validate(k,s)
    with open(lock,'a') as lease:
        fcntl.flock(lease,fcntl.LOCK_EX)
        c=proc(child)
        if c['start'] != s['child']['start'] or c['ppid'] != int(watcher): raise ValueError('child PID reused/reparented')
        if not any(Path(a).name == 'ot-heavy' for a in c['argv'][:3]): raise ValueError('not an ot-heavy waiter')
        age=float(Path('/proc/uptime').read_text().split()[0])-c['start']/os.sysconf('SC_CLK_TCK')
        if age < min_age or time.time()-r['observed'] < flat_seconds or c['ticks'] != r['child']['ticks']:
            raise ValueError('requires 2h unstarted + flat CPU observation')
        if list(Path(lock).parent.glob('res.oth-*-'+str(child)+'-*')):
            raise ValueError('child already admitted; live proofs never migrate')
        running=subprocess.run(['docker','inspect','-f','{{.State.Running}}',s['owner']+'-lec'],capture_output=True,text=True,timeout=5)
        if running.returncode==0 and running.stdout.strip()=='true': raise ValueError('proof container already running')
        # Admission cannot race this test/cancel: ot-heavy uses this exact lock.
        os.kill(int(child),signal.SIGTERM)
        s.update(phase='exported',destination_host=r['host'],destination_kit=r['kit'],exported=time.time())
        atomic(k/PACKET,s); atomic(k/STATE,s)
    return s


def worker(k, packet_path):
    p=read(packet_path)
    if p['destination_host'] != host() or str(k.resolve()) != p['destination_kit']:
        raise ValueError('destination host/path binding differs')
    validate(k,p)
    actual_image=subprocess.check_output(['docker','image','inspect','-f','{{.Id}}',p['image']],text=True).strip()
    if actual_image!=p['image_id']:raise ValueError('proof tool image changed')
    if (k/'lec/lec.json').exists(): raise ValueError('worker requires an unstarted proof')
    scope=Path('/proc/self/cgroup').read_text()
    if 'oth-' not in scope:raise ValueError('worker requires a normal admitted ot-heavy scope')
    cmd='\n'.join((k/'lec_async.ready').read_text().splitlines()[1:])
    envargs=[x for a,b in sorted(p['env'].items()) for x in ('-e',a+'='+b)]
    run=['docker','run','--rm','--memory='+str(p['mem'])+'g','--memory-swap='+str(p['mem'])+'g',
         '--cpus='+str(p['cpus']),'-v',str(k)+':/work']+envargs+['--entrypoint','bash',p['image_id'],'-lc',
         'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; ( '+cmd+' ); r=$?; chown -R '+str(os.getuid())+':'+str(os.getgid())+' /work/lec 2>/dev/null; exit $r']
    with open(k/'lec_handoff_worker.log','xb') as log:
        rc=subprocess.run(run,stdout=log,stderr=subprocess.STDOUT).returncode
    validate(k,p)
    report=k/'lec/lec.json'
    result=dict(schema=VERSION,packet_sha=digest(p),host=host(),kit=str(k.resolve()),rc=rc,worker_pid=os.getpid(),worker_scope=scope,
                report_sha=sha(report) if report.is_file() else None,finished=time.time())
    atomic(k/RESULT,result)
    return rc


def import_result(k, completed):
    s=read(k/STATE); p=read(k/PACKET); r=read(completed/RESULT)
    if s.get('phase') != 'exported' or s['source_host'] != host(): raise ValueError('not original bound exported watcher')
    if proc(s['watcher']['pid'])['start'] != s['watcher']['start']: raise ValueError('original watcher no longer alive')
    if p != s: raise ValueError('exported watcher session differs')
    if r.get('schema') != VERSION or r['packet_sha'] != digest(p): raise ValueError('result session identity differs')
    if r['host'] != p['destination_host'] or r['kit'] != p['destination_kit']: raise ValueError('result host/path binding differs')
    validate(k,p);validate(completed,p)
    if not r['report_sha']:
        if r['rc']==0: raise ValueError('zero exit without actual LEC receipt')
        # Tool/transport failures are terminal NO VERDICT, never a guessed proof.
        r=dict(r,original_rc=r['rc'],rc=143,result_class='NO_VERDICT')
        (k/'lec_async.unit_rc').write_text('143\n')
        atomic(k/'lec_async.handoff.returned.json',r)
        s['phase']='returned';atomic(k/STATE,s)
        return
    if sha(completed/'lec/lec.json') != r['report_sha']: raise ValueError('changed actual LEC receipt')
    report=read(completed/'lec/lec.json')
    if report.get('netlist') != p['fingerprint']['netlist']: raise ValueError('receipt netlist differs')
    if r['rc']==0 and report.get('verdict') != 'EQUIVALENT': raise ValueError('zero exit without equivalent receipt')
    if (k/'lec/lec.json').exists(): raise ValueError('original already has a proof verdict; never overwrite')
    for f in (completed/'lec').rglob('*'):
        if f.is_file():
            d=k/'lec'/f.relative_to(completed/'lec');d.parent.mkdir(parents=True,exist_ok=True)
            if d.exists() and sha(d)!=sha(f): raise ValueError('existing proof artifact differs')
            if not d.exists(): shutil.copy2(f,d)
    (k/'lec_async.unit_rc').write_text(str(r['rc'])+'\n')
    atomic(k/'lec_async.handoff.returned.json',r)
    s['phase']='returned';atomic(k/STATE,s)


def main():
    ap=argparse.ArgumentParser(description=__doc__);sp=ap.add_subparsers(dest='cmd',required=True)
    for name in ('register','request','accept','worker','import-result','result-rc'):
        q=sp.add_parser(name);q.add_argument('kit',type=Path)
        if name=='register':
            for n in ('watcher','child','owner','image','mem','cpus'):q.add_argument(n)
        if name=='request':q.add_argument('dest_host');q.add_argument('dest_kit')
        if name=='accept':q.add_argument('watcher');q.add_argument('child')
        if name=='worker':q.add_argument('packet',type=Path)
        if name=='import-result':q.add_argument('completed',type=Path)
    a=ap.parse_args();kw=vars(a).copy();cmd=kw.pop('cmd');k=kw.pop('kit').resolve()
    try:
        if cmd=='register':register(k,**kw)
        elif cmd=='request':request(k,**kw)
        elif cmd=='accept':accept(k,**kw)
        elif cmd=='worker':return worker(k,kw['packet'])
        elif cmd=='result-rc':
            s=read(k/STATE);r=read(k/'lec_async.handoff.returned.json')
            if s['phase']!='returned' or s['source_host']!=host() or r['packet_sha']!=digest(read(k/PACKET)):raise ValueError('remote result not ready')
            validate(k,s);print(r['rc'])
        else:import_result(k,kw['completed'])
    except Exception as e:print('LEC_HANDOFF_REFUSED '+str(e),file=__import__('sys').stderr);return 11
    return 0

if __name__=='__main__':raise SystemExit(main())
