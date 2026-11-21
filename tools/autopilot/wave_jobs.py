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
import sys
import csv, json, os, re, shlex
from concurrent.futures import ThreadPoolExecutor

# WAVE-LONGRUN-1 11-15: the default named intel2,epyc2,intel1,epyc4: epyc7/8/9/10 were never probed or stopped (the scopes of
# CANCELLED rows kept running there) and the terminated epyc4 timed out every call ("epyc4 not checked"), so every REAP-DEAD probe
# was "unreadable (reported only)".  kit_wave._step now sets the list from kit_wave.json (set_fleet / fleet_from_cfg).
FLEET = [h for h in os.environ.get('OT_FLEET_HOSTS', 'intel2,intel1,epyc2,epyc7,epyc8,epyc9,epyc10').split(',') if h]


def fleet_from_cfg(cfg, hub):
    """hosts of kit_wave.json (global + every die: hosts, place_prefer, gen_hosts, gen_overflow_hosts) plus the hub, minus
    retired_hosts and 'localhost'.  -> list; the default FLEET if the config names none"""
    cfg = cfg or {}
    retired = set(cfg.get('retired_hosts') or [])
    names = [hub]
    lists = [cfg.get(k) for k in ('hosts', 'place_prefer', 'gen_hosts', 'gen_overflow_hosts')]
    for d in (cfg.get('dies') or {}).values():
        if isinstance(d, dict):
            lists += [d.get(k) for k in ('hosts', 'place_prefer', 'gen_hosts', 'gen_overflow_hosts')]
    for lst in lists:
        names += [h for h in (lst or []) if isinstance(h, str)]
    out = [h for h in dict.fromkeys(names) if h and h != 'localhost' and h not in retired]
    return out if len(out) > 1 else list(FLEET)


def set_fleet(hosts):
    """replace FLEET in place (callers read WJ.FLEET at call time)"""
    hosts = [h for h in dict.fromkeys(hosts or []) if h]
    if hosts:
        FLEET[:] = hosts
    return list(FLEET)
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


def judged_row(rows_by, wid):
    """FLOW-OPS-1000: the kit_wave_state row judge() decides on for identity wid (same attempt, else the newest newer one), or None"""
    if not wid:
        return None
    die, event, item, attempt = wid
    rows = rows_by.get((die, event, item)) or []
    a = lambda r: int(r.get('attempt') or 1)
    same = [r for r in rows if a(r) == attempt]
    newer = [r for r in rows if a(r) > attempt]
    return max(same or newer, key=lambda x: (a(x), x.get('updated') or 0)) if (same or newer) else None


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
# FLOW-FIX-2045 (FABLE-FLOW-1949 class 5: 11 scopes of CANCELLED attempts lived 17-28 h at cpu 0): an ot-heavy scope with NO container (a waiting / dead-client scope) is named by no mount, so the
# container pass above never found it.  Match every active oth-* scope whose processes name a path under a cancelled attempt's root (cmdline words or cwd).
if not os.environ.get('XDG_RUNTIME_DIR'):
    os.environ['XDG_RUNTIME_DIR'] = '/run/user/%d' % os.getuid()
try:
    act = [l.split()[0][:-6] for l in subprocess.run(['systemctl', '--user', 'list-units', '--type=scope', '--state=active', '--no-legend', '--plain', 'oth-*'], capture_output=True, text=True, timeout=60).stdout.splitlines() if l.split()]
except Exception:
    act = []
for u in act:
    if u + '.scope' in scopes:
        continue
    pids = []
    for root, dirs, files in os.walk('/sys/fs/cgroup/user.slice'):
        if os.path.basename(root) == u + '.scope':
            try:
                pids = [int(x) for x in open(os.path.join(root, 'cgroup.procs')).read().split()]
            except OSError:
                pass
            dirs[:] = []
    for p in pids:
        try:
            av = open('/proc/%d/cmdline' % p, 'rb').read().decode('utf-8', 'replace').split('\0')
            av.append(os.readlink('/proc/%d/cwd' % p))
        except OSError:
            continue
        if any(w.startswith('/') and under(w) for w in av):
            scopes.add(u + '.scope')
            break
left = []
if not dry:
    for u in sorted(scopes):
        subprocess.run(['systemctl', '--user', 'stop', u], capture_output=True, timeout=120)
    for n in names:
        subprocess.run(['docker', 'stop', '-t', '30', n], capture_output=True, timeout=120)
    # verify by unit name: a scope that is still active after the stop is reported so the caller keeps the row's reap pending
    for u in sorted(scopes):
        if subprocess.run(['systemctl', '--user', 'is-active', '--quiet', u], capture_output=True).returncode == 0:
            left.append(u)
print(json.dumps(dict({'containers': names, 'scopes': sorted(scopes)}, **({'left': left} if left else {}))))
'''


BAD_HOSTS = set()      # COORD 11-19 (FLOW-1150 B): hosts the wave found unreadable / over 2x cores this tick (kit_wave sets it); the stop / scan paths do not wait on them
STOP_SSH_S = 30        # a remote stop that has not answered in 30 s is 'not checked' (12:00-13:05 ticks: 11 cancel-stops cost 455 s, the tick passed its 50 min TimeoutStartSec before the launch pass)
SSH_CONNECT_S = 10     # ssh ConnectTimeout of every fleet-wide stop / scan call (was 15)


def stop_on_fleet(sh, hub, roots, hosts=None, dry=False):
    """stop every container (and its ot-heavy scope) with an RW mount on these kit/attempt roots, on all hosts: ot-run may
    have spilled the job anywhere and a hub client's stop leaves a started command running.  Exact names, never pkill.
    sh(cmd, timeout=, input=) -> (rc, out, err).  -> {host: {'containers': [...], 'scopes': [...]} or {'error': ...}}"""
    roots = sorted({r for r in roots if r})
    if not roots:
        return {}
    args = json.dumps({'roots': roots, 'dry': bool(dry)})

    def one(h):
        if h in BAD_HOSTS:
            return h, {'error': 'skipped: host unreadable or over 2x its cores this tick'}
        cmd = ['python3', '-I', '-', args] if h in ('localhost', hub, os.uname().nodename) else \
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % SSH_CONNECT_S, '-o', 'ControlPath=none', h,
             'python3', '-I', '-', shlex.quote(args)]
        try:
            rc, out, err = sh(cmd, timeout=(240 if len(cmd) < 4 or cmd[0] != 'ssh' else STOP_SSH_S), input=STOP_KIT)
            if rc != 0 or not (out or '').strip():
                return h, {'error': 'rc %s %s' % (rc, (err or '')[-160:])}
            return h, json.loads(out.strip().splitlines()[-1])
        except Exception as e:  # noqa: the watchdog is the safety net for a host missed here
            return h, {'error': str(e)[:160]}
    hosts = list(hosts or FLEET)
    with ThreadPoolExecutor(max(1, len(hosts))) as ex:
        return dict(ex.map(one, hosts))


# WAVE-LONGRUN-1 11-15: the oth-* scopes of an attempt the wave replaced.  A row keeps only its newest attempt, so the
# older attempt's running ot-heavy scope (a 17 h GRT of ot_s81sl_leaf__t47 a7 while a8 existed) is named by no row and by no
# root list.  This host script reads DATA = {"die|event|item": [[attempt, started_epoch, status], ...]} (kit_wave rows) and
# stops, with ot-heavy-stop --unit (containers first), every scope that is older than ORPHAN_MIN_AGE_S and whose kit-wave path
# names an attempt N for which a NEWER attempt of the same (die, event, item) STARTED AFTER the scope did.  A scope started
# after the newer attempt (a lane resume), an attempt the state does not know, and everything outside kit-wave paths are left.
ORPHAN_SCAN = r'''
import json, os, re, subprocess, sys, time
a = json.loads(sys.argv[1]); dry = a.get('dry'); min_age = a.get('min_age', 1800); cap = a.get('cap', 40)
rx = re.compile(r'/kit-wave/([^/\s]+)/([^/\s]+)/items/([^/\s]+)/attempt_(\d+)(?=[/\s]|$)')
if not os.environ.get('XDG_RUNTIME_DIR'):
    os.environ['XDG_RUNTIME_DIR'] = '/run/user/%d' % os.getuid()
units = [l.split()[0][:-6] for l in subprocess.run(['systemctl', '--user', 'list-units', '--type=scope', '--state=active', '--no-legend', '--plain', 'oth-*'],
         capture_output=True, text=True).stdout.splitlines() if l.split()]
out, now = [], time.time()
for u in units:
    if len(out) >= cap:
        break
    m = re.search(r'-(\d{10})$', u)
    t0 = float(m.group(1)) if m else 0.0
    if not t0 or now - t0 < min_age:
        continue
    pids = []
    for root, dirs, files in os.walk('/sys/fs/cgroup/user.slice'):
        if os.path.basename(root) == u + '.scope':
            try:
                pids = [int(x) for x in open(os.path.join(root, 'cgroup.procs')).read().split()]
            except OSError:
                pass
            dirs[:] = []
    hit = None
    for p in pids:
        try:
            txt = open('/proc/%d/cmdline' % p).read().replace('\0', ' ') + ' ' + os.readlink('/proc/%d/cwd' % p)
        except OSError:
            continue
        hit = rx.search(txt)
        if hit:
            break
    if not hit:
        continue
    die, ev, item, n = hit.group(1), hit.group(2), hit.group(3), int(hit.group(4))
    rows = a['rows'].get('%s|%s|%s' % (die, ev, item))
    if not rows:
        continue
    # Parallel block identities can have different attempt numbers within the same event and item.
    # A live owner of this scope takes precedence over any newer sibling row.
    if any(r[0] == n and r[2] in ('LAUNCHING', 'RUNNING', 'ENQUEUED') and r[1] <= t0 + 60 for r in rows):
        continue
    newer = [r for r in rows if r[0] > n and r[1] > t0]
    own = [r for r in rows if r[0] == n and r[2] in ('FAIL', 'CANCELLED', 'DEDUP') and len(r) > 3 and r[3] > t0 + 60]
    if own and not newer:
        # FABLE-FLOW-0800 B: the attempt's own row is terminal (recorded FAIL / CANCELLED after this scope started) but its scope lives on.  Stop it unless it still burns CPU (two samples 1 s apart).
        def ticks():
            t = 0
            for p in pids:
                try:
                    f = open('/proc/%d/stat' % p).read().rsplit(')', 1)[1].split()
                    t += int(f[11]) + int(f[12])
                except (OSError, IndexError, ValueError):
                    pass
            return t
        t1 = ticks(); time.sleep(1); busy = (ticks() - t1) / (1.0 * os.sysconf('SC_CLK_TCK'))
        if busy > 0.3:
            continue
        why = 'attempt %d of %s/%s is recorded %s but its scope lives on (cpu %.2f cores)' % (n, die, item, own[0][2], busy)
        if not dry:
            subprocess.run(['ot-heavy-stop', '--unit', u], capture_output=True, timeout=300)
        out.append({'unit': u, 'why': why, 'age_h': round((now - t0) / 3600, 1)})
        continue
    if not newer:
        continue
    why = 'attempt %d of %s/%s older than attempt %d started %d s after it' % (n, die, item, max(r[0] for r in newer), int(max(r[1] for r in newer) - t0))
    if not dry:
        subprocess.run(['ot-heavy-stop', '--unit', u], capture_output=True, timeout=300)
    out.append({'unit': u, 'why': why, 'age_h': round((now - t0) / 3600, 1)})
print(json.dumps({'orphans': out}))
'''


def orphan_scopes(sh, hub, rows, hosts=None, dry=False, min_age=1800, cap=40):
    """run ORPHAN_SCAN on every fleet host -> {host: {'orphans': [...]} or {'error': ...}}"""
    args = json.dumps({'rows': rows, 'dry': bool(dry), 'min_age': min_age, 'cap': cap})

    def one(h):
        # the args (every recent row) are sent on stdin with the script: they no longer fit argv (E2BIG once single-attempt rows were included)
        if h in BAD_HOSTS:
            return h, {'error': 'skipped: host unreadable or over 2x its cores this tick'}
        cmd = ['python3', '-I', '-'] if h in ('localhost', hub, os.uname().nodename) else \
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=%d' % SSH_CONNECT_S, '-o', 'ControlPath=none', h,
             'python3', '-I', '-']
        try:
            rc, out, err = sh(cmd, timeout=300, input='import sys\nsys.argv[1:2] = [%r]\n' % args + ORPHAN_SCAN)
            if rc != 0 or not (out or '').strip():
                return h, {'error': 'rc %s %s' % (rc, (err or '')[-160:])}
            return h, json.loads(out.strip().splitlines()[-1])
        except Exception as e:  # noqa: the next tick retries
            return h, {'error': str(e)[:160]}
    hosts = list(hosts or FLEET)
    with ThreadPoolExecutor(max(1, len(hosts))) as ex:
        return dict(ex.map(one, hosts))


def stop_bg_spawn(hub, roots, log_path, tag=""):
    """COORD 11-20 (tick poll_running 140 s: one fleet-wide ssh stop per cancelled job inside the tick): fire and forget; the detached process appends `<time> stop-bg [<tag>] ...` to log_path.
    -> True when started"""
    import subprocess as _sp
    roots = sorted({r for r in roots if r})
    if not roots:
        return False
    try:
        _sp.Popen([sys.executable, "-I", os.path.abspath(__file__), "stop-bg", str(hub), json.dumps(roots), str(log_path), str(tag)],
                  stdin=_sp.DEVNULL, stdout=_sp.DEVNULL, stderr=_sp.DEVNULL, start_new_session=True)
        return True
    except OSError:
        return False


def stop_result_for(log_text, tag):
    """the last `stop-bg [<tag>]` line of the log: -> (found, ok, text); ok False when a host was not checked"""
    hit = [l for l in (log_text or "").splitlines() if f"stop-bg [{tag}]" in l]
    if not hit:
        return False, False, ""
    return True, "not checked" not in hit[-1], hit[-1]


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




def _cli(argv):
    """python3 -I wave_jobs.py stop-bg <hub> <json roots> [log]: the fleet stop of the wave, run detached from the tick (G, FABLE-FLOW-0600: remote stops and ssh timeouts inside the tick made it 463-688 s)"""
    import subprocess as _sp, time as _t
    def sh(cmd, timeout=300, input=None):
        try:
            r = _sp.run(cmd, capture_output=True, text=True, timeout=timeout, input=input)
            return r.returncode, r.stdout, r.stderr
        except _sp.TimeoutExpired:
            return 124, "", "timeout"
    hub, roots = argv[1], json.loads(argv[2])
    tag = argv[4] if len(argv) > 4 else ""
    res = stop_on_fleet(sh, hub, roots)
    line = "%s stop-bg [%s] %d root(s): %s%s" % (_t.strftime("%F %T"), tag, len(roots), " ".join(stopped_names(res))[:400] or "none running",
                                          "".join("; %s not checked: %s" % (h, v["error"]) for h, v in res.items() if v.get("error")))
    if len(argv) > 3:
        with open(argv[3], "a") as f:
            f.write(line + "\n")
    print(line)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "stop-bg":
    _cli(sys.argv[1:])
