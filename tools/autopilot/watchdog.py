#!/usr/bin/env python3
"""watchdog.py -- HUNG-JOB WATCHDOG (OWNER 12.22 item 1, 2026-10-30; lane WATCHDOG-1).

Rule: a job in a step below whose log has not moved for 2 h is stopped (that exact systemd scope / container only, never
pkill).  Lane jobs in OpenROAD place/CTS/GRT/DRT are relaunched ONCE with the same command in the same directory; a second
hang of the same kit -> a FIX line to the owning lane file and to COORD-REVIEW-QUEUE.md, no third launch.  Tool only: no
sign-off gate reads this.

Detection reuses tools/auto_owner/stall_watch.py (same probe, same "newest log" evidence: ORFS stage log first, else the
newest file under the job's RW mounts / cwd).

Progress signal per step (WATCHDOG-1 11-03):
  PLACE, CTS              no log, no new file and no container stdout for 2 h = HUNG, CPU or not.
  LEC                     a flat log alone never stops a LEC (OWNER/COORD 11-06; KW-FIX-25): single abc &scorr/&sat calls run
                          for hours and write nothing (26 LEC stops at ~2 h idle 11-03..11-06, 21 on serdes; t4 vB was CPU-bound).  Report only
                          while it is busy (tool CPU +--cpu-min-s in --cpu-sample-s, or its tool processes changed in the
                          sample) or the CPU could not be read; HUNG only with a tool alive, measured and idle, at 2 h.
  GRT, DRT, ROUTE         FastRoute logs once per extra iteration and DRT once per 10%, and late ones take > 2 h, so a
                          busy job (tool CPU +--cpu-min-s in --cpu-sample-s) may stay silent for 3 x its mean progress
                          interval, between 6 h and 12 h; past that it is HUNG.  Without CPU: HUNG at 2 h.
                          The post-GRT OT_MAXWIRE repair_design (open marker in the log, no end marker after it) is single-
                          threaded and logs once per 1,000 nets: busy, it may stay silent for the full 12 h (KW43-63, COORD 11-10).
Superseded (any log age; tools/autopilot/wave_jobs.py judge):
  STOP    wave row CANCELLED; attempt older than a live attempt of the same item on the current plan; running since before
          its row FAILED; an older second container on the same kit /work that has lost its ot-run client
  REPORT  plan_current=no but not cancelled, or superseded in a way not proven (owner: in-flight variants may finish)

Verdicts:
  ACT     lane job hung in place/CTS/GRT/DRT: stop + relaunch (only with --act; dry-run prints "would")
  FIX     as ACT, already relaunched once and hung again: stop, FIX line, no relaunch
  STOP    stop, note to the lane, no relaunch: superseded; a kit-wave job (the wave's own client retries it; a relaunch here
          made a second flow on one kit); hung LEC/synth (deterministic); a 'stop-only' line of WATCHDOG.skip
  REPORT  not acted on, with the reason: hand-launched Codex job (a /codex-* path outside a kit-wave root; kit-wave roots
          such as codex-s81-wave-1345 are autopilot output and count as normal), run dir deleted, no tool process alive,
          no log file visible, other step, listed in <coord>/autopilot/WATCHDOG.skip, busy within its GRT/DRT limit, or
          the fresh re-check found a newer log
Every --act action is appended to <coord>/autopilot/WATCHDOG.log; per-kit relaunch history in WATCHDOG.state.json.  At most
--max-stops per tick (the rest wait for the next tick).  The re-check runs once per host, in parallel, with one shared CPU
sample, so a tick costs one sample however many jobs look hung.  SYNTH: a busy yosys has only its per-pass log: HUNG at 6 h
silent, idle at 2 h.

Usage: watchdog.py [--act] [--hosts intel2,epyc2,intel1,epyc4] [--idle-min 120] [--coord DIR] [--rows FILE.json]
"""
import argparse, json, os, re, shlex, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'auto_owner'))
import stall_watch  # noqa: E402
import wave_jobs as WJ  # noqa: E402

HUB = os.environ.get('OT_HUB_NAME', 'intel2')
stall_watch.LOCAL_NAME = HUB
DEFAULT_HOSTS = ','.join(WJ.FLEET)
BUSY_MIN_S, BUSY_CAP_S = 6 * 3600, 12 * 3600   # busy and silent: never hung below MIN (measured: FastRoute 4.5 h per iteration), always above CAP

# ORFS stage names: 2_x floorplan/PDN (no), 3_x place, 4_x CTS, 5_x GRT/DRT/fill
ORFS_STEP = [(re.compile(r'^1_'), 'SYNTH'), (re.compile(r'^3_'), 'PLACE'), (re.compile(r'^4_'), 'CTS'), (re.compile(r'^5_1_grt'), 'GRT'),
             (re.compile(r'^5_2_route'), 'DRT'), (re.compile(r'^5_'), 'ROUTE')]
LEC_LOG = re.compile(r'/lec[^/]*/|/[^/]*lec[^/]*\.log$')
# OpenROAD message prefixes in a log tail (custom tcl scripts: die GRT, ECO DRT, ...)
CPU_STEPS = ('GRT', 'DRT', 'ROUTE', 'SYNTH', 'LEC', 'PLACE', 'CTS')   # CPU progress re-check before any stop; KW-FIX-46 11-12: every watched step (hung = no log AND no CPU)
TAIL_STEP = [('DRT-', 'DRT'), ('GRT-', 'GRT'), ('CTS-', 'CTS'), ('DPL-', 'PLACE'), ('GPL-', 'PLACE'),
             ('detailed_route', 'DRT'), ('global_route', 'GRT'), ('clock_tree_synthesis', 'CTS'),
             ('detailed_placement', 'PLACE'), ('global_placement', 'PLACE')]


def proc_tools(procs):
    """tool names from `docker top`/scope command lines; a wrapper `bash -c ... lec.py ...` does not count"""
    out = set()
    for p in procs or ():
        f = p.split()
        f = f[1:] if f and f[0].isdigit() else f
        if not f:
            continue
        b = os.path.basename(f[0])
        if b.startswith('python') and any(os.path.basename(x) == 'lec.py' for x in f[1:]):
            out.add('lec.py')
        elif b in ('openroad', 'yosys', 'yosys-abc'):
            out.add(b)
    return out


def step_of(stage, log, tail, procs=()):
    """the step a hung job sits in (PLACE CTS GRT DRT ROUTE SYNTH LEC), or None for anything else (floorplan, STA, ...)"""
    tools = proc_tools(procs)
    if 'openroad' not in tools:
        if 'lec.py' in tools or LEC_LOG.search(log or ''):
            return 'LEC'
        if tools & {'yosys', 'yosys-abc'} or 'yosys' in os.path.basename(log or ''):
            return 'SYNTH'
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


def job_wave(row):
    """kit-wave identity of a stall_watch row: every RW mount / cwd of the job is inside one kit-wave item.  A lane job that
    only reads a wave kit or also writes its own dir has none.  (A row without wave_paths: its log and run dir.)"""
    if 'wave_paths' in row:
        ps = row['wave_paths']
        return WJ.wave_id(ps) if ps and all(WJ.WAVE_RX.search(str(p)) for p in ps) else None
    return WJ.wave_id([row.get('log'), row.get('run')])


def skip_hit(row, skip):
    """(stop_only, substr) of the first WATCHDOG.skip line naming this job, else None"""
    paths = ' '.join(str(x) for x in (row.get('id'), row.get('run'), row.get('log'), row.get('cmd')))
    for s in skip:
        if s.startswith('stop-only '):
            if s[10:].strip() in paths:
                return True, s[10:].strip()
        elif s in paths:
            return False, s
    return None


def classify(row, state, skip, idle_min, tail='', procs=()):
    """-> (verdict, step, reason) for a stall_watch row; None when the job is not idle >= idle_min.
    tail: the log's last 8 kB from the host re-check (custom OpenROAD scripts have no ORFS stage name)"""
    if row['idle_s'] < idle_min * 60:
        return None
    step = step_of(row.get('stage'), row.get('log'), (row.get('last') or '') + '\n' + (tail or ''), procs)
    paths = ' '.join(str(x) for x in (row.get('id'), row.get('run'), row.get('log'), row.get('cmd')))
    wave = job_wave(row)
    if not wave and (row.get('lane') == 'CODEX' or '/codex-' in paths or '[codex-' in paths):
        return 'REPORT', step, 'Codex hand-launched, outside a wave root: report only (stop only if COORD says superseded)'
    if '(deleted)' in paths:
        return 'REPORT', step, 'run dir deleted: orphan, owner lane must clean up'
    if step is None:
        return 'REPORT', step, 'not a watched step (stage %s)' % row.get('stage', '-')
    if not row.get('log') or row['log'] == '-':
        return 'REPORT', step, 'no log file visible (stdout piped to caller?)'
    hit = skip_hit(row, skip)
    if hit:
        if hit[0]:
            return 'STOP', step, 'hung %s, stop-only in WATCHDOG.skip (%s): stop, no relaunch' % (stall_watch.hm(row['idle_s']), hit[1])
        return 'REPORT', step, 'listed in WATCHDOG.skip (%s)' % hit[1]
    if wave:
        return 'STOP', step, 'hung %s: stop; the kit-wave client retries or fails the row, no relaunch here' % stall_watch.hm(row['idle_s'])
    if '/ot-jobs/' in paths:
        # KW-FIX-46 11-12 (hbm PHY_NC): a sealed ot-job deletes its job dir when the command ends, so a relaunch in that dir
        # (13:13 docker run -d dpkit-PHY_NC-3468881) is orphaned within a minute; the autopilot client classifies the stop
        return 'STOP', step, 'hung %s in a sealed ot-job: stop, no relaunch here (the job dir dies with the command; the autopilot client decides)' % stall_watch.hm(row['idle_s'])
    if step in ('LEC', 'SYNTH'):
        return 'STOP', step, 'hung %s in %s: stop, no relaunch (the same run would hang again)' % (stall_watch.hm(row['idle_s']), step)
    hist = state.get(kit_key(row), {}).get('relaunches', [])
    if hist:
        return 'FIX', step, 'second hang of this kit (relaunched %s): stop, FIX to lane, no relaunch' % hist[-1]['at']
    return 'ACT', step, 'hung %s: stop + relaunch once' % stall_watch.hm(row['idle_s'])


def silent_limit_s(age_s, progress_n):
    """busy GRT/DRT/synth: 3 x the job's mean progress-line interval, clamped to [BUSY_MIN_S, BUSY_CAP_S]; without progress
    lines (a yosys pass) the floor for synth, which logs per pass, and the cap for an OpenROAD step not iterating yet"""
    if not age_s or not progress_n:
        return BUSY_CAP_S
    return min(BUSY_CAP_S, max(BUSY_MIN_S, 3.0 * age_s / progress_n))


def cpu_busy_reason(step, cpu_delta_s, cpu_min_s, cpu_sample_s, idle_s, limit_s, pids=None, progress_n='?'):
    """KW-FIX-46 11-12 (COORD; hbm PHY_NC 2731c12447d5): the OWNER 12.22 2-h rule stops HUNG jobs, not quiet ones.  A job in a
    CPU step whose sampled openroad / tool CPU grew by >= cpu_min_s is progressing: report only, at any silence.  The old
    busy cap (silent > BUSY_MIN..CAP = hung even while computing) killed PHY_NC's single-thread FastRoute at extra iteration
    23/30, 6h18 silent, while its container had used 12h48m CPU in 12h00m wall.  -> REPORT reason, or None (not busy)."""
    if step not in CPU_STEPS or not cpu_sample_s or cpu_delta_s is None or cpu_delta_s < cpu_min_s:
        return None
    over = ' (silent past the %s progress-line estimate: owner lane may look)' % stall_watch.hm(limit_s) \
        if limit_s is not None and idle_s >= limit_s else ''
    return ('progressing, CPU active, log silent: openroad +%.0f s CPU in %g s (pids %s), %s progress lines; '
            'not stopped (hung = no log AND no CPU)%s' % (cpu_delta_s, cpu_sample_s, pids, progress_n, over))


def busy_limit_s(step, age_s, progress_n, maxwire=False):
    """silent limit of a CPU-busy job in this step; a GRT job inside the OT_MAXWIRE repair_design gets the full cap"""
    if step == 'SYNTH':
        return BUSY_MIN_S
    if step == 'GRT' and maxwire:
        return BUSY_CAP_S
    return silent_limit_s(age_s, progress_n)


def duplicates(rows, verdicts):
    """{row id: (stop?, reason)} for all but the newest of the jobs on one kit /work, on any host, none of them already to
    stop.  stop only when the older job has lost its ot-run client: then nobody reads its result (a resubmit left it behind).
    A client-owned older job with a newer detached one is reported, for the lane: which should go is not this tool's call."""
    by = {}
    for r in rows:
        if (verdicts.get(id(r)) or ('', ''))[0] == 'STOP':
            continue
        for w in r.get('work') or []:
            by.setdefault(w, []).append(r)
    out = {}
    for w, rs in by.items():
        if len(rs) > 1:
            rs.sort(key=lambda r: r.get('age_s') or 0)
            for r in rs[1:]:
                gone = bool(r.get('client_gone'))
                out[id(r)] = (gone, 'second container on kit %s: this one %s, newer %s on %s'
                              % (w, 'lost its client' if gone else 'has its client', rs[0]['id'][:70], rs[0]['host']))
    return out


# ---------------------------------------------------------------- host side (runs on the job's host via ssh python3 -I -)
VERIFY = r'''
import json, os, re, subprocess, sys, time
A = json.loads(sys.argv[1])
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
def is_lec_tool(av):
    # KW-FIX-25: the processes of a LEC that burn CPU: yosys-abc is caught by 'yosys', a bare abc and the python drivers are not
    b = os.path.basename(av[0]) if av else ''
    return b == 'abc' or (b.startswith('python') and any(os.path.basename(x) in ('lec.py', 'miter_cone.py') for x in av[1:6]))
def or_pids(a):
    out = []
    for p in (procs_of_unit(a['unit']) if a.get('unit') else []):
        if any(k in x for x in argv(p)[:2] for k in ('openroad', 'yosys')) or is_lec_tool(argv(p)):
            out.append(p)
    for c in a.get('containers', []):
        t = subprocess.run(['docker', 'top', c, '-eo', 'pid,args'], capture_output=True, text=True)
        for l in t.stdout.splitlines()[1:]:
            f = l.split(None, 1)
            if len(f) == 2 and f[0].isdigit() and (any(k in f[1].split(' ', 1)[0] for k in ('openroad', 'yosys'))
                                                   or is_lec_tool(f[1].split())):
                out.append(int(f[0]))
    return sorted(set(out))
def cpu_s(pids):
    tot, seen = 0, 0
    for p in pids:
        try:
            f = open('/proc/%d/stat' % p).read().rsplit(')', 1)[1].split()
            tot += int(f[11]) + int(f[12]); seen += 1
        except Exception:
            pass
    return tot / float(os.sysconf('SC_CLK_TCK')) if seen else None
PROGRESS = re.compile(rb'Start extra iteration|Completing +\d+%')
def check(a):
    r = {'ok': True}
    try:
        r['log_mtime'] = os.stat(a['log']).st_mtime
    except (OSError, TypeError):
        r['log_mtime'] = None
    try:
        with open(a['log'], 'rb') as fh:
            fh.seek(0, 2); sz = fh.tell(); fh.seek(max(0, sz - 8192)); r['tail'] = fh.read().decode('utf-8', 'replace')
            fh.seek(max(0, sz - 2**27)); body = fh.read(); r['progress_n'] = len(PROGRESS.findall(body))
            r['maxwire'] = body.rfind(b'OT_MAXWIRE repair_design') > body.rfind(b'OT_MAXWIRE leaf instances')
    except (OSError, TypeError):
        r['tail'] = ''
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
        if a.get('idle_min'):    # stdout of a container: a progress signal the file walk cannot see
            try:
                o = subprocess.run(['docker', 'logs', '--since', '%dm' % a['idle_min'], '--tail', '1', c], capture_output=True, timeout=60)
                r['stdout_recent'] = bool((o.stdout + o.stderr).strip()) or r.get('stdout_recent', False)
            except Exception:
                pass
    r['openroad'] = any('openroad' in c for c in comms)
    r['tool'] = any(k in c for c in comms for k in ('openroad', 'yosys', 'lec.py', 'miter_cone'))   # wrappers too: alive check only
    r['procs'] = comms[:30]
    return r
res = [check(a) for a in A['jobs']]
if A.get('cpu_sample_s'):
    try:
        ps = [or_pids(a) if a.get('sample') else [] for a in A['jobs']]
        # KW-FIX-25: the first look has no process list, so an async LEC beside a stale ORFS stage log reads as PLACE/CTS
        # and asked for no sample; it is sampled once its processes show it (no openroad, a LEC tool alive)
        for k, (a, r) in enumerate(zip(A['jobs'], res)):
            if not ps[k] and not r['openroad'] and any(x in c for c in r['procs'] for x in ('lec.py', 'yosys-abc', 'miter_cone')):
                ps[k] = or_pids(a)
        c0 = [cpu_s(p) for p in ps]
        if any(c is not None for c in c0):
            time.sleep(A['cpu_sample_s'])
            for r, p, c in zip(res, ps, c0):
                c1 = cpu_s(p) if c is not None else None
                if c1 is not None:
                    r['cpu_delta_s'] = round(c1 - c, 1)
                    r['cpu_pids'] = p[:8]
            for a, r, p in zip(A['jobs'], res, ps):   # KW-FIX-25: a LEC runs one abc after another: new tool processes = moving
                if p and set(or_pids(a)) != set(p):
                    r['tool_churn'] = True
    except Exception as e:
        for r in res:
            r['cpu_error'] = str(e)[:120]
print(json.dumps(res))
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
    ap.add_argument('--max-stops', type=int, default=40, help='stops per tick; the rest wait for the next tick')
    ap.add_argument('--cpu-sample-s', type=float, default=60,
                    help='GRT/DRT: seconds between the two openroad CPU-time samples, shared per host (0 = no CPU re-check)')
    ap.add_argument('--cpu-min-s', type=float, default=30,
                    help='GRT/DRT: CPU seconds gained in the sample that mean "progressing" (within its silent limit)')
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
    t_probe = time.time() - now
    rows = sorted(rows, key=lambda r: -r['idle_s'])
    # superseded: any log age
    wave_rows = WJ.load_rows(apdir)
    sup = {}
    for r in rows:
        age = r.get('age_s')
        j = WJ.judge(wave_rows, job_wave(r), now - age if age is not None else None)
        if j:
            sup[id(r)] = j
    for rid, (gone, why) in duplicates(rows, sup).items():
        r = next(x for x in rows if id(x) == rid)
        sup[rid] = ('STOP', why) if gone and job_wave(r) else ('REPORT', why)
    for r in rows:
        hit = skip_hit(r, skip)
        if id(r) in sup and sup[id(r)][0] == 'STOP' and hit and not hit[0]:
            sup[id(r)] = ('REPORT', sup[id(r)][1] + '; listed in WATCHDOG.skip (%s)' % hit[1])
    # hung re-check on each host, once, in parallel, with one shared CPU sample
    todo = []
    for r in rows:
        c = classify(r, state, skip, a.idle_min)
        if sup.get(id(r), ('',))[0] == 'STOP' or not c:
            continue
        if c[0] in ('ACT', 'FIX', 'STOP') or (c[0] == 'REPORT' and c[2].startswith('not a watched')
                                              and r.get('stage', '-') == '-' and r.get('log') not in (None, '-')):
            todo.append((r, c))
    verified, failed = {}, {}
    by_host = {}
    for r, c in todo:
        unit, conts = job_handles(r)
        by_host.setdefault(r['host'], []).append((r, {'log': r['log'], 'unit': unit, 'containers': conts, 'idle_min': a.idle_min,
                                                      'sample': c[1] in CPU_STEPS or c[1] is None}))

    def verify_host(item):
        h, jobs = item
        cs = a.cpu_sample_s                  # VERIFY sleeps only when it has a process to sample (KW-FIX-25: async LEC)
        try:
            return h, jobs, ssh_py(h, VERIFY, {'jobs': [x[1] for x in jobs], 'cpu_sample_s': cs}, timeout=240 + int(cs)), None
        except Exception as e:  # noqa
            return h, jobs, None, str(e)[:120]
    if by_host:
        with ThreadPoolExecutor(len(by_host)) as ex:
            for h, jobs, res, err in ex.map(verify_host, by_host.items()):
                for k, (r, _) in enumerate(jobs):
                    if res is None:
                        failed[id(r)] = err
                    else:
                        verified[id(r)] = res[k]
    t_verify = time.time() - now - t_probe
    out = ['# WATCHDOG %s %s: %d running jobs, idle threshold %d min (log, files, stdout; per-step rule)' % (mode, ts, len(rows), a.idle_min)]
    n = {'ACT': 0, 'FIX': 0, 'STOP': 0, 'REPORT': 0}
    nsup = {'STOP': 0, 'REPORT': 0}
    stops = 0
    for r in rows:
        v = verified.get(id(r), {})
        s_ = sup.get(id(r))
        if s_ and s_[0] == 'STOP':
            verdict, step, reason = 'STOP', None, 'SUPERSEDED: ' + s_[1]
        else:
            c = classify(r, state, skip, a.idle_min, v.get('tail', ''), v.get('procs') or ())
            if not c and not s_:
                continue
            verdict, step, reason = c or ('REPORT', None, '')
            if id(r) in failed and verdict in ('ACT', 'FIX', 'STOP'):
                verdict, reason = 'REPORT', 'verify failed: %s' % failed[id(r)]
            elif verdict in ('ACT', 'FIX', 'STOP'):
                busy = step in CPU_STEPS and a.cpu_sample_s and v.get('cpu_delta_s') is not None and v['cpu_delta_s'] >= a.cpu_min_s
                limit = busy_limit_s(step, r.get('age_s'), v.get('progress_n'), v.get('maxwire'))
                lec_idle = (v.get('cpu_delta_s') is not None and v['cpu_delta_s'] < a.cpu_min_s and not v.get('tool_churn'))
                if v.get('log_mtime') and now - v['log_mtime'] < a.idle_min * 60:
                    verdict, reason = 'REPORT', 'log written again at re-check'
                elif v.get('stdout_recent'):
                    verdict, reason = 'REPORT', 'container stdout moved within %d min' % a.idle_min
                elif step == 'LEC' and v.get('tool', v.get('openroad')) and not lec_idle:
                    verdict, reason = 'REPORT', ('LEC with a flat log, not idle: tool CPU %s s in %g s%s (pids %s); never stopped '
                                                 'for a flat log (KW-FIX-25), owner lane judges'
                                                 % (v.get('cpu_delta_s', 'unread'), a.cpu_sample_s,
                                                    ', tool processes changed' if v.get('tool_churn') else '', v.get('cpu_pids')))
                elif busy:
                    verdict, reason = 'REPORT', cpu_busy_reason(step, v['cpu_delta_s'], a.cpu_min_s, a.cpu_sample_s,
                                                                r['idle_s'], limit, v.get('cpu_pids'), v.get('progress_n', '?'))
                elif not v.get('tool', v.get('openroad')):
                    verdict, reason = 'REPORT', 'no tool process alive in the job (%s)' % (v.get('procs') or ['-'])[0][:80]
                elif verdict == 'ACT' and job_handles(r)[0] and not names_kit(v, kit_key(r)):
                    verdict, reason = 'REPORT', ('root command does not name the kit or its parent dir (a driver such as '
                                                 'die_ci.py): relaunch would rerun the whole driver, not the hung step')
            if s_:   # superseded but not stopped: its line always shows, hung or not
                nsup['REPORT'] += 1
                reason = 'SUPERSEDED (report): %s%s' % (s_[1], ('; ' + reason) if reason else '')
        if verdict in ('ACT', 'FIX', 'STOP'):
            stops += 1
            if stops > a.max_stops:
                verdict, reason = 'REPORT', 'stop cap %d this tick, next tick: %s' % (a.max_stops, reason)
                if a.act:
                    append(logf, '%s STOP-CAP %s %s' % (ts, r['host'], r['id'][:110]))
            elif s_ and s_[0] == 'STOP':
                nsup['STOP'] += 1
        unit, conts = job_handles(r)
        key = kit_key(r)
        n[verdict] += 1
        out.append('%-6s %-7s %-5s idle %-6s age %-6s lane %-12s %s' % (verdict, r['host'], step or '-', stall_watch.hm(r['idle_s']),
                                                                       stall_watch.hm(r.get('age_s')), r['lane'], r['id'][:110]))
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
        # KW-FIX-44 11-09: the reason goes on the line (autopilot classify names it for the 137/143 the stop causes)
        append(logf, '%s STOP %s %s %s idle %s lane %s kit %s rc %s why %s' % (ts, r['host'], step, r['id'], stall_watch.hm(r['idle_s']),
                                                                             r['lane'], key, rc, ' '.join(str(reason).split())[:240]))
        if verdict == 'STOP':
            lf = os.path.join(a.coord, 'lanes', '%s.md' % r['lane'])
            if r['lane'] not in ('?', 'CODEX') and os.path.isfile(lf):
                append(lf, '[WATCHDOG %s] %s %s (%s, idle %s): stopped, not relaunched. %s. Kit %s.'
                       % (ts, r['host'], r['id'][:80], step, stall_watch.hm(r['idle_s']), reason[:200], key))
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
    out.append('# %d ACT, %d FIX, %d STOP (%d superseded), %d REPORT (%d superseded) (%s); probe %.0f s, re-check %.0f s, tick %.0f s'
               % (n['ACT'], n['FIX'], n['STOP'], nsup['STOP'], n['REPORT'], nsup['REPORT'], mode, t_probe, t_verify, time.time() - now))
    print('\n'.join(out))
    if a.act:
        append(logf, '%s TICK %d ACT %d FIX %d STOP %d REPORT' % (ts, n['ACT'], n['FIX'], n['STOP'], n['REPORT']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
