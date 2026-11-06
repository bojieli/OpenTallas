#!/usr/bin/env python3
"""ot-reaper (OWNER 2026-10-13): failed / cancelled / superseded closure-loop jobs are deleted at once, unarchived.
Only CLOSED routes have archival value (those go through closed_archive + el1012-epyc1-disk/drive.py, not here).

Runs on localhost (the job records live here) from cron every 30 min and drives every fleet host over ssh:
  JOBS  every job directory under a closure-loop root whose records are ALL strippable loses its large files:
        the source copies (src, bench_src*, bsrc_*, *_src) and every file that is not a small log / report / json /
        script (see KEEP_EXT, KEEP_MAX).  record/ and .keep are kept.  Strippable = status in FAIL, or any other
        terminal non-CLOSED status whose element (spec.block) has a newer job.
        Never: a job that is not terminal (QUEUED SYNC READY RUNNING ECO ECO_INSTALL ...), a CLOSED job, a directory
        a live job's record mentions, a directory a live process references, a directory written in the last
        QUIET_MIN minutes, or a hand-run directory a live job record / pending spec / hosts.json references, a directory with a .keep whose job is still the newest job of its element.
  HAND  whole hand-run directories (direct children of HAND_ROOTS) with no live process, no .keep and no file
        newer than HAND_IDLE_H (owner rule 10-09: scratch idle > 48 h is deleted).
  GATE  (ROOT-2130 2026-10-18, FLEET-DISK P1) every pre_route_gate run under a ref_gate root idle > GATE_IDLE_H with no
        live process, no .keep, no live-job / pending_results / recent HANDOFF or lane mention loses its regenerable
        bulk (src/, bin/, odb/def/spef/v/gds over 20 MB, any other non-log/json/png/rpt file over 50 MB); logs, json,
        png and reports are kept.  Every host (EPYC4 held 444 GB of 12-48 h gate bulk the 48 h HAND rule could not reach).
  UMBRELLA (FLEET-DISK P2) a HAND dir that is NOT reapable as a whole (a live / recent child keeps it "recent") and holds
        > UMBRELLA_GB with >= 4 child dirs is judged one level down: each child with no process, no .keep, no reference
        or mention and no file newer than HAND_IDLE_H goes (a git worktree only when clean and its HEAD is on a branch,
        via `git worktree remove`).  claude/qwen-kvsys (829 GB, 62 children) was never reaped before.
  HOSTS (FLEET-DISK P3) = the closure-loop hosts.json hosts + ot-run's HOSTS + STATIC_HOSTS, so a new host (ot-epyc5)
        is covered.  EARLY_FAIL_* jobs are FAIL (P4).
Usage: ot-reaper.py [--dry] [--host H ...] [--no-hand]      log: ~/claude-takeover-20261007/ot-reaper.log
"""
import collections, datetime as dt, fcntl, glob, json, os, subprocess, sys, time

JOBS = os.path.expanduser("~/.local/state/closure_loop/jobs")
LOG = os.path.expanduser("~/claude-takeover-20261007/ot-reaper.log")
STATIC_HOSTS = ["ot-epyc4", "ot-epyc7", "ot-epyc8", "ot-epyc9", "ot-gold2", "ot-gold1", "ot-agidock128", "ot-pve1"]   # epyc6/7 FLEET-NEW 2026-10-19
HOSTS_JSON = [os.path.expanduser("~/wt-claude-closure-daemon-1010/tools/closure_loop/hosts.json")]   # the LIVE daemon's
OT_RUN = os.path.expanduser("~/bin/ot-run")
RETIRED = {"ot-epyc1", "ot-epyc1tb", "ot-epyc2", "ot-epyc3", "ot-epyc5", "ot-epyc6", "localhost"}
FAIL = {"NEEDS_RTL", "NEEDS_HUMAN", "FLOORPLAN_MARGIN", "PREROUTE_MARGIN", "REFUSED", "CANCELLED", "INVALID",
        "EARLY_FAIL"}                                   # + every EARLY_FAIL_* (strippable_status)
TAKEOVER = os.path.expanduser("~/claude-takeover-20261007")
GATE_ROOTS = ["/srv/opentallas-scratch/claude/ref_gate", "/srv/opentallas-scratch2/claude/ref_gate"]
GATE_IDLE_H = 12
UMBRELLA_GB = 100
MENTION_LANE_H = 24
MENTION_HANDOFF_LINES = 400
TERMINAL_OTHER = {"SMOKE_OK", "NEEDS_BUDGET"}          # strippable only when superseded
HAND_ROOTS = ["/srv/opentallas/claude", "/srv/opentallas/scratch-overflow/claude", "/srv/opentallas/jobs-overflow",
              "/srv/opentallas-scratch/claude", "/srv/opentallas-scratch/codex", "/srv/opentallas-scratch/opentallas/claude",
              "/srv/opentallas-scratch2/claude", "/srv/opentallas-scratch2/codex",
              "/srv/opentallas-scratch2/scratch/claude", "/srv/opentallas-scratch2/scratch/codex",
              # ROOTSCR_1101: epyc2 second scratch root on the root disk (bind mount of /home/ubuntu/scratch-root)
              "/srv/opentallas-scratch3/claude", "/srv/opentallas-scratch3/codex",
              # GATE (ROOT 2026-10-15): pre_route_gate staging runs (<name>-<ts>/ + .tgz) were HAND_NEVER as a parent and
              # never reaped -- 1.18 TB on EPYC1.  Each run is judged like a hand-run dir (idle > 48 h, no process, no
              # .keep, not referenced by a live job); the committed gate_result.json keeps the record.
              "/srv/opentallas-scratch/claude/ref_gate", "/srv/opentallas-scratch2/claude/ref_gate"]   # absent roots are skipped
HAND_NEVER = ["closure-loop", "closure-loop-moved", "closed-archive-gds", "lost+found", "tools", "seed", "repos", "data",
              "ref_gate", "git-mirror", "layout-viewer-store", "viz-elem-store",
              # fleet flow snapshots every route's command picks (PATHPICK, ROOT-2130 10-18): never reaped as scratch
              "ttbatch", "flowhold", "ttviews"]
HAND_IDLE_H = 48
ROOTSCR_ALIAS = ("/home/ubuntu/scratch-root/", "/srv/opentallas-scratch3/")   # ROOTSCR_1101 real path -> mount path
HOLDS = os.path.expanduser("~/.local/state/closure_loop/reaper_holds")        # touch <job name> to keep a job's files
ADOPT_HOLDS = os.path.expanduser("~/.local/state/closure_loop/adoption_holds")
POSTROUTE_STAGES = {"collect", "verdict", "meas_resta", "export", "record"}
POSTROUTE_GRACE_H = 24

HOST_PY = r'''
import json, os, re, shutil, stat, subprocess, sys, time
A = json.loads(sys.stdin.read())
DRY = A["dry"]; NOW = time.time()
KEEP_EXT = {".log", ".rpt", ".json", ".txt", ".md", ".sdc", ".tcl", ".mk", ".sh", ".yaml", ".yml", ".csv", ".py", ".rc"}
KEEP_MAX = {".log": 20e6, ".rpt": 20e6}; KEEP_DEF = 5e6
SRC_RE = re.compile(r"^(src|bench_src.*|bsrc_.*|.*_src|.*_src_.*)$")
QUIET = A["quiet_min"] * 60
def procs():
    out = []
    for p in os.listdir("/proc"):
        if not p.isdigit() or int(p) == os.getpid(): continue
        try:
            out.append(open(f"/proc/{p}/cmdline", "rb").read().replace(b"\0", b" ").decode("utf-8", "replace"))
            out.append(os.readlink(f"/proc/{p}/cwd"))
        except OSError: pass
        try:                                   # open files too (a reader of an older sibling's outputs)
            for fd in os.listdir(f"/proc/{p}/fd"):
                try: out.append(os.readlink(f"/proc/{p}/fd/{fd}"))
                except OSError: pass
        except OSError: pass
    try: out.append(subprocess.run("docker ps -q | xargs -r docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}'",
                                   shell=True, capture_output=True, text=True, timeout=60).stdout)
    except Exception: pass
    return "\n".join(out)
BLOB = procs()
def live(d): return (d + "/") in BLOB or (d + " ") in BLOB or (d + "\n") in BLOB or BLOB.endswith(d)
def blocks(p):
    try: return os.lstat(p).st_blocks * 512
    except OSError: return 0
def rm(p, isdir):
    if DRY: return
    try:
        shutil.rmtree(p) if isdir else os.unlink(p)
    except FileNotFoundError: pass
    except OSError:
        subprocess.run(["sudo", "-n", "rm", "-rf", "--one-file-system", p], capture_output=True)
def tree(p):
    t = 0
    for r, ds, fs in os.walk(p):
        t += sum(blocks(os.path.join(r, f)) for f in fs)
    return t
def strip(d):
    freed = 0
    for e in os.scandir(d):
        if e.is_dir(follow_symlinks=False) and SRC_RE.match(e.name):
            freed += tree(e.path); rm(e.path, True)
    for r, ds, fs in os.walk(d, topdown=False):
        rel = os.path.relpath(r, d)
        if rel == "record" or rel.startswith("record/"): continue
        for f in fs:
            p = os.path.join(r, f); x = os.path.splitext(f)[1]
            try: st = os.lstat(p)
            except OSError: continue
            if f == ".keep": continue
            if stat.S_ISREG(st.st_mode) and x in KEEP_EXT and st.st_size <= KEEP_MAX.get(x, KEEP_DEF): continue
            freed += st.st_blocks * 512; rm(p, False)
        if not DRY and r != d:
            try: os.rmdir(r)
            except OSError: pass
    return freed
def recent(d):
    try: return any(NOW - e.stat(follow_symlinks=False).st_mtime < QUIET for e in os.scandir(d)) or NOW - os.lstat(d).st_mtime < QUIET
    except OSError: return True
tot = 0
def free():
    o = {}
    for r in A["roots"] + [h[0] for h in A["hand"]] + A.get("gate_roots", []):
        if os.path.isdir(r):
            v = os.statvfs(r); o[os.stat(r).st_dev] = (o.get(os.stat(r).st_dev, (r,))[0], v.f_bavail * v.f_frsize)
    return o
F0 = free()
for root in A["roots"]:
    if os.path.basename(root.rstrip("/")) != "closure-loop" or not os.path.isdir(root): continue
    for e in sorted(os.scandir(root), key=lambda e: e.name):
        j = A["jobs"].get(e.name)
        if not j or e.is_symlink() or not e.is_dir(follow_symlinks=False): continue
        d = e.path
        if os.path.exists(d + "/.keep") and j["keep"]: continue
        if live(d) or recent(d): continue
        try: f = strip(d)
        except Exception as ex:
            print(f"ERROR {d}: {ex!r}"); continue
        tot += f
        if f >= 1e6: print(f"JOB {d} {f/1e9:.2f} GB ({j['why']})")
for root, never in A["hand"]:
    if not os.path.isdir(root): continue
    for e in sorted(os.scandir(root), key=lambda e: e.name):
        if root.rstrip("/").endswith("/ref_gate") and e.name.endswith(".tgz"):
            try:       # a live gate may remove its own archive while we look (17:22 10-15 FileNotFoundError)
                old = e.is_file(follow_symlinks=False) and NOW - e.stat(follow_symlinks=False).st_mtime > A["hand_idle_h"] * 3600
                if old and not live(e.path):
                    f = blocks(e.path)
                    if not DRY: os.unlink(e.path)
                    tot += f; print(f"HAND {e.path} {f/1e9:.2f} GB (gate archive idle > {A['hand_idle_h']} h)")
            except OSError:
                pass
            continue
        if e.name in never or e.name.startswith(".") or e.is_symlink() or not e.is_dir(follow_symlinks=False): continue
        d = e.path
        if os.path.exists(d + "/.keep") or live(d): continue
        if any(x == d or x.startswith(d + "/") for x in A["refs"]) or os.path.basename(d) in A.get("mentions", ""):
            continue
        r = subprocess.run(["find", d, "-xdev", "-newermt", f"-{A['hand_idle_h']} hours", "-print", "-quit"], capture_output=True, text=True)
        if r.returncode or r.stdout.strip(): continue
        f = tree(d); rm(d, True); tot += f
        print(f"HAND {d} {f/1e9:.2f} GB (no process, no .keep, idle > {A['hand_idle_h']} h)")
BULK = re.compile(r"\.(odb|def|spef|v|v\.gz|gds|gds\.gz|sv|vcd|fst|o|a|gch)$")
GATE_KEEP = (".png", ".json", ".log", ".rpt")
MENT = A.get("mentions", "")
def mentioned(d): return os.path.basename(d.rstrip("/")) in MENT
def refd(d): return any(x == d or x.startswith(d + "/") for x in A["refs"])
for root in A.get("gate_roots", []):
    if not os.path.isdir(root): continue
    for e in sorted(os.scandir(root), key=lambda e: e.name):
        if e.name.startswith(".") or e.is_symlink() or not e.is_dir(follow_symlinks=False): continue
        d = e.path
        if os.path.exists(d + "/.keep") or live(d) or refd(d) or mentioned(d): continue
        mark = d + "/.ot_gate_trimmed"
        newest, files = 0, []
        for r, ds, fs in os.walk(d):
            for f in fs:
                p = os.path.join(r, f)
                try: st = os.lstat(p)
                except OSError: continue
                if f != ".ot_gate_trimmed": newest = max(newest, st.st_mtime)
                files.append((p, st))
        if NOW - newest < A["gate_idle_h"] * 3600: continue
        if os.path.exists(mark) and os.lstat(mark).st_mtime >= newest: continue
        freed = 0
        for p, st in files:
            top = os.path.relpath(p, d).split(os.sep)[0]
            if not stat.S_ISREG(st.st_mode) and not stat.S_ISLNK(st.st_mode): continue
            if top in ("src", "bin") or (BULK.search(p) and st.st_size > 20e6) or (st.st_size > 50e6 and not p.endswith(GATE_KEEP)):
                freed += st.st_blocks * 512; rm(p, False)
        for sub in ("src", "bin"):
            if os.path.isdir(d + "/" + sub) and not os.path.islink(d + "/" + sub): rm(d + "/" + sub, True)
        if not DRY:
            open(mark, "w").close()
        tot += freed
        if freed >= 1e8: print(f"GATE {d} {freed/1e9:.2f} GB (gate idle {(NOW-newest)/3600:.0f} h > {A['gate_idle_h']} h; logs/json/png kept)")
def git_clean_worktree(d):
    """a clean git worktree whose HEAD is on some branch: (True, git dir) ; else (False, why)"""
    def g(*a):
        return subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=300)
    st = g("status", "--porcelain")
    if st.returncode: return False, "git status failed"
    dirty = [x for x in st.stdout.splitlines() if "__pycache__" not in x and not x.endswith(".pyc")]
    if dirty: return False, f"dirty ({len(dirty)} paths)"
    br = g("branch", "-a", "--contains", "HEAD")
    if br.returncode or not br.stdout.strip(): return False, "HEAD on no branch"
    return True, ""
DU_CACHE = "/tmp/ot-reaper-du.json"
try: DUC = json.load(open(DU_CACHE))
except Exception: DUC = {}
def du_gb(d):
    c = DUC.get(d)
    if c and NOW - c[0] < 6 * 3600: return c[1]          # du of an 800-GB umbrella every 30 min is too costly
    try:
        r = subprocess.run(["du", "-sx", "--block-size=1G", d], capture_output=True, text=True, timeout=900)
        v = int(r.stdout.split()[0])
    except Exception: return 0
    DUC[d] = [NOW, v]
    try: json.dump(DUC, open(DU_CACHE, "w"))
    except OSError: pass
    return v
for root, never in A["hand"] if A.get("umbrella_gb") else []:
    if not os.path.isdir(root) or root.rstrip("/").endswith("/ref_gate"): continue
    for e in sorted(os.scandir(root), key=lambda e: e.name):
        if e.name in never or e.name.startswith(".") or e.is_symlink() or not e.is_dir(follow_symlinks=False): continue
        d = e.path
        if not os.path.isdir(d) or os.path.exists(d + "/.keep") or os.path.isfile(d + "/.git"): continue
        kids = [k for k in os.scandir(d) if k.is_dir(follow_symlinks=False) and not k.name.startswith(".")]
        if len(kids) < 4 or du_gb(d) < A["umbrella_gb"]: continue
        for k in sorted(kids, key=lambda k: k.name):
            c = k.path
            if k.name in never or os.path.exists(c + "/.keep") or live(c) or refd(c) or mentioned(c): continue
            r = subprocess.run(["find", c, "-xdev", "-newermt", f"-{A['hand_idle_h']} hours", "-print", "-quit"], capture_output=True, text=True)
            if r.returncode or r.stdout.strip(): continue
            if os.path.isfile(c + "/.git"):
                ok, why = git_clean_worktree(c)
                if not ok:
                    print(f"SKIP {c}: git worktree {why}"); continue
                f = tree(c)
                if not DRY:
                    rr = subprocess.run(["git", "-C", c, "worktree", "remove", "--force", c], capture_output=True, text=True, timeout=1800)
                    if rr.returncode:
                        print(f"SKIP {c}: git worktree remove failed {rr.stderr.strip()[-200:]}"); continue
                tot += f; print(f"UMBRELLA {c} {f/1e9:.2f} GB (clean git worktree, idle > {A['hand_idle_h']} h)")
                continue
            f = tree(c); rm(c, True); tot += f
            print(f"UMBRELLA {c} {f/1e9:.2f} GB (child of a > {A['umbrella_gb']} GB dir; no process, no .keep, idle > {A['hand_idle_h']} h)")
F1 = free()
print("DF " + "; ".join(f"{F1[k][0]} {F0[k][1]/1e9:.0f} -> {F1[k][1]/1e9:.0f} GB free" for k in F1))
print(f"TOTAL {tot/1e9:.1f}")
'''

RELEASED_HOST_PY = r'''

# Exact creator releases only; the legacy broad strip path is not called.
import hashlib, shlex
SAFE_RELEASE_ROOTS = ('/srv/opentallas-scratch/claude/', '/srv/opentallas-scratch2/claude/', '/srv/opentallas-scratch3/claude/', '/home/ubuntu/scratch-root/claude/')
CACHE_EXT = {'.cpp', '.h', '.d', '.dat', '.mk', '.f'}
BULK_EXT = {'.odb', '.def', '.gds', '.spef', '.rtlil'}
CHECKPOINTS = {'6_final.odb', '5_1_grt.odb', '4_cts.odb'}

def signed_record(value):
    if isinstance(value, dict):
        return any((k in ('verdict', 'local_verdict', 'status') and v == 'SIGNED') or signed_record(v) for k,v in value.items())
    return isinstance(value, list) and any(signed_record(v) for v in value)

def release_guard(row):
    d = os.path.normpath(row['path'])
    if not any(d.startswith(root) and d != root.rstrip('/') for root in SAFE_RELEASE_ROOTS): return 'unsafe root'
    if not row.get('creator_release'): return 'no creator release'
    kind = row.get('kind')
    if kind not in ('generated-cache', 'duplicate-bulk', 'intermediate-bulk'): return 'unknown release kind'
    if not os.path.isdir(d) or os.path.islink(d): return 'missing or linked root'
    if kind == 'generated-cache' and not any(x in ('obj', 'obj_dir') for x in d.split('/')): return 'not a generated obj root'
    # Any live process/container/parent or live record dependency preserves it.
    pattern = r'/(?:srv/opentallas-scratch[^/\s]*|home/ubuntu/scratch-root)/claude/[^\s\x00\"\'<>|;,:()\[\]=]+'
    refs = re.findall(pattern, BLOB) + list(A.get('refs', []))
    for ref in refs:
        ref = ref.rstrip('/')
        if ref == d or ref.startswith(d + '/') or d.startswith(ref + '/'): return 'live/reference: ' + ref
    # A selective empty ancestor marker exception must be explicit per cache.
    ancestor = d
    while any((ancestor + '/').startswith(root) for root in SAFE_RELEASE_ROOTS):
        marker = os.path.join(ancestor, '.keep')
        if os.path.lexists(marker):
            allowed = kind == 'generated-cache' and row.get('empty_ancestor_keep_exception') is True and ancestor != d and os.path.isfile(marker) and os.stat(marker).st_size == 0
            if not allowed: return '.keep: ' + marker
        ancestor = os.path.dirname(ancestor)
    checks = [d]
    # Check direct capsule signoff paths without scanning unrelated sibling kits.
    ancestor = d
    while any((ancestor + '/').startswith(root) for root in SAFE_RELEASE_ROOTS):
        checks += [os.path.join(ancestor, 'signoff'), os.path.join(ancestor, 'signoff.json')]
        ancestor = os.path.dirname(ancestor)
    for root in checks:
        items = [root] if os.path.isfile(root) else (os.path.join(dp, f) for dp, dirs, fs in os.walk(root) for f in fs + [name for name in dirs if name == '.git'] if f in ('.keep', 'signoff.json', 'SIGNED', '.git'))
        for path in items:
            name = os.path.basename(path)
            if name in ('.keep', 'SIGNED', '.git'): return 'protected: ' + path
            if name == 'signoff.json':
                try:
                    if signed_record(json.load(open(path))): return 'SIGNED: ' + path
                except (OSError, ValueError): return 'unreadable signoff: ' + path
    if os.path.lexists(os.path.join(d, '.git')): return 'git source'
    if kind == 'duplicate-bulk' and not row.get('destination'): return 'no preserved destination'
    if kind == 'intermediate-bulk':
        if not row.get('preserve'): return 'no latest checkpoint contract'
        if not all(os.path.isfile(p) and os.path.getsize(p) > 0 for p in row['preserve']): return 'missing preserved checkpoint'
    return ''

def retained_destination(row):
    """Verify the retained copy on its actual host in one bounded batch."""
    destination=row.get('destination','')
    host, sep, root=destination.partition(':')
    if not sep or not re.fullmatch(r'[A-Za-z0-9_.-]+',host) or not root.startswith('/'):
        return 'invalid preserved destination'
    payload=dict(root=root,files=[dict(relative=os.path.relpath(item['path'],row['path']),bytes=item['bytes'],sha256=item.get('sha256')) for item in row['files']])
    script="""import os,sys,json,hashlib
request=json.load(sys.stdin);root=os.path.realpath(request['root'])
if not os.path.isdir(root):raise ValueError('retained root missing')
for item in request['files']:
 path=os.path.join(root,item['relative']);real=os.path.realpath(path)
 if os.path.commonpath([root,real])!=root or os.path.islink(path):raise ValueError('retained path escapes root')
 if not os.path.isfile(path) or os.path.getsize(path)!=item['bytes']:raise ValueError('retained file missing or changed')
 digest=hashlib.sha256()
 with open(path,'rb') as stream:
  for block in iter(lambda:stream.read(4<<20),b''):digest.update(block)
 if digest.hexdigest()!=item['sha256']:raise ValueError('retained hash differs')
print('RETAINED_COPY_VERIFIED')
"""
    same=host==row.get('host') or {host,row.get('host')}<={'localhost','intel2'}
    command=['python3','-c',script]
    if not same:
        if host in ('localhost','intel2'):host='hub'
        remote='python3 -c '+shlex.quote(script)
        command=['ssh','-o','ConnectTimeout=10','-o','BatchMode=yes',host,remote]
        if os.geteuid()==0:command=['sudo','-n','-u','ubuntu']+command
    try:
        result=subprocess.run(command,input=json.dumps(payload),capture_output=True,text=True,timeout=180)
        if result.returncode or result.stdout.strip()!='RETAINED_COPY_VERIFIED':return 'retained destination not verified: '+result.stderr[-160:]
    except (OSError,subprocess.SubprocessError) as error:return 'retained destination unavailable: '+repr(error)
    return ''


def tracked_files(d):
    command=['git','-C',d,'ls-files','-z','--']
    if os.geteuid()==0:command=['sudo','-n','-u','ubuntu']+command
    try:
        result=subprocess.run(command,capture_output=True,timeout=30,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
    except (OSError,subprocess.SubprocessError):return None
    if result.returncode:
        if b'not a git repository' in result.stderr:return set()
        return None
    return {os.path.normpath(os.path.join(d,os.fsdecode(p))) for p in result.stdout.split(b'\0') if p}

def apply_release(row):
    result = dict(id=row['id'], path=row['path'], files=0, bytes=0)
    if not os.path.lexists(row['path']) and all(not os.path.lexists(item['path']) for item in row['files']):
        result.update(status='ALREADY_REMOVED',actual_freed_bytes=0); return result
    reason = release_guard(row)
    if reason:
        result.update(status='SKIP', reason=reason); return result
    d = os.path.normpath(row['path']); real_root=os.path.realpath(d); kind = row['kind']; selected=[]
    tracked=tracked_files(d)
    if tracked is None:
        result.update(status='SKIP',reason='Git source guard unavailable');return result
    # Validate the entire exact manifest before the first mutation.
    for item in row['files']:
        p = os.path.normpath(item['path']); ext = os.path.splitext(p)[1]
        if not p.startswith(d + '/') or os.path.islink(p) or os.path.commonpath([real_root,os.path.realpath(p)])!=real_root:
            result.update(status='SKIP', reason='unsafe file: ' + p); return result
        if p in tracked:
            result.update(status='SKIP',reason='tracked Git source: '+p);return result
        if kind == 'generated-cache':
            if ext == '.h' and 'dpi' in os.path.basename(p).lower():
                result.update(status='SKIP',reason='DPI header required for reuse: '+p);return result
            if not all(key in item for key in ('mtime_ns', 'inode')):
                result.update(status='SKIP', reason='cache identity missing: ' + p); return result
            good = ext in CACHE_EXT and ext in row.get('released_suffixes', []) and os.path.basename(p).startswith('V')
        else:
            good = ext in BULK_EXT and p not in row.get('preserve', [])
            if kind == 'intermediate-bulk': good = good and os.path.basename(p) not in CHECKPOINTS and 'seed' not in os.path.basename(p).lower()
        if not good:
            result.update(status='SKIP', reason='unique/source/checkpoint file: ' + p); return result
        try: st = os.lstat(p)
        except FileNotFoundError: continue
        if not stat.S_ISREG(st.st_mode) or st.st_size != item['bytes'] or any(key in item and getattr(st, attr) != item[key] for key, attr in (('mtime_ns','st_mtime_ns'), ('inode','st_ino'))):
            result.update(status='SKIP', reason='changed file: ' + p); return result
        if kind == 'duplicate-bulk':
            if not item.get('sha256'):
                result.update(status='SKIP', reason='no duplicate identity: ' + p); return result
            h=hashlib.sha256()
            with open(p,'rb') as stream:
                for block in iter(lambda: stream.read(4 << 20), b''): h.update(block)
            if h.hexdigest()!=item['sha256']:
                result.update(status='SKIP', reason='duplicate identity changed: ' + p); return result
        selected.append((p, st))
    if kind == 'duplicate-bulk' and selected:
        reason=retained_destination(row)
        if reason:
            result.update(status='SKIP',reason=reason);return result
    # Resample process/mount references immediately before unlinking the batch.
    global BLOB
    BLOB = procs()
    reason=release_guard(row)
    if reason:
        result.update(status='SKIP',reason=reason);return result
    before=os.statvfs(d)
    for p, st in selected:
        if os.path.commonpath([real_root,os.path.realpath(p)])!=real_root:
            result.update(status='SKIP',reason='path escaped at apply: '+p);return result
        now=os.lstat(p)
        if (now.st_ino,now.st_mtime_ns,now.st_size)!=(st.st_ino,st.st_mtime_ns,st.st_size):
            result.update(status='SKIP',reason='file changed at apply: '+p);return result
    for p, st in selected:
        if not DRY:
            rm(p, False)
            if os.path.lexists(p):
                result.update(status='FAILED', reason='unlink did not remove: '+p); return result
        result['files']+=1;result['bytes']+=st.st_blocks*512
    after=os.statvfs(d)
    result.update(status='DRY' if DRY else ('APPLIED' if selected else 'ALREADY_REMOVED'), actual_freed_bytes=(after.f_bavail-before.f_bavail)*after.f_frsize)
    return result

for row in A.get('released', []):
    try: print('RELEASE ' + json.dumps(apply_release(row)), flush=True)
    except Exception as ex: print('RELEASE ' + json.dumps(dict(id=row['id'],path=row.get('path'),status='SKIP',reason=repr(ex))),flush=True)
headroom=[]
for path in ('/', '/srv/opentallas-scratch/claude', '/srv/opentallas-scratch2/claude', '/srv/opentallas-scratch3/claude'):
    try:
        s=os.stat(path);v=os.statvfs(path);headroom.append(dict(path=path,device=s.st_dev,on_root=s.st_dev==os.stat('/').st_dev,available_bytes=v.f_bavail*v.f_frsize))
    except OSError:pass
print('HEADROOM '+json.dumps(headroom),flush=True)
'''


def released_main():
    """Bounded exact-file queue. This path never runs legacy HAND/JOB stripping."""
    import base64, hashlib, pathlib, shlex
    queue = pathlib.Path(sys.argv[sys.argv.index('--released-manifest') + 1]).expanduser()
    receipt_dir = (queue if queue.is_dir() else queue.parent) / 'receipts'
    receipt_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(queue.glob('*.json')) if queue.is_dir() else [queue]
    rows=[]
    for path in files:
        try: value=json.loads(path.read_text())
        except (OSError,ValueError) as error:
            print('SKIP manifest',str(path),repr(error),flush=True);continue
        for row in value if isinstance(value,list) else [value]:
            row=dict(row)
            identity=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
            row['id']=identity
            previous=receipt_dir/(identity+'.json')
            if previous.exists():
                try:
                    if json.loads(previous.read_text()).get('status') in ('APPLIED','ALREADY_REMOVED'): continue
                except (OSError,ValueError):pass
            rows.append(row)
    hosts=[sys.argv[i+1] for i,a in enumerate(sys.argv) if a=='--host'] or sorted({r['host'] for r in rows})
    dry='--dry' in sys.argv
    lock=open('/tmp/ot-reaper.lock','w')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:return
    # Reuse the existing process/mount scanner and exact unlink helper, never strip().
    prefix=HOST_PY.split('tot = 0\n',1)[0].replace('BLOB = procs()', 'BLOB = procs() if A.get("released") else ""').replace('docker ps -q |', 'docker ps -aq |')
    code=prefix+RELEASED_HOST_PY
    encoded=base64.b64encode(code.encode()).decode()
    command='sudo -n python3 -c '+shlex.quote('import base64;exec(base64.b64decode('+repr(encoded)+'))')
    active, _ = table()
    if active is None:
        print('SKIP: unreadable job record',flush=True);return
    def one(host):
        own=[r for r in rows if r['host']==host or {r['host'],host}=={'intel2','localhost'}]
        args=dict(dry=dry,quiet_min=20,refs=REFS,released=own)
        try:
            result=subprocess.run(['ssh','-o','ConnectTimeout=15','-o','BatchMode=yes',host,command],input=json.dumps(args),capture_output=True,text=True,timeout=900)
            return host,result
        except subprocess.SubprocessError as ex:return host,ex
    import concurrent.futures as cf
    with cf.ThreadPoolExecutor(max(1,min(6,len(hosts)))) as executor:
        for host,result in executor.map(one,hosts):
            if not isinstance(result,subprocess.CompletedProcess):
                print(host,repr(result),flush=True);continue
            if result.returncode:print(host,'ERROR',result.stderr[-500:],flush=True)
            for line in result.stdout.splitlines():
                print(host,line,flush=True)
                if not line.startswith('RELEASE ') or dry:continue
                value=json.loads(line[8:]);value.update(host=host,finished=time.time())
                dest=receipt_dir/(value['id']+'.json');tmp=dest.with_suffix('.tmp')
                tmp.write_text(json.dumps(value,indent=2)+'\n');os.replace(tmp,dest)


def now(): return dt.datetime.now().astimezone().isoformat(timespec="seconds")
def log(m):
    with open(LOG, "a") as f: f.write(f"{now()} ot-reaper {m}\n")

def table():
    jobs = []
    for f in glob.glob(os.path.join(JOBS, "*.json")):
        try: d = json.load(open(f))
        except (OSError, ValueError): return None, None      # a record mid-write: skip this whole run
        d["_txt"] = open(f).read(); jobs.append(d)
    def strippable_status(s): return s in FAIL or s.startswith("EARLY_FAIL")
    def terminal(s): return strippable_status(s) or s in TERMINAL_OTHER or s == "CLOSED"
    newest = {}
    for d in jobs:
        b = (d.get("spec") or {}).get("block") or d["name"]
        if b not in newest or (d.get("created") or "") > (newest[b].get("created") or ""): newest[b] = d
    live_txt = "\n".join(d["_txt"] for d in jobs if not terminal(d.get("status") or ""))
    by = collections.defaultdict(list); roots = set()
    for d in jobs:
        by[d["name"]].append(d)
        if d.get("run"):
            by[os.path.basename(d["run"].rstrip("/"))].append(d); roots.add(os.path.dirname(d["run"].rstrip("/")))
    out = {}
    held = set(os.listdir(HOLDS)) if os.path.isdir(HOLDS) else set()
    held |= set(os.listdir(ADOPT_HOLDS)) if os.path.isdir(ADOPT_HOLDS) else set()
    held = {h[:-5] if h.endswith(".json") else h for h in held}
    def postroute_hold(d):
        # ROOT 2026-10-15 (QVM ne2 reaped 09:00 with a CLOSED-verdict route under flow-bug recovery): a job whose
        # physical route FINISHED (rc=0, verdict computed) and then stopped NEEDS_HUMAN in a post-route stage keeps
        # its ODB/SPEF/SDC for POSTROUTE_GRACE_H, and indefinitely under an explicit hold marker or pending recovery.
        if d["name"] in held or d.get("postroute_recovery") or d.get("eco_overlay_recovery"):
            return True
        # ROOT 2026-10-16 (ls5 46.9 GB / ctrl core s4 42 GB reaped after a PASSING hold ECO whose install failed on a
        # missing 6_final.def): a NEEDS_HUMAN job stopped at eco_install after "hold ECO passed" is a closed result
        # awaiting re-install -- kept, no grace expiry, until it leaves NEEDS_HUMAN or is cancelled.
        if d.get("status") == "NEEDS_HUMAN" and (d.get("stage_key") == "eco_install"
                                                 or "hold ECO passed" in (d.get("reason") or "")):
            return True
        if d.get("status") != "NEEDS_HUMAN" or d.get("stage_key") not in POSTROUTE_STAGES:
            return False
        ev = " ".join(d.get("events") or [])
        if "route done (rc=0)" not in ev or " verdict " not in ev:
            return False
        # ROOT 2026-10-15 (peer review 11:00: 30 S81 fill routes CLOSED TT/FF/DRC 0, then collect crashed twice on a
        # child_lint bug; 17 run dirs were deleted before the lint was fixed): a CLOSED route verdict whose collect /
        # export crashed is evidence awaiting re-collection, kept until the job leaves NEEDS_HUMAN (retry --at collect)
        # or is cancelled -- no grace expiry.
        if d.get("stage_key") in ("collect", "export", "record") and "-> CLOSED" in ev:
            return True
        try:
            age = (dt.datetime.now().astimezone() - dt.datetime.fromisoformat(d.get("updated") or "")).total_seconds()
        except ValueError:
            return True
        return age < POSTROUTE_GRACE_H * 3600
    for name, ds in by.items():
        ok, keep, why = True, False, set()
        if any(postroute_hold(d) for d in ds): continue
        for d in ds:
            s = d.get("status") or ""; b = (d.get("spec") or {}).get("block") or d["name"]
            is_new = newest[b] is d
            if not (strippable_status(s) or (s in TERMINAL_OTHER and not is_new)): ok = False; break
            keep |= is_new; why.add(s if is_new else s + ",superseded")
        if not ok: continue
        if f"/{name}/" in live_txt or f"/{name}\"" in live_txt: continue     # a live job's record mentions this directory
        out[name] = dict(keep=keep, why="+".join(sorted(why)))
    import re
    for f in glob.glob(os.path.expanduser("~/OpenTallas/tools/closure_loop/jobs/*.json")) + [os.path.expanduser("~/OpenTallas/tools/closure_loop/hosts.json")]:
        try: live_txt += "\n" + open(f).read()                 # submitted / pending specs and external-job inventory
        except OSError: pass
    global REFS, MENTIONS
    MENTIONS = mentions()
    live_txt += "\n" + MENTIONS                                 # pending_results / recent HANDOFF + lanes: /srv paths too
    REFS = sorted({m for m in re.findall(r"/srv/[\w.+/-]+", live_txt)})
    # COORD 2026-11-01: counted routed DBs in coord lanes/PROTECTED-DBS.txt are never reaped (3 were lost 10-31);
    # ROOTSCR_1101: rows naming the epyc2 root-disk path count under its /srv/opentallas-scratch3 mount path
    try:
        _prot = [l.split("\t")[1].strip() for l in open(os.path.expanduser("~/coord/lanes/PROTECTED-DBS.txt"))
                 if not l.startswith("#") and l.count("\t") >= 1]
    except OSError:
        sys.exit("ot-reaper: PROTECTED-DBS.txt unreadable, refusing to run")
    _prot = [ROOTSCR_ALIAS[1] + x[len(ROOTSCR_ALIAS[0]):] if x.startswith(ROOTSCR_ALIAS[0]) else x for x in _prot]
    REFS = sorted(set(REFS) | {x for x in _prot if x.startswith("/srv/")})
    return out, sorted(r for r in roots if r.endswith("/closure-loop") and r.startswith("/srv/"))

def mentions():
    """text an agent will come back to: pending_results.txt, the last HANDOFF lines, lane files written in 24 h"""
    out = []
    for f in [os.path.join(TAKEOVER, "pending_results.txt")]:
        try: out.append(open(f, errors="replace").read())
        except OSError: pass
    try: out.append("".join(open(os.path.join(TAKEOVER, "HANDOFF.md"), errors="replace").readlines()[-MENTION_HANDOFF_LINES:]))
    except OSError: pass
    for f in glob.glob(os.path.join(TAKEOVER, "lanes", "*.md")):
        try:
            if dt.datetime.now().timestamp() - os.path.getmtime(f) < MENTION_LANE_H * 3600: out.append(open(f, errors="replace").read())
        except OSError: pass
    return "\n".join(out)

def fleet_hosts():
    """closure-loop hosts.json + ot-run HOSTS + STATIC_HOSTS (a new host is reaped without editing this file)"""
    import re
    hs = list(STATIC_HOSTS)
    for f in HOSTS_JSON:
        try: hs += [h["name"] for h in json.load(open(f))["hosts"] if h.get("name")]
        except (OSError, ValueError, KeyError, TypeError): pass
    try:
        m = re.search(r"^HOSTS = \[([^\]]*)\]", open(OT_RUN).read(), re.M)
        hs += re.findall(r"[\"']([\w.-]+)[\"']", m.group(1)) if m else []
    except OSError: pass
    return [h for h in dict.fromkeys(hs) if h not in RETIRED]

MENTIONS = ""

def main():
    if "--released-manifest" in sys.argv:
        return released_main()
    dry = "--dry" in sys.argv
    hosts = [sys.argv[i + 1] for i, a in enumerate(sys.argv) if a == "--host"] or fleet_hosts()
    lk = open("/tmp/ot-reaper.lock", "w")
    try: fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError: return
    jobs, roots = table()
    if jobs is None: log("SKIP: a job record was unreadable (mid-write)"); return
    def one(h):
        arg = dict(refs=REFS, dry=dry, quiet_min=20, jobs=jobs, roots=roots, hand_idle_h=HAND_IDLE_H,
                   hand=[] if "--no-hand" in sys.argv else [(r, HAND_NEVER) for r in HAND_ROOTS],
                   gate_roots=GATE_ROOTS, gate_idle_h=GATE_IDLE_H, mentions=MENTIONS,
                   umbrella_gb=0 if "--no-umbrella" in sys.argv else UMBRELLA_GB)
        try:
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", h, "cat > /tmp/ot-reaper-arg.json && python3 -c " +
                                "'import sys;exec(open(\"/tmp/ot-reaper-host.py\").read())' < /tmp/ot-reaper-arg.json"],
                               input=json.dumps(arg), capture_output=True, text=True, timeout=1500)
        except subprocess.TimeoutExpired: return h, 124, "", "timeout"
        return h, r.returncode, r.stdout, r.stderr
    import concurrent.futures as cf
    up = []
    for h in hosts:
        try:
            r = subprocess.run(["ssh", "-o", "ConnectTimeout=20", "-o", "BatchMode=yes", h, "cat > /tmp/ot-reaper-host.py"],
                               input=HOST_PY, text=True, timeout=120, capture_output=True)
        except subprocess.TimeoutExpired:
            r = None
        if r is None or r.returncode:
            log(f"{h} UNREACHABLE: {(r.stderr.strip()[-200:] if r else 'timeout')}")
        else:
            up.append(h)
    hosts = up
    if not hosts: return
    with cf.ThreadPoolExecutor(len(hosts)) as ex:
        for h, rc, out, err in ex.map(one, hosts):
            lines = out.splitlines(); tot = next((x.split()[1] for x in lines if x.startswith("TOTAL")), None)
            for x in lines:
                if not x.startswith("TOTAL") and (float(tot or 0) > 0 or not x.startswith("DF")): log(f"{'DRY ' if dry else ''}{h} {x}")
            if tot is None: log(f"{h} FAILED rc={rc} {err.strip()[-300:]}")
            elif float(tot) > 0 or dry: log(f"{'DRY ' if dry else ''}{h} deleted {tot} GB apparent (hardlinked source copies count once per link; see DF) ({len(jobs)} strippable job names fleet-wide)")
            print(h, rc, tot, err.strip()[-200:])

if __name__ == "__main__":
    main()
