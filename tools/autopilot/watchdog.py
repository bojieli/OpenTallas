#!/usr/bin/env python3
"""watchdog.py -- HUNG-JOB WATCHDOG (OWNER 12.22 item 1, 2026-10-30; lane WATCHDOG-1).

Rule: an OpenROAD place / CTS / GRT / DRT / route step (ot-run scopes and lane docker runs on intel1, intel2, epyc2)
whose log has not been written for 2 h is stopped (that exact systemd scope / container only, never pkill) and relaunched
ONCE with the same command in the same directory.  The relaunch resumes from the last checkpoint because the command is
the job's own: an ORFS `make ... do-<stage>` / `make <target>` restarts at the first stage whose .odb is missing (the
hung stage), a script re-reads its own input odb.  A second hang of the same kit -> a FIX line to the owning lane file and
to COORD-REVIEW-QUEUE.md; no third launch.

Detection reuses tools/auto_owner/stall_watch.py (same probe, same "newest log" evidence: ORFS stage log first, else the
newest file under the job's RW mounts / cwd).  Log mtime is the only progress signal; runtime never is, so a long step
that still logs (stall_watch RUNAWAY) is never touched.

Verdicts (one line per job idle >= --idle-min, default 120 min):
  ACT        in scope, owner may be relaunched: stop + relaunch (only with --act; dry-run prints "would")
  FIX        in scope, this kit was already relaunched once by the watchdog and hung again: stop, FIX line, no relaunch
  STOP       in scope, matched a 'stop-only' line of WATCHDOG.skip (COORD/owner: e.g. a kit on a block the pending
             QC/HBM plan change touches, OWNER 12.22 item 4): stop, note to the lane, no relaunch
  REPORT     hung but not acted on, with the reason: Codex-owned (COORD decides; OWNER 12.22 brief), run dir deleted,
             no OpenROAD process alive, no log file visible (stdout piped to the caller), step not place/CTS/GRT/DRT
             (e.g. yosys), listed in <coord>/autopilot/WATCHDOG.skip, or the fresh re-check found a newer log
Every --act action is appended to <coord>/autopilot/WATCHDOG.log; per-kit relaunch history in WATCHDOG.state.json.

Usage: watchdog.py [--act] [--hosts intel2,epyc2,intel1] [--idle-min 120] [--coord DIR] [--rows FILE.json]
"""
import argparse, json, os, re, shlex, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'auto_owner'))
import stall_watch  # noqa: E402

HUB = os.environ.get('OT_HUB_NAME', 'intel2')
stall_watch.LOCAL_NAME = HUB
DEFAULT_HOSTS = 'intel2,epyc2,intel1'

# ORFS stage names: 2_x floorplan/PDN (no), 3_x place, 4_x CTS, 5_x GRT/DRT/fill
ORFS_STEP = [(re.compile(r'^3_'), 'PLACE'), (re.compile(r'^4_'), 'CTS'), (re.compile(r'^5_1_grt'), 'GRT'),
             (re.compile(r'^5_2_route'), 'DRT'), (re.compile(r'^5_'), 'ROUTE')]
# OpenROAD message prefixes in a log tail (custom tcl scripts: die GRT, ECO DRT, ...)
TAIL_STEP = [('DRT-', 'DRT'), ('GRT-', 'GRT'), ('CTS-', 'CTS'), ('DPL-', 'PLACE'), ('GPL-', 'PLACE'),
             ('detailed_route', 'DRT'), ('global_route', 'GRT'), ('clock_tree_synthesis', 'CTS'),
             ('detailed_placement', 'PLACE'), ('global_placement', 'PLACE')]


def step_of(stage, log, tail):
    """the OpenROAD step a hung job sits in, or None when it is not place/CTS/GRT/DRT (synth, LEC, STA, ...)"""
    if stage and stage != '-':
        for rx, s in ORFS_STEP:
            if rx.match(stage):
                return s
        return None
    for tok, s in TAIL_STEP:
        if tok in (tail or ''):
            return s
    base = os.path.basename(log or '')
    for rx, s in ORFS_STEP:
        if rx.match(base):
            return s
    return None


def kit_key(row):
    """one key per kit: the ORFS run's kit dir (stall_watch 'run'), else the job's log dir"""
    run = row.get('run') or '-'
    if run in ('-', '') or run.endswith('(deleted)'):
        run = os.path.dirname(row.get('log') or '') or row['id']
    return '%s:%s' % (row['host'], run.rstrip('/'))


def load_skip(coord):
    """WATCHDOG.skip: one substring per line (kit dir, container or unit name); '#' comments.
    '<substr>'           a job known to be silent for > 2 h while progressing: report only (a lane adds its own line)
    'stop-only <substr>' COORD/owner: stop when hung, never relaunch"""
    p = os.path.join(coord, 'autopilot', 'WATCHDOG.skip')
    try:
        return [l.split('#')[0].strip() for l in open(p) if l.split('#')[0].strip()]
    except OSError:
        return []


def load_state(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return {}


def save_state(path, st):
    tmp = path + '.tmp.%d' % os.getpid()
    with open(tmp, 'w') as f:
        json.dump(st, f, indent=1, sort_keys=True)
    os.replace(tmp, path)


def classify(row, state, skip, idle_min, tail=''):
    """-> (verdict, step, reason) for a stall_watch row; None when the job is not idle >= idle_min.
    tail: the log's last 8 kB from the host re-check (custom OpenROAD scripts have no ORFS stage name)"""
    if row['idle_s'] < idle_min * 60:
        return None
    step = step_of(row.get('stage'), row.get('log'), (row.get('last') or '') + '\n' + (tail or ''))
    paths = ' '.join(str(x) for x in (row.get('id'), row.get('run'), row.get('log'), row.get('cmd')))
    if row.get('lane') == 'CODEX' or '/codex-' in paths or '[codex-' in paths:
        return 'REPORT', step, 'Codex-owned: report only (stop only if COORD says superseded)'
    if '(deleted)' in paths:
        return 'REPORT', step, 'run dir deleted: orphan, owner lane must clean up'
    if step is None:
        return 'REPORT', step, 'not a place/CTS/GRT/DRT step (stage %s)' % row.get('stage', '-')
    if not row.get('log') or row['log'] == '-':
        return 'REPORT', step, 'no log file visible (stdout piped to caller?)'
    for s in skip:
        if s.startswith('stop-only '):
            if s[10:].strip() in paths:
                return 'STOP', step, 'hung %s, stop-only in WATCHDOG.skip (%s): stop, no relaunch' % (
                    stall_watch.hm(row['idle_s']), s[10:].strip())
        elif s in paths:
            return 'REPORT', step, 'listed in WATCHDOG.skip (%s)' % s
    hist = state.get(kit_key(row), {}).get('relaunches', [])
    if hist:
        return 'FIX', step, 'second hang of this kit (relaunched %s): stop, FIX to lane, no relaunch' % hist[-1]['at']
    return 'ACT', step, 'hung %s: stop + relaunch once' % stall_watch.hm(row['idle_s'])


# ---------------------------------------------------------------- host side (runs on the job's host via ssh python3 -I -)
VERIFY = r'''
import json, os, subprocess, sys, time
a = json.loads(sys.argv[1]); now = time.time(); r = {'ok': True}
try:
    r['log_mtime'] = os.stat(a['log']).st_mtime
except OSError:
    r['log_mtime'] = None
try:
    with open(a['log'], 'rb') as fh:
        fh.seek(0, 2); fh.seek(max(0, fh.tell() - 8192)); r['tail'] = fh.read().decode('utf-8', 'replace')
except (OSError, TypeError):
    r['tail'] = ''
def procs_of_unit(u):
    cg = subprocess.run(['systemctl', '--user', 'show', '-p', 'ControlGroup', '--value', u], capture_output=True, text=True).stdout.strip()
    try:
        return [int(x) for x in open('/sys/fs/cgroup' + cg + '/cgroup.procs').read().split()]
    except Exception:
        return []
def argv(p):
    try:
        return [x.decode('utf-8', 'replace') for x in open('/proc/%d/cmdline' % p, 'rb').read().split(b'\0') if x]
    except OSError:
        return []
comms = []
if a.get('unit'):
    pids = procs_of_unit(a['unit'])
    r['unit_alive'] = bool(pids)
    pp = {}
    for p in pids:
        try:
            pp[p] = int(open('/proc/%d/stat' % p).read().rsplit(')', 1)[1].split()[1])
        except Exception:
            pass
        comms.append(' '.join(argv(p))[:200])
    roots = sorted(p for p in pids if pp.get(p) not in pids)
    roots = [p for p in roots if 'ot-heavy-exit' in ' '.join(argv(p)[:2])] + [p for p in roots if 'ot-heavy-exit' not in ' '.join(argv(p)[:2])]
    if roots:
        av = argv(roots[0])
        if len(av) > 2 and av[0].endswith('bash') and len(av) > 2 and av[1].endswith('ot-heavy-exit'):
            av = av[3:]
        elif av and av[0].endswith('ot-heavy-exit'):
            av = av[2:]
        r['argv'] = av
        try:
            r['cwd'] = os.readlink('/proc/%d/cwd' % roots[0])
            env = open('/proc/%d/environ' % roots[0], 'rb').read().split(b'\0')
            r['env'] = [e.decode('utf-8', 'replace') for e in env if e and b'=' in e]
        except OSError:
            pass
    mm = subprocess.run(['systemctl', '--user', 'show', '-p', 'MemoryMax', '--value', a['unit']], capture_output=True, text=True).stdout.strip()
    r['mem_gb'] = int(mm) // 2**30 if mm.isdigit() else None
for c in a.get('containers', []):
    t = subprocess.run(['docker', 'top', c, '-eo', 'pid,args'], capture_output=True, text=True)
    comms += t.stdout.splitlines()[1:]
    if not a.get('unit'):
        i = subprocess.run(['docker', 'inspect', c], capture_output=True, text=True)
        try:
            r['inspect'] = json.loads(i.stdout)[0]
        except Exception:
            pass
r['openroad'] = any('openroad' in c for c in comms)
r['procs'] = comms[:30]
print(json.dumps(r))
'''


def ssh_py(host, script, args, timeout=120):
    cmd = ['python3', '-I', '-', json.dumps(args)]
    if host not in ('localhost', HUB, os.uname().nodename):
        cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none', host] + \
              ['python3', '-I', '-', shlex.quote(json.dumps(args))]
    p = subprocess.run(cmd, input=script, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 or not p.stdout.strip():
        raise RuntimeError('verify on %s rc %s: %s' % (host, p.returncode, p.stderr.strip()[-200:]))
    return json.loads(p.stdout.strip().splitlines()[-1])


def ssh_sh(host, sh, timeout=300):
    cmd = ['bash', '-c', sh] if host in ('localhost', HUB, os.uname().nodename) else \
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none', host, sh]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, 'timeout after %d s' % timeout   # rc 124 is logged and the tick still saves its state
    return p.returncode, (p.stdout + p.stderr).strip()


def job_handles(row):
    """(unit, [containers]) of a stall_watch row: 'oth-....scope [c1,c2]' or a bare container name"""
    if row['kind'] == 'ot-run':
        m = re.match(r'(\S+\.scope)(?: \[([^\]]*)\])?', row['id'])
        return m.group(1), [c for c in (m.group(2) or '').split(',') if c]
    return None, [row['id']]


def names_kit(v, key):
    """True when the job's root command/cwd names the kit dir or its parent: then the same command resumes this kit's
    hung step.  A driver that builds many kits (die_ci.py --g2 all) would restart from scratch: report instead."""
    kit = key.split(':', 1)[1].rstrip('/')
    if kit.endswith('.log'):
        kit = os.path.dirname(kit)
    text = ' '.join([v.get('cwd') or ''] + list(v.get('argv') or []))
    return any(d and d != '/' and re.search(re.escape(d) + r'(/|\b|$)', text) for d in (kit, os.path.dirname(kit)))


def relaunch_script(v, unit, containers, tag):
    """the shell that relaunches the job with the same command; None when it cannot be reconstructed"""
    if unit:
        if not v.get('argv') or not v.get('cwd') or not v.get('mem_gb'):
            return None
        env = ' '.join(shlex.quote(e) for e in v.get('env', []) if not e.startswith(('SSH_', 'INVOCATION_ID=', 'JOURNAL_STREAM=')))
        log = os.path.join(v['cwd'], '.watchdog_relaunch_%s.log' % tag)
        # brace group: only the job goes to the background (its fds on the log), so the remote shell exits at once and
        # ssh returns; a bare `cd X && cmd ... &` backgrounds the whole list in a subshell that holds ssh's pipes open
        return ('cd %s && { setsid nohup env -i %s /usr/local/bin/ot-heavy --mem %d -- %s > %s 2>&1 < /dev/null & }'
                % (shlex.quote(v['cwd']), env, v['mem_gb'], ' '.join(shlex.quote(x) for x in v['argv']), shlex.quote(log)))
    c = v.get('inspect')
    if not c:
        return None
    hc, cfg = c.get('HostConfig', {}), c.get('Config', {})
    a = ['docker', 'run', '-d', '--name', c['Name'].lstrip('/')]
    if hc.get('AutoRemove'):
        a.append('--rm')
    if hc.get('Memory'):
        a += ['--memory', '%db' % hc['Memory']]
    if hc.get('MemorySwap'):
        a += ['--memory-swap', '%db' % hc['MemorySwap']]
    if hc.get('NanoCpus'):
        a += ['--cpus', '%g' % (hc['NanoCpus'] / 1e9)]
    if cfg.get('User'):
        a += ['--user', cfg['User']]
    for m in c.get('Mounts', []):
        if m.get('Type') == 'bind':
            a += ['-v', '%s:%s%s' % (m['Source'], m['Destination'], '' if m.get('RW', True) else ':ro')]
    if cfg.get('WorkingDir'):
        a += ['-w', cfg['WorkingDir']]
    for e in cfg.get('Env') or []:
        a += ['-e', e]
    ep = cfg.get('Entrypoint') or []
    cmd = cfg.get('Cmd') or []
    if ep:
        a += ['--entrypoint', ep[0]]
    a += [cfg['Image']] + ep[1:] + cmd
    return ' '.join(shlex.quote(x) for x in a)


def stop_script(unit, containers):
    s = []
    if unit:
        s.append('systemctl --user stop %s' % shlex.quote(unit))
    for c in containers:
        s.append('docker stop -t 30 %s >/dev/null 2>&1' % shlex.quote(c))
    for c in containers:  # --rm: wait until the name is free for the relaunch
        s.append('for i in $(seq 60); do docker inspect %s >/dev/null 2>&1 || break; sleep 1; done' % shlex.quote(c))
    return '; '.join(s) + '; true'


def append(path, line):
    with open(path, 'a') as f:
        f.write(line.rstrip('\n') + '\n')


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--act', action='store_true', help='stop + relaunch (default: dry run, prints what it would do)')
    ap.add_argument('--hosts', default=DEFAULT_HOSTS)
    ap.add_argument('--idle-min', type=float, default=120)
    ap.add_argument('--coord', default=os.environ.get('OT_COORD_DIR', os.path.expanduser('~/coord')))
    ap.add_argument('--rows', default=None, help='use stall_watch rows from this JSON (tests) instead of probing')
    ap.add_argument('--timeout', type=int, default=240)
    a = ap.parse_args(argv)
    now = time.time()
    ts = time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now))
    apdir = os.path.join(a.coord, 'autopilot')
    os.makedirs(apdir, exist_ok=True)
    logf, statef = os.path.join(apdir, 'WATCHDOG.log'), os.path.join(apdir, 'WATCHDOG.state.json')
    if a.rows:
        rows = json.load(open(a.rows))
    else:
        hosts = [h for h in a.hosts.split(',') if h]
        probes = {}
        with ThreadPoolExecutor(len(hosts)) as ex:
            for h, r, e in ex.map(lambda h: stall_watch.run_probe('localhost' if h == HUB else h, a.timeout), hosts):
                probes[h] = r
                if e:
                    print('# probe %s FAILED: %s' % (h, e))
        lanes = set()
        ld = os.path.join(a.coord, 'lanes')
        if os.path.isdir(ld):
            lanes = {f[:-3] for f in os.listdir(ld) if f.endswith('.md')}
        sw = argparse.Namespace(idle_min=a.idle_min, drt_idle_min=a.idle_min, stage_hours=6)
        rows = stall_watch.analyse(probes, lanes, sw, now)
    state, skip = load_state(statef), load_skip(a.coord)
    mode = 'ACT' if a.act else 'DRY-RUN'
    out = ['# WATCHDOG %s %s: %d running jobs, idle threshold %d min (log mtime only)' % (mode, ts, len(rows), a.idle_min)]
    n = {'ACT': 0, 'FIX': 0, 'STOP': 0, 'REPORT': 0}
    for r in sorted(rows, key=lambda r: -r['idle_s']):
        c = classify(r, state, skip, a.idle_min)
        if not c:
            continue
        verdict, step, reason = c
        unit, conts = job_handles(r)
        key = kit_key(r)
        v = {}
        if verdict in ('ACT', 'FIX', 'STOP') or (verdict == 'REPORT' and reason.startswith('not a place')
                                         and r.get('stage', '-') == '-' and r.get('log') not in (None, '-')):
            try:  # fresh re-check on the host just before acting: log still old, OpenROAD still alive, log tail
                v = ssh_py(r['host'], VERIFY, {'log': r['log'], 'unit': unit, 'containers': conts})
                verdict, step, reason = classify(r, state, skip, a.idle_min, v.get('tail', '')) or (verdict, step, reason)
            except Exception as e:  # noqa
                verdict, reason, v = 'REPORT', 'verify failed: %s' % str(e)[:120], {}
            if verdict in ('ACT', 'FIX', 'STOP'):
                if v.get('log_mtime') and now - v['log_mtime'] < a.idle_min * 60:
                    verdict, reason = 'REPORT', 'log written again at re-check'
                elif not v.get('openroad'):
                    verdict, reason = 'REPORT', 'no openroad process alive in the job (%s)' % (v.get('procs') or ['-'])[0][:80]
                elif verdict == 'ACT' and unit and not names_kit(v, key):
                    verdict, reason = 'REPORT', ('root command does not name the kit or its parent dir (a driver such as '
                                                 'die_ci.py): relaunch would rerun the whole driver, not the hung step')
        n[verdict] += 1
        out.append('%-6s %-7s %-5s idle %-6s lane %-12s %s' % (verdict, r['host'], step or '-', stall_watch.hm(r['idle_s']),
                                                               r['lane'], r['id'][:110]))
        out.append('         kit %s' % key)
        out.append('         log %s' % r['log'])
        out.append('         why %s' % reason)
        if verdict not in ('ACT', 'FIX', 'STOP'):
            continue
        tag = time.strftime('%m%d%H%M', time.localtime(now))
        rl = relaunch_script(v, unit, conts, tag) if verdict == 'ACT' else None
        if verdict == 'ACT' and not rl:
            out.append('         REPORT instead: relaunch command could not be reconstructed (no root argv/cwd/mem); not stopped')
            n['ACT'] -= 1; n['REPORT'] += 1
            continue
        out.append('         stop: %s' % stop_script(unit, conts)[:200])
        if rl:
            out.append('         relaunch: %s' % rl[:300])
        if not a.act:
            continue
        rc, msg = ssh_sh(r['host'], stop_script(unit, conts))
        append(logf, '%s STOP %s %s %s idle %s lane %s kit %s rc %s' % (ts, r['host'], step, r['id'], stall_watch.hm(r['idle_s']),
                                                                      r['lane'], key, rc))
        if verdict == 'STOP':
            lf = os.path.join(a.coord, 'lanes', '%s.md' % r['lane'])
            if r['lane'] not in ('?', 'CODEX') and os.path.isfile(lf):
                append(lf, '[WATCHDOG %s] %s %s hung (%s, idle %s), stop-only per WATCHDOG.skip: stopped, not relaunched. Kit %s.'
                       % (ts, r['host'], r['id'][:80], step, stall_watch.hm(r['idle_s']), key))
            state.setdefault(key, {})['stopped_at'] = ts
        elif verdict == 'FIX':
            line = ('FIX [WATCHDOG %s] %s %s hung twice (%s, idle %s; first relaunch %s): stopped, NOT relaunched (OWNER 12.22). '
                    'Kit %s, log %s. Owner lane %s: root-cause the hang before any new launch.'
                    % (ts, r['host'], r['id'][:80], step, stall_watch.hm(r['idle_s']),
                       state[key]['relaunches'][-1]['at'], key, r['log'], r['lane']))
            append(os.path.join(a.coord, 'lanes', 'COORD-REVIEW-QUEUE.md'), line)
            lf = os.path.join(a.coord, 'lanes', '%s.md' % r['lane'])
            if r['lane'] not in ('?', 'CODEX') and os.path.isfile(lf):
                append(lf, line)
            state[key]['fix_at'] = ts
            append(logf, '%s FIX %s posted' % (ts, key))
        else:
            rc2, msg2 = ssh_sh(r['host'], rl)
            state.setdefault(key, {}).setdefault('relaunches', []).append(
                {'at': ts, 'id': r['id'], 'step': step, 'idle': stall_watch.hm(r['idle_s']), 'rc': rc2, 'cmd': rl[:2000]})
            append(logf, '%s RELAUNCH %s %s rc %s: %s' % (ts, r['host'], key, rc2, rl[:400]))
        save_state(statef, state)
    out.append('# %d ACT, %d FIX, %d STOP, %d REPORT (%s)' % (n['ACT'], n['FIX'], n['STOP'], n['REPORT'], mode))
    print('\n'.join(out))
    if a.act:
        append(logf, '%s TICK %d ACT %d FIX %d STOP %d REPORT' % (ts, n['ACT'], n['FIX'], n['STOP'], n['REPORT']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
