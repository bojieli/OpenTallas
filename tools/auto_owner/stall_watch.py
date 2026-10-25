#!/usr/bin/env python3
"""stall_watch.py -- REPORT-ONLY stall watchdog for running fleet jobs (coordinator 2026-10-25).

Runs on the ot-run hub (epyc1) from a systemd --user timer every 15 min.  It kills nothing, submits nothing and writes
exactly one file: <coord>/STALLS.txt (default ~/coord/STALLS.txt; the rtx-pro crontab rsync copies it next to
TASK_WATCH_SUMMARY.txt into the live coordination dir).

What is a job
  * every running ot-heavy unit (systemd --user scope `oth-*`) on every fleet host, and
  * every running docker container (ORFS/OpenROAD runs started by ot-run jobs or directly as probes).
  A scope that started named containers (`docker run --name X`) is reported once, with the containers' evidence.

What is its log
  * container: the newest file under its read-write bind mounts (ORFS run/logs/asap7/*/* first, then the mount, depth-
    and count-bounded walk, .git skipped);
  * scope: the newest regular file its processes hold open for writing; if none (stdout is an ssh pipe back to the
    caller), the newest file under the processes' working directories (bounded walk).
  idle = now - max(newest log mtime, job start).

Verdicts
  STALLED  idle > --idle-min (90) minutes, or > --drt-idle-min (180) when the job is in detailed route (DRT): newest
           ORFS log is 5_2_route*, or its tail has DRT- messages.
  RUNAWAY  (INFO, not a stall) the log still grows but one ORFS stage has run > --stage-hours (6) h; e.g. GRT FF-hold
           repair inserting 2 buffers per iteration for 11 h.
Lane/owner guess: the /srv/opentallas-scratch*/claude/<dir>/ component (wt/<dir> too) mapped to a lane file under
<coord>/lanes/ (exact, then shortened prefixes; codex-* -> CODEX).

Usage: stall_watch.py [--coord DIR] [--hosts h1,h2] [--out FILE] [--stdout] [--json FILE]
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

DEFAULT_HOSTS = ['localhost', 'epyc2', 'epyc3', 'intel1', 'intel2']
LOCAL_NAME = 'epyc1'

PROBE = r'''
import os, re, json, time, subprocess
now = time.time()
MAXN = 40000
def walk_newest(root, maxdepth=5, maxn=MAXN):
    best = (0.0, None); n = 0
    root = root.rstrip('/') or '/'
    base = root.count('/')
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in ('.git', '__pycache__', 'node_modules', 'proc', 'sys')]
        if dp.count('/') - base >= maxdepth:
            dns[:] = []
        for f in fns:
            n += 1
            if n > maxn:
                return best
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if st.st_mtime > best[0] and st.st_mtime <= now + 60:
                best = (st.st_mtime, p)
    return best
def orfs_logdirs(root):
    out = []
    for sub in ('run/logs/asap7', 'logs/asap7', 'work/logs/asap7', 'orfs/logs/asap7'):
        d = os.path.join(root, sub)
        if os.path.isdir(d):
            for design in os.listdir(d):
                dd = os.path.join(d, design)
                if os.path.isdir(dd):
                    for v in os.listdir(dd):
                        if os.path.isdir(os.path.join(dd, v)):
                            out.append(os.path.join(dd, v))
    return out
def orfs_state(ld):
    logs = []
    for f in os.listdir(ld):
        if f.endswith('.log'):
            try:
                logs.append((os.stat(os.path.join(ld, f)).st_mtime, f))
            except OSError:
                pass
    if not logs:
        return None
    logs.sort()
    mt, f = logs[-1]
    prev = [m for m, g in logs if g != f and not g.endswith('.tmp.log')]
    stage_start = max(prev) if prev else None
    tail = ''
    try:
        with open(os.path.join(ld, f), 'rb') as fh:
            fh.seek(0, 2); sz = fh.tell(); fh.seek(max(0, sz - 4096)); tail = fh.read().decode('utf-8', 'replace')
    except OSError:
        pass
    lines = [l.strip() for l in tail.splitlines() if l.strip()]
    return {'log': os.path.join(ld, f), 'mtime': mt, 'stage': f[:-4], 'stage_start': stage_start,
            'running': f.endswith('.tmp.log'), 'drt': f.startswith('5_2_route') or 'DRT-' in tail,
            'last': lines[-1][:160] if lines else ''}
def evidence(roots):
    ev = {'mtime': 0.0, 'log': None, 'orfs': None}
    for r in roots:
        if not os.path.isdir(r):
            continue
        for ld in orfs_logdirs(r):
            st = orfs_state(ld)
            if st and (ev['orfs'] is None or st['mtime'] > ev['orfs']['mtime']):
                ev['orfs'] = st
        mt, p = walk_newest(r)
        if mt > ev['mtime']:
            ev['mtime'], ev['log'] = mt, p
    if ev['orfs'] and ev['orfs']['mtime'] >= ev['mtime'] - 1:
        ev['mtime'], ev['log'] = ev['orfs']['mtime'], ev['orfs']['log']
    return ev
res = {'host': os.uname().nodename, 'now': now, 'scopes': [], 'containers': [], 'errors': []}
# containers
conts = {}
try:
    ids = subprocess.run(['docker', 'ps', '-q', '--no-trunc'], capture_output=True, text=True, timeout=60).stdout.split()
    if ids:
        for c in json.loads(subprocess.run(['docker', 'inspect'] + ids, capture_output=True, text=True, timeout=120).stdout or '[]'):
            name = c.get('Name', '').lstrip('/')
            st = c.get('State', {}).get('StartedAt', '')
            try:
                import datetime
                t0 = datetime.datetime.fromisoformat(st[:26].rstrip('Z') + '+00:00' if st.endswith('Z') else st[:26]).timestamp()
            except Exception:
                t0 = None
            binds = [m['Source'] for m in c.get('Mounts', []) if m.get('Type') == 'bind' and m.get('RW', True)
                     and not m['Source'].startswith(('/tmp/.X11', '/var/run', '/run', '/etc', '/dev', '/sys', '/proc'))
                     and m['Source'] not in ('/', '/home', '/home/ubuntu', '/srv')]
            conts[name] = {'name': name, 'start': t0, 'image': c.get('Config', {}).get('Image', ''), 'binds': binds}
except Exception as e:
    res['errors'].append('docker: %s' % e)
for c in conts.values():
    c['ev'] = evidence(c['binds'])
    res['containers'].append(c)
# ot-heavy scopes
try:
    out = subprocess.run(['systemctl', '--user', 'list-units', 'oth-*', '--plain', '--no-legend', '--state=running'],
                         capture_output=True, text=True, timeout=60).stdout
    units = [l.split()[0] for l in out.splitlines() if l.strip()]
except Exception as e:
    units = []; res['errors'].append('systemctl: %s' % e)
props = {}
if units:
    out = subprocess.run(['systemctl', '--user', 'show', '-p', 'Id,ControlGroup,ActiveEnterTimestamp'] + units,
                         capture_output=True, text=True, timeout=120).stdout
    cur = {}
    for l in out.splitlines() + ['']:
        if not l.strip():
            if cur.get('Id'):
                props[cur['Id']] = cur
            cur = {}
            continue
        k, _, v = l.partition('=')
        cur[k] = v
for u in units:
    p = props.get(u, {})
    cg = p.get('ControlGroup', '')
    pids = []
    try:
        pids = [int(x) for x in open('/sys/fs/cgroup' + cg + '/cgroup.procs').read().split()]
    except Exception:
        pass
    t0 = None
    try:
        t0 = time.mktime(time.strptime(' '.join(p.get('ActiveEnterTimestamp', '').split()[1:3]), '%Y-%m-%d %H:%M:%S'))
    except Exception:
        pass
    cmd = ''; cwds = set(); wfiles = []; names = []; unnamed_docker = False
    for pid in pids:
        try:
            argv = open('/proc/%d/cmdline' % pid, 'rb').read().split(b'\0')
            argv = [a.decode('utf-8', 'replace') for a in argv if a]
        except OSError:
            continue
        s = ' '.join(argv)
        if 'ot-heavy' not in s and not s.startswith('systemd-run') and len(s) > len(cmd):
            cmd = s
        if argv and os.path.basename(argv[0]) == 'docker' and 'run' in argv:
            if '--name' in argv:
                i = argv.index('--name')
                if i + 1 < len(argv):
                    names.append(argv[i + 1])
            else:
                nm = [a[7:] for a in argv if a.startswith('--name=')]
                names += nm
                unnamed_docker = unnamed_docker or not nm
        try:
            cwds.add(os.readlink('/proc/%d/cwd' % pid))
        except OSError:
            pass
        try:
            for fd in os.listdir('/proc/%d/fd' % pid):
                try:
                    tgt = os.readlink('/proc/%d/fd/%s' % (pid, fd))
                    if not tgt.startswith('/') or tgt.startswith(('/dev/', '/proc/', '/sys/', '/memfd')):
                        continue
                    fl = 0
                    for l in open('/proc/%d/fdinfo/%s' % (pid, fd)):
                        if l.startswith('flags:'):
                            fl = int(l.split()[1], 8)
                    if fl & 3 and os.path.isfile(tgt):
                        wfiles.append(tgt)
                except OSError:
                    continue
        except OSError:
            pass
    ev = {'mtime': 0.0, 'log': None, 'orfs': None}
    for f in set(wfiles):
        try:
            m = os.stat(f).st_mtime
        except OSError:
            continue
        if m > ev['mtime']:
            ev['mtime'], ev['log'] = m, f
    roots = [c for c in cwds if c not in ('/', '/home/ubuntu', '/tmp', '/srv') and not c.startswith('/proc')]
    ev2 = evidence(roots)
    if ev2['orfs']:
        ev['orfs'] = ev2['orfs']
    if ev2['mtime'] > ev['mtime']:
        ev['mtime'], ev['log'] = ev2['mtime'], ev2['log']
    res['scopes'].append({'unit': u, 'start': t0, 'cmd': cmd[:400], 'cwds': sorted(cwds)[:4], 'containers': names,
                          'unnamed_docker': unnamed_docker, 'npids': len(pids), 'ev': ev})
print(json.dumps(res))
'''


def run_probe(host, timeout):
    cmd = ['python3', '-I', '-'] if host == 'localhost' else \
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none', host, 'nice', '-n', '10', 'python3', '-I', '-']
    try:
        p = subprocess.run(cmd, input=PROBE, capture_output=True, text=True, timeout=timeout)
        if p.returncode != 0 or not p.stdout.strip():
            return host, None, 'rc %s: %s' % (p.returncode, (p.stderr.strip().splitlines() or [''])[-1][:200])
        return host, json.loads(p.stdout.strip().splitlines()[-1]), None
    except subprocess.TimeoutExpired:
        return host, None, 'probe timeout %d s' % timeout
    except Exception as e:  # noqa
        return host, None, str(e)[:200]


LANE_RX = re.compile(r'/srv/opentallas-scratch2?/(?:claude|codex)/(?:wt/|moved/)?([A-Za-z0-9][A-Za-z0-9_.+\-]*)')


def lane_guess(paths, lanes):
    for p in paths:
        if not p:
            continue
        m = LANE_RX.search(p)
        if not m:
            m2 = re.search(r'/home/ubuntu/(?:wt|ot-scratch)/([A-Za-z0-9][A-Za-z0-9_.+\-]*)', p)
            if not m2:
                continue
            m = m2
        d = m.group(1)
        if d.startswith('codex'):
            return 'CODEX', d
        parts = re.split(r'[-_]', d.upper())
        for n in range(len(parts), 0, -1):
            cand = '-'.join(parts[:n])
            if cand in lanes:
                return cand, d
        alias = {'KV-CORES': 'KVG3-CORES', 'KVCORES': 'KVG3-CORES', 'S81-KITS': 'S81-CORES', 'HBM-HC': 'ELEM-HBM',
                 'HBM': 'HBM-ARCH', 'QC': 'QC-A0', 'KV': 'KV-G3', 'ELEM-S81-ST405': 'ELEM-S81', 'PROTO-CORES': 'PROTO',
                 'S81-H23': 'S81-HEAD', 'S81-HEAD2': 'S81-HEAD', 'S81-IR': 'S81', 'FP32S': 'FP32'}
        for n in range(len(parts), 0, -1):
            cand = '-'.join(parts[:n])
            if cand in alias:
                return alias[cand], d
        return '?', d
    return '?', '-'


def hm(sec):
    if sec is None:
        return '-'
    m = int(sec // 60)
    return '%dh%02d' % (m // 60, m % 60) if m >= 60 else '%dm' % m


def analyse(probes, lanes, a, now):
    rows = []
    for host, r in probes.items():
        if not r:
            continue
        hn = LOCAL_NAME if host == 'localhost' else host
        cont = {c['name']: c for c in r['containers']}
        claimed = set()
        jobs = []
        for s in r['scopes']:
            evs = [cont[n] for n in s['containers'] if n in cont]
            claimed.update(c['name'] for c in evs)
            ev = s['ev']
            for c in evs:  # a scope driving containers: the containers' logs are the evidence
                if c['ev']['mtime'] > ev['mtime'] or (c['ev']['orfs'] and not ev.get('orfs')):
                    ev = dict(c['ev']) if c['ev']['mtime'] >= ev['mtime'] else dict(ev, orfs=c['ev']['orfs'])
            paths = [ev.get('log')] + s['cwds'] + [b for c in evs for b in c['binds']] + [s['cmd']]
            jobs.append({'kind': 'ot-run', 'id': s['unit'] + (' [' + ','.join(c['name'] for c in evs) + ']' if evs else ''),
                         'start': s['start'], 'ev': ev, 'paths': paths, 'cmd': s['cmd'],
                         'note': 'docker run w/o --name: container reported separately' if s['unnamed_docker'] and not evs else ''})
        for c in r['containers']:
            if c['name'] in claimed:
                continue
            jobs.append({'kind': 'docker', 'id': c['name'], 'start': c['start'], 'ev': c['ev'], 'paths': [c['ev'].get('log')] + c['binds'],
                         'cmd': c['image'], 'note': '' if c['binds'] else 'no RW bind mount: no log visible'})
        for j in jobs:
            ev = j['ev']; o = ev.get('orfs') or {}
            start = j['start'] or now
            last = max(ev['mtime'] or 0, start)
            idle = max(0.0, now - last)
            drt = bool(o.get('drt')) and o.get('log') == ev.get('log')
            lim = (a.drt_idle_min if drt else a.idle_min) * 60
            lane, d = lane_guess(j['paths'], lanes)
            if o.get('log'):  # the ORFS run's kit dir (a wrapper's own log may name a sibling kit)
                run = o['log'].split('/logs/asap7/')[0]
                run = run[:-4] if run.endswith('/run') else run
            else:
                run = next((p for p in j['paths'] if p and '/srv/' in p), j['paths'][0] if j['paths'] else '')
            row = {'host': hn, 'kind': j['kind'], 'id': j['id'], 'lane': lane, 'dir': d, 'stage': o.get('stage', '-'),
                   'drt': drt, 'idle_s': idle, 'age_s': now - start if j['start'] else None, 'log': ev.get('log') or '-',
                   'run': run or '-', 'last': o.get('last', ''), 'note': j['note'], 'cmd': j['cmd'][:160]}
            if idle > lim:
                row['verdict'] = 'STALLED'
            elif o.get('running') and o.get('stage_start') and now - o['stage_start'] > a.stage_hours * 3600 and idle < lim:
                row['verdict'] = 'RUNAWAY'; row['stage_age_s'] = now - o['stage_start']
            else:
                row['verdict'] = 'OK'
            rows.append(row)
    return rows


def render(rows, probes, errs, a, now):
    ts = time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now))
    st = sorted([r for r in rows if r['verdict'] == 'STALLED'], key=lambda r: -r['idle_s'])
    ra = sorted([r for r in rows if r['verdict'] == 'RUNAWAY'], key=lambda r: -r['stage_age_s'])
    out = ['# STALLS -- stall_watch.py (report only; nothing is killed) generated %s on %s' % (ts, LOCAL_NAME),
           '# STALLED = log not grown for > %d min (> %d min in DRT); RUNAWAY (info) = log grows but one ORFS stage > %g h'
           % (a.idle_min, a.drt_idle_min, a.stage_hours),
           '# hosts: ' + '; '.join('%s %s' % (LOCAL_NAME if h == 'localhost' else h,
                                             ('ok %d scopes %d containers' % (len(r['scopes']), len(r['containers']))) if r else 'PROBE FAILED: ' + errs.get(h, '?'))
                                  for h, r in probes.items()),
           '# jobs: %d running, %d STALLED, %d RUNAWAY' % (len(rows), len(st), len(ra)), '']
    out.append('STALLED %d' % len(st))
    for r in st:
        out.append('  %-7s %-5s idle %-6s age %-6s lane %-11s stage %-22s %s' % (
            r['host'], 'DRT' if r['drt'] else '', hm(r['idle_s']), hm(r['age_s']), r['lane'], r['stage'][:22], r['id'][:110]))
        out.append('          run %s' % r['run'])
        out.append('          log %s' % r['log'])
        if r['last']:
            out.append('          last: %s' % r['last'][:150])
        if r['note']:
            out.append('          note: %s' % r['note'])
        if r['kind'] == 'ot-run' and r['cmd']:
            out.append('          cmd: %s' % r['cmd'][:150])
    out += ['', 'RUNAWAY %d (info: still logging, one stage > %g h)' % (len(ra), a.stage_hours)]
    for r in ra:
        out.append('  %-7s stage %-18s %-6s (idle %s) lane %-11s %s' % (r['host'], r['stage'][:18], hm(r['stage_age_s']),
                                                                     hm(r['idle_s']), r['lane'], r['id'][:100]))
        out.append('          run %s' % r['run'])
        if r['last']:
            out.append('          last: %s' % r['last'][:150])
    return '\n'.join(out) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--coord', default=os.environ.get('OT_COORD_DIR', os.path.expanduser('~/coord')))
    ap.add_argument('--hosts', default=','.join(DEFAULT_HOSTS))
    ap.add_argument('--out', default=None, help='default <coord>/STALLS.txt')
    ap.add_argument('--stdout', action='store_true', help='print, do not write')
    ap.add_argument('--json', default=None, help='also dump the rows as JSON to this path (testing)')
    ap.add_argument('--idle-min', type=float, default=90)
    ap.add_argument('--drt-idle-min', type=float, default=180)
    ap.add_argument('--stage-hours', type=float, default=6)
    ap.add_argument('--timeout', type=int, default=240)
    a = ap.parse_args(argv)
    hosts = [h for h in a.hosts.split(',') if h]
    lanes = set()
    ld = os.path.join(a.coord, 'lanes')
    if os.path.isdir(ld):
        lanes = {f[:-3] for f in os.listdir(ld) if f.endswith('.md') and not f.startswith('_')}
    now = time.time()
    probes, errs = {}, {}
    with ThreadPoolExecutor(len(hosts)) as ex:
        for h, r, e in ex.map(lambda h: run_probe(h, a.timeout), hosts):
            probes[h] = r
            if e:
                errs[h] = e
    rows = analyse(probes, lanes, a, now)
    text = render(rows, probes, errs, a, now)
    if a.json:
        with open(a.json, 'w') as f:
            json.dump(rows, f, indent=1, default=str)
    if a.stdout:
        sys.stdout.write(text)
        return 0
    out = a.out or os.path.join(a.coord, 'STALLS.txt')
    tmp = out + '.tmp.%d' % os.getpid()
    with open(tmp, 'w') as f:
        f.write(text)
    os.replace(tmp, out)
    print('stall_watch: %d jobs, %s -> %s' % (len(rows), text.splitlines()[3][2:], out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
