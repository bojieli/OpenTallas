#!/usr/bin/env python3
"""release_task_watch.py -- liveness of EVERY open release-tree task, from evidence, not from its status text (TASK-WATCH, owner 10-19).

Why: on 10-18/19 the die-level gates stalled for ~15 h unnoticed (S81 real-view chain died 19:38, Qwen GEN chain 18:11,
KV real case 21:31) while RELEASE_TREE.md still said RUNNING: only elements were watched (element_owner_watch.py), not
release-tree tasks.  This watch runs every 30 min from element-owner-watch.timer, right after the element watch and
before the /release re-render, so it survives Claude session restarts and Codex takeovers.

(1) TASKS: every open line `- [ ] ID task · owner/lane · STATUS · note` of RELEASE_TREE.md (all sections: die gates
    <P>.BIND/GRT/STA/CLK and all their children, TOKEN, STUDY (MU, HMTP, HNEXT), INFRA), parsed with the renderer's parser.
(2) EVIDENCE per task (never the status text):
    names       from the line itself, and (job names / absolute paths only) from the tail of its owner lane files and from
                pending_results.txt lines of its owner lanes or naming its ID:
                closure-daemon job names (`<block>-...-<9 hex>`), absolute run paths, run tags (`dv2f14bi`, `case_p4l3_rv`,
                `kvs14p-90dedf84f`, script names), `pid N`, other tree IDs (`→ ID`), lanes/*.md files.
    runtime     one probe per fleet host + localhost (ssh, parallel, 90 s): processes whose cwd or argv names a run dir or
                tag (shell-snapshot wrappers, sleep/tail/grep watchers excluded); run dirs = the named absolute paths plus
                dirs under /srv/opentallas-scratch/{claude,codex}/ , /home/ubuntu/artifacts/ (depth <= 2) whose name is a
                run tag (primary) or contains it as a -/_ segment (related); per dir: live process, newest mtime, exit
                markers (*.done, *.exit, *.rc, EXIT, exit_code, STATUS*, chain.log, run_all.log: last `rc N` / `exit=N`).
                Closure-daemon job json (~/.local/state/closure_loop/jobs) and fleet-viz /api/fleetjobs rows by name.
    activity    owner lane file mtime; timed HANDOFF lines naming the ID or written by an owner lane; run-dir mtimes;
                named closure jobs' last update.
(3) CLASS
    LIVE              a live process in a named run dir, a live closure job / fleet job / process naming a tag, or any
                      activity < 60 min; a parent with a LIVE child task is LIVE too (unless its own chain is DEAD).
    DEAD              the newest named primary run (run dir or closure job) failed (non-zero rc / terminal-fail job) and
                      nothing named is live -- whatever the status says.  Only a HANDOFF line or owner-lane tail that names
                      the ID or the run, written after the failure and < 60 min ago, keeps it LIVE ("owner reacting").
    WAITS-OK          status WAITS/BLOCKED/TODO/NEW/REVIEW/COORD with no own evidence, and a named dependency (→ ID / ID in
                      the note) or a child task is LIVE.
    BLOCKED-ON-OWNER  status OWNER, or parked by the owner (note says NEXT RELEASE / waits on the owner).
    STALE             none of the above (no evidence for 60 min).
    Die gate lines (<P>.BIND/GRT/STA/CLK) also report whether their chain run dir finished after the last tree edit
    (a result nobody harvested).
(4) OUTPUT: TASKS_STALE.json (input contract of the coordinator's hourly check, Claude or Codex: EVERY task with
    needs_agent true -- DEAD or STALE -- gets a FRESH short agent) + TASK_WATCH_SUMMARY.txt; the /release page shows the
    banner "tasks LIVE n / STALE n / DEAD n" and the STALE/DEAD list (release_tree_render.py reads TASKS_STALE.json).

Run:  python3 release_task_watch.py [--summary] [--no-remote] [--md PATH] [--out-dir DIR]
"""
import argparse, collections, concurrent.futures, datetime, json, os, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import release_tree_render as rtr        # noqa: E402  (same directory: deployed copy or tools/auto_owner)

BASE = Path(os.environ.get('OT_COORD_DIR', str(Path.home() / 'coord')))
MD = BASE / 'RELEASE_TREE.md'
LANES = BASE / 'lanes'
HANDOFF = BASE / 'HANDOFF.md'
PENDING = BASE / 'pending_results.txt'
JOBS = Path.home() / '.local/state/closure_loop/jobs'
FLEET_URL = 'http://127.0.0.1:8765/api/fleetjobs'
OT_RUN = Path.home() / '.local/bin/ot-run'
DEFAULT_HOSTS = ['epyc2', 'epyc3', 'intel1', 'intel2']
SCAN_ROOTS = ['/srv/opentallas-scratch/claude', '/srv/opentallas-scratch/codex', '/srv/opentallas-scratch2/claude',
              '/srv/opentallas-scratch2/codex', '/home/ubuntu/artifacts']
NOT_RUN_RX = re.compile(r'^/home/ubuntu/(OpenTallas|\.ssh|\.claude|\.codex|\.config|bin)(/|$)')
DENY_PARENTS = SCAN_ROOTS + ['/srv/opentallas-scratch', '/srv/opentallas-scratch2', '/home/ubuntu', '/home/ubuntu/scratch', '/home/ubuntu/wt', str(BASE), str(BASE / 'lanes'),
                             '/home/ubuntu/bin', '/home/ubuntu/OpenTallas']
LIVE_MIN = 60.0
LIVE_JOB = {'READY', 'RUNNING', 'ECO', 'QUEUED', 'PENDING', 'SUBMITTED', 'BENCH', 'GATE'}
FAIL_JOB = {'NEEDS_HUMAN', 'NEEDS_RTL', 'EARLY_FAIL_SETUP', 'EARLY_FAIL_HOLD', 'EARLY_FAIL_CONGESTION', 'EARLY_FAIL_DRC',
            'EARLY_FAIL_STALL', 'FLOORPLAN_MARGIN', 'PREROUTE_MARGIN', 'FAILED', 'FAIL', 'INVALID', 'LOST'}
WAIT_ST = {'WAITS', 'BLOCKED', 'TODO', 'NEW', 'REVIEW', 'COORD'}
CLASSES = ['LIVE', 'WAITS-OK', 'BLOCKED-ON-OWNER', 'STALE', 'DEAD']
GATE_RX = re.compile(r'^[A-Z0-9]+\.(BIND|GRT|STA|CLK)$')
LANE_TAIL = 40
NON_LANES = {'COORD', 'COORDINATOR', 'OWNER', 'CLAUDE', 'CODEX', 'ROOT', 'COORD-REVIEW-QUEUE'}
# 2026-10-24 (INFRA.WATCH): tree owner fields name TEAMS ('QC', 'KV', 'HBM', 'TOK-QK'), lane files name LANES
# (lanes/QC-A0.md, lanes/KV-G3.md ...).  Without this map every QC/KV/HBM task had no lane file -> "no evidence found".
LANE_ALIASES = {
    'QC': ['QC-A0'],
    'KV': ['KV-G3', 'KV-TOK', 'KVG3-CORES'],
    'HBM': ['HBM-ARCH', 'ELEM-HBM'],
    'S81': ['S81', 'S81-CORES', 'S81-HEAD'],
    'TOK-QK': ['KV-TOK', 'TOK-QW'],
    'TOK-QW': ['TOK-QW'],
    'TOK-DS': ['TOK-DS'],
    'TOK-HBM': ['TOK-HBM'],
    'CLOCK': ['CLOCK'],
    'RESET': ['RESET'],
}
COORD_OWNERS = {'COORD', 'COORDINATOR'}
LANE_LIVE_MIN = 120.0     # lane-file / HANDOFF lane lines / lane run dirs: activity < 2 h keeps a task LIVE
LANE_DIR_SKIP = {'wt', 'moved', 'recovered-1023', 'geom-review', 'die-ci', 'fleet-disk'}   # shared / non-run dirs
LANE_DIR_RX = re.compile(r'/srv/opentallas-scratch2?/claude/([A-Za-z0-9][A-Za-z0-9_+\-]*)(?=/|\s|$|[,;)`\'"])')
TS_RX = re.compile(r'^(?:- )?(\d{4})-(\d{2})-(\d{2})[ T](\d{1,2}):(\d{2})(?::\d{2})?(?: (PDT|PST|UTC|GMT|SGT))?\s+([A-Za-z0-9][A-Za-z0-9_\-]*)')
TZ_OFF_H = {'PDT': -7, 'PST': -8, 'UTC': 0, 'GMT': 0, 'SGT': 8}   # coord lines are written in PDT; hosts may run UTC

NOW = time.time()


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def age_min(t, now=None):
    return None if not t else ((now or NOW) - t) / 60.0


def hm(m):
    if m is None: return 'never'
    m = max(0.0, m)
    return '%dm' % m if m < 120 else '%.1fh' % (m / 60.0)


def atomic_write(p, text):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name('.%s.%d.tmp' % (p.name, os.getpid()))
    tmp.write_text(text); os.chmod(tmp, 0o644); os.replace(tmp, p)


# ------------------------------------------------------------------------------------------------- tree
def load_tasks(md_text):
    """open tasks (dicts) in tree order, with section, parent, children and gate flag"""
    _, secs = rtr.parse_md(md_text)
    out = []

    def rec(items, sec, parent):
        for it in items:
            t = dict(id=it['id'], section=sec, status=it['status'], owner=it['owner'], task=it['task'], note=it['note'],
                     level=it['level'], checked=it['checked'], parent=parent, kids=[k['id'] for k in it['kids']],
                     gate=bool(GATE_RX.match(it['id'])))
            out.append(t)
            rec(it['kids'], sec, it['id'])
    for s in secs:
        if s['kind'] in ('RULES', 'WAITS'): continue
        rec(s['items'], s.get('key') if s['kind'] == 'DIE' else s['kind'], None)
    return out


# ------------------------------------------------------------------------------------------------- names in text
PATH_RX = re.compile(r'(/(?:srv|home/ubuntu)/[^\s,;()\'"`|<>\]\[]+)')
JOB_RX = re.compile(r'(?<![\w/.\-])([A-Za-z0-9][A-Za-z0-9_.\-]*-[0-9a-f]{9})(?![\w\-])')
HASH_RX = re.compile(r'(?<![\w/.\-])([0-9a-f]{9})(?![\w\-])')
PID_RX = re.compile(r'\bpids? (\d{3,8})\b')
TAG_RX = re.compile(r'(?<![\w/.\-])([A-Za-z0-9][A-Za-z0-9_\-]*[A-Za-z0-9](?:\.(?:sh|py|tcl))?)(?![\w/\-]|\.\w)')
HOST_RX = re.compile(r'^(ot-|epyc|agidock|pve|localhost)', re.I)
LANEFILE_RX = re.compile(r'lanes/([A-Za-z0-9_\-./]+?\.md)')
ID_RX = re.compile(r'(?<![\w.])([A-Z][A-Z0-9]*(?:\.[A-Z0-9]+)+)(?![\w.]*[\w])')


def is_tag(tok):
    if len(tok) < 6: return False
    core = re.sub(r'\.(sh|py|tcl)$', '', tok)
    if not (re.search(r'[A-Za-z]', core) and re.search(r'\d', core)): return False
    if re.fullmatch(r'[0-9a-f]{7,40}', core): return False                    # commit / bare job hash
    if re.fullmatch(r'\d+[-:x]\d+([-:x]\d+)*[A-Za-z]*', core): return False   # dates, times, 64x64
    if re.fullmatch(r'\d+(\.\d+)?[A-Za-z]{1,3}', core): return False          # 120ps, 16GB
    if HOST_RX.match(core): return False
    if re.fullmatch(r'(claude|codex)', core.split('-')[0], re.I) and re.search(r'-10\d\d$', core): return False   # branch stem
    return True


def refs_of(text, full=True):
    """names in a text; full=False (lane tails, pending lines) keeps only jobs, paths and lane files"""
    text = text or ''
    r = dict(paths=set(), jobs=set(), hashes=set(), tags=set(), pids=set(), lanefiles=set(), ids=set())
    for m in PATH_RX.finditer(text):
        p = m.group(1).rstrip('.:,;)')
        if len(p) > 12 and not NOT_RUN_RX.match(p): r['paths'].add(p)
    for m in JOB_RX.finditer(text): r['jobs'].add(m.group(1))
    for m in LANEFILE_RX.finditer(text): r['lanefiles'].add(m.group(1))
    if not full: return r
    for m in HASH_RX.finditer(text): r['hashes'].add(m.group(1))
    for m in PID_RX.finditer(text): r['pids'].add(int(m.group(1)))
    clean = PATH_RX.sub(' ', text)
    for m in TAG_RX.finditer(clean):
        if is_tag(m.group(1)): r['tags'].add(m.group(1))
    for m in ID_RX.finditer(text): r['ids'].add(m.group(1))
    return r


def owner_lanes(owner):
    """lane names of an owner field ('S81-DIE8', 'OWN-S81/SLICEPAR', 'H-D4G / DIE-HBM-LEAD', 'QXPQ-FIX/coordinator')"""
    parts = [p.strip() for p in re.split(r'[/,+]| and ', owner or '') if p.strip()]
    out = []
    for p in parts:
        p = p.split()[0] if p.split() else p
        if p.upper() in NON_LANES or not re.match(r'^[A-Za-z0-9][A-Za-z0-9_\-]+$', p): continue
        out.append(p)
    return out


def owner_tokens(owner):
    """raw upper-case owner tokens, NON_LANES included ('S81 / QC / KV / HBM' -> S81, QC, KV, HBM)"""
    return [p.strip().split()[0].upper() for p in re.split(r'[/,+]| and ', owner or '') if p.strip()]


def owner_lane_names(owner):
    """owner tokens + the lane names they map to (LANE_ALIASES): used to match HANDOFF '<lane>:' lines"""
    out = list(owner_lanes(owner))
    for p in owner_lanes(owner):
        out += LANE_ALIASES.get(p.upper(), [])
    return list(dict.fromkeys(out))


def lane_paths(owner, lanefiles=()):
    parts = owner_lanes(owner)
    cands = []
    for p in parts: cands.append(LANES / (p + '.md'))
    for p in parts: cands += [LANES / (q + '.md') for q in LANE_ALIASES.get(p.upper(), [])]
    if len(parts) >= 2:
        cands += [LANES / ('%s_%s.md' % (parts[0], q)) for q in parts[1:]]
        cands += [LANES / parts[0] / (q + '.md') for q in parts[1:]]
    cands += [LANES / f for f in lanefiles]
    seen, out = set(), []
    for c in cands:
        if c in seen: continue
        seen.add(c)
        if c.is_file(): out.append(c)
    return out


# ------------------------------------------------------------------------------------------------- inputs
HO_RX = re.compile(r'^- \[([^\]]+)\]\s*(?:(\d{2})-(\d{2})\s+)?(\d{1,2}):(\d{2})')
HO2_RX = re.compile(r'^- (\d{2})-(\d{2})\s+~?(\d{1,2}):(\d{2})')


def handoff_lines(text, now=None):
    """[(lane or None, t, line)] for timed HANDOFF bullet lines"""
    now = now or NOW
    today = datetime.datetime.fromtimestamp(now)
    out = []
    for l in text.splitlines():
        m = TS_RX.match(l)        # current form: '2026-10-24 21:14 PDT COORD: ...' (also '- 2026-10-24 ...')
        if m:
            try:
                dt = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)))
                if m.group(6) in TZ_OFF_H:
                    dt = dt.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=TZ_OFF_H[m.group(6)])))
                t = dt.timestamp()
            except ValueError: continue
            if t > now + 300: continue
            out.append((m.group(7), t, l))
            continue
        m = HO_RX.match(l); lane = None
        if m:
            lane = re.split(r'[\s/]', m.group(1).strip())[0]
            mo, dd, hh, mm = m.group(2), m.group(3), int(m.group(4)), int(m.group(5))
        else:
            m = HO2_RX.match(l)
            if not m: continue
            mo, dd, hh, mm = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        if hh > 23 or mm > 59: continue
        try:
            dt = today.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if mo: dt = dt.replace(month=int(mo), day=int(dd))
        except ValueError: continue
        t = dt.timestamp()
        if not mo and t > now + 300: t -= 86400
        if t > now + 300: continue
        out.append((lane, t, l))
    return out


def load_pending(text):
    out = []
    for l in text.splitlines():
        if not l.strip() or l.startswith('#'): continue
        f = [x.strip() for x in l.split('|')]
        out.append((f[-1] if len(f) >= 3 else '', l))
    return out


def load_jobs(max_age_d=10, jobs_dir=JOBS):
    jobs = {}
    for f in jobs_dir.glob('*.json') if jobs_dir.is_dir() else []:
        try:
            mt = f.stat().st_mtime
            if NOW - mt > max_age_d * 86400: continue
            d = json.loads(f.read_text())
        except Exception: continue
        name = d.get('name') or f.stem
        upd = mt
        try: upd = datetime.datetime.fromisoformat(str(d.get('updated'))).timestamp()
        except Exception: pass
        jobs[name] = dict(name=name, status=str(d.get('status')), t=upd)
    return jobs


def job_index(jobs):
    by_hash = collections.defaultdict(list)
    for n in jobs:
        m = re.search(r'-([0-9a-f]{9})(?:-[a-z0-9]+)?$', n)
        if m: by_hash[m.group(1)].append(n)
    return by_hash


def match_jobs(jobs, by_hash, job_tokens, hashes):
    """named closure jobs: exact name, or same 9-hex suffix whose name contains the token's first segment"""
    out = set()
    for tok in job_tokens:
        if tok in jobs: out.add(tok); continue
        h = tok[-9:]; head = tok[:-10].split('-')[0]
        for n in by_hash.get(h, []):
            if head and head in n: out.add(n)
    for h in hashes:
        out.update(by_hash.get(h, []))
    return out


def fleet_hosts():
    try:
        m = re.search(r'^HOSTS\s*=\s*(\[[^\]]*\])', OT_RUN.read_text(), re.M)
        hs = json.loads(m.group(1).replace("'", '"'))
        if hs: return hs
    except Exception: pass
    return list(DEFAULT_HOSTS)


# ------------------------------------------------------------------------------------------------- host probe
PROBE = r'''
import os, re, json, time
D = json.loads(%r)
now = time.time(); me = os.getpid(); par = os.getppid()
try: clk = os.sysconf('SC_CLK_TCK')
except Exception: clk = 100
btime = 0
for l in open('/proc/stat'):
    if l.startswith('btime'): btime = int(l.split()[1])
SKIP0 = {'sleep', 'tail', 'less', 'cat', 'grep', 'pgrep', 'ps', 'watch', 'inotifywait', 'ssh', 'sshd', 'timeout'}
procs = []
for p in os.listdir('/proc'):
    if not p.isdigit(): continue
    pid = int(p)
    if pid in (me, par): continue
    try:
        cmd = open('/proc/%%d/cmdline' %% pid, 'rb').read().split(b'\0')
        cmd = [c.decode('utf-8', 'replace') for c in cmd if c]
        if not cmd: continue
        st = open('/proc/%%d/stat' %% pid).read().rsplit(')', 1)[1].split()
        start = btime + int(st[19]) / float(clk)
    except Exception: continue
    try: cwd = os.readlink('/proc/%%d/cwd' %% pid)
    except Exception: cwd = ''
    s = ' '.join(cmd)
    b0 = os.path.basename(cmd[0])
    if s.startswith('ssh:') or 'shell-snapshots' in s or 'release_task_watch' in s or ('until ' in s and 'sleep ' in s): continue
    if b0 in SKIP0 and not (b0 == 'timeout' and len(cmd) > 2): continue
    if b0 in ('bash', 'sh') and len(cmd) >= 3 and cmd[1] == '-c' and re.match(r'\s*(sleep|tail|grep|cat|ls|until|while)\b', cmd[2]): continue
    fds = []
    try:
        for fd in os.listdir('/proc/%%d/fd' %% pid)[:64]:
            try: l = os.readlink('/proc/%%d/fd/%%s' %% (pid, fd))
            except Exception: continue
            if l.startswith(('/srv/', '/home/')): fds.append(l)
    except Exception: pass
    procs.append((pid, start, cwd, s, fds))
roots = []
for r in D['roots']:
    try: l1 = [e.path for e in os.scandir(r) if e.is_dir(follow_symlinks=False)]
    except Exception: continue
    roots += l1
    for d in l1:
        try: roots += [e.path for e in os.scandir(d) if e.is_dir(follow_symlinks=False)]
        except Exception: pass
tags = D['tags']
found = {}
for d in roots:
    b = os.path.basename(d)
    for t in tags:
        if b == t or b == re.sub(r'\.(sh|py|tcl)$', '', t): found.setdefault(d, []).append([t, 1])
        elif re.search(r'(^|[-_])' + re.escape(t) + r'($|[-_])', b): found.setdefault(d, []).append([t, 0])
for p in D['paths']:
    q = p.rstrip('/')
    if not os.path.exists(q): continue
    found.setdefault(q, []).append([p, 2])
    par = os.path.dirname(q)
    if os.path.isfile(q) and par not in D['deny'] and par.count('/') >= 4: found.setdefault(par, []).append([p, 2])
MARK = re.compile(r'(\.done|\.exit|\.rc|\.status|^EXIT|exit_code|^STATUS(\.log|\.txt)?|^chain[^/]*\.log|^run_all\.log|^DONE|^FAILED)$')
RC = re.compile(r'(?:\brc\s*[=: ]\s*|\bexit(?:_code| code| status)?\s*[=: ]\s*|process_exit=|EXIT\s+)(-?\d+)')
def probe(d):
    info = dict(path=d, isdir=os.path.isdir(d))
    try: info['mtime'] = os.stat(d).st_mtime
    except Exception: info['mtime'] = 0
    newest = info['mtime']; marks = []; n = 0
    if info['isdir']:
        stack = [(d, 0)]
        while stack and n < 3000:
            cur, lev = stack.pop()
            try: ents = list(os.scandir(cur))
            except Exception: continue
            for e in ents:
                n += 1
                try: st = e.stat(follow_symlinks=False)
                except Exception: continue
                newest = max(newest, st.st_mtime)
                if e.is_dir(follow_symlinks=False):
                    if lev == 0: stack.append((e.path, 1))
                    continue
                if MARK.search(e.name):
                    rc = None
                    try:
                        with open(e.path, 'rb') as f:
                            f.seek(max(0, st.st_size - 4096)); txt = f.read().decode('utf-8', 'replace')
                        ms = RC.findall(txt)
                        if ms: rc = int(ms[-1])
                        elif e.name.endswith(('.exit', '.rc')) or e.name.startswith(('EXIT', 'exit_code')):
                            s = txt.strip().split()
                            if s and re.fullmatch(r'-?\d+', s[-1]): rc = int(s[-1])
                    except Exception: pass
                    fin = rc is not None or bool(re.search(r'(\.done|\.exit|\.rc|^EXIT|exit_code|^DONE|^FAILED)$', e.name))
                    if fin: marks.append(dict(f=os.path.relpath(e.path, d), t=st.st_mtime, rc=rc))
    info['newest'] = newest
    marks.sort(key=lambda m: m['t'])
    info['marks'] = marks[-6:]
    pr = []
    for pid, start, cwd, s, fds in procs:
        if cwd == d or cwd.startswith(d + '/') or d in s or any(f == d or f.startswith(d + '/') for f in fds):
            pr.append([pid, round(start), s[:200]])
    pr.sort(key=lambda x: x[1])
    info['procs'] = pr[:6]; info['nprocs'] = len(pr)
    return info
runs = {}
for d, hits in found.items():
    i = probe(d); i['hits'] = hits; runs[d] = i
tagprocs = {}
for t in tags:
    rx = re.compile(r'(^|[\s/=:"\'])' + re.escape(t) + r'($|[\s/."\'_-])')
    L = [[pid, round(start), s[:200]] for pid, start, cwd, s, fds in procs if rx.search(s)]
    if L: tagprocs[t] = L[:4]
lanedirs = {}
for nm in D.get('lanedirs', []):
    for r in D.get('laneroots', []):
        d = r + '/' + nm
        if not os.path.isdir(d): continue
        try: newest = os.stat(d).st_mtime
        except Exception: newest = 0
        stack = [(d, 0)]; n = 0
        while stack and n < 4000:
            cur, lev = stack.pop()
            try: ents = list(os.scandir(cur))
            except Exception: continue
            for e in ents:
                n += 1
                try: newest = max(newest, e.stat(follow_symlinks=False).st_mtime)
                except Exception: continue
                if lev < 2 and e.is_dir(follow_symlinks=False): stack.append((e.path, lev + 1))
        pr = [[pid, round(start), s[:200]] for pid, start, cwd, s, fds in procs
              if cwd == d or cwd.startswith(d + '/') or (d + '/') in s or s.endswith(d)]
        pr.sort(key=lambda x: x[1])
        lanedirs.setdefault(nm, []).append(dict(path=d, newest=newest, nprocs=len(pr), procs=pr[:3]))
pids = {}
for pid in D['pids']:
    try: pids[pid] = ' '.join(c.decode('utf-8', 'replace') for c in open('/proc/%%d/cmdline' %% pid, 'rb').read().split(b'\0') if c)[:200]
    except Exception: pass
print(json.dumps(dict(now=now, runs=runs, tagprocs=tagprocs, pids=pids, nprocs=len(procs), lanedirs=lanedirs)))
'''
LANE_ROOTS = ['/srv/opentallas-scratch/claude', '/srv/opentallas-scratch2/claude']


def probe_script(paths, tags, pids, lanedirs=()):
    return PROBE % json.dumps(dict(paths=sorted(paths), tags=sorted(tags), pids=sorted(pids), roots=SCAN_ROOTS, deny=DENY_PARENTS,
                                   lanedirs=sorted(lanedirs), laneroots=LANE_ROOTS))


def lane_dirs_of(lane_file, text):
    """run-dir names (under /srv/opentallas-scratch*/claude/) of one lane: its lower-case name + every claude/<x> it names"""
    out = {Path(lane_file).stem.lower()}
    out |= {m.group(1) for m in LANE_DIR_RX.finditer(text or '')}
    return {d for d in out if d not in LANE_DIR_SKIP}


def lane_last_activity(text, mtime):
    """newest timestamped line of a lane file ('2026-10-24 21:33 PDT QC: ...'); the file mtime only when it has none
    (the epyc1 ~/coord mirror resets mtimes on every fast-forward, so mtime alone over-reports activity)"""
    ts = [t for _, t, _ in handoff_lines(text or '')]
    return max(ts) if ts else mtime


def run_probe(host, script, timeout=90):
    if host == 'localhost':
        cmd = ['python3', '-I', '-']
    else:
        cmd = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', '-o', 'ControlPath=none', host, 'python3', '-I', '-']
    try:
        p = subprocess.run(cmd, input=script, capture_output=True, text=True, timeout=timeout)
        if p.returncode: return None, 'rc %d: %s' % (p.returncode, p.stderr.strip()[-200:])
        return json.loads(p.stdout), None
    except Exception as e:   # noqa: BLE001
        return None, str(e)[:200]


def probe_all(hosts, paths, tags, pids, lanedirs=()):
    script = probe_script(paths, tags, pids, lanedirs)
    res, errs = {}, {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as ex:
        futs = {ex.submit(run_probe, h, script): h for h in hosts}
        for f in concurrent.futures.as_completed(futs):
            h = futs[f]; d, e = f.result()
            if d is None: errs[h] = e
            else: res[h] = d
    return res, errs


# ------------------------------------------------------------------------------------------------- evidence
def run_state(r):
    """RUNNING / OK / FAIL / IDLE of one probed run dir"""
    if r.get('nprocs'): return 'RUNNING', None, None
    ms = [m for m in r.get('marks') or [] if m.get('rc') is not None]
    fin = r.get('marks') or []
    if ms:
        m = ms[-1]
        return ('OK' if m['rc'] == 0 else 'FAIL'), m['rc'], m['t']
    if fin: return 'OK', None, fin[-1]['t']     # done marker without an rc
    return 'IDLE', None, None


def build_refs(t, lane_texts, pending):
    """names of a task. Tier 'own' = its own line (full scan); tier 'lane' = job names / absolute paths in the tail of its
    owner lane files and in pending_results lines of its owner lanes or naming its ID (used only when the line names no run)"""
    line = '%s %s' % (t['task'], t['note'])
    r = refs_of(line)
    lanes = owner_lanes(t['owner'])
    t['lane_files'] = [str(p) for p in lane_paths(t['owner'], r['lanefiles'])]
    r['lane_jobs'], r['lane_paths'] = set(), set()
    for lp in t['lane_files']:
        tail = '\n'.join(lane_texts.get(lp, '').splitlines()[-LANE_TAIL:])
        rr = refs_of(tail, full=False)
        r['lane_jobs'] |= rr['jobs']; r['lane_paths'] |= rr['paths']
    idrx = re.compile(r'(?<![\w.])%s(?![\w.]*\w)' % re.escape(t['id']))
    for lane, l in pending:
        if (lane and lane in lanes) or idrx.search(l):
            rr = refs_of(l.split('|')[0], full=False)
            r['lane_jobs'] |= rr['jobs']; r['lane_paths'] |= rr['paths']
    r['lane_jobs'] -= r['jobs']; r['lane_paths'] -= r['paths']
    # a bare scratch root / lane root named in prose ('/srv/opentallas-scratch2 87%') is not a run: its probe would match
    # every ot-run command line on the fleet (they all name both scratch roots)
    r['lane_paths'] = {p for p in r['lane_paths'] if p.rstrip('/') not in DENY_PARENTS and p.rstrip('/').count('/') >= 4}
    r['words'] = {w for w in re.findall(r'[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+|[A-Za-z]{4,}\w*', line) if len(w) >= 4}
    return r


def _runs_for(probes, paths, tags):
    runs = []
    for host, d in probes.items():
        for path, info in (d.get('runs') or {}).items():
            ks = [k for tg, k in info.get('hits') or [] if (k == 2 and tg in paths) or (k in (0, 1) and tg in tags)]
            if not ks: continue
            st, rc, tend = run_state(info)
            runs.append(dict(host=host, path=path, primary=max(ks) >= 1, state=st, rc=rc, t_end=tend,
                             newest=info.get('newest') or 0, isdir=info.get('isdir'), procs=info.get('procs') or []))
    return runs


def gather(tasks, md_mtime, lane_texts, lane_mtimes, hand, pending, jobs, fleet_rows, probes, probe_errs, now=None):
    """evidence dict per task id (pure: every input is passed in)"""
    now = now or NOW
    by_hash = job_index(jobs)
    ev = {}
    for t in tasks:
        r = t['refs']
        e = dict(live=[], activity=[], react=[], runs=[], jobs=[], dead=None, notes=[], harvest=None, tier='own',
                 lane_live=[], lane_act=[])
        tags = r['tags']
        own_runs = _runs_for(probes, r['paths'], tags)
        hashes = {h for h in r['hashes'] if any(len(w) >= 6 and w in n.split('-')[0] for n in by_hash.get(h, []) for w in r.get('words', ()))}
        own_jobs = sorted(match_jobs(jobs, by_hash, r['jobs'], hashes))
        if not (own_runs or own_jobs) and t['gate']:   # 'same chain': a die gate line shares its die's chain with the other gate lines
            for o in tasks:
                if o is not t and o['gate'] and o['section'] == t['section']:
                    own_runs += _runs_for(probes, o['refs']['paths'], o['refs']['tags'])
                    own_jobs = sorted(set(own_jobs) | match_jobs(jobs, by_hash, o['refs']['jobs'], set()))
            if own_runs or own_jobs: e['notes'].append('no run named on the line: uses the runs of the other %s gate lines' % t['section'])
        if own_runs or own_jobs:
            runs, jnames = own_runs, own_jobs
        else:   # the line names no run: fall back to its owner lanes / pending_results
            runs = _runs_for(probes, r.get('lane_paths', set()), set())
            jnames = sorted(match_jobs(jobs, by_hash, r.get('lane_jobs', set()), set()))
            e['tier'] = 'lane' if (runs or jnames) else 'none'
        e['runs'] = runs
        for x in runs:
            if x['state'] == 'RUNNING' and (x['primary'] or not any(y['primary'] for y in runs)):
                e['live'].append('%s:%s running (%s)' % (x['host'], x['path'], x['procs'][0][2][:80] if x['procs'] else ''))
            if x['newest']: e['activity'].append((x['newest'], 'run %s:%s touched' % (x['host'], x['path'])))
        # processes naming a tag of the line that has no run dir
        dir_names = {x['path'].rsplit('/', 1)[-1] for x in runs}
        for host, d in probes.items():
            for tag, L in (d.get('tagprocs') or {}).items():
                if tag in tags and not any(tag in b for b in dir_names):
                    e['live'].append('%s: process naming %s (pid %s: %s)' % (host, tag, L[0][0], L[0][2][:80]))
        for pid in sorted(r['pids']):
            if probes and not any(str(pid) in (d.get('pids') or {}) for d in probes.values()):
                e['notes'].append('named pid %d is not running on any probed host' % pid)
        # closure-daemon jobs + fleet-viz rows
        for n in jnames:
            j = jobs[n]
            e['jobs'].append(dict(name=n, status=j['status'], t=j['t']))
            if j['status'] in LIVE_JOB: e['live'].append('closure job %s %s' % (n, j['status']))
            e['activity'].append((j['t'], 'closure job %s %s' % (n, j['status'])))
        jtoks = r['jobs'] if e['tier'] == 'own' else r.get('lane_jobs', set())
        for row in fleet_rows:
            nm = row.get('name') or ''
            if nm and (any(j in nm for j in jtoks) or any(len(tg) >= 8 and tg in nm for tg in tags)):
                e['live'].append('fleet %s %s on %s' % (row.get('kind', 'job'), nm, row.get('host')))
        # lane + HANDOFF activity (lane-level evidence: LANE_LIVE_MIN window, never overrides DEAD)
        lanes = set(owner_lane_names(t['owner']))
        idrx = re.compile(r'(?<![\w.])%s(?![\w.]*\w)' % re.escape(t['id']))
        named = [t['id']] + sorted(tags)[:20] + sorted(r['jobs'])[:20]
        nrx = re.compile('|'.join(r'(?<![\w.])%s(?![\w])' % re.escape(x) for x in named))
        seen_dirs = set()
        for lp in t['lane_files']:
            ln = Path(lp).name
            txt = lane_texts.get(lp, '')
            la = lane_last_activity(txt, lane_mtimes.get(lp))
            if la:
                e['activity'].append((la, 'lane %s' % ln)); e['lane_act'].append((la, 'lane %s' % ln))
            tail = '\n'.join(txt.splitlines()[-LANE_TAIL:])
            if la and nrx.search(tail): e['react'].append((la, 'lane %s names it' % ln))
            for nm in sorted(lane_dirs_of(lp, txt)):     # the lane's run dirs on every probed host
                for host, d in probes.items():
                    for x in (d.get('lanedirs') or {}).get(nm, []):
                        if (host, x['path']) in seen_dirs: continue
                        seen_dirs.add((host, x['path']))
                        if x.get('nprocs'):
                            e['lane_live'].append('%s:%s running, %d proc (lane %s: %s)' % (
                                host, x['path'], x['nprocs'], ln, x['procs'][0][2][:80] if x.get('procs') else ''))
                        if x.get('newest'): e['lane_act'].append((x['newest'], 'lane run dir %s:%s touched' % (host, x['path'])))
        coord = bool(set(owner_tokens(t['owner'])) & COORD_OWNERS) or t['status'] == 'COORD'   # the renderer reads '· COORD ·' as the status
        last_comp = t['id'].rsplit('.', 1)[-1]
        crx = re.compile(r'(?<![\w.])%s(?![\w])' % re.escape(last_comp), re.I) if len(last_comp) >= 4 else None
        for lane, ht, l in hand:
            if idrx.search(l):
                e['activity'].append((ht, 'HANDOFF names %s' % t['id'])); e['react'].append((ht, 'HANDOFF names %s' % t['id']))
                if lane and (lane in lanes or (coord and lane.upper() in COORD_OWNERS)):
                    e['lane_act'].append((ht, 'HANDOFF [%s] names %s' % (lane, t['id'])))
            elif lane and lane in lanes:
                e['activity'].append((ht, 'HANDOFF [%s]' % lane)); e['lane_act'].append((ht, 'HANDOFF [%s]' % lane))
                if nrx.search(l): e['react'].append((ht, 'HANDOFF [%s] names it' % lane))
            elif coord and lane and lane.upper() in COORD_OWNERS and crx and crx.search(l):
                e['lane_act'].append((ht, 'HANDOFF [%s] names %s' % (lane, last_comp)))
        # dead: the newest named primary run dir / closure job failed and nothing named is live
        cands = [(x['newest'] or x['t_end'] or 0, 'run', x) for x in runs if x['primary'] and x['isdir']]
        cands += [(j['t'], 'job', j) for j in e['jobs']]
        if cands and not e['live']:
            tnew, kind, x = max(cands, key=lambda c: c[0])
            if e['tier'] == 'lane':   # lane / pending names can prove a task LIVE, never DEAD (they may belong to other tasks)
                cands = []
            if not cands:
                pass
            elif kind == 'run' and x['state'] == 'FAIL':
                e['dead'] = dict(what='%s:%s exit rc %s' % (x['host'], x['path'], x['rc']), t=x['t_end'] or tnew)
            elif kind == 'job' and x['status'] in FAIL_JOB:
                e['dead'] = dict(what='closure job %s %s' % (x['name'], x['status']), t=x['t'])
        if t['gate']:
            ok = [x for x in runs if x['primary'] and x['state'] == 'OK' and x['t_end'] and x['t_end'] > md_mtime]
            if ok: e['harvest'] = '%s:%s finished rc 0 at %s, after the last tree edit' % (
                ok[-1]['host'], ok[-1]['path'], datetime.datetime.fromtimestamp(ok[-1]['t_end']).strftime('%m-%d %H:%M'))
            if not any(x['primary'] and x['isdir'] for x in runs): e['notes'].append('no die-chain run dir found from the line / lane')
        if probe_errs: e['notes'].append('probe failed on %s' % ', '.join(sorted(probe_errs)))
        ev[t['id']] = e
    return ev


# ------------------------------------------------------------------------------------------------- classify
def own_class(t, e, now=None):
    now = now or NOW
    last = max([a[0] for a in e['activity']] or [0])
    if e['live']: return 'LIVE', e['live'][0], last
    if e['dead']:
        rk = [a for a in e['react'] if a[0] > (e['dead']['t'] or 0) and age_min(a[0], now) < LIVE_MIN]
        if rk: return 'LIVE', 'owner reacting after %s: %s' % (e['dead']['what'], rk[-1][1]), last
        return 'DEAD', e['dead']['what'], last
    fresh = [a for a in e['activity'] if age_min(a[0], now) is not None and age_min(a[0], now) < LIVE_MIN]
    if fresh:
        a = max(fresh, key=lambda x: x[0])
        return 'LIVE', '%s %s ago' % (a[1], hm(age_min(a[0], now))), last
    if e.get('lane_live'): return 'LIVE', e['lane_live'][0], last
    lfresh = [a for a in e.get('lane_act', []) if a[0] <= now + 300 and age_min(a[0], now) < LANE_LIVE_MIN]
    if lfresh:
        a = max(lfresh, key=lambda x: x[0])
        return 'LIVE', '%s %s ago' % (a[1], hm(age_min(a[0], now))), max(last, a[0])
    return None, None, max([last] + [a[0] for a in e.get('lane_act', [])])


def parked(t):
    return t['status'] == 'OWNER' or bool(re.search(r'NEXT RELEASE|wait\w* on (the )?owner|owner decides|parked by (the )?owner',
                                                     '%s %s' % (t['task'], t['note']), re.I))


def classify(tasks, ev, now=None):
    now = now or NOW
    byid = {t['id']: t for t in tasks}
    own = {t['id']: own_class(t, ev[t['id']], now) for t in tasks}
    memo, busy = {}, set()

    def cls(i):
        if i in memo: return memo[i]
        if i in busy: return ('STALE', 'dependency cycle')
        busy.add(i)
        t = byid[i]; c, why, _ = own[i]
        if c == 'LIVE' or c == 'DEAD':
            res = (c, why)
        else:
            kids_live = [k for k in t['kids'] if k in byid and cls(k)[0] in ('LIVE', 'WAITS-OK')]
            deps = [d for d in sorted(t['refs']['ids']) if d in byid and d != i and not d.startswith(i + '.') and not i.startswith(d + '.')]
            deps_live = [d for d in deps if cls(d)[0] in ('LIVE', 'WAITS-OK')]   # waiting on a task that itself waits OK is OK
            if parked(t):
                res = ('BLOCKED-ON-OWNER', 'status %s / parked by the owner' % t['status'])
            elif kids_live and t['status'] not in WAIT_ST:
                res = ('LIVE', 'child task live: %s' % ', '.join(kids_live[:4]))
            elif kids_live or deps_live:
                res = ('WAITS-OK', 'waits on live %s' % ', '.join((deps_live + kids_live)[:4]))
            else:
                bad = [d for d in deps if cls(d)[0] in ('DEAD', 'STALE')]
                last = own[i][2]
                why = 'no evidence for %s' % hm(age_min(last, now)) if last else 'no evidence found'
                if t['status'] in ('COORD', 'REVIEW'): why += '; waits on the coordinator'
                if bad: why += '; waits on %s' % ', '.join('%s (%s)' % (d, cls(d)[0]) for d in bad[:3])
                res = ('STALE', why)
        busy.discard(i); memo[i] = res
        return res

    out = []
    for t in tasks:
        c, why = cls(t['id']); e = ev[t['id']]
        last = own[t['id']][2]
        out.append(dict(id=t['id'], section=t['section'], owner=t['owner'], status_text=t['status'], cls=c, why=why,
                        task=t['task'][:160], last_evidence_min=None if not last else round(age_min(last, now), 1),
                        live=e['live'][:4], lane_live=e['lane_live'][:3], dead=e['dead'], harvest=e['harvest'], notes=e['notes'][:4],
                        runs=[dict(host=x['host'], path=x['path'], primary=x['primary'], state=x['state'], rc=x['rc'])
                              for x in sorted(e['runs'], key=lambda x: -(x['newest'] or 0))[:5]],
                        jobs=[dict(name=j['name'], status=j['status']) for j in sorted(e['jobs'], key=lambda j: -j['t'])[:5]],
                        lane_files=[Path(p).name for p in t['lane_files']], gate=t['gate'], parent=t['parent'],
                        needs_agent=c in ('DEAD', 'STALE'), mismatch=(t['status'] in ('RUNNING', 'PASS') and c in ('DEAD', 'STALE'))))
    return out


# ------------------------------------------------------------------------------------------------- output
def summary(res, gen, errs):
    c = collections.Counter(r['cls'] for r in res)
    L = ['TASK WATCH %s: open tasks %d -- LIVE %d / WAITS-OK %d / BLOCKED-ON-OWNER %d / STALE %d / DEAD %d%s' % (
        gen, len(res), c['LIVE'], c['WAITS-OK'], c['BLOCKED-ON-OWNER'], c['STALE'], c['DEAD'],
        ('  (probe failed: %s)' % ', '.join(sorted(errs))) if errs else '')]
    for cl in ('DEAD', 'STALE'):
        rows = [r for r in res if r['cls'] == cl]
        if not rows: continue
        L.append('%s (%d) -- each needs a FRESH agent from the hourly check:' % (cl, len(rows)))
        for r in rows:
            L.append('  %-8s %-26s %-8s %-22s %s%s' % (cl, r['id'], r['status_text'], (r['owner'] or '-')[:22], r['why'][:150],
                                                     '  [tree says %s]' % r['status_text'] if r['mismatch'] else ''))
    hv = [r for r in res if r.get('harvest')]
    for r in hv: L.append('HARVEST %s: %s' % (r['id'], r['harvest']))
    g = [r for r in res if r['gate']]
    if g: L.append('die gates: ' + ' | '.join('%s %s' % (r['id'], r['cls']) for r in g))
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--md', default=str(MD))
    ap.add_argument('--out-dir', default=str(BASE))
    ap.add_argument('--no-remote', action='store_true', help='probe localhost only')
    ap.add_argument('--summary', action='store_true')
    a = ap.parse_args(argv)
    md = Path(a.md)
    tasks = [t for t in load_tasks(md.read_text()) if not t['checked']]
    lane_texts, lane_mtimes = {}, {}
    for f in list(LANES.glob('*.md')) + list(LANES.glob('*/*.md')):
        try: lane_mtimes[str(f)] = f.stat().st_mtime; lane_texts[str(f)] = f.read_text(errors='replace')
        except OSError: pass
    try: hand = handoff_lines(HANDOFF.read_text(errors='replace'))
    except OSError: hand = []
    try: pending = load_pending(PENDING.read_text(errors='replace'))
    except OSError: pending = []
    for t in tasks: t['refs'] = build_refs(t, lane_texts, pending)
    paths = set().union(*[t['refs']['paths'] | t['refs']['lane_paths'] for t in tasks]) if tasks else set()
    tags = set().union(*[t['refs']['tags'] for t in tasks]) if tasks else set()
    pids = set().union(*[t['refs']['pids'] for t in tasks]) if tasks else set()
    lanedirs = set()
    for lp in {lp for t in tasks for lp in t['lane_files']}: lanedirs |= lane_dirs_of(lp, lane_texts.get(lp, ''))
    hosts = list(dict.fromkeys(['localhost'] + ([] if a.no_remote else fleet_hosts())))
    log('tasks %d open; probing %s for %d paths / %d tags / %d lane dirs' % (len(tasks), ','.join(hosts), len(paths), len(tags), len(lanedirs)))
    probes, errs = probe_all(hosts, paths, tags, pids, lanedirs)
    jobs = load_jobs()
    try:
        import urllib.request
        with urllib.request.urlopen(FLEET_URL, timeout=60) as f: fleet = json.load(f).get('rows', [])
    except Exception as e:   # noqa: BLE001
        log('fleetjobs', e); fleet = []
    ev = gather(tasks, md.stat().st_mtime, lane_texts, lane_mtimes, hand, pending, jobs, fleet, probes, errs)
    res = classify(tasks, ev)
    gen = datetime.datetime.fromtimestamp(NOW).strftime('%Y-%m-%d %H:%M')
    cnt = collections.Counter(r['cls'] for r in res)
    out = dict(generated=gen, generated_t=NOW, source=str(md), tree_mtime=md.stat().st_mtime, hosts=hosts, probe_errors=errs,
               counts=dict(open=len(res), **{k: cnt.get(k, 0) for k in CLASSES}, needs_agent=sum(r['needs_agent'] for r in res)),
               contract='hourly check (Claude or Codex coordinator): every task with needs_agent true (DEAD or STALE) gets a FRESH '
                        'short agent (common_brief + the task row); mismatch = the tree status says RUNNING/PASS',
               tasks=res)
    od = Path(a.out_dir)
    atomic_write(od / 'TASKS_STALE.json', json.dumps(out, indent=1))
    s = summary(res, gen, errs)
    atomic_write(od / 'TASK_WATCH_SUMMARY.txt', s)
    if a.summary: sys.stdout.write(s)
    return 0


if __name__ == '__main__':
    sys.exit(main())
