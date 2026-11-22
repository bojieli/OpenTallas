#!/usr/bin/env python3
"""auto_export.py: every R-MINIMAL sign-off goes to both signed stores with no lane step (AUTO-EXPORT-1118, OWNER r711).

Stores (OWNER export split 11-18: full records on rtx-pro only, AGIdock metadata + web-display export only):
  rtx-pro  /home/ubuntu/signed-export-1114/<die>/<unit>/   + INDEX.tsv   full record: 6_final.{odb,def,spef,v,sdc} + sign-off
           json; pulled by rtx-pro straight from the build host (the hub has no route to rtx-pro)
  AGIdock  /archive/opentallas-signed-1114/<die>/<unit>/   + INDEX.tsv   metadata only: signoff.json and the other sign-off
           json, MANIFEST.json (size + sha256 of every full-record file), display/ (renders + view pack: png/svg/webp,
           LEF, libs, pins/abstract json, layout_dump.json); no DB copy.  Reached from the hub, key ~/.ssh/agidock_ot.

Flow:
  1. hook   signoff.py cmd_run, after signoff.json is written: profile minimal + verdict SIGNED -> one spool file on the
            build host, ~/.local/state/ot-auto-export/spool/<record sha16>.json (host, signoff path, die/element/kind hints
            from OT_EXPORT_DIE / OT_EXPORT_ELEMENT / OT_EXPORT_KIND).  Never fails the sign-off.
  2. drain  hub (intel2) systemd --user timer every 5 min, flock: reads every build host's spool (and, every
            OT_AUTO_EXPORT_SCAN_H hours, a scan of the host's scratch roots for R-MINIMAL SIGNED signoff.json of the last
            OT_AUTO_EXPORT_WINDOW_H hours, which catches kits whose bundled signoff.py predates the hook), hashes the files
            on the host, skips any record whose ODB sha256 is already an INDEX row, streams the metadata + display files
            host -> AGIdock <unit>.meta-partial-<ts> (no fleet staging), verifies every sha256 there, renames to <unit>
            (never over an existing dir, never deletes on AGIdock), and lists the unit for rtx-pro.
  3. rtx    rtx-pro cron */5 (`rtx-pull --hub intel2`): streams each listed unit's full record host -> rtx-pro,
            verifies every sha256 against the hub's hashes, appends its INDEX row, reports back to the hub.
  4. index  next drain: appends the AGIdock INDEX row (status RTX-FULL-AGI-META), posts `AUTO-EXPORT <die>/<element>`
            via ~/coord/bin/post.sh, removes the host spool file.
  5. view   (EXPLORER-STORE-R1 11-22) every unit that reaches 'done' is queued for its routed-layout pack: a detached
            `auto_export.py view-packs` worker on the hub cuts it on the build host under ot-run (design_export.py cut,
            IDENTICAL round trip, at most VIEWPACK_PER_HOST per host) and publishes it into the explorer layout store on
            the store host (epyc8 LV_STORE), node id <die>.<t|c>.<element>, so every new sign-off is viewable with no lane step.
  Units exported before the split (ledger state 'agi': full copy already on AGIdock) finish the old way, ARCHIVED-BOTH.
Idempotent: an ODB sha already in the AGIdock INDEX is skipped at every step; the hub ledger keeps per-unit state.
Never modifies or deletes an existing archive file: new units only, <unit>.partial staging, append-only INDEX.

  auto_export.py enqueue SIGNOFF_JSON [--die D] [--element E] [--kind t|c]     (build host; the hook calls this logic)
  auto_export.py drain [--scan] [--list-only] [--hosts h,...] [--budget-s N]    (hub)
  auto_export.py rtx-pull [--hub intel2]                                        (rtx-pro)
  auto_export.py view-packs                                                     (hub; started by finish(), one at a time)
"""
import argparse, collections, fcntl, hashlib, json, os, re, shlex, socket, subprocess, sys, time

HOME = os.path.expanduser('~')
STATE = os.environ.get('OT_AUTO_EXPORT_STATE', os.path.join(HOME, '.local/state/ot-auto-export'))
SPOOL_REL = '.local/state/ot-auto-export/spool'
SPOOL_POLL_S = float(os.environ.get('OT_AUTO_EXPORT_SPOOL_POLL_S', 300))   # FLOW-FLEET-R1: spools re-read this often while a scan drain runs
AGI_ROOT = '/archive/opentallas-signed-1114'
RTX_ROOT = os.environ.get('OT_RTX_ROOT', '/home/ubuntu/signed-export-1114')
AGI = ['ssh', '-i', os.path.join(HOME, '.ssh/agidock_ot'), '-o', 'IdentitiesOnly=yes', '-o', 'ControlPath=none',
       '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', 'ubuntu@155.103.253.53']
SSH = ['ssh', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20']
# FLOW-FLEET-R1 11-22 (FABLE-FLOW-0000 F9): intel2 is a build host too (capped); its own spool was never read (45 files, oldest 10:40)
HOSTS = ('intel1', 'intel2', 'epyc2', 'epyc7', 'epyc8', 'epyc9', 'epyc10')
SPOOL_RETRY_AGE_S = float(os.environ.get('OT_AUTO_EXPORT_SPOOL_RETRY_H', 2)) * 3600   # F9: older -> retried once, then set aside
SPOOL_ASIDE_AFTER_S = 600                                                               # the retry gets at least one more drain
NOT_RECORD = re.compile(r"/(flow-canary|test_[^/]*|[^/]*pyt-[^/]*|[^/]*pytest[^/]*|fixtures?)/")   # canary / test runs: never a sign-off of record
DIES = ('s81_head', 's81', 'qwen_compute', 'qwen_kvsys', 'hbm')
WINDOW_H = float(os.environ.get('OT_AUTO_EXPORT_WINDOW_H', 72))
SCAN_H = float(os.environ.get('OT_AUTO_EXPORT_SCAN_H', 6))
LANE = 'AUTO-EXPORT'
RESERVE_GB = float(os.environ.get('OT_RTX_RESERVE_GB', 100))   # rtx-pro root disk: never copy below this free space
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
        # FLOW-FLEET-R1 11-22: the autopilot RELOCATES a signed kit to <host>:.../autopilot/closed/<die>/<item>__<sha>/ (record written on the build host it
        # ran on, often the hub); the original is then gone, and skipping every copy left those sign-offs unexported (pending_archive for 14-19 h).
        # A closed relocation is authoritative: export it; duplicates are still dropped by the ODB sha256 (INDEX / ledger).
        if "/autopilot/closed/" not in so:
            o["err"] = "record of host %%s (copy)" %% rec.get("host"); return o
        o["copy_of"] = rec.get("host")
    inp = rec.get("inputs") or {}
    odb = inp.get("odb") or (inp.get("base") and os.path.join(inp["base"], "6_final.odb"))
    if not odb or not os.path.isfile(odb):          # autopilot relocated copy: <dest>/kit/<signoff dir>/ next to <dest>/base/
        d = os.path.dirname(so)
        for _ in range(3):
            d = os.path.dirname(d)
            if os.path.isfile(os.path.join(d, "base", "6_final.odb")):
                odb = os.path.join(d, "base", "6_final.odb"); break
    if not odb or not os.path.isfile(odb) or os.path.getsize(odb) < 1 << 20:
        o["err"] = "no routed DB %%s" %% odb; return o
    dbd, sod = os.path.dirname(os.path.realpath(odb)), os.path.dirname(so)
    files = [(dbd, f) for f in DB if os.path.isfile(os.path.join(dbd, f))]
    for f in sorted(os.listdir(sod)):
        p = os.path.join(sod, f)
        if f.endswith(".json") and os.path.isfile(p) and os.path.getsize(p) < 20 << 20 and f not in [x[1] for x in files]:
            files.append((sod, f))
    # EVIDENCE-EXPORT-1119 (QC-RING-REBUILD: exports held only 6_final.* + signoff.json, so a signed child's views could not be regenerated once its kit was cleaned): the landing evidence
    # (land_slots.json, face_guard.json, 1_synth.v) and the view pack (export_view output: a view/ or views/ dir next to the record, the DB or the kit) travel with the record, 2 GB cap.
    have_f = set(x[1] for x in files)
    for r in [x for x in (inp.get("kit"), inp.get("base"), dbd) if x and os.path.isdir(x)]:
        for f in ("land_slots.json", "face_guard.json", "1_synth.v"):
            if f not in have_f and os.path.isfile(os.path.join(r, f)):
                files.append((r, f)); have_f.add(f)
        if "1_synth.v" not in have_f:
            for dp, dn, fn in os.walk(r):
                dn[:] = [d for d in dn if d not in ("objects", ".git", "__pycache__")] if dp.count("/") - r.count("/") < 4 else []
                if "1_synth.v" in fn:
                    files.append((dp, "1_synth.v")); have_f.add("1_synth.v"); break
    vt = 0
    for vr in [x for x in (os.path.join(sod, "view"), os.path.join(sod, "views"), os.path.join(os.path.dirname(sod), "view"), os.path.join(os.path.dirname(sod), "views"),
                           os.path.join(dbd, "view"), os.path.join(dbd, "views"), os.path.join(inp.get("kit") or "/nonexistent", "views")) if os.path.isdir(x)]:
        for dp, dn, fn in os.walk(vr):
            for f in fn:
                q = os.path.join(dp, f)
                if os.path.isfile(q) and vt + os.path.getsize(q) < 2 << 30:
                    rel = os.path.basename(vr) + "/" + os.path.relpath(q, vr)
                    if rel not in have_f:
                        files.append((os.path.dirname(vr), rel)); have_f.add(rel); vt += os.path.getsize(q)
    disp, taken, tot = [], set(), 0
    DISP = re.compile(r"\.(png|svg|webp|jpe?g|lef|lib|lib\.gz)$|(^|_)(pins|abstract|layout_dump|bb)\.(json|v)$|_bb\.v$")
    roots = [sod, os.path.dirname(sod), dbd, inp.get("kit"), os.path.join(os.path.dirname(sod), "view"), os.path.join(os.path.dirname(sod), "views"),
             os.path.join(os.path.dirname(dbd), "view")]
    for r in [r for i, r in enumerate(roots) if r and os.path.isdir(r) and r not in roots[:i]]:
        for dp, dn, fn in os.walk(r):
            dn[:] = [d for d in dn if d not in ("objects", "logs", "results", "work", "tmp", ".git", "__pycache__")] if dp.count("/") - r.count("/") < 2 else []
            for f in fn:
                q = os.path.join(dp, f); rel = os.path.relpath(q, r)
                rq = os.path.realpath(q)
                if not DISP.search(f) or rel in taken or rq in taken or not os.path.isfile(q): continue
                z = os.path.getsize(q)
                if z > 50 << 20 or tot + z > 300 << 20: continue
                taken.update((rel, rq)); tot += z; disp.append((r, rel))
    tt = ((rec.get("checks") or {}).get("setup_tt") or {}).get("wns_ps")
    ff = ((rec.get("checks") or {}).get("hold_ff") or {}).get("wns_ps")
    o.update(odb=os.path.realpath(odb), odb_size=os.path.getsize(odb), odb_mtime=os.path.getmtime(odb), files=files,
             display=disp, top=top_of(rec, so), tt=tt, ff=ff, drc=((rec.get("route") or {}).get("drc")))
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
        u["spool"] = f
        try: u["spool_age_s"] = round(time.time() - os.path.getmtime(os.path.join(SPOOL, f)), 1)
        except OSError: pass
        print(json.dumps(u), flush=True)
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
elif mode == "evidence":
    u = unit(arg["signoff"])
    print(json.dumps(dict(files=[x for x in u.get("files", []) if x[1] in ("land_slots.json", "face_guard.json", "1_synth.v") or "/" in x[1]], err=u.get("err"))))
elif mode == "asidespool":
    fd = os.path.join(SPOOL, "failed"); os.makedirs(fd, exist_ok=True)
    for f, why in arg["items"]:
        if re.fullmatch(r"[0-9a-f]{16}\.json", f) and os.path.isfile(os.path.join(SPOOL, f)):
            os.replace(os.path.join(SPOOL, f), os.path.join(fd, f))
            open(os.path.join(fd, f + ".reason"), "w").write(json.dumps(dict(reason=why, at=time.strftime("%%Y-%%m-%%dT%%H:%%M:%%S%%z"))) + "\n")
    print("{}")
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
    # the wave's item name is the element the count and the lanes use (hd_st_str, not its module ot_s81hd_st_str)
    # FLOW-FLEET-R1 11-22: a private kit (kit_wave private-spec work dir <event>/private/<lane>/<item>_<MMDDhhmmss>/) is the same element as its wave item
    w = (re.search(r'/kit-wave/([a-z0-9_]+)/[^/]+/items/([^/]+)/', u['signoff'])
         or re.search(r'/kit-wave/([a-z0-9_]+)/[^/]+/private/[^/]+/(.+?)_\d{10}/', u['signoff'])
         or re.search(r'/autopilot/closed/([a-z0-9_]+)/(.+?)__[0-9a-f]{10}/', u['signoff']))
    el = hint.get('element') or (w and w.group(2)) or u.get('top') or u.get('name') or 'unknown'
    el = re.sub(r'[^A-Za-z0-9_.-]', '_', el)
    by_el = collections.Counter((r[0], r[2]) for r in rows if r[1] == el and r[0] in DIES)
    kind = hint.get('kind') or (by_el.most_common(1)[0][0][1] if by_el else ('c' if re.search(r'core', u['signoff']) else 't'))
    if hint.get('die'):
        return hint['die'], el, kind, 'hint'
    if w and w.group(1) in DIES:
        return w.group(1), el, kind, 'wave path'
    m = re.search(r'/runs/([a-z0-9_]+)/kit-wave/|/kit-wave/([a-z0-9_]+)/', u['signoff'])
    if m and (m.group(1) or m.group(2)) in DIES:
        return m.group(1) or m.group(2), el, kind, 'wave path'
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
    pend = [dict(key=k, mode='host' if u['state'] == 'meta' else 'agidock',
                 **{x: u[x] for x in ('die', 'unit', 'element', 'kind', 'record', 'odb_sha', 'odb_size', 'shas', 'src', 'bytes',
                                      'host', 'files', 'display') if x in u})
            for k, u in L['units'].items() if u.get('state') in ('agi', 'meta')]
    tmp = os.path.join(STATE, 'pending_rtx.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(pend, f, indent=1)
    os.replace(tmp, os.path.join(STATE, 'pending_rtx.json'))


SPLIT_STATUS = 'RTX-FULL-AGI-META'   # full record on rtx-pro, metadata + display on AGIdock (OWNER export split 11-18)


def index_row(u):
    """one INDEX row, the same on both stores.  Split units: db (the AGIdock DB column) is empty, pack = display dir."""
    k = '%s/%s' % (u['die'], u['unit'])
    meta = '%s/%s/signoff.json' % (AGI_ROOT, k)
    split = u.get('state') == 'meta' or u.get('mode') == 'host'
    db = '' if split else '%s/%s/6_final.odb' % (AGI_ROOT, k)
    pack = '%s/display' % k if split and u.get('display') else ''
    return '\t'.join([u['die'], u['element'], u['kind'], u['record'], db, '%s/%s/6_final.odb' % (RTX_ROOT, k),
                      str(u['odb_size']), u['odb_sha'], pack, meta, SPLIT_STATUS if split else 'ARCHIVED-BOTH', u['src']]) + '\n'


def meta_files(u):
    """the AGIdock share of a unit: the sign-off json (not the 6_final.* DB files)."""
    return [(d, f) for d, f in u['files'] if not f.startswith('6_final.') and f != '1_synth.v' and '/' not in f]   # the big evidence (1_synth.v, view packs) stays rtx-pro only


def export_agi_meta(u):
    """AGIdock gets metadata + display only: stream them host -> <unit>.meta-partial-<ts>, add MANIFEST.json, verify every
    sha256, rename to <unit>.  Never deletes or overwrites on AGIdock.  -> None or error text."""
    k = '%s/%s' % (u['die'], u['unit'])
    dest, part = '%s/%s' % (AGI_ROOT, k), '%s/%s.meta-partial-%d' % (AGI_ROOT, k, int(time.time()))
    chk = agi('test -e %s && echo EXISTS; true' % shlex.quote(dest))
    if 'EXISTS' in chk.stdout:
        return 'AGIdock %s already exists (never overwritten)' % dest
    mk = agi('mkdir -p %s/display' % shlex.quote(part))
    if mk.returncode:
        return 'mkdir failed: %s' % mk.stderr[-200:]
    for files, sub in ((meta_files(u), ''), ([tuple(x) for x in u.get('display') or ()], '/display')):
        groups = collections.OrderedDict()
        for d, f in files:
            groups.setdefault(d, []).append(f)
        for d, fs in groups.items():
            src = subprocess.Popen(SSH + [u['host'], 'nice -n 10 tar cf - -C %s %s' % (shlex.quote(d), ' '.join(map(shlex.quote, fs)))],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            dst = subprocess.run(AGI + ['tar xf - --skip-old-files -C %s%s' % (shlex.quote(part), sub)], stdin=src.stdout,
                                 capture_output=True, timeout=3600)
            src.stdout.close()
            src.wait()
            if src.returncode or dst.returncode:
                return 'stream failed host rc %s agi rc %s %s' % (src.returncode, dst.returncode, (dst.stderr or b'')[-200:])
    manifest = dict(schema='opentallas.auto_export.manifest.v1', split='full record on rtx-pro only (OWNER 11-18)', die=u['die'],
                    element=u['element'], unit=u['unit'], record=u['record'], host=u['host'], signoff=u['signoff'],
                    rtx_dir='%s/%s' % (RTX_ROOT, k), odb_sha256=u['odb_sha'], odb_size=u['odb_size'], files=u['shas'],
                    sizes=u.get('sizes'), display=u.get('display_shas'))
    w = agi('cat > %s/MANIFEST.json' % shlex.quote(part), input=json.dumps(manifest, indent=1) + '\n')
    if w.returncode:
        return 'MANIFEST write failed: %s' % w.stderr[-200:]
    want = {f: u['shas'][f] for _, f in meta_files(u)}
    want.update({'display/' + f: s_ for f, s_ in (u.get('display_shas') or {}).items()})
    if want:
        v = agi('cd %s && sha256sum %s' % (shlex.quote(part), ' '.join(shlex.quote(f) for f in want)), timeout=3600)
        got = dict((l.split(None, 1)[1].strip(), l.split()[0]) for l in v.stdout.splitlines() if len(l.split()) >= 2)
        bad = [f for f, s_ in want.items() if got.get(f) != s_]
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


def collect(hosts, scan, spool=True):
    """-> candidate units (dicts) from spools (+ scans), all hosts in parallel."""
    import concurrent.futures as cf

    def one(h):
        out = []
        try:
            for u in (probe(h, 'spool', {}) if spool else ()):
                out.append(dict(u, host=h, via='spool'))
            if scan:
                for u in probe(h, 'scan', dict(hours=WINDOW_H, roots=ROOTS), timeout=3 * 3600):
                    out.append(dict(u, host=h, via='scan'))
        except Exception as e:
            say('host %s: %s' % (h, e))
        return out
    with cf.ThreadPoolExecutor(len(hosts)) as ex:
        return [u for part in ex.map(one, hosts) for u in part]


def spool_triage(L, cands, now=None):
    """F9 (FLOW-FLEET-R1 11-22): -> (keep, aside {host: [(file, reason)]}, drop {host: [file]}).  Per spool unit:
      canary / test run                     -> set aside now (never a sign-off of record)
      ledger state done / skip              -> spool file dropped (already exported / ODB already in INDEX)
      older than SPOOL_RETRY_AGE_S, first   -> retried once (an export that failed 3 times gets one more try), stays
      older, retried >= SPOOL_ASIDE_AFTER_S ago and still here -> set aside with its reason (signoff gone, last export error,
                                               rtx-pro not verified, ...) in the host's spool/failed/<file> + .reason"""
    now = time.time() if now is None else now
    sr = L.setdefault('spool_retry', {})
    keep, aside, drop = [], {}, {}
    for u in cands:
        if u.get('via') != 'spool' or not u.get('spool'):
            keep.append(u)
            continue
        h, f, so = u['host'], u['spool'], u.get('signoff') or ''
        k = '%s:%s' % (h, f)
        if NOT_RECORD.search(so):
            aside.setdefault(h, []).append((f, 'canary / test run, not a sign-off of record: %s' % so))
            continue
        okey = '%s:%s' % (h, u['odb']) if u.get('odb') else None
        prev = L['units'].get(okey) or {} if okey else {}
        if prev.get('state') in ('done', 'skip'):
            drop.setdefault(h, []).append(f)
            continue
        if u.get('spool_age_s', 0) < SPOOL_RETRY_AGE_S:
            keep.append(u)
            continue
        e = sr.get(k)
        if e is None:
            sr[k] = dict(at=now, signoff=so)
            if prev.get('tries', 0) >= 3:
                prev['tries'] = 2                  # one more export try
            keep.append(u)
            continue
        if now - e['at'] < SPOOL_ASIDE_AFTER_S:
            keep.append(u)
            continue
        why = (u.get('err') or prev.get('err') or prev.get('rtx_err')
               or ('exported, rtx-pro has not verified it' if prev.get('state') in ('agi', 'meta') else '')
               or 'not exported after one retry')
        aside.setdefault(h, []).append((f, '%s (spool age %.1f h): %s' % (why, u.get('spool_age_s', 0) / 3600, so)))
        sr.pop(k, None)
    return keep, aside, drop


def apply_spool_triage(L, cands):
    """spool_triage + the host probes; -> the units to export"""
    keep, aside, drop = spool_triage(L, cands)
    for h, items in aside.items():
        try:
            probe(h, 'asidespool', dict(items=items))
            for f, why in items:
                say('spool %s:%s SET ASIDE: %s' % (h, f, why[:300]))
        except Exception as e:
            say('asidespool %s: %s' % (h, e))
    for h, files in drop.items():
        try:
            probe(h, 'rmspool', dict(files=files))
            say('spool %s: %d file(s) dropped (already exported / in INDEX)' % (h, len(files)))
        except Exception as e:
            say('rmspool %s: %s' % (h, e))
    sp = [u for u in cands if u.get('via') == 'spool']
    if sp:
        say('SPOOL %d file(s), oldest %.1f h; %d set aside, %d dropped' % (
            len(sp), max(u.get('spool_age_s', 0) for u in sp) / 3600, sum(map(len, aside.values())), sum(map(len, drop.values()))))
    return keep


def finish(L, have):
    """4. units rtx-pro has verified: append the AGIdock INDEX row, drop the host spool file, post AUTO-EXPORT.
    Runs at the start of every drain and after every export, so a long backfill still indexes as it goes."""
    t0 = time.time()
    done = []
    rp = os.path.join(STATE, 'rtx_done.jsonl')
    if os.path.isfile(rp):
        for line in open(rp):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            u = L['units'].get(d.get('key'))
            if u and u.get('state') in ('agi', 'meta') and d.get('ok'):
                if append_agi_index(index_row(u), u['odb_sha']):
                    have.add(u['odb_sha'])
                u['how_stored'] = SPLIT_STATUS if u['state'] == 'meta' else 'ARCHIVED-BOTH'
                u['state'], u['done'] = 'done', time.strftime('%Y-%m-%dT%H:%M:%S%z')
                done.append(u)
            elif u and u.get('state') in ('agi', 'meta') and not d.get('ok'):
                u['rtx_err'] = d.get('err')
        os.replace(rp, rp + '.%d' % int(t0))
        for old in os.listdir(STATE):          # F9: rotated rtx_done files are already merged into the ledger above; keep 3 days
            if old.startswith('rtx_done.jsonl.') and old.rsplit('.', 1)[-1].isdigit() and t0 - int(old.rsplit('.', 1)[-1]) > 3 * 86400:
                try:
                    os.unlink(os.path.join(STATE, old))
                except OSError:
                    pass
    if done:
        for h in {u['host'] for u in done if u.get('spool')}:
            try:
                probe(h, 'rmspool', dict(files=[u['spool'] for u in done if u['host'] == h and u.get('spool')]))
            except Exception as e:
                say('rmspool %s: %s' % (h, e))
        lines = ['AUTO-EXPORT %s/%s (%s %s:%s) %s %s/%s (%s), ODB sha %s, record %s, TT %s FF %s, INDEX rows on both'
                 % (u['die'], u['element'], u['via'], u['host'], u['signoff'], u['how_stored'], u['die'], u['unit'],
                    'full record rtx-pro, metadata+display AGIdock' if u['how_stored'] == SPLIT_STATUS else 'full record both stores',
                    u['odb_sha'][:12], u['record'][:12], u.get('tt'), u.get('ff')) for u in done]
        post('\n'.join(lines))
        if queue_view_packs(done):   # 5. the routed-layout pack of every new sign-off (EXPLORER-STORE-R1)
            start_view_packs()
    save_ledger(L)


# ---- 5. view pack (hub -> build host -> explorer store) ------------------------------------------------------------------
# EXPLORER-STORE-R1 (OWNER 11-22: every signed-off record shows its routed layout on the explorer, with no lane step).
VP_ROOT = os.environ.get('OT_VIEWPACK_ROOT', '/srv/opentallas-scratch2/claude/explorer-store-r1')   # per build host: venv/ (brotli + numpy), bin/node, tmp/
VP_CODE = os.environ.get('OT_VIEWPACK_CODE', '/srv/opentallas-scratch2/claude/rt/current/tools/fleet_viz')   # main checkout on every host
VP_STORE_HOST = os.environ.get('OT_VIEWPACK_STORE_HOST', 'epyc8')
VP_STORE_ENV = os.environ.get('OT_VIEWPACK_STORE_ENV', '/srv/opentallas-scratch2/claude/explorer-2-work/explorer2.env')   # LV_STORE, DESIGN_INDEX
VP_STORE_PY = os.environ.get('OT_VIEWPACK_STORE_PY', '/srv/opentallas-scratch2/claude/explorer-2-work/rt/venv/bin/python3')
VIEWPACK_PER_HOST = 2
VP_VARIANT = re.compile(r"__(a\d+_\d{4}|legalrows_\d+)$")


def view_pack_node(u):
    """explorer node id of a unit: <die>.<t|c>.<element without the re-sign suffix> (= design_index tid/cid, any_plan_records.record_id)"""
    return '%s.%s.%s' % (u['die'], 'c' if u.get('kind') == 'c' else 't', VP_VARIANT.sub('', u['element']))


def queue_view_packs(units, state=None):
    """append one view-pack job per unit to <state>/viewpack_queue.jsonl; -> number queued"""
    state = state or STATE
    jobs = [dict(node=view_pack_node(u), host=u['host'], odb=u['odb'], size=u.get('odb_size') or 0, sha=u.get('odb_sha'),
                 label='%s:%s' % (u['host'], u['odb']), queued=time.strftime('%Y-%m-%dT%H:%M:%S%z')) for u in units if u.get('odb') and u.get('die') and u.get('element')]
    if jobs:
        with open(os.path.join(state, 'viewpack_queue.jsonl'), 'a') as f:
            for j in jobs:
                f.write(json.dumps(j) + '\n')
    return len(jobs)


def view_pack_pending(state=None):
    """queued jobs not yet published (newest record per node wins; a job that failed twice is left out)"""
    state = state or STATE
    done, tries = set(), collections.Counter()
    dp = os.path.join(state, 'viewpack_done.jsonl')
    if os.path.isfile(dp):
        for line in open(dp):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            k = (d.get('node'), d.get('sha') or d.get('label'))
            if d.get('ok'):
                done.add(k)
            else:
                tries[k] += 1
    q, qp = {}, os.path.join(state, 'viewpack_queue.jsonl')
    if os.path.isfile(qp):
        for line in open(qp):
            try:
                j = json.loads(line)
            except ValueError:
                continue
            k = (j.get('node'), j.get('sha') or j.get('label'))
            if k in done or tries[k] >= 2:
                continue
            q[j['node']] = j
    return list(q.values())


def view_pack_cmds(j):
    """-> (ot-run argv for the cut on the build host, publish command for the store host, pack dir on the build host)"""
    w = '%s/tmp/auto/%s' % (VP_ROOT, j['node'])
    mem = int((j.get('size') or 0) * 16 / 1e9 + 16)   # the tile step peaks above the extraction (explorer cut_one.sh)
    cut = ('mkdir -p {w} && {L}/venv/bin/python3 -I {code}/design_export.py cut --node {n} --db {db} --work {w} --py {L}/venv/bin/python3 '
           '--node-bin {L}/bin/node --db-label {lab} --no-timing --drop-raw > {w}.log 2>&1; r=$?; tail -2 {w}.log; exit $r').format(
        w=shlex.quote(w), L=VP_ROOT, code=VP_CODE, n=shlex.quote(j['node']), db=shlex.quote(j['odb']), lab=shlex.quote(j['label']))
    inc = '%s/incoming/%s' % (VP_ROOT, j['node'])
    pub = ('set -a; . {env}; set +a; cd {code} && nice -n 10 {py} -I design_export.py publish --node {n} --pack {inc}/{n}.lvp --index "$DESIGN_INDEX" '
           '--store "$LV_STORE" 2>&1 | tail -1; for f in {inc}/{n}.lvp {inc}/verify.json {inc}/cut.json; do rm -f "$f"; done').format(
        env=VP_STORE_ENV, code=VP_CODE, py=VP_STORE_PY, n=shlex.quote(j['node']), inc=shlex.quote(inc))
    return (['ot-run', '--hosts', j['host'], '--dir', VP_ROOT, '--mem', str(mem), '--threads', '4', '--', 'bash', '-c', cut], pub, w, inc)


def view_pack_one(j, state=None):
    """cut one pack on its build host, copy it to the store host, publish; -> (ok, message)"""
    run, pub, w, inc = view_pack_cmds(j)
    r = subprocess.run(run, capture_output=True, text=True, timeout=12 * 3600, stdin=subprocess.DEVNULL)
    if r.returncode:
        return False, 'cut rc %d: %s' % (r.returncode, (r.stdout + r.stderr)[-300:])
    subprocess.run(SSH + [VP_STORE_HOST, 'mkdir -p %s' % shlex.quote(inc)], capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    for f in (j['node'] + '.lvp', 'verify.json', 'cut.json'):
        r = subprocess.run(['scp', '-3', '-q', '-o', 'ControlPath=none', '-o', 'BatchMode=yes', '%s:%s/%s' % (j['host'], w, f), '%s:%s/' % (VP_STORE_HOST, inc)],
                           capture_output=True, text=True, timeout=3600)
        if r.returncode:
            return False, 'copy %s: %s' % (f, r.stderr[-200:])
    r = subprocess.run(SSH + [VP_STORE_HOST, pub], capture_output=True, text=True, timeout=1800, stdin=subprocess.DEVNULL)
    if 'published' not in r.stdout:
        return False, 'publish: %s %s' % (r.stdout[-200:], r.stderr[-200:])
    subprocess.run(SSH + [j['host'], 'rm -f %s/%s.lvp' % (shlex.quote(w), shlex.quote(j['node']))], capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    return True, r.stdout.strip()[-200:]


def view_packs(a=None, state=None, one=view_pack_one):
    """worker: every pending job, at most VIEWPACK_PER_HOST at a time per build host; results to viewpack_done.jsonl"""
    import threading
    state = state or STATE
    lk = open(os.path.join(state, 'viewpack.lock'), 'w')
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return 0
    jobs = view_pack_pending(state)
    sem = collections.defaultdict(lambda: threading.Semaphore(VIEWPACK_PER_HOST))
    wl = threading.Lock()

    def run(j):
        with sem[j['host']]:
            try:
                ok, msg = one(j)
            except Exception as e:
                ok, msg = False, '%s: %s' % (type(e).__name__, e)
        with wl, open(os.path.join(state, 'viewpack_done.jsonl'), 'a') as f:
            f.write(json.dumps(dict(node=j['node'], sha=j.get('sha'), label=j['label'], ok=ok, msg=msg[-300:], at=time.strftime('%Y-%m-%dT%H:%M:%S%z'))) + '\n')
        say('VIEWPACK %s %s %s' % (j['node'], 'published' if ok else 'FAILED', msg[-160:]))
    ts = [threading.Thread(target=run, args=(j,)) for j in jobs]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    return 0


def start_view_packs():
    """detached worker (the drain never waits for a cut); off with OT_VIEWPACK=0 and under pytest"""
    if os.environ.get('OT_VIEWPACK', '1') == '0' or 'PYTEST_CURRENT_TEST' in os.environ:
        return None
    return subprocess.Popen([sys.executable, '-I', os.path.abspath(__file__), 'view-packs'], start_new_session=True, stdin=subprocess.DEVNULL,
                            stdout=open(os.path.join(STATE, 'viewpack.log'), 'a'), stderr=subprocess.STDOUT)


def evidence_backfill(L, budget_s=1500):
    """EVIDENCE-EXPORT-1119: for every exported ('done') unit whose kit still exists on its host, list its landing evidence + view pack, hash it and queue it for rtx-pro (evidence_rtx.json).
    Units whose kit is gone stay without (nothing to copy).  A unit is tried once per drain; evidence_done.jsonl from rtx-pro marks it ev_done."""
    t0, queue = time.time(), []
    dp = os.path.join(STATE, 'evidence_done.jsonl')
    if os.path.isfile(dp):
        for line in open(dp):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            u = L['units'].get(d.get('key'))
            if u and d.get('ok'):
                u['ev_done'] = time.strftime('%Y-%m-%dT%H:%M:%S%z')
        os.replace(dp, dp + '.%d' % int(t0))
    for k, u in L['units'].items():
        if u.get('state') != 'done' or u.get('ev_done') or u.get('ev_none') or not u.get('host') or not u.get('signoff'):
            continue
        if time.time() - t0 > budget_s:
            break
        try:
            ev = probe(u['host'], 'evidence', dict(signoff=u['signoff']), timeout=600)[0]
        except Exception as e:
            say('evidence %s: %s' % (k, e))
            continue
        fl = [tuple(x) for x in ev.get('files') or ()]
        if not fl:
            u['ev_none'] = ev.get('err') or 'no kit evidence on host'
            continue
        hs = probe(u['host'], 'hash', dict(paths=[os.path.join(d, f) for d, f in fl]), timeout=3600)[0]
        u['ev_files'] = [[d, f] for d, f in fl if hs[os.path.join(d, f)][0]]
        u['ev_shas'] = {f: hs[os.path.join(d, f)][0] for d, f in fl if hs[os.path.join(d, f)][0]}
    queue = [dict(key=k, die=u['die'], unit=u['unit'], host=u['host'], files=u['ev_files'], shas=u['ev_shas'])
             for k, u in L['units'].items() if u.get('ev_files') and not u.get('ev_done')]
    tmp = os.path.join(STATE, 'evidence_rtx.json.tmp')
    with open(tmp, 'w') as f:
        json.dump(queue, f, indent=1)
    os.replace(tmp, os.path.join(STATE, 'evidence_rtx.json'))
    save_ledger(L)
    say('evidence backfill: %d unit(s) queued for rtx-pro' % len(queue))


MAIN_GIT = os.environ.get('OT_MAIN_GIT', '/srv/opentallas-scratch2/git/OpenTallas.git')
SIGNOFF_NAME = re.compile(r'(^|/)([^/]*\.)?signoff\.json$')


def main_record_shas(git_dir=None, ref='main'):
    """CLEAN-AGGR-R3 11-22 (intel2 at 150 GB): a sign-off record committed to main IS exported (git is the store of record); every source tree copy carries the
    221 tracked records (physical/ref_tile views, results/...) and the guard refused those trees as 'signed record not exported'.  -> sha256 set ({} on error)"""
    g = ['git', '--git-dir', git_dir or MAIN_GIT]
    try:
        ls = subprocess.run(g + ['ls-tree', '-r', ref], capture_output=True, text=True, timeout=300).stdout
        objs = [ln.split()[2] for ln in ls.splitlines() if ln.split('\t')[0].split()[1:2] == ['blob'] and SIGNOFF_NAME.search(ln.split('\t', 1)[1])]
        if not objs:
            return set()
        out = subprocess.run(g + ['cat-file', '--batch'], input=('\n'.join(objs) + '\n').encode(), capture_output=True, timeout=300).stdout
    except (OSError, subprocess.SubprocessError, IndexError):
        return set()
    shas, i = set(), 0
    while i < len(out):
        j = out.index(b'\n', i)
        hdr = out[i:j].split()
        if len(hdr) < 3 or hdr[1] != b'blob':
            break
        n = int(hdr[2])
        shas.add(hashlib.sha256(out[j + 1:j + 1 + n]).hexdigest())
        i = j + 1 + n + 1
    return shas


def write_guard_exported(L, rows, hosts, push=True, git_dir=None):
    """CLEAN-AGGR-R2 (COORD / FABLE-FLOW-2000 item 5): the delete guard keeps a signed result until it is exported.  Write every exported sign-off record
    sha (INDEX 'record' column + ledger units in state done) and every exported ODB sha to ~/.local/state/ot-delete-guard/exported_records.txt and push it
    to the build hosts.  -> number of shas"""
    shas = set()
    for r in rows:
        for c in (r[3], r[7]):
            if re.fullmatch(r'[0-9a-f]{64}', c or ''):
                shas.add(c)
    for u in L.get('units', {}).values():
        if isinstance(u, dict) and u.get('state') == 'done':
            for c in (u.get('record'), u.get('odb_sha')):
                if isinstance(c, str) and re.fullmatch(r'[0-9a-f]{64}', c):
                    shas.add(c)
    shas |= main_record_shas(git_dir)
    d = os.path.join(HOME, '.local/state/ot-delete-guard')
    os.makedirs(d, exist_ok=True)
    out = os.path.join(d, 'exported_records.txt')
    with open(out + '.tmp', 'w') as f:
        f.write('# built %d (auto_export drain: INDEX record + ODB shas, ledger done, main records)\n' % time.time())
        f.writelines(x + '\n' for x in sorted(shas))
    os.replace(out + '.tmp', out)
    if push:
        for h in hosts:
            try:
                subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=20', '-o', 'ControlPath=none', out,
                                '%s:.local/state/ot-delete-guard/exported_records.txt.new' % h], timeout=120, capture_output=True)
                subprocess.run(SSH + [h, 'mv -f ~/.local/state/ot-delete-guard/exported_records.txt.new ~/.local/state/ot-delete-guard/exported_records.txt'],
                               timeout=120, capture_output=True)
            except Exception as e:
                say('guard exported list push %s: %s' % (h, e))
    return len(shas)


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
    finish(L, have)
    try:
        write_guard_exported(L, rows, HOSTS)
    except Exception as e:
        say('guard exported list: %s' % e)
    if a.evidence:
        evidence_backfill(L, a.budget_s)
        return 0
    # 2. collect new candidates.  FLOW-FLEET-R1 11-22: spools first, the scan in the background with the spools polled again every SPOOL_POLL_S
    # while it runs: a scan (probe timeout 3 h per host; manual `drain --scan` runs held the lock 19:15-22:0x on 11-21) never delays a fresh sign-off
    scan = a.scan or (time.time() - L.get('last_scan', 0) > SCAN_H * 3600)
    import threading
    scan_box, scan_done = [], threading.Event()

    def _scan():
        try:
            scan_box.append(collect(hosts, True, False))
        finally:
            scan_done.set()
    if scan:      # a daemon thread: a drain that reached its budget exits without waiting for the scan
        threading.Thread(target=_scan, daemon=True).start()
    t1 = time.time()
    seen, listed = set(), []
    stop = [False]
    last_poll = [time.time()]

    def poll_spool():
        if time.time() - last_poll[0] >= SPOOL_POLL_S:
            last_poll[0] = time.time()
            finish(L, have)           # units rtx-pro verified meanwhile get their INDEX row now, not after the scan
            process(collect(hosts, False), 'spool re-poll')

    def process(cands, what, repoll=False):
        if stop[0]:
            return
        if what.startswith('spool'):
            cands = apply_spool_triage(L, cands)
        todo = pick(cands)
        if todo or what == 'spool':
            say('%d candidate DBs (%d from spool), %s, scan=%s' % (len(todo), sum(u['via'] == 'spool' for u in todo), what, scan))
        for u in todo:
            if time.time() - t1 > a.budget_s:
                say('budget reached; rest next tick')
                stop[0] = True
                return
            export_one(u)
            if repoll:
                poll_spool()

    def pick(cands):
        todo = []
        for u in cands:
            if 'err' in u:
                if u.get('via') == 'spool':
                    say('spool %s:%s skipped: %s' % (u['host'], u.get('signoff'), u['err']))
                continue
            key = '%s:%s' % (u['host'], u['odb'])
            prev = L['units'].get(key, {})
            if key in seen or prev.get('state') in ('agi', 'meta', 'done', 'skip') or prev.get('tries', 0) >= 3:
                continue
            seen.add(key)
            todo.append(u)
        return todo

    def export_one(u):
        try:
            hs = probe(u['host'], 'hash', dict(paths=[os.path.join(d, f) for d, f in u['files']] +
                                                [os.path.join(d, f) for d, f in u.get('display') or ()]), timeout=3600)[0]
        except Exception as e:
            say('hash %s: %s' % (u['odb'], e))
            return
        shas = {f: hs[os.path.join(d, f)][0] for d, f in u['files']}
        u['bytes'] = sum(hs[os.path.join(d, f)][1] or 0 for d, f in u['files'])
        u['sizes'] = {f: hs[os.path.join(d, f)][1] for d, f in u['files']}
        u['display_shas'] = {f: hs[os.path.join(d, f)][0] for d, f in u.get('display') or () if hs[os.path.join(d, f)][0]}
        u['display'] = [(d, f) for d, f in u.get('display') or () if f in u['display_shas']]
        if None in shas.values():
            say('hash failed %s' % u['odb'])
            return
        osha = shas['6_final.odb']
        key = '%s:%s' % (u['host'], u['odb'])
        if osha in have or any(x.get('odb_sha') == osha and x.get('state') in ('agi', 'meta', 'done') for x in L['units'].values()):
            L['units'][key] = dict(state='skip', odb_sha=osha, why='ODB sha already in INDEX / ledger', signoff=u['signoff'])
            return
        die, el, kind, how = infer(u, rows)
        u.update(die=die, element=el, kind=kind, how=how, odb_sha=osha, shas=shas, unit='%s__ax_%s' % (el, osha[:10]),
                 src='%s %s:%s (%s, die by %s) R-MINIMAL SIGNED TT %s FF %s' % (SRC_TAG, u['host'], u['signoff'], u['via'], how, u.get('tt'), u.get('ff')))
        listed.append(u)
        if a.list_only:
            return
        say('export %s/%s from %s:%s' % (die, u['unit'], u['host'], u['signoff']))
        err = export_agi_meta(u)
        if err:
            say('  FAIL', err)
            L['units'][key] = dict(u, state='err', err=err, at=time.time(), tries=L['units'].get(key, {}).get('tries', 0) + 1)
            save_ledger(L)
            return
        have.add(osha)
        L['units'][key] = dict(u, state='meta', agi_at=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
        save_ledger(L)
        finish(L, have)
    process(collect(hosts, False), 'spool')
    if scan:
        while not stop[0] and not scan_done.wait(SPOOL_POLL_S):
            last_poll[0] = 0
            poll_spool()
        scanned = scan_box[0] if scan_done.is_set() and scan_box and not stop[0] else None
        if scanned is not None:
            if not a.list_only and not a.hosts:
                L['last_scan'] = t0
            process(scanned, 'scan', repoll=True)
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
    er = subprocess.run(SSH + [a.hub, 'cat .local/state/ot-auto-export/evidence_rtx.json'], capture_output=True, text=True, timeout=120)
    ev_reports = []
    for u in (json.loads(er.stdout or '[]') if er.returncode == 0 else []):
        dest = os.path.join(RTX_ROOT, u['die'], u['unit'])
        if not os.path.isdir(dest):
            continue
        err = None
        groups = collections.OrderedDict()
        for d, f in u['files']:
            groups.setdefault(d, []).append(f)
        for d, fs in groups.items():
            src = subprocess.Popen(SSH + [u['host'], 'nice -n 10 tar cf - -C %s %s' % (shlex.quote(d), ' '.join(map(shlex.quote, fs)))], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            dst = subprocess.run(['tar', 'xf', '-', '--skip-old-files', '-C', dest], stdin=src.stdout, capture_output=True, timeout=6 * 3600)
            src.stdout.close()
            src.wait()
            if src.returncode or dst.returncode:
                err = 'evidence stream rc %s/%s' % (src.returncode, dst.returncode)
                break
        if not err:
            bad = []
            for f, sh_ in u['shas'].items():
                h = hashlib.sha256()
                try:
                    with open(os.path.join(dest, f), 'rb') as fh:
                        for b in iter(lambda: fh.read(1 << 22), b''):
                            h.update(b)
                except OSError:
                    bad.append(f)
                    continue
                if h.hexdigest() != sh_:
                    bad.append(f)
            err = 'evidence sha mismatch %s' % bad[:5] if bad else None
        ev_reports.append(dict(key=u['key'], ok=not err, err=err))
        say('evidence', u['die'], u['unit'], err or 'ok')
    if ev_reports:
        subprocess.run(SSH + [a.hub, 'cat >> .local/state/ot-auto-export/evidence_done.jsonl'], input=''.join(json.dumps(x) + '\n' for x in ev_reports), text=True, timeout=120, check=True)
    for u in json.loads(r.stdout or '[]'):
        k = '%s/%s' % (u['die'], u['unit'])
        dest, part = os.path.join(RTX_ROOT, k), os.path.join(RTX_ROOT, k + '.partial')
        idx = os.path.join(RTX_ROOT, 'INDEX.tsv')
        if any(c[7] == u['odb_sha'] for c in parse_index(open(idx).read())):
            reports.append(dict(key=u['key'], ok=True, note='already in rtx INDEX'))
            continue
        if not os.path.exists(dest):
            st = os.statvfs(RTX_ROOT)
            free = st.f_bavail * st.f_frsize
            if free - u.get('bytes', 0) < RESERVE_GB * 1e9:
                say('DISK HOLD %s: %.0f GB free, unit %.1f GB, reserve %d GB; stays pending' % (k, free / 1e9, u.get('bytes', 0) / 1e9, RESERVE_GB))
                continue
            os.makedirs(part, exist_ok=True)
            if u.get('mode') == 'host':     # OWNER split 11-18: the full record comes straight from the build host
                err = None
                groups = collections.OrderedDict()
                for d, f in u['files']:
                    groups.setdefault(d, []).append(f)
                for d, fs in groups.items():
                    src = subprocess.Popen(SSH + [u['host'], 'nice -n 10 tar cf - -C %s %s' % (shlex.quote(d), ' '.join(map(shlex.quote, fs)))],
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    dst = subprocess.run(['tar', 'xf', '-', '-C', part], stdin=src.stdout, capture_output=True, timeout=6 * 3600)
                    src.stdout.close()
                    src.wait()
                    if src.returncode or dst.returncode:
                        err = 'host stream rc %s/%s %s' % (src.returncode, dst.returncode, (dst.stderr or b'')[-200:])
                        break
                if err:
                    reports.append(dict(key=u['key'], ok=False, err=err))
                    continue
            else:                           # units exported before the split: their full copy is on AGIdock
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
    d.add_argument('--evidence', action='store_true', help='backfill landing evidence + view packs of already exported units whose kit still exists')
    d.add_argument('--budget-s', type=float, default=2400)
    r = sub.add_parser('rtx-pull')
    r.add_argument('--hub', default='intel2')
    sub.add_parser('view-packs', help='cut + publish the queued routed-layout packs (started by the drain)')
    a = ap.parse_args(argv)
    if a.cmd == 'view-packs':
        return view_packs(a)
    if a.cmd == 'enqueue':
        p = enqueue(a.signoff, die=a.die, element=a.element, kind=a.kind)
        print(p or 'not R-MINIMAL SIGNED: nothing queued')
        return 0
    return drain(a) if a.cmd == 'drain' else rtx_pull(a)


if __name__ == '__main__':
    sys.exit(main())
