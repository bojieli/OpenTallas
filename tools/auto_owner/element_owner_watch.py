#!/usr/bin/env python3
"""element_owner_watch.py -- every open element of the current dies has a live job or a live owner (AUTO-OWNER, owner 10-18).

The owner noticed 2-3 times a day that open elements sat with no live job and no one driving them.  This watch makes that
automatic.  It runs every 30 min from element-owner-watch.timer (user systemd), then re-renders the release tree, whose
/release page shows the banner "ACTIVE n / STALE n / UNOWNED n".

(1) STATE of every open element (rows of http://localhost:8765/api/elements with 'dies', category not closed/superseded):
    live job      closure-daemon job (READY/RUNNING/ECO/QUEUED/...) of the block or of a kit naming it, a fleet ref_gate /
                  bench / ot-run job naming it (fleet-viz /api/fleetjobs), a local ot-run client naming it; for a parent,
                  a live or ACTIVE child (dies[].parents) counts.
    owner/activity newest of: a lanes/*.md file that names it (mtime counts only when the mention sits in the last 40
                  lines -- an old mention gives the owner lane but no fresh time), a timed HANDOFF line '- [LANE] 10-18 HH:MM'
                  naming it, a pending_results.txt line naming it (lane; time = the named closure job's last update),
                  commits on origin branches that touch a kit dir of the element, the end of its last closure job.
    ACTIVE   live job, or activity < 60 min
    STALE    an owner, no live job, activity 60-180 min
    UNOWNED  no owner, or activity > 180 min
(2) AUTOMATIC ACTIONS (no agent; only with --act; each logged to lanes/AUTO-OWNER.md + auto_owner/actions.jsonl):
    A. kit-prepared, not critical (critical_tiles.txt), no live job/gate, newest kit branch has a PASSING gate
       (verdict PASS/WARN, trial GRT overflow 0, TT and FF pin-flop spread <= 80): main's submit_exact
       (`submit_exact.py physical/ref_tile/<kit>/job.json --follow-head --regate --gate-args '--remote auto --cts'`, so a
       gate that no longer binds the source is re-run on the exact commit and the job is submitted when it passes);
    B. kit-prepared, not critical, no live job/gate, NO gate result: the same command in the background (it launches the
       gate --remote auto --cts and submits when it passes);
    C. flow failure (OOM / earlyoom kill / disk / harness LOST / ssh / docker) of a job whose spec carried an approved
       reroute_reason: resubmit that spec with reroute_reason {kind: flow_failure, failed_job, failure} via submit_exact;
    D. critical tile with a passing gate: append one entry to lanes/COORD-REVIEW-QUEUE.md (never submitted here);
       a REVIEW_REQUIRED refusal of A/B is queued the same way.
    Never touches a closed view: closed / superseded elements are not acted on, and submit_exact + the daemon's
    CLOSED-STANDS gate refuse a re-route without an approved reroute_reason.  Worktrees are sparse, detached, under
    /home/ubuntu/wt/auto-owner/<kit>; each auto action on an element is retried at most once per 6 h.
(3) OUTPUT: UNOWNED.json (the input contract of the coordinator's hourly check, Claude or Codex: every element with
    needs_agent true -- UNOWNED/STALE and no automatic action -- gets a fresh family agent) + ELEMENT_OWNER_SUMMARY.txt.

Run:  python3 element_owner_watch.py [--act] [--summary] [--no-fetch]
"""
import argparse, collections, datetime, glob, json, os, re, shlex, subprocess, sys, tempfile, time, urllib.request
from pathlib import Path

BASE = Path('/home/ubuntu/claude-takeover-20261007')
LANES = BASE / 'lanes'
HANDOFF = BASE / 'HANDOFF.md'
PENDING = BASE / 'pending_results.txt'
CRIT = BASE / 'critical_tiles.txt'
OUT = BASE / 'UNOWNED.json'
SUMMARY = BASE / 'ELEMENT_OWNER_SUMMARY.txt'
STATE_DIR = BASE / 'auto_owner'
ACTLOG = STATE_DIR / 'actions.jsonl'
LANE_LOG = LANES / 'AUTO-OWNER.md'
REVIEW_Q = LANES / 'COORD-REVIEW-QUEUE.md'
REPO = Path('/home/ubuntu/OpenTallas')
GITDIR = REPO / '.git'
WT_ROOT = Path('/home/ubuntu/wt/auto-owner')
JOBS = Path.home() / '.local/state/closure_loop/jobs'
FV_STATE = Path.home() / '.local/state/fleet-viz'
EL_URL = 'http://127.0.0.1:8765/api/elements'
FLEET_URL = 'http://127.0.0.1:8765/api/fleetjobs'
LIVE_ST = {'READY', 'RUNNING', 'ECO', 'QUEUED', 'PENDING', 'SUBMITTED', 'BENCH', 'GATE'}
TERMINAL_FAIL = {'NEEDS_HUMAN', 'NEEDS_RTL', 'EARLY_FAIL_SETUP', 'EARLY_FAIL_HOLD', 'EARLY_FAIL_CONGESTION', 'EARLY_FAIL_DRC',
                 'EARLY_FAIL_STALL', 'FLOORPLAN_MARGIN', 'PREROUTE_MARGIN'}
FLOW_RX = re.compile(r'out of memory|\bOOM\b|oom[-_ ]kill|earlyoom|SIGKILL|rc=137|exit (code )?137|No space left|ENOSPC|disk full|'
                     r'disk floor|LOST: stage wrapper|harness|ssh[^;]{0,40}(fail|timed out|refused)|Connection (reset|closed|refused)|'
                     r'docker: Error|container [^;]{0,30}(died|vanished)|host unreachable|retired from hosts', re.I)
ACTIVE_MIN, STALE_MIN = 60.0, 180.0
RETRY_H = 6.0
MAX_SUBMITS, MAX_GATES, MAX_FLOW = 6, 4, 4
SPREAD_MAX = 80.0
ROSTER_N = 8          # a lane tail / HANDOFF line naming more elements than this is a roster: owner, not activity
NOW = time.time()


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def git(*args, cwd=None, timeout=900, check=False):
    cmd = ['git', '-C', str(cwd)] if cwd else ['git', '--git-dir', str(GITDIR)]
    p = subprocess.run(cmd + list(args), capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError('git %s: %s' % (' '.join(args[:3]), p.stderr.strip()[:300]))
    return p.stdout


def cat_batch(objs):
    """{'<ref>:<path>': text or None} via one git cat-file --batch"""
    out = {}
    if not objs: return out
    p = subprocess.run(['git', '--git-dir', str(GITDIR), 'cat-file', '--batch'], input=('\n'.join(objs) + '\n').encode(),
                       capture_output=True, timeout=900)
    buf = p.stdout; i = 0
    for o in objs:
        j = buf.index(b'\n', i); head = buf[i:j].decode(errors='replace'); i = j + 1
        if head.endswith(' missing') or head.endswith(' ambiguous'):
            out[o] = None; continue
        n = int(head.split()[-1]); out[o] = buf[i:i + n].decode(errors='replace'); i += n + 1
    return out


def fetch_json(url, timeout=150):
    with urllib.request.urlopen(url, timeout=timeout) as f: return json.load(f)


def ago_min(t): return (NOW - t) / 60.0 if t else None


def hm(minutes):
    if minutes is None: return 'never'
    return '%dm' % minutes if minutes < 120 else '%.1fh' % (minutes / 60.0)


def atomic_write(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix='.' + p.name + '.')
    with os.fdopen(fd, 'w') as f: f.write(text)
    os.chmod(tmp, 0o644); os.replace(tmp, p)


# ------------------------------------------------------------------------------------------------- inputs
def load_elements():
    try:
        d = fetch_json(EL_URL)
        rows = [r for r in d.get('rows', []) if r.get('dies')]
        if rows: return rows, None
        err = 'element table has no current-die rows (warming?)'
    except Exception as e:  # noqa: BLE001
        err = 'element table unreachable: %s' % e
    try:   # the release renderer's last good copy
        return json.loads((FV_STATE / 'release_tree_elements_cache.json').read_text())['rows'], err + '; using release_tree_elements_cache.json'
    except Exception as e:  # noqa: BLE001
        raise SystemExit('no element table: %s / %s' % (err, e))


def is_open(r):
    c = r.get('category') or ''
    return not (c.startswith('closed') or c == 'superseded' or r.get('superseded'))


def load_jobs(max_age_d=10):
    jobs = {}
    for f in glob.glob(str(JOBS / '*.json')):
        try:
            mt = os.path.getmtime(f)
            if NOW - mt > max_age_d * 86400: continue
            d = json.load(open(f))
        except Exception: continue
        s = d.get('spec') or {}
        cmd = ((s.get('stages') or {}).get('route') or {}).get('cmd', '') if isinstance(s.get('stages'), dict) else ''
        m = re.search(r'physical/ref_tile/([^/\s]+)/kit\.env', cmd or '')
        upd = mt
        try: upd = datetime.datetime.fromisoformat(str(d.get('updated'))).timestamp()
        except Exception: pass
        jobs[d.get('name') or Path(f).stem] = dict(name=d.get('name') or Path(f).stem, status=str(d.get('status')), block=s.get('block'),
                                                   kit=m.group(1) if m else None, t=upd, reason=str(d.get('reason') or ''),
                                                   owner=s.get('owner'), crashes=d.get('crashes') or [], path=f)
    return jobs


def load_clients():
    out = []
    r = subprocess.run(['ps', '-eo', 'pid,etimes,args'], capture_output=True, text=True)
    for l in r.stdout.splitlines()[1:]:
        p = l.split(None, 2)
        if len(p) == 3 and re.search(r'(ot-run|pre_route_gate\.py|submit_exact\.py)', p[2]) and 'element_owner_watch' not in p[2]:
            out.append(dict(pid=int(p[0]), elapsed=int(p[1]), text=p[2]))
    return out


def load_critical():
    out = []
    try:
        for l in CRIT.read_text().splitlines():
            l = l.strip()
            if l and not l.startswith('#'): out.append(l.split()[0])
    except OSError: pass
    return out


def is_critical(names, crit):
    return next((c for c in crit for n in names if n and n.startswith(c)), None)


def kit_index(no_fetch=False):
    """kit -> {refs: [(t, ref, commit)] newest first} from origin branches (4 days) + main kits; kit -> spec top"""
    if not no_fetch:
        subprocess.run(['git', '-C', str(REPO), 'fetch', '-q', '--prune', 'origin'], capture_output=True, timeout=900)
    txt = git('log', '--remotes=origin', '--since=4.days', '--no-renames', '--source', '--format=C\t%H\t%ct\t%S', '--name-only',
              '--', 'physical/ref_tile', timeout=1200)
    kits = collections.defaultdict(list); cur = None
    for l in txt.splitlines():
        if l.startswith('C\t'):
            _, h, ct, src = l.split('\t'); cur = (int(ct), src.replace('refs/remotes/', ''), h); continue
        m = re.match(r'physical/ref_tile/([^/]+)/', l)
        if m and cur:
            L = kits[m.group(1)]
            if not L or L[-1] != cur: L.append(cur)
    for k in kits: kits[k].sort(reverse=True)
    main_kits = set()
    for l in git('ls-tree', '-d', '--name-only', 'origin/main', 'physical/ref_tile/').splitlines():
        main_kits.add(l.rsplit('/', 1)[-1])
    objs = ['origin/main:physical/ref_tile/%s/spec.json' % k for k in main_kits]
    for k, L in kits.items():
        objs.append('%s:physical/ref_tile/%s/spec.json' % (L[0][1], k))
    blobs = cat_batch(objs)
    top = {}
    for o, t in blobs.items():
        if not t: continue
        k = o.split('physical/ref_tile/')[1].split('/')[0]
        try: tp = json.loads(t).get('top')
        except Exception: tp = None
        if tp and (k not in top or not o.startswith('origin/main:')): top[k] = tp
    return kits, main_kits, top


def contract_kits():
    try: d = json.loads((FV_STATE / 'die_contracts_live.json').read_text())
    except Exception: return {}, {}
    return d.get('kits') or {}, d.get('aliases') or {}


# ------------------------------------------------------------------------------------------------- mentions
def stem(n):
    n = re.sub(r'^(ot_|qfd_|qkd_|hfd_|dsfd_|dsdv_|hbm_|hgi_)', '', n)
    return n


def alias_rx(names):
    al = sorted({n for n in names if n and len(n) >= 6}, key=len, reverse=True)
    if not al: return None
    return re.compile(r'(?<![A-Za-z0-9_])(%s)(?![A-Za-z0-9])' % '|'.join(re.escape(a) for a in al))


HO_RX = re.compile(r'^- \[([^\]]+)\]\s*(?:(\d{2})-(\d{2})\s+)?(\d{1,2}):(\d{2})')


def handoff_lines():
    out = []
    try: text = HANDOFF.read_text(errors='replace')
    except OSError: return out
    today = datetime.datetime.fromtimestamp(NOW)
    for l in text.splitlines():
        m = HO_RX.match(l)
        tag = None; t = None
        if m:
            tag = m.group(1)
            hh, mm = int(m.group(4)), int(m.group(5))
            if hh > 23 or mm > 59: continue
            m2 = re.search(r'(\d{1,2}):(\d{2})$', tag)    # '- [LANE 10:08]' carries its time in the tag
            if m.group(2):
                try: dt = today.replace(month=int(m.group(2)), day=int(m.group(3)), hour=hh, minute=mm, second=0, microsecond=0)
                except ValueError: continue
            else:
                dt = today.replace(hour=hh, minute=mm, second=0, microsecond=0)
                if dt.timestamp() > NOW + 300: dt -= datetime.timedelta(days=1)
            t = dt.timestamp()
            if t > NOW + 300: t = None
        else:
            m = re.match(r'^- \[([^\]]+)\]', l)
            if not m: continue
            tag = m.group(1)
            m2 = re.search(r'\s(\d{1,2}):(\d{2})$', tag)
            if m2:
                dt = today.replace(hour=int(m2.group(1)) % 24, minute=int(m2.group(2)) % 60, second=0, microsecond=0)
                if dt.timestamp() > NOW + 300: dt -= datetime.timedelta(days=1)
                t = dt.timestamp()
        lane = re.split(r'[\s/]', tag.strip())[0] if tag else None
        out.append((lane, t, l))
    return out


def lane_files(max_age_h=48):
    out = []
    for f in glob.glob(str(LANES / '*.md')) + glob.glob(str(LANES / '*/*.md')):
        p = Path(f)
        if p.name in ('AUTO-OWNER.md', 'COORD-REVIEW-QUEUE.md', 'ELEMENT-TABLE.md', 'ELEM-GAPS.md'): continue
        try:
            mt = p.stat().st_mtime
            if NOW - mt > max_age_h * 3600: continue
            lines = p.read_text(errors='replace').splitlines()
        except OSError: continue
        lane = p.stem if p.parent == LANES else p.parent.name.replace('_logs', '') + '/' + p.stem
        out.append(dict(lane=lane, t=mt, lines=lines))
    return out


def pending_lines():
    try: return [l for l in PENDING.read_text(errors='replace').splitlines() if l.strip() and not l.startswith('#')]
    except OSError: return []


# ------------------------------------------------------------------------------------------------- gate results
def gate_ok(g):
    """(ok, why) for a gate_result.json dict: verdict PASS/WARN, trial GRT overflow 0, TT+FF pin-flop spread <= 80"""
    if not isinstance(g, dict): return False, 'no gate result'
    v = g.get('verdict')
    if v not in ('PASS', 'WARN'): return False, 'gate verdict %s' % v
    tr = g.get('trial_route') or {}
    ovf = tr.get('overflow')
    if ovf is None: return False, 'gate has no trial GRT'
    if ovf != 0: return False, 'trial GRT overflow %s' % ovf
    c = g.get('clock') or {}
    if not g.get('cts') and not c.get('cts'): return False, 'gate without CTS'
    tt = c.get('tt_pin_spread_ps', c.get('tt_spread_ps')); ff = c.get('ff_pin_spread_ps', c.get('ff_spread_ps'))
    if tt is None or ff is None: return False, 'gate lacks TT/FF pin-flop spread'
    if tt > SPREAD_MAX or ff > SPREAD_MAX: return False, 'pin-flop spread TT %.1f / FF %.1f > 80' % (tt, ff)
    return True, '%s, GRT ovf 0, spread TT %.1f / FF %.1f' % (v, tt, ff)


# ------------------------------------------------------------------------------------------------- state
def load_state():
    try: return json.loads((STATE_DIR / 'state.json').read_text())
    except Exception: return dict(actions={}, review_queued={}, bg={})


def save_state(st):
    atomic_write(STATE_DIR / 'state.json', json.dumps(st, indent=1, sort_keys=True))


def record(kind, element, detail, st, act):
    ent = dict(t=datetime.datetime.fromtimestamp(NOW).isoformat(timespec='seconds'), kind=kind, element=element, act=act, **detail)
    if act:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(ACTLOG, 'a') as f: f.write(json.dumps(ent) + '\n')
        st['actions'][element + '|' + kind] = NOW
    return ent


def recently_acted(st, element, kind):
    t = st['actions'].get(element + '|' + kind)
    return t and NOW - t < RETRY_H * 3600


# ------------------------------------------------------------------------------------------------- worktrees
def sparse_wt(name, ref, patterns):
    """detached sparse (no-cone) worktree /home/ubuntu/wt/auto-owner/<name> at ref with exactly these patterns"""
    wt = WT_ROOT / name
    WT_ROOT.mkdir(parents=True, exist_ok=True)
    if not (wt / '.git').exists():
        subprocess.run(['git', '-C', str(REPO), 'worktree', 'add', '--no-checkout', '--detach', str(wt), ref],
                       capture_output=True, text=True, timeout=600, check=True)
    top = git('rev-parse', '--show-toplevel', cwd=wt).strip()
    if top != str(wt):
        raise RuntimeError('worktree toplevel %r != %s' % (top, wt))
    git('sparse-checkout', 'set', '--no-cone', *sorted(set(patterns)), cwd=wt, check=True)
    git('checkout', '-q', '--detach', '--force', ref, cwd=wt, check=True)
    return wt


PATH_TOKEN = re.compile(r'(?<![A-Za-z0-9_./-])((?:physical|rtl|results|tools|testdata|docs)/[A-Za-z0-9_.+\-/]*[A-Za-z0-9_])')


def sparse_patterns(spec, kit, ref):
    """what a submit / re-gate of <kit> reads: tools/, rtl/, the small top-level files of every physical/<dir>/ (shared SDC /
    tcl / json the kit generator reads), the kit dir, the spec's sources + extra_paths, and every repo path the kit files
    name.  Never the 20 GB of other kits' views."""
    src = spec.get('source') or {}
    toks = set(str(p).strip('/') for p in list(spec.get('sources') or []) + list(src.get('extra_paths') or []) if p and not str(p).startswith('/'))
    kd = 'physical/ref_tile/%s' % kit
    ls = git('ls-tree', '-r', '-l', ref, kd + '/')
    objs = []
    for l in ls.splitlines():
        meta, path = l.split('\t', 1)
        size = meta.split()[3]
        if re.search(r'/(views|gate_layout|source_binding_history)/', path) or not size.isdigit() or int(size) > 400000: continue
        if re.search(r'\.(json|env|tcl|sdc|mk|sh|py|txt|v|sv)$', path): objs.append('%s:%s' % (ref, path))
    for t in cat_batch(objs).values():
        if t: toks |= set(PATH_TOKEN.findall(t))
    toks = {t for t in toks if not t.startswith(kd) and '..' not in t}
    pats = {'/tools/', '/rtl/', '/physical/*/*.*', '/%s/' % kd}
    if toks:
        chk = subprocess.run(['git', '--git-dir', str(GITDIR), 'cat-file', '--batch-check'], capture_output=True, timeout=300,
                             input=''.join('%s:%s\n' % (ref, t) for t in sorted(toks)).encode()).stdout.decode(errors='replace').splitlines()
        for t, c in zip(sorted(toks), chk):
            typ = c.split()[1] if len(c.split()) >= 3 else None
            if typ == 'blob': pats.add('/' + t)
            elif typ == 'tree' and not re.match(r'^(physical/ref_tile|physical|rtl|tools|docs|testdata|results(/[^/]+)?)$', t):
                pats.add('/' + t + '/')
    return sorted(pats)


def cleanup_wt(wt):
    """remove an auto-owner worktree whose commits are all on origin and which has no local edits; else keep it"""
    wt = Path(wt)
    if not (wt / '.git').exists() or WT_ROOT not in wt.parents: return 'gone'
    if git('rev-parse', '--show-toplevel', cwd=wt).strip() != str(wt): return 'kept (toplevel mismatch)'
    if git('log', '--oneline', '-1', 'HEAD', '--not', '--remotes=origin', cwd=wt).strip(): return 'kept (unpushed commit)'
    if git('status', '--porcelain', '--untracked-files=no', cwd=wt).strip(): return 'kept (local edits)'
    p = subprocess.run(['git', '-C', str(REPO), 'worktree', 'remove', '--force', str(wt)], capture_output=True, text=True, timeout=600)
    return 'removed' if p.returncode == 0 else 'kept (%s)' % p.stderr.strip()[:100]


def bg_outcome(logf):
    try: t = Path(logf).read_text(errors='replace')
    except OSError: return 'no log', None
    t = t[t.rfind('\n=== '):] if '\n=== ' in t else t
    m = re.search(r'^SUBMITTED (\S+)', t, re.M)
    if m: return 'SUBMITTED %s' % m.group(1), 'submitted'
    m = re.search(r'^(REFUSED LOCALLY[^\n]*)', t, re.M)
    if m:
        return m.group(1)[:300], 'review' if 'REVIEW' in m.group(1) else 'refused'
    tail = [l for l in t.strip().splitlines() if l.strip()][-1:] or ['(empty log)']
    return 'ended: ' + tail[0][:300], 'error'


def run_bg(cmd, cwd, logf):
    logf.parent.mkdir(parents=True, exist_ok=True)
    with open(logf, 'ab') as lf:
        lf.write(('\n=== %s %s (cwd %s)\n' % (datetime.datetime.now().isoformat(timespec='seconds'), ' '.join(map(shlex.quote, cmd)), cwd)).encode())
        p = subprocess.Popen(cmd, cwd=str(cwd), stdout=lf, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, start_new_session=True)
    return p.pid


def pid_alive(pid):
    try:
        if int(pid) <= 1: return False
        os.kill(int(pid), 0); return True
    except Exception: return False


# ------------------------------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--act', action='store_true', help='perform the automatic actions (default: report what would be done)')
    ap.add_argument('--summary', action='store_true', help='print the summary')
    ap.add_argument('--no-fetch', action='store_true')
    ap.add_argument('--out', default=str(OUT))
    a = ap.parse_args(argv)
    rows, el_err = load_elements()
    open_rows = [r for r in rows if is_open(r)]
    log('elements: %d current-die rows, %d open' % (len(rows), len(open_rows)))
    jobs = load_jobs()
    try: fleet = fetch_json(FLEET_URL, 60).get('rows', [])
    except Exception as e: log('fleetjobs', e); fleet = []
    clients = load_clients()
    crit = load_critical()
    ckits, caliases = contract_kits()
    log('git kit index ...')
    kits_hist, main_kits, kit_top = kit_index(a.no_fetch)
    st = load_state()
    st.setdefault('bg', {}); st.setdefault('results', {}); st.setdefault('actions', {}); st.setdefault('review_queued', {})
    finished = []
    for k, v in list(st['bg'].items()):
        if pid_alive(v.get('pid')): continue
        st['bg'].pop(k)
        out, cls = bg_outcome(v.get('log'))
        wtst = cleanup_wt(v['wt']) if a.act and v.get('wt') else 'kept (dry run)'
        st['results'][v.get('element') or k] = dict(kit=k, what=v.get('what'), outcome=out, cls=cls, t=NOW, wt=wtst, log=v.get('log'),
                                                     ref=v.get('ref'))
        ent = dict(t=datetime.datetime.fromtimestamp(NOW).isoformat(timespec='seconds'), kind='finished', element=v.get('element') or k,
                   kit=k, what=v.get('what'), outcome=out, wt=wtst)
        finished.append(ent)
        if a.act:
            with open(ACTLOG, 'a') as f: f.write(json.dumps(ent) + '\n')

    # ---- names per element
    top_kits = collections.defaultdict(set)
    for k, t in kit_top.items(): top_kits[t].add(k)
    names, kits_of = {}, {}
    for r in open_rows:
        e = r['element']
        ks = set(ckits.get(e) or []) | top_kits.get(e, set())
        m = re.match(r'kit (.+?) committed', r.get('via') or '')
        if m: ks |= {x.strip() for x in m.group(1).split(',')}
        ks |= {j['kit'] for j in jobs.values() if j['block'] == e and j['kit']}
        nm = {e} | set(r.get('variants') or []) | set(caliases.get(e) or []) | ks
        names[e] = nm; kits_of[e] = sorted(ks)
    blocks_of = {e: names[e] for e in names}

    # ---- live jobs
    live = collections.defaultdict(list)
    by_block = collections.defaultdict(list)
    for j in jobs.values():
        if j['block']: by_block[j['block']].append(j)
    elem_of_name = {}
    for e, nm in names.items():
        for n in nm: elem_of_name.setdefault(n, e)
    for j in jobs.values():
        if j['status'] in LIVE_ST:
            e = elem_of_name.get(j['block']) or elem_of_name.get(j['kit'])
            if e: live[e].append('daemon %s %s' % (j['status'], j['name']))
    rxs = {e: alias_rx(nm) for e, nm in names.items()}
    big = alias_rx(list(elem_of_name))
    live_kits = set()
    for f in fleet:
        if f.get('kind') == 'loop route': continue      # daemon jobs counted above from the state files
        txt = '%s %s' % (f.get('name') or '', f.get('detail') or '')
        m = re.match(r'ref_gate (\S+)', f.get('name') or '')
        if m: live_kits.add(m.group(1))
        for h in set(big.findall(txt)) if big else ():
            e = elem_of_name[h]
            live[e].append('fleet %s %s %s' % (f.get('host'), f.get('kind'), (f.get('name') or '')[:60]))
    for c in clients:
        m = re.search(r'ref_gate_(.+?)_\d{8}-\d{6}\.sh', c['text']) or re.search(r'pre_route_gate\.py\s+(?:physical/ref_tile/)?([^\s/]+)', c['text'])
        if m: live_kits.add(m.group(1))
        for h in set(big.findall(c['text'])) if big else ():
            live[elem_of_name[h]].append('local pid %d %s' % (c['pid'], c['text'][:70]))
    for k, v in st.get('bg', {}).items():
        e = v.get('element')
        if e: live[e].append('auto-owner pid %s %s' % (v.get('pid'), v.get('what', '')))

    # ---- activity
    act = collections.defaultdict(list)     # element -> [(t or None, lane, what)]
    for lf in lane_files():
        n = len(lf['lines']); hits = {}
        text_tail = '\n'.join(lf['lines'][max(0, n - 40):]); text_all = '\n'.join(lf['lines'])
        for h in set(big.findall(text_all)) if big else ():
            hits[elem_of_name[h]] = False
        tail_hits = {elem_of_name[h] for h in (set(big.findall(text_tail)) if big else ())}
        if len(tail_hits) <= ROSTER_N:      # a dispatcher roster / table naming many elements is not activity on each
            for e in tail_hits: hits[e] = True
        for e, recent in hits.items():
            act[e].append((lf['t'] if recent else None, lf['lane'], 'lanes/%s.md' % lf['lane']))
    for lane, t, l in handoff_lines():
        hs = {elem_of_name[h] for h in (set(big.findall(l)) if big else ())}
        for e in hs:
            act[e].append((t if len(hs) <= ROSTER_N else None, lane, 'HANDOFF'))
    for l in pending_lines():
        parts = [p.strip() for p in l.split(' | ')]
        lane = parts[-1] if len(parts) >= 3 else None
        jt = None
        for tok in re.findall(r'[A-Za-z0-9_.\-]{12,}', parts[0] if parts else l):
            if tok in jobs: jt = max(jt or 0, jobs[tok]['t'])
        for h in set(big.findall(l)) if big else ():
            act[elem_of_name[h]].append((jt, lane, 'pending_results'))
    for e, ks in kits_of.items():
        for k in ks:
            for (t, ref, h) in kits_hist.get(k, [])[:3]:
                if 'closure-record' in ref: continue
                act[e].append((t, ref.replace('origin/', '').split('/')[-1] if '/' in ref else ref, 'commit %s %s kit %s' % (h[:9], ref, k)))
    for e, nm in names.items():
        for n in nm:
            for j in by_block.get(n, []):
                if j['status'] not in LIVE_ST:
                    act[e].append((j['t'], j['owner'] or None, 'job %s %s' % (j['name'], j['status'])))

    # ---- element state
    res = {}
    for r in open_rows:
        e = r['element']
        A = act.get(e, [])
        timed = [x for x in A if x[0]]
        newest = max(timed, key=lambda x: x[0]) if timed else None
        lanes = [x[1] for x in sorted(A, key=lambda x: -(x[0] or 0)) if x[1]]
        owner = (newest[1] if newest and newest[1] else None) or (lanes[0] if lanes else None) or r.get('owner_stream') or r.get('owner') or None
        am = ago_min(newest[0]) if newest else None
        L = sorted(set(live.get(e, [])))
        if L or (am is not None and am < ACTIVE_MIN): s = 'ACTIVE'
        elif owner and am is not None and am <= STALE_MIN: s = 'STALE'
        else: s = 'UNOWNED'
        res[e] = dict(element=e, dies=[d.get('design') for d in r['dies']], roles=sorted({d.get('role') or '' for d in r['dies']}),
                      parents=sorted({p for d in r['dies'] for p in (d.get('parents') or [])}), category=r.get('category'),
                      state=s, owner=owner, owner_stream=r.get('owner_stream'), last_activity=newest[2] if newest else None,
                      last_activity_t=newest[0] if newest else None, age_min=round(am, 1) if am is not None else None,
                      live=L[:6], kits=kits_of.get(e, []), critical=is_critical(names[e], crit), auto=None, needs_agent=False)
    # a parent with an ACTIVE child is ACTIVE (the leaves are under way)
    for e, x in res.items():
        if x['state'] == 'ACTIVE': continue
        kids = [k for k, y in res.items() if e in y['parents'] and y['state'] == 'ACTIVE']
        if kids:
            x['state'] = 'ACTIVE'; x['live'] = x['live'] + ['child ACTIVE: ' + ', '.join(kids[:4])]

    # ---- automatic actions
    actions = []
    nsub = ngate = nflow = 0
    gate_objs = []
    pick = {}
    for e, x in res.items():
        if x['category'] != 'kit prepared, no route job': continue
        cands = []
        for k in x['kits']:
            if re.search(r'diag', k): continue
            H = [h for h in kits_hist.get(k, []) if 'closure-record' not in h[1]]
            ref = H[0][1] if H else ('origin/main' if k in main_kits else None)
            if ref: cands.append(((H[0][0] if H else 0), k, ref))
        if cands:
            cands.sort(reverse=True); pick[e] = cands
            for _, k, ref in cands:
                gate_objs += ['%s:physical/ref_tile/%s/gate_result.json' % (ref, k), '%s:physical/ref_tile/%s/job.json' % (ref, k)]
    blobs = cat_batch(gate_objs)
    for e, cands in pick.items():
        x = res[e]
        best = None
        for _, k, ref in cands:
            gtxt = blobs.get('%s:physical/ref_tile/%s/gate_result.json' % (ref, k))
            jtxt = blobs.get('%s:physical/ref_tile/%s/job.json' % (ref, k))
            try: g = json.loads(gtxt) if gtxt else None
            except ValueError: g = None
            ok, why = gate_ok(g)
            cand = dict(kit=k, ref=ref, gate=why, gate_ok=ok, has_gate=g is not None, has_job=bool(jtxt),
                        gate_generated=(g or {}).get('generated'), spec=jtxt)
            if best is None or (ok and not best['gate_ok']): best = cand
            if ok: break
        if not best: continue
        k, ref = best['kit'], best['ref']
        busy = x['live'] or k in live_kits
        base = dict(kit=k, ref=ref, gate=best['gate'])
        if busy:
            x['auto'] = 'kit %s: live work, no action' % k; continue
        if not best['has_job']:
            x['auto'] = None; x['auto_note'] = 'kit %s on %s has no job.json (needs an owner)' % (k, ref); continue
        if x['critical']:
            if best['gate_ok']:
                key = '%s@%s' % (k, best['gate_generated'])
                try: qtext = REVIEW_Q.read_text(errors='replace')
                except OSError: qtext = ''
                if any(re.search(r'(?<![A-Za-z0-9_])%s(?![A-Za-z0-9_])' % re.escape(k), l) and '~~' not in l.split('|')[0]
                       for l in qtext.splitlines() if l.startswith('- ')):
                    x['auto'] = 'critical: already in COORD-REVIEW-QUEUE'; continue
                if key in st['review_queued']:
                    x['auto'] = 'critical: in COORD-REVIEW-QUEUE since %s' % st['review_queued'][key]; continue
                ent = record('review_queue', e, base, st, a.act)
                if a.act:
                    br = ref.replace('origin/', '')
                    with open(REVIEW_Q, 'a') as f:
                        f.write('- %s (AUTO-OWNER %s, critical prefix %s) | %s | gate %s | physical/ref_tile/%s/gate_layout/{floorplan,density}.png on %s | '
                                'after REVIEW.json: from a sparse wt of %s (tools from origin/main): python3 tools/closure_loop/submit_exact.py '
                                'physical/ref_tile/%s/job.json --follow-head\n' % (k, datetime.datetime.fromtimestamp(NOW).strftime('%m-%d %H:%M'),
                                                                                  x['critical'], ref, best['gate'], k, br, br, k))
                    st['review_queued'][key] = datetime.datetime.fromtimestamp(NOW).strftime('%m-%d %H:%M')
                actions.append(ent); x['auto'] = 'critical: queued for coordinator review'
            else:
                x['auto_note'] = 'critical kit %s: %s (owner must gate; coordinator reviews)' % (k, best['gate'])
            continue
        kind = 'submit' if best['gate_ok'] else ('gate_and_submit' if not best['has_gate'] else None)
        if kind is None:
            x['auto_note'] = 'kit %s gate not passing (%s): needs an owner' % (k, best['gate']); continue
        if recently_acted(st, e, kind):
            pr = st['results'].get(e) or {}
            if pr.get('cls') == 'review' and ('%s@review' % k) not in st['review_queued']:
                if a.act:
                    br = ref.replace('origin/', '')
                    with open(REVIEW_Q, 'a') as f:
                        f.write('- %s (AUTO-OWNER %s, submit_exact REVIEW_REQUIRED) | %s | gate %s | physical/ref_tile/%s/gate_layout/{floorplan,density}.png on %s | '
                                'after REVIEW.json: python3 tools/closure_loop/submit_exact.py physical/ref_tile/%s/job.json --follow-head '
                                '(sparse wt of %s) | %s\n' % (k, datetime.datetime.fromtimestamp(NOW).strftime('%m-%d %H:%M'), ref, best['gate'], k, br, k, br,
                                                             pr.get('outcome', '')[:200]))
                    st['review_queued']['%s@review' % k] = datetime.datetime.fromtimestamp(NOW).strftime('%m-%d %H:%M')
                actions.append(record('review_queue', e, dict(base, why=pr.get('outcome')), st, a.act))
                x['auto'] = 'REVIEW_REQUIRED: queued for coordinator review'; continue
            if pr.get('cls') in ('refused', 'error'):
                x['auto_note'] = 'auto %s of %s REFUSED (%s): owner must fix; log %s' % (kind, k, pr.get('outcome', '')[:160], pr.get('log'))
            elif pr.get('cls') == 'review':
                x['auto'] = 'REVIEW_REQUIRED: in COORD-REVIEW-QUEUE'
            else:
                x['auto'] = '%s tried < %.0f h ago: %s' % (kind, RETRY_H, pr.get('outcome', 'see auto_owner/actions.jsonl')[:120])
            continue
        if kind == 'submit' and nsub >= MAX_SUBMITS or kind == 'gate_and_submit' and ngate >= MAX_GATES:
            x['auto_note'] = '%s deferred (per-run cap)' % kind; continue
        cmd = [sys.executable, 'tools/closure_loop/submit_exact.py', 'physical/ref_tile/%s/job.json' % k, '--follow-head',
               '--regate', '--gate-args', '--remote auto --cts']
        detail = dict(base, cmd=' '.join(shlex.quote(c) for c in cmd))
        if a.act:
            try:
                spec = json.loads(best['spec'])
                wt = sparse_wt(k, ref, sparse_patterns(spec, k, ref))
                logf = STATE_DIR / 'logs' / ('%s-%s.log' % (k, kind))
                pid = run_bg(cmd, wt, logf)
                st['bg'][k] = dict(pid=pid, element=e, what=kind, t=NOW, log=str(logf), wt=str(wt), ref=ref)
                detail.update(pid=pid, log=str(logf), wt=str(wt))
            except Exception as ex:  # noqa: BLE001
                detail['error'] = str(ex)[:300]
        actions.append(record(kind, e, detail, st, a.act))
        x['auto'] = '%s %s (%s)' % (kind, k, best['gate'])
        nsub += kind == 'submit'; ngate += kind == 'gate_and_submit'

    # flow failures with an approved reroute
    for e, x in res.items():
        for n in names[e]:
            J = sorted(by_block.get(n, []), key=lambda j: j['t'])
            if not J: continue
            j = J[-1]
            if j['status'] not in TERMINAL_FAIL or NOW - j['t'] > 48 * 3600: continue
            cr = (j['crashes'] or [{}])[-1]
            flow = bool(FLOW_RX.search(j['reason'])) or cr.get('cls') == 'oom_kill' or (cr.get('resource') and j['status'] == 'NEEDS_HUMAN')
            if not flow: continue
            try: d = json.load(open(j['path']))
            except Exception: continue
            spec = d.get('spec_submitted') or d.get('spec') or {}
            rr = spec.get('reroute_reason')
            if not isinstance(rr, dict) or not rr.get('kind'):
                x['auto_note'] = 'flow failure of %s (%s) without an approved reroute: owner decides' % (j['name'], j['status']); continue
            if x['live'] or recently_acted(st, e, 'flow_resubmit') or nflow >= MAX_FLOW:
                continue
            c9 = str((spec.get('source') or {}).get('commit') or '')[:9]
            nm = spec.get('name') or j['name']
            new = re.sub(r'-%s$' % re.escape(c9), '', nm) + '-ffr' + ('-' + c9 if c9 else '')
            spec2 = dict(spec, name=new, reroute_reason=dict(kind='flow_failure', failed_job=j['name'],
                                                             failure=(j['reason'] or j['status'])[:200], prior=rr.get('kind')))
            detail = dict(failed_job=j['name'], status=j['status'], new_name=new, failure=j['reason'][:160])
            if a.act:
                try:
                    kit = j['kit'] or ''
                    br = (spec.get('source') or {}).get('commit')
                    wt = sparse_wt('ffr-' + (kit or n), br, sparse_patterns(spec, kit, br) if kit else ['/tools/', '/rtl/'])
                    sp = STATE_DIR / 'specs' / (new + '.json'); atomic_write(sp, json.dumps(spec2, indent=1))
                    logf = STATE_DIR / 'logs' / (new + '.log')
                    pid = run_bg([sys.executable, 'tools/closure_loop/submit_exact.py', str(sp), '--no-push'], wt, logf)
                    st['bg']['ffr-' + n] = dict(pid=pid, element=e, what='flow_resubmit', t=NOW, log=str(logf), wt=str(wt))
                    detail.update(pid=pid, log=str(logf), spec=str(sp))
                except Exception as ex:  # noqa: BLE001
                    detail['error'] = str(ex)[:300]
            actions.append(record('flow_resubmit', e, detail, st, a.act)); nflow += 1
            x['auto'] = 'flow_failure resubmit of %s' % j['name']
            break

    for x in res.values():
        pr = st['results'].get(x['element'])
        if pr: x['auto_last'] = '%s %s: %s' % (pr.get('what'), pr.get('kit'), pr.get('outcome'))
    actions = finished + actions
    for x in res.values():
        x['needs_agent'] = x['state'] in ('UNOWNED', 'STALE') and not x['auto']
    cnt = collections.Counter(x['state'] for x in res.values())
    doc = dict(schema='opentallas.auto_owner.unowned.v1', generated=datetime.datetime.fromtimestamp(NOW).isoformat(timespec='seconds'),
               generated_t=NOW, act=a.act, element_table_note=el_err,
               rule='ACTIVE = live job or activity < %d min; STALE = owner, no live job, activity %d-%d min; UNOWNED = no owner or > %d min. '
                    'Coordinator hourly check (Claude or Codex): every element with needs_agent true gets a fresh family agent '
                    '(one per family, compact brief, short life); auto = handled by the watch this run.' % (ACTIVE_MIN, ACTIVE_MIN, STALE_MIN, STALE_MIN),
               counts=dict(ACTIVE=cnt['ACTIVE'], STALE=cnt['STALE'], UNOWNED=cnt['UNOWNED'], open=len(res),
                           needs_agent=sum(1 for x in res.values() if x['needs_agent'])),
               actions=actions,
               elements=sorted(res.values(), key=lambda x: (['UNOWNED', 'STALE', 'ACTIVE'].index(x['state']), -(x['age_min'] or 1e9), x['element'])))
    atomic_write(Path(a.out), json.dumps(doc, indent=1))
    if a.act: save_state(st)
    # summary
    S = ['ELEMENT OWNER WATCH %s%s: open %d -> ACTIVE %d / STALE %d / UNOWNED %d; needs_agent %d; actions %d (%s)' % (
        doc['generated'], '' if a.act else ' (dry run)', len(res), cnt['ACTIVE'], cnt['STALE'], cnt['UNOWNED'], doc['counts']['needs_agent'],
        len(actions), ', '.join('%s %d' % kv for kv in collections.Counter(x['kind'] for x in actions).items()) or 'none')]
    by_die = collections.defaultdict(collections.Counter)
    for x in res.values():
        for d in x['dies']: by_die[d][x['state']] += 1
    S.append('per die: ' + '; '.join('%s A%d/S%d/U%d' % (d, c['ACTIVE'], c['STALE'], c['UNOWNED']) for d, c in sorted(by_die.items())))
    for x in doc['elements']:
        if x['state'] == 'ACTIVE': continue
        S.append('  %-7s %-40s %-6s owner %-18s last %s%s%s' % (x['state'], x['element'][:40], hm(x['age_min']), (x['owner'] or '-')[:18],
                                                            (x['last_activity'] or '-')[:60], ' | AUTO ' + x['auto'] if x['auto'] else '',
                                                            ' | ' + x['auto_note'] if x.get('auto_note') else ''))
    for ent in actions:
        S.append('  %s %s %s %s' % ('DONE' if ent['kind'] == 'finished' else 'ACTION', ent['kind'], ent['element'], json.dumps({k: v for k, v in ent.items() if k not in ('t', 'kind', 'element')})[:300]))
    text = '\n'.join(S) + '\n'
    atomic_write(SUMMARY, text)
    if a.act and (actions or True):
        with open(LANE_LOG, 'a') as f:
            f.write('- %s %s\n' % (datetime.datetime.fromtimestamp(NOW).strftime('%m-%d %H:%M'), S[0].split(': ', 1)[1]))
            for ent in actions:
                f.write('  - %s %s: %s\n' % (ent['kind'], ent['element'], ', '.join('%s=%s' % (k, v) for k, v in ent.items()
                                                                                 if k in ('kit', 'ref', 'gate', 'pid', 'log', 'error', 'failed_job', 'new_name', 'outcome', 'wt'))))
    if a.summary: sys.stdout.write(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
