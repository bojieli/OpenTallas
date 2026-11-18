#!/usr/bin/env python3
"""auto_export.py: every R-MINIMAL sign-off goes to both signed stores with no lane step (AUTO-EXPORT-1118, OWNER r711).

Stores (the count reads only these; same relative layout, INDEX.tsv append-only on both):
  AGIdock  /archive/opentallas-signed-1114/<die>/<unit>/   + INDEX.tsv     (reached from the hub, key ~/.ssh/agidock_ot)
  rtx-pro  /home/ubuntu/signed-export-1114/<die>/<unit>/   + INDEX.tsv     (pulls from AGIdock; the fleet has no route to it)

Flow:
  1. hook   signoff.py cmd_run, after signoff.json is written: profile minimal + verdict SIGNED -> one spool file on the
            build host, ~/.local/state/ot-auto-export/spool/<record sha16>.json (host, signoff path, die/element/kind hints
            from OT_EXPORT_DIE / OT_EXPORT_ELEMENT / OT_EXPORT_KIND).  Never fails the sign-off.
  2. drain  hub (intel2) systemd --user timer every 5 min, flock: reads every build host's spool (and, every
            OT_AUTO_EXPORT_SCAN_H hours, a scan of the host's scratch roots for R-MINIMAL SIGNED signoff.json of the last
            OT_AUTO_EXPORT_WINDOW_H hours, which catches kits whose bundled signoff.py predates the hook), hashes the files
            on the host, skips any record whose ODB sha256 is already an INDEX row, streams host -> AGIdock
            <unit>.partial (no fleet staging), verifies every sha256 there, renames to <unit> (never over an existing dir),
            and lists the unit for rtx-pro.
  3. rtx    rtx-pro cron */5 (`rtx-pull --hub intel2`): copies each listed unit AGIdock -> rtx-pro, verifies every sha256,
            appends its INDEX row, reports back to the hub.
  4. index  next drain: appends the AGIdock INDEX row (ARCHIVED-BOTH: both copies verified), posts
            `AUTO-EXPORT <die>/<element>` via ~/coord/bin/post.sh, removes the host spool file.
Idempotent: an ODB sha already in the AGIdock INDEX is skipped at every step; the hub ledger keeps per-unit state.
Never modifies or deletes an existing archive file: new units only, <unit>.partial staging, append-only INDEX.

  auto_export.py enqueue SIGNOFF_JSON [--die D] [--element E] [--kind t|c]     (build host; the hook calls this logic)
  auto_export.py drain [--scan] [--list-only] [--hosts h,...] [--budget-s N]    (hub)
  auto_export.py rtx-pull [--hub intel2]                                        (rtx-pro)
"""
import argparse, collections, fcntl, hashlib, json, os, re, shlex, socket, subprocess, sys, time

HOME = os.path.expanduser('~')
STATE = os.environ.get('OT_AUTO_EXPORT_STATE', os.path.join(HOME, '.local/state/ot-auto-export'))
SPOOL_REL = '.local/state/ot-auto-export/spool'
AGI_ROOT = '/archive/opentallas-signed-1114'
RTX_ROOT = os.environ.get('OT_RTX_ROOT', '/home/ubuntu/signed-export-1114')
AGI = ['ssh', '-i', os.path.join(HOME, '.ssh/agidock_ot'), '-o', 'IdentitiesOnly=yes', '-o', 'ControlPath=none',
       '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'ubuntu@155.103.253.53']
SSH = ['ssh', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20']
HOSTS = ('intel1', 'epyc2', 'epyc7', 'epyc8', 'epyc9', 'epyc10')
DIES = ('s81_head', 's81', 'qwen_compute', 'qwen_kvsys', 'hbm')
WINDOW_H = float(os.environ.get('OT_AUTO_EXPORT_WINDOW_H', 72))
SCAN_H = float(os.environ.get('OT_AUTO_EXPORT_SCAN_H', 6))
LANE = 'AUTO-EXPORT'
SRC_TAG = 'AUTO-EXPORT-1118'


def say(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


# ---- 1. hook / enqueue (build host) -----------------------------------------------------------------------------------
def r_minimal_pass(rec):
    return rec.get('profile') == 'minimal' and rec.get('verdict') == 'SIGNED'


def enqueue(signoff, rec=None, die=None, element=None, kind=None, spool=None):
    """spool one R-MINIMAL SIGNED record; -> spool path or None (not R-MINIMAL PASS / disabled)."""
    if os.environ.get('OT_AUTO_EXPORT', '1') == '0':
        return None
    signoff = os.path.realpath(signoff)
    raw = open(signoff, 'rb').read()
    rec = rec if rec is not None else json.loads(raw)
    if not r_minimal_pass(rec):
        return None
    sha = hashlib.sha256(raw).hexdigest()
    spool = spool or os.environ.get('OT_AUTO_EXPORT_SPOOL') or os.path.join(HOME, SPOOL_REL)
    os.makedirs(spool, exist_ok=True)
    row = dict(schema='opentallas.auto_export.spool.v1', signoff=signoff, record=sha, host=socket.gethostname(),
               name=rec.get('name'), generated=rec.get('generated'), queued=time.strftime('%Y-%m-%dT%H:%M:%S%z'),
               die=die or os.environ.get('OT_EXPORT_DIE') or None,
               element=element or os.environ.get('OT_EXPORT_ELEMENT') or None,
               kind=kind or os.environ.get('OT_EXPORT_KIND') or None)
    p = os.path.join(spool, sha[:16] + '.json')
    tmp = p + '.tmp%d' % os.getpid()
    with open(tmp, 'w') as f:
        json.dump(row, f)
    os.replace(tmp, p)
    return p


# ---- host probe (runs on a build host over ssh, script on stdin) ------------------------------------------------------
PROBE = r'''
import hashlib, json, os, re, socket, sys, time
mode, arg = sys.argv[1], json.loads(sys.argv[2])
HOME = os.path.expanduser("~"); SPOOL = os.path.join(HOME, %(spool)r)
CACHE = os.path.join(HOME, ".local/state/ot-auto-export/sha_cache.json")
DB = ("6_final.odb", "6_final.def", "6_final.spef", "6_final.v", "6_final.sdc")
TESTY = re.compile(r"/(test_[^/]*|[^/]*pyt-[^/]*|[^/]*pytest[^/]*|fixtures?)/")
HN = socket.gethostname()
def top_of(rec, so):
    for d in (rec.get("inputs", {}).get("kit"), rec.get("inputs", {}).get("orfs")):
        if d and os.path.isfile(os.path.join(d, "config.mk")):
            try:
                m = re.search(r"^\s*export\s+DESIGN_NAME\s*\??=\s*(\S+)", open(os.path.join(d, "config.mk")).read(), re.M)
                if m: return m.group(1)
            except OSError: pass
    return None
def unit(so, hint=None):
    try:
        raw = open(so, "rb").read(); rec = json.loads(raw)
    except Exception as e:
        return dict(signoff=so, err="unreadable: %%s" %% str(e)[:120])
    o = dict(signoff=so, record=hashlib.sha256(raw).hexdigest(), name=rec.get("name"), generated=rec.get("generated"),
             rec_host=rec.get("host"), profile=rec.get("profile"), verdict=rec.get("verdict"), hint=hint or {})
    if not (rec.get("profile") == "minimal" and rec.get("verdict") == "SIGNED"):
        o["err"] = "not R-MINIMAL SIGNED"; return o
    if rec.get("host") and rec.get("host") != HN:
        o["err"] = "record of host %%s (copy)" %% rec.get("host"); return o
    inp = rec.get("inputs") or {}
    odb = inp.get("odb") or (inp.get("base") and os.path.join(inp["base"], "6_final.odb"))
    if not odb or not os.path.isfile(odb) or os.path.getsize(odb) < 1 << 20:
        o["err"] = "no routed DB %%s" %% odb; return o
    dbd, sod = os.path.dirname(os.path.realpath(odb)), os.path.dirname(so)
    files = [(dbd, f) for f in DB if os.path.isfile(os.path.join(dbd, f))]
    for f in sorted(os.listdir(sod)):
        p = os.path.join(sod, f)
        if f.endswith(".json") and os.path.isfile(p) and os.path.getsize(p) < 20 << 20 and f not in [x[1] for x in files]:
            files.append((sod, f))
    tt = ((rec.get("checks") or {}).get("setup_tt") or {}).get("wns_ps")
    ff = ((rec.get("checks") or {}).get("hold_ff") or {}).get("wns_ps")
    o.update(odb=os.path.realpath(odb), odb_size=os.path.getsize(odb), odb_mtime=os.path.getmtime(odb), files=files,
             top=top_of(rec, so), tt=tt, ff=ff, drc=((rec.get("route") or {}).get("drc")))
    return o
def sha(p, cache):
    st = os.stat(p); k = "%%s|%%d|%%d" %% (p, st.st_size, int(st.st_mtime))
    if k not in cache:
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
        cache[k] = h.hexdigest()
    return cache[k], st.st_size
if mode == "spool":
    for f in sorted(os.listdir(SPOOL)) if os.path.isdir(SPOOL) else ():
        if not f.endswith(".json"): continue
        try: s = json.load(open(os.path.join(SPOOL, f)))
        except Exception: continue
        u = unit(s["signoff"], {k: s.get(k) for k in ("die", "element", "kind")}) if os.path.isfile(s.get("signoff", "")) else dict(signoff=s.get("signoff"), err="signoff.json gone")
        u["spool"] = f; print(json.dumps(u), flush=True)
elif mode == "scan":
    cut = time.time() - arg["hours"] * 3600
    import subprocess
    roots = [r for r in arg["roots"] if os.path.isdir(r)]
    cmd = ["nice", "-n", "15", "ionice", "-c3", "find"] + roots + ["(", "-name", ".git", "-o", "-name", "objects", "-o", "-name", "__pycache__", "-o", "-name", "node_modules", ")", "-prune", "-o", "-type", "f", "-name", "signoff.json", "-mmin", "-%%d" %% int(arg["hours"] * 60 + 1), "-print"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    for line in p.stdout:
        so = line.strip()
        rel = next(("/" + so[len(r):] for r in roots if so.startswith(r.rstrip("/") + "/")), so)
        if not so or TESTY.search(rel): continue
        try:
            with open(so, "rb") as f: head = f.read()
            if b'"minimal"' not in head or b'"SIGNED"' not in head: continue
        except OSError: continue
        u = unit(so)
        if "err" not in u: print(json.dumps(u), flush=True)
elif mode == "hash":
    try: cache = json.load(open(CACHE))
    except Exception: cache = {}
    out = {}
    for p in arg["paths"]:
        try: out[p] = sha(p, cache)
        except OSError as e: out[p] = [None, str(e)[:120]]
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    tmp = CACHE + ".tmp"; json.dump(cache, open(tmp, "w")); os.replace(tmp, CACHE)
    print(json.dumps(out))
elif mode == "rmspool":
    for f in arg["files"]:
        if re.fullmatch(r"[0-9a-f]{16}\.json", f) and os.path.isfile(os.path.join(SPOOL, f)):
            os.unlink(os.path.join(SPOOL, f))
    print("{}")
''' % dict(spool=SPOOL_REL)
ROOTS = ['/srv/opentallas-scratch/claude', '/srv/opentallas-scratch2/claude', '/srv/opentallas-scratch3/claude']


def probe(host, mode, arg, timeout=1800):
    r = subprocess.run(SSH + [host, 'python3 -I - %s %s' % (mode, shlex.quote(json.dumps(arg)))], input=PROBE,
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError('%s probe %s rc %d: %s' % (host, mode, r.returncode, r.stderr.strip()[-300:]))
    return [json.loads(l) for l in r.stdout.splitlines() if l.startswith('{')]


# ---- INDEX ------------------------------------------------------------------------------------------------------------
def parse_index(text):
    rows = []
    for line in text.splitlines()[1:]:
        c = line.split('\t')
        if len(c) >= 8:
            rows.append(c)
    return rows


def agi(cmd, input=None, timeout=600):
    return subprocess.run(AGI + [cmd], input=input, capture_output=True, text=True, timeout=timeout)


def agi_index():
    r = agi('cat %s/INDEX.tsv' % AGI_ROOT)
    if r.returncode:
        raise RuntimeError('AGIdock INDEX unreadable: ' + r.stderr[-200:])
    return parse_index(r.stdout)


# ---- die / element / kind inference -----------------------------------------------------------------------------------
TOKEN_DIE = (({'head', 'hd', 's81hd', 's81_head'}, 's81_head'), ({'hbm', 'hfd', 'hnx', 'hgi'}, 'hbm'),
             ({'kv', 'kvsys', 'qkd', 'kv3', 'kv4', 'qwen_kvsys'}, 'qwen_kvsys'),
             ({'qc', 'qfd', 'qcr3', 'qwen_compute', 'sle', 'slw'}, 'qwen_compute'), ({'s81', 'dsdv', 'dsfd', 's81svc'}, 's81'))


def die_of_tokens(text):
    t = set(re.split(r'[/_.-]+', text.lower()))
    for keys, d in TOKEN_DIE:
        if t & keys:
            return d
    return None


def infer(u, rows):
    """-> (die, element, kind, how)."""
    hint = u.get('hint') or {}
    el = hint.get('element') or u.get('top') or u.get('name') or 'unknown'
    el = re.sub(r'[^A-Za-z0-9_.-]', '_', el)
    by_el = collections.Counter((r[0], r[2]) for r in rows if r[1] == el and r[0] in DIES)
    kind = hint.get('kind') or (by_el.most_common(1)[0][0][1] if by_el else ('c' if re.search(r'core', u['signoff']) else 't'))
    if hint.get('die'):
        return hint['die'], el, kind, 'hint'
    m = re.search(r'/runs/([a-z0-9_]+)/kit-wave/|/kit-wave/([a-z0-9_]+)/', u['signoff'])
    if m and (m.group(1) or m.group(2)) in DIES:
        return m.group(1) or m.group(2), el, kind, 'kit-wave path'
    if by_el:
        return by_el.most_common(1)[0][0][0], el, kind, 'INDEX element'
    m = re.search(r'/claude/([^/]+)/', u['signoff'])
    for text, how in ((m.group(1) if m else '', 'lane dir'), (el, 'element prefix'), (u['signoff'], 'path keyword')):
        d = die_of_tokens(text)
        if d:
            return d, el, kind, how
    pre = '_'.join(el.split('_')[:2])
    by_pre = collections.Counter(r[0] for r in rows if '_'.join(r[1].split('_')[:2]) == pre and r[0] in DIES)
    if by_pre:
        return by_pre.most_common(1)[0][0], el, kind, 'INDEX prefix'
    return '_', el, kind, 'unassigned'


# ---- 2. drain (hub) ---------------------------------------------------------------------------------------------------
def load_ledger():
    p = os.path.join(STATE, 'ledger.json')
    try:
        return json.load(open(p))
    except (OSError, ValueError):
        return dict(units={}, last_scan=0)


def save_ledger(L):
    p = os.path.join(STATE, 'ledger.json')
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(L, f, indent=1)
    os.replace(tmp, p)
    pend = [dict(key=k, **{x: u[x] for x in ('die', 'unit', 'element', 'kind', 'record', 'odb_sha', 'odb_size', 'shas', 'src')})
            for k, u in L['units'].items() if u.get('state') == 'agi']
    tmp = os.path.join(STATE, 'pending_rtx.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(pend, f, indent=1)
    os.replace(tmp, os.path.join(STATE, 'pending_rtx.json'))


def index_row(u, status='ARCHIVED-BOTH'):
    k = '%s/%s' % (u['die'], u['unit'])
    meta = '%s/%s/signoff.json' % (AGI_ROOT, k)
    return '\t'.join([u['die'], u['element'], u['kind'], u['record'], '%s/%s/6_final.odb' % (AGI_ROOT, k),
                      '%s/%s/6_final.odb' % (RTX_ROOT, k), str(u['odb_size']), u['odb_sha'], '', meta, status, u['src']]) + '\n'


def export_agi(u):
    """stream host -> AGIdock <unit>.partial, verify, rename.  -> None or error text."""
    k = '%s/%s' % (u['die'], u['unit'])
    dest, part = '%s/%s' % (AGI_ROOT, k), '%s/%s.partial' % (AGI_ROOT, k)
    chk = agi('test -e %s && echo EXISTS; true' % shlex.quote(dest))
    if 'EXISTS' in chk.stdout:
        return 'AGIdock %s already exists (never overwritten)' % dest
    groups = collections.OrderedDict()
    for d, f in u['files']:
        groups.setdefault(d, []).append(f)
    tar = 'tar cf - ' + ' '.join('-C %s %s' % (shlex.quote(d), ' '.join(map(shlex.quote, fs))) for d, fs in groups.items())
    src = subprocess.Popen(SSH + [u['host'], 'nice -n 10 ' + tar], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dst = subprocess.run(AGI + ['rm -rf %s && mkdir -p %s && tar xf - -C %s' % (shlex.quote(part), shlex.quote(part), shlex.quote(part))],
                         stdin=src.stdout, capture_output=True, timeout=6 * 3600)
    src.stdout.close()
    src.wait()
    if src.returncode or dst.returncode:
        return 'stream failed host rc %s agi rc %s %s' % (src.returncode, dst.returncode, (dst.stderr or b'')[-200:])
    v = agi('cd %s && sha256sum %s' % (shlex.quote(part), ' '.join(shlex.quote(f) for f in u['shas'])), timeout=3600)
    got = dict((l.split()[1], l.split()[0]) for l in v.stdout.splitlines() if len(l.split()) == 2)
    bad = [f for f, s in u['shas'].items() if got.get(f) != s]
    if bad:
        return 'sha mismatch on AGIdock: %s' % bad[:5]
    mv = agi('test -e %s || mv -T %s %s && test -d %s' % ((shlex.quote(dest),) + (shlex.quote(part), shlex.quote(dest), shlex.quote(dest))))
    return None if mv.returncode == 0 else 'rename failed: %s' % mv.stderr[-200:]


def append_agi_index(row, sha):
    """append under the INDEX lock unless the ODB sha is already a row; -> True when this call appended."""
    script = ('import sys,fcntl\nroot=%r\nsha=%r\nrow=sys.stdin.read()\n'
              'l=open(root+"/INDEX.tsv.lock","a");fcntl.flock(l,fcntl.LOCK_EX)\n'
              'if any(len(c)>7 and c[7]==sha for c in (x.split("\\t") for x in open(root+"/INDEX.tsv"))):print("HAVE")\n'
              'else:\n f=open(root+"/INDEX.tsv","a");f.write(row);f.flush();print("APPENDED")\n') % (AGI_ROOT, sha)
    r = subprocess.run(AGI + ['python3 -I -c %s' % shlex.quote(script)], input=row, capture_output=True, text=True, timeout=120)
    if r.returncode:
        raise RuntimeError('AGIdock INDEX append: ' + r.stderr[-200:])
    return 'APPENDED' in r.stdout


def post(text):
    if os.environ.get('OT_AUTO_EXPORT_NOPOST'):
        say('POST (suppressed):', text)
        return
    subprocess.run(['bash', os.path.join(HOME, 'coord/bin/post.sh'), LANE, text], timeout=300)


def collect(hosts, scan, rows, L):
    """-> candidate units (dicts) from spools (+ scans), deduped by ODB path."""
    cands = []
    for h in hosts:
        try:
            for u in probe(h, 'spool', {}):
                u['host'], u['via'] = h, 'spool'
                cands.append(u)
            if scan:
                for u in probe(h, 'scan', dict(hours=WINDOW_H, roots=ROOTS), timeout=3 * 3600):
                    u['host'], u['via'] = h, 'scan'
                    cands.append(u)
        except Exception as e:
            say('host %s: %s' % (h, e))
    return cands


def drain(a):
    os.makedirs(STATE, exist_ok=True)
    lk = open(os.path.join(STATE, 'drain.lock'), 'w')
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        say('another drain holds the lock')
        return 0
    t0 = time.time()
    L = load_ledger()
    rows = agi_index()
    have = {r[7] for r in rows}
    hosts = a.hosts.split(',') if a.hosts else HOSTS
    # 4. index + post units that rtx-pro finished
    done = []
    rp = os.path.join(STATE, 'rtx_done.jsonl')
    if os.path.isfile(rp):
        for line in open(rp):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            u = L['units'].get(d.get('key'))
            if u and u.get('state') == 'agi' and d.get('ok'):
                if append_agi_index(index_row(u), u['odb_sha']):
                    have.add(u['odb_sha'])
                u['state'], u['done'] = 'done', time.strftime('%Y-%m-%dT%H:%M:%S%z')
                done.append(u)
            elif u and u.get('state') == 'agi' and not d.get('ok'):
                u['rtx_err'] = d.get('err')
        os.replace(rp, rp + '.%d' % int(t0))
    if done:
        for h in {u['host'] for u in done if u.get('spool')}:
            try:
                probe(h, 'rmspool', dict(files=[u['spool'] for u in done if u['host'] == h and u.get('spool')]))
            except Exception as e:
                say('rmspool %s: %s' % (h, e))
        lines = ['AUTO-EXPORT %s/%s (%s %s:%s) ARCHIVED-BOTH AGIdock+rtx-pro %s/%s, ODB sha %s, record %s, TT %s FF %s, INDEX rows on both'
                 % (u['die'], u['element'], u['via'], u['host'], u['signoff'], u['die'], u['unit'], u['odb_sha'][:12],
                    u['record'][:12], u.get('tt'), u.get('ff')) for u in done]
        post('\n'.join(lines))
    # 2. collect new candidates
    scan = a.scan or (time.time() - L.get('last_scan', 0) > SCAN_H * 3600)
    cands = collect(hosts, scan, rows, L)
    if scan and not a.list_only and not a.hosts:
        L['last_scan'] = t0
    seen, todo = set(), []
    for u in cands:
        if 'err' in u:
            if u.get('via') == 'spool':
                say('spool %s:%s skipped: %s' % (u['host'], u.get('signoff'), u['err']))
            continue
        key = '%s:%s' % (u['host'], u['odb'])
        prev = L['units'].get(key, {})
        if key in seen or prev.get('state') in ('agi', 'done', 'skip') or prev.get('tries', 0) >= 3:
            continue
        seen.add(key)
        todo.append(u)
    # newest record first per DB is irrelevant: the DB is the unit
    say('%d candidate DBs (%d from spool), scan=%s' % (len(todo), sum(u['via'] == 'spool' for u in todo), scan))
    listed = []
    for u in todo:
        if time.time() - t0 > a.budget_s:
            say('budget reached; rest next tick')
            break
        try:
            hs = probe(u['host'], 'hash', dict(paths=[os.path.join(d, f) for d, f in u['files']]), timeout=3600)[0]
        except Exception as e:
            say('hash %s: %s' % (u['odb'], e))
            continue
        shas = {f: hs[os.path.join(d, f)][0] for d, f in u['files']}
        if None in shas.values():
            say('hash failed %s' % u['odb'])
            continue
        osha = shas['6_final.odb']
        key = '%s:%s' % (u['host'], u['odb'])
        if osha in have or any(x.get('odb_sha') == osha and x.get('state') in ('agi', 'done') for x in L['units'].values()):
            L['units'][key] = dict(state='skip', odb_sha=osha, why='ODB sha already in INDEX / ledger', signoff=u['signoff'])
            continue
        die, el, kind, how = infer(u, rows)
        u.update(die=die, element=el, kind=kind, how=how, odb_sha=osha, shas=shas, unit='%s__ax_%s' % (el, osha[:10]),
                 src='%s %s:%s (%s, die by %s) R-MINIMAL SIGNED TT %s FF %s' % (SRC_TAG, u['host'], u['signoff'], u['via'], how, u.get('tt'), u.get('ff')))
        listed.append(u)
        if a.list_only:
            continue
        say('export %s/%s from %s:%s' % (die, u['unit'], u['host'], u['signoff']))
        err = export_agi(u)
        if err:
            say('  FAIL', err)
            L['units'][key] = dict(u, state='err', err=err, at=time.time(), tries=L['units'].get(key, {}).get('tries', 0) + 1)
            save_ledger(L)
            continue
        have.add(osha)
        L['units'][key] = dict(u, state='agi', agi_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
        save_ledger(L)
    if a.list_only:
        for u in listed:
            print('\t'.join([u['die'], u['element'], u['kind'], u['host'], u['signoff'], u['odb_sha'][:12], u['how']]))
    save_ledger(L)
    return 0


# ---- 3. rtx-pull (rtx-pro) --------------------------------------------------------------------------------------------
def rtx_pull(a):
    lk = open('/tmp/ot-auto-export-rtx.lock', 'w')
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0
    r = subprocess.run(SSH + [a.hub, 'cat .local/state/ot-auto-export/pending_rtx.json'], capture_output=True, text=True, timeout=120)
    if r.returncode:
        say('hub unreadable', r.stderr[-200:])
        return 1
    reports = []
    for u in json.loads(r.stdout or '[]'):
        k = '%s/%s' % (u['die'], u['unit'])
        dest, part = os.path.join(RTX_ROOT, k), os.path.join(RTX_ROOT, k + '.partial')
        idx = os.path.join(RTX_ROOT, 'INDEX.tsv')
        if any(c[7] == u['odb_sha'] for c in parse_index(open(idx).read())):
            reports.append(dict(key=u['key'], ok=True, note='already in rtx INDEX'))
            continue
        if not os.path.exists(dest):
            os.makedirs(part, exist_ok=True)
            c = subprocess.run(['rsync', '-a', '-e', ' '.join(AGI[:-1]), '%s:%s/%s/' % (AGI[-1], AGI_ROOT, k), part + '/'],
                               capture_output=True, text=True, timeout=6 * 3600)
            if c.returncode:
                reports.append(dict(key=u['key'], ok=False, err='rsync rc %d %s' % (c.returncode, c.stderr[-200:])))
                continue
            os.rename(part, dest)
        bad = []
        for f, s in u['shas'].items():
            h = hashlib.sha256()
            with open(os.path.join(dest, f), 'rb') as fh:
                for b in iter(lambda: fh.read(1 << 22), b''):
                    h.update(b)
            if h.hexdigest() != s:
                bad.append(f)
        if bad:
            reports.append(dict(key=u['key'], ok=False, err='rtx sha mismatch %s' % bad[:5]))
            continue
        with open(os.path.join(RTX_ROOT, 'INDEX.tsv.lock'), 'a') as l:
            fcntl.flock(l, fcntl.LOCK_EX)
            if not any(c[7] == u['odb_sha'] for c in parse_index(open(idx).read())):
                with open(idx, 'a') as f:
                    f.write(index_row(u))
        say('rtx done', k)
        reports.append(dict(key=u['key'], ok=True))
    if reports:
        subprocess.run(SSH + [a.hub, 'cat >> .local/state/ot-auto-export/rtx_done.jsonl'],
                       input=''.join(json.dumps(x) + '\n' for x in reports), text=True, timeout=120, check=True)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    e = sub.add_parser('enqueue')
    e.add_argument('signoff')
    e.add_argument('--die')
    e.add_argument('--element')
    e.add_argument('--kind', choices=('t', 'c'))
    d = sub.add_parser('drain')
    d.add_argument('--scan', action='store_true')
    d.add_argument('--list-only', action='store_true')
    d.add_argument('--hosts')
    d.add_argument('--budget-s', type=float, default=2400)
    r = sub.add_parser('rtx-pull')
    r.add_argument('--hub', default='intel2')
    a = ap.parse_args(argv)
    if a.cmd == 'enqueue':
        p = enqueue(a.signoff, die=a.die, element=a.element, kind=a.kind)
        print(p or 'not R-MINIMAL SIGNED: nothing queued')
        return 0
    return drain(a) if a.cmd == 'drain' else rtx_pull(a)


if __name__ == '__main__':
    sys.exit(main())
