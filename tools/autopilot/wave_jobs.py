#!/usr/bin/env python3
"""wave_jobs.py -- which kit-wave row a running job belongs to, whether that row still wants it, and how to stop a kit's
remote job (WATCHDOG-1 11-03, after HUNG-1103: 59 containers stopped by hand, 34 of them on rows that no longer wanted
them).  Used by watchdog.py (superseded report/stop), autopilot.py (no resubmit of a superseded job, one flow container
per kit) and kit_wave.py (a cancel stops the remote container).  Tool only; no sign-off gate reads this.

A job's identity comes from its kit-wave path, also under a wave root such as codex-s81-wave-1345/:
    .../kit-wave/<die>/<event>/items/<item>[/attempt_<n>]/...
Attempts compare only within one (die, event, item).  A variant or form has another item name or event, so it is never
superseded by the other (owner: in-flight variants may finish).
"""
import csv, json, os, re, shlex
from concurrent.futures import ThreadPoolExecutor

FLEET = [h for h in os.environ.get('OT_FLEET_HOSTS', 'intel2,epyc2,intel1,epyc4').split(',') if h]
WAVE_RX = re.compile(r'/kit-wave/([^/\s]+)/([^/\s]+)/items/([^/\s]+)(?:/attempt_(\d+))?(?=[/\s]|$)')
LIVE = ('RUNNING', 'LAUNCHING', 'ENQUEUED')


def wave_id(paths):
    """(die, event, item, attempt) from the first kit-wave path, else None"""
    for p in paths:
        m = WAVE_RX.search(str(p or ''))
        if m:
            return m.group(1), m.group(2), m.group(3), int(m.group(4) or 1)
    return None


def load_rows(ap_dir):
    """{(die, event, item): [row]} from kit_wave_state.json, plan_current joined from kit_wave_stages.tsv; {} if unreadable"""
    try:
        items = json.load(open(os.path.join(ap_dir, 'kit_wave_state.json'))).get('items') or {}
    except (OSError, ValueError):
        return {}
    cur = {}
    try:
        with open(os.path.join(ap_dir, 'kit_wave_stages.tsv'), newline='') as f:
            for r in csv.DictReader(f, delimiter='\t', quoting=csv.QUOTE_NONE):
                cur[(r.get('die'), r.get('item'), r.get('block_sha'))] = r.get('plan_current') or ''
    except OSError:
        pass
    out = {}
    for r in items.values():
        r = dict(r, plan_current=cur.get((r.get('die'), r.get('item'), (r.get('block_sha') or '')[:12]), ''))
        out.setdefault((r.get('die'), r.get('event'), r.get('item')), []).append(r)
    return out


def _live(r):
    return r.get('status') in LIVE and not str(r.get('q_status') or '').startswith(('DONE', 'CANCELLED', 'WITHDRAWN'))


def judge(rows_by, wid, start):
    """does the wave still want the job (identity wid, started at epoch start or None)?
    -> ('STOP', why): row CANCELLED; older than a live attempt of the item on the current plan and running since before
                      that attempt started; running since before its row FAILED
       ('REPORT', why): superseded by plan_current=no or an older attempt, but not stopped (owner: in-flight may finish)
       None: nothing to say (no row, or the row wants it)"""
    if not wid:
        return None
    die, event, item, attempt = wid
    rows = rows_by.get((die, event, item)) or []
    if not rows:
        return None
    a = lambda r: int(r.get('attempt') or 1)
    same = [r for r in rows if a(r) == attempt]
    newer = [r for r in rows if a(r) > attempt]
    r = max(same or newer or [{}], key=lambda x: (a(x), x.get('updated') or 0)) if (same or newer) else None
    if r is None:   # an attempt dir newer than the state knows: unknown, leave it
        return None
    tag = '%s/%s@%d row %s@%d' % (die, item, attempt, r.get('event'), a(r))
    if r.get('status') == 'CANCELLED':
        return 'STOP', '%s CANCELLED class %s: %s' % (tag, r.get('class') or '-', (r.get('reason') or '')[:120])
    cur_live = [x for x in newer if _live(x) and x.get('plan_current') == 'yes']
    if cur_live:
        x = max(cur_live, key=a)
        if start is not None and start < float(x.get('started') or 0):
            return 'STOP', '%s: older than live attempt_%d on the current plan' % (tag, a(x))
        return 'REPORT', ('%s: older attempt than live attempt_%d, but started after it (a lane resume): not stopped' % (tag, a(x)))
    if r.get('status') == 'FAIL':
        if start is not None and start < float(r.get('updated') or 0):
            return 'STOP', '%s FAILED while it ran: %s' % (tag, (r.get('reason') or '')[:120])
        return 'REPORT', '%s FAIL but this job started after it (stage resume or a lane relaunch): not stopped' % tag
    if r.get('plan_current') == 'no':
        return 'REPORT', '%s plan_current=no, not cancelled yet' % tag
    other = [x for x in newer if _live(x)]
    if other:
        x = max(other, key=a)
        return 'REPORT', '%s: older than live attempt_%d, plan_current=%s' % (tag, a(x), x.get('plan_current') or '?')
    return None


# ----------------------------------------------------------------- stop a kit's remote job (runs on the host, python3 -I -)
STOP_KIT = r'''
import json, os, subprocess, sys
a = json.loads(sys.argv[1]); roots = [r.rstrip('/') for r in a['roots']]; dry = a.get('dry')
def under(p):
    p = p.rstrip('/')
    for r in roots:
        if p == r:
            return True
        if p.startswith(r + '/') and not p[len(r) + 1:].startswith('attempt_'):   # attempt 1's root holds the later attempts
            return True
    return False
def origins(c):
    # FAILFAST-1 11-12 (orphan leak): an ot-job isolated copy mounts <ot-jobs>/<tag>/work, which is under no kit root, so a stop by
    # mount source never found it (q_su31 a11, col_h10_r1 a11, sle_fe_v1 a9 ... ran 60-70 h after their rows were CANCELLED).
    # The job spec names the ORIGINAL kit the wave / autopilot row points at (work.at, return.to): match on that too.
    out = []
    for m in c.get('Mounts', []):
        if m.get('Destination') == '/work' and m.get('Source'):
            try:
                spec = json.load(open(os.path.join(os.path.dirname(m['Source'].rstrip('/')), '.ot-job', 'job.json'))).get('spec') or {}
            except (OSError, ValueError, AttributeError):
                continue
            out += [(spec.get('work') or {}).get('at'), (spec.get('return') or {}).get('to')]
    return [o for o in out if o]
ids = subprocess.run(['docker', 'ps', '-q', '--no-trunc'], capture_output=True, text=True, timeout=60).stdout.split()
names = []
if ids:
    for c in json.loads(subprocess.run(['docker', 'inspect'] + ids, capture_output=True, text=True, timeout=120).stdout or '[]'):
        if any(m.get('Type') == 'bind' and m.get('RW', True) and under(m['Source']) for m in c.get('Mounts', [])) or \
                any(under(o) for o in origins(c)):
            names.append(c['Name'].lstrip('/'))
scopes = set()
for pid in filter(str.isdigit, os.listdir('/proc')):
    try:
        av = open('/proc/%s/cmdline' % pid, 'rb').read().decode('utf-8', 'replace').split('\0')
        if os.path.basename(av[0]) == 'docker' and 'run' in av and any(n in av or '--name=' + n in av for n in names):
            for l in open('/proc/%s/cgroup' % pid):
                u = l.strip().rsplit('/', 1)[-1]
                if u.startswith('oth-') and u.endswith('.scope'):
                    scopes.add(u)
    except (OSError, IndexError):
        pass
if not dry:
    for u in sorted(scopes):
        subprocess.run(['systemctl', '--user', 'stop', u], capture_output=True, timeout=120)
    for n in names:
        subprocess.run(['docker', 'stop', '-t', '30', n], capture_output=True, timeout=120)
print(json.dumps({'containers': names, 'scopes': sorted(scopes)}))
'''


def stop_on_fleet(sh, hub, roots, hosts=None, dry=False):
    """stop every container (and its ot-heavy scope) with an RW mount on these kit/attempt roots, on all hosts: ot-run may
    have spilled the job anywhere and a hub client's stop leaves a started command running.  Exact names, never pkill.
    sh(cmd, timeout=, input=) -> (rc, out, err).  -> {host: {'containers': [...], 'scopes': [...]} or {'error': ...}}"""
    roots = sorted({r for r in roots if r})
    if not roots:
        return {}
    args = json.dumps({'roots': roots, 'dry': bool(dry)})

    def one(h):
        cmd = ['python3', '-I', '-', args] if h in ('localhost', hub, os.uname().nodename) else \
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', '-o', 'ControlPath=none', h,
             'python3', '-I', '-', shlex.quote(args)]
        try:
            rc, out, err = sh(cmd, timeout=240, input=STOP_KIT)
            if rc != 0 or not (out or '').strip():
                return h, {'error': 'rc %s %s' % (rc, (err or '')[-160:])}
            return h, json.loads(out.strip().splitlines()[-1])
        except Exception as e:  # noqa: the watchdog is the safety net for a host missed here
            return h, {'error': str(e)[:160]}
    hosts = list(hosts or FLEET)
    with ThreadPoolExecutor(max(1, len(hosts))) as ex:
        return dict(ex.map(one, hosts))


def stop_row_containers(sh, hub, roots, hosts=None, dry=False):
    """FAILFAST-1 11-12: what a cancel does to its row's running containers, in one call.  -> (names 'host:container ...', errors text)
    Exact names only (stop_on_fleet); the caller stores both on the row and logs them."""
    roots = sorted({r for r in roots if r})
    if not roots:
        return '', ''
    res = stop_on_fleet(sh, hub, roots, hosts, dry)
    errs = ''.join('; %s not checked: %s' % (h, v['error']) for h, v in sorted(res.items()) if v.get('error'))
    return ' '.join(stopped_names(res)), errs


def stopped_names(res):
    return ['%s:%s' % (h, c) for h, v in sorted(res.items()) for c in (v.get('containers') or [])]


