#!/usr/bin/env python3
"""EPYC6-RETIRE watcher (OWNER 2026-10-19 21:35; drain from 10-21 08:12; OWNER 10-21 deadline 14:15 PT): drain and terminate ot-epyc6 (Cherry 1036642 'sacred-porpoise', EPYC 9554P,
Stockholm, 185.189.44.151, 2.68 EUR/h) once its running jobs finish and its results are archived on AGIdock.
Instance of lanes/epyc8-retire/epyc8_retire.py (proven 10-20). Additions for EPYC6:
  - 48 h rule: job items older than 48 h are killed by exact PID / container / ot-heavy unit (owner rule 10-09).
  - DEADLINE 2026-10-21 14:15 PT (owner 10-21): at/after it, a pass first copies partial results (C3 non-final copy),
    then kills every remaining job (daemon jobs via `closure_loop.py cancel`, then containers / ot-heavy units / PIDs
    exactly), notes each killed job in pending_results.txt "KILLED at epyc6 retire, relaunch elsewhere" with its owner
    lane, then re-runs the full pass (final copy + verify, closed check) and terminates.
  - retire also edits ~/.ssh/config (Host ot-epyc6 -> ot-epyc6-RETIRED), ~/bin/ssh-mux-heal, ~/bin/fleet-objtrim.

One pass (cron every 15 min, flock): evaluates every condition, does the (non-destructive) archive copies, and only
when ALL hold (and not --dry-run) terminates Cherry server 1036642 via the API, then retires ot-epyc6 from the live
configs, logs HANDOFF + lane file and removes its own cron line.

  C1 idle      no ot-heavy units / docker containers / job processes < 48 h old on ot-epyc6 (older = owner 48 h rule,
               ignored and listed), no local ot-run client attached to ot-epyc6, ot-run --status shows no run there,
               no non-terminal closure-daemon job with host ot-epyc6
  C2 closed    every CLOSED daemon job whose host is ot-epyc6 has a closed_archive manifest (archive.py run for the
               missing ones), its job dir is pushed to AGIdock (append-only, like backup_to_archive.sh) and every
               manifest file is on AGIdock (backup or frozen copy) with its size; final views sha256-matched
  C3 pending   every dir on ot-epyc6 that an open pending_results / RELEASE_TREE line names, plus every work dir a
               live job used while this watcher observed it, is copied to AGIdock /archive/epyc6-retire-1021/<path>
               (final copy made after C1 holds) and verified file-by-file (count + size); new paths noted in
               pending_results.txt
  C4 repo      branch claude/epyc6-retire-1021 (hosts.json / TOOL_REF_HOST / retired_hosts / fleet_viz) pushed
  C5 daemon    the live daemon no longer uses ot-epyc6 as TOOL_REF_HOST (restarted after the patch; the watcher
               restarts it itself once C1-C4 hold)
Usage: epyc6_retire.py [--dry-run] [--no-copy] [--no-hash] [--wait-lock]
"""
import argparse, concurrent.futures as cf, datetime as dt, fcntl, glob, hashlib, json, os, re, shlex, subprocess, sys, time

LANE = "/home/ubuntu/claude-takeover-20261007/lanes/epyc6-retire"
T = "/home/ubuntu/claude-takeover-20261007"
LOG = f"{LANE}/watch.log"
STATE = f"{LANE}/state"
HOST = "ot-epyc6"
IP = "185.189.44.151"
CHERRY_ID = 1036642
CHERRY_HOSTNAME = "sacred-porpoise"   # Cherry API hostname
SSH_HOSTNAME = "ot-epyc6"          # `hostname` on the box itself (differs from the Cherry name)
AGI = "ubuntu@155.103.253.53"
AGI_KEY = "/home/ubuntu/.ssh/agidock_ot"
DEST = "/archive/epyc6-retire-1021"
BACKUP = "/archive/opentallas-localhost-backup/home__ubuntu__closed_archive"
FROZEN = "/archive/opentallas-closed-archive-frozen"
CA = "/home/ubuntu/closed_archive"
JOBS = "/home/ubuntu/.local/state/closure_loop/jobs"
DAEMON_WT = "/home/ubuntu/wt-claude-closure-daemon-1010"
BRANCH = "claude/epyc6-retire-1021"
SSH_H = ["ssh", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=30"]
SSH_A = ["ssh", "-i", AGI_KEY, "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=30"]
TERMINAL = re.compile(r"^(CLOSED|CANCELLED|REFUSED|INVALID|SMOKE_OK|FAILED|SUPERSEDED|ABANDONED|NEEDS_.*|EARLY_FAIL.*|.*_MARGIN)$")
FINAL_ROLE = re.compile(r"^(final_.*|abstract_lef|lib_tt|lib_ff|lib_ss)$")
DEADLINE = dt.datetime(2026, 10, 21, 14, 15).astimezone()   # local tz of this host = PT
KILL_TAG = "KILLED at epyc6 retire, relaunch elsewhere"
TOP_CAP_BYTES = 50 << 30
AGI_FLOOR = 300 << 30     # keep >= 300 GB free on AGIdock /archive (1.1 TB free at 10-21 08:30)       # a depth-4 umbrella dir (/srv/<root>/<user>/<proj>) bigger than this is not auto-copied


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def log(msg):
    line = f"{now()} {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def jload(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def jsave(p, obj):
    with open(p + ".tmp", "w") as f:
        json.dump(obj, f, indent=1)
    os.replace(p + ".tmp", p)


def run(cmd, inp=None, timeout=600, **kw):
    return subprocess.run(cmd, input=inp, capture_output=True, text=True, timeout=timeout, **kw)


def host_py(script, inp="", timeout=1800):
    """run a local helper script ON ot-epyc6 (script via scp-free heredoc: stdin = script, args via env)"""
    code = open(f"{LANE}/{script}").read()
    # script source goes in a file on the host so the payload can use stdin
    r = run(SSH_H + [HOST, "mkdir -p /tmp/e6r && cat > /tmp/e6r/" + script], inp=code, timeout=120)
    if r.returncode:
        raise RuntimeError(f"upload {script}: {r.stderr[-300:]}")
    r = run(SSH_H + [HOST, f"nice -n 10 ionice -c3 python3 /tmp/e6r/{script}"], inp=inp, timeout=timeout)
    if r.returncode:
        raise RuntimeError(f"{script} on {HOST}: rc {r.returncode} {r.stderr[-300:]}")
    return json.loads(r.stdout)


def agi_py(mode, payload, timeout=7200):
    code = open(f"{LANE}/remote_verify.py").read()
    r = run(SSH_A + [AGI, "mkdir -p /tmp/e6r && cat > /tmp/e6r/remote_verify.py"], inp=code, timeout=120)
    if r.returncode:
        raise RuntimeError(f"upload verify: {r.stderr[-300:]}")
    r = run(SSH_A + [AGI, f"nice -n 10 python3 /tmp/e6r/remote_verify.py {mode}"], inp=json.dumps(payload), timeout=timeout)
    if r.returncode:
        raise RuntimeError(f"verify {mode}: rc {r.returncode} {r.stderr[-300:]}")
    return json.loads(r.stdout)


# ---------------------------------------------------------------- C1
def daemon_jobs():
    out = {}
    for f in glob.glob(JOBS + "/*.json"):
        d = jload(f, None)
        if isinstance(d, dict) and d.get("host") == HOST:
            out[d.get("name")] = d
    return out


def check_idle(jobs):
    why = []
    st = host_py("remote_host_state.py", timeout=300)
    if st.get("hostname") != SSH_HOSTNAME:
        why.append(f"ssh hostname {st.get('hostname')!r} != {SSH_HOSTNAME}")
    if st.get("docker_error"):
        why.append("docker state unknown: " + st["docker_error"])
    for u in st["units"]:
        why.append(f"unit {u['unit']} age {u['age'] // 60} min cwd {u['cwd']}")
    for c in st["docker"]:
        why.append(f"container {c['name']} age {c['age'] // 60} min")
    for p in st["procs"]:
        why.append(f"proc {p['pid']} {p['comm']} age {p['age'] // 60} min: {p['args'][:120]}")
    act = [(n, d.get("status")) for n, d in jobs.items() if not TERMINAL.match(str(d.get("status")))]
    for n, s in act:
        why.append(f"daemon job {n} {s}")
    # local ot-run clients holding an ssh session to ot-epyc6 (ot-heavy launch)
    r = run(["ps", "-eo", "pid,args"], timeout=60)
    for l in r.stdout.splitlines():
        if re.search(r"\bssh\b.*\b(ot-epyc6|185\.189\.44\.151)\b.*ot-heavy", l) and "epyc6_retire" not in l:
            why.append("local ot-run client: " + l.strip()[:160])
    r = run(["/home/ubuntu/bin/ot-run", "--status"], timeout=120)
    m = re.search(r"ot-epyc6 [^|]*?\brun (\d+)", r.stdout)
    if m and int(m.group(1)) > 0:
        why.append(f"ot-run --status: ot-epyc6 run {m.group(1)}")
    if st["stale"] and not getattr(check_idle, "dry", False):
        log(f"C1: {len(st['stale'])} item(s) older than 48 h -> killed by exact id (owner 48 h rule): "
            + "; ".join((x.get('unit') or x.get('name') or str(x.get('pid'))) for x in st['stale'])[:400])
        kill_items(st["stale"], "older than 48 h (owner rule)")
    return not why, why, st


def work_dirs(st):
    """work dirs live jobs use: unit cwd, container bind mounts, scratch paths in job argv -> normalised roots"""
    cands = set()
    for u in st["units"]:
        cands.add(u["cwd"])
        cands.update(re.findall(r"/srv/opentallas-scratch2?/[^\s'\";|]+", u["argv"]))
    for c in st["docker"]:
        cands.update(c["mounts"])
    for p in st["procs"]:
        cands.add(p["cwd"])
    out = set()
    for c in cands:
        m = re.match(r"^(/srv/opentallas-scratch2?/(?:claude|codex)/.+)$", c or "")
        if not m or "/closure-loop/" in c:
            continue
        p = m.group(1).rstrip("/")
        mm = re.match(r"^(/srv/opentallas-scratch2?/(?:claude|codex)/ref_gate/[^/]+)", p)
        if mm:
            out.add(mm.group(1))
            continue
        parts = p.split("/")
        for i, comp in enumerate(parts):
            if i >= 5 and re.match(r"^(src[0-9a-z_-]*|bench_src.*|bsrc_.*)$", comp):
                p = "/".join(parts[:i])
                break
        out.add(p)
    return out


# ---------------------------------------------------------------- kills (48 h rule / deadline)
def kill_items(items, why):
    """kill exact items reported by remote_host_state.py: ot-heavy unit (systemctl stop of that scope), container (docker
    kill by full name), process (kill exact PID, TERM then KILL). Returns the list of descriptions killed."""
    cmds, desc = [], []
    for x in items:
        if x.get("unit"):
            u = shlex.quote(x["unit"] + ".scope")
            cmds.append(f"systemctl --user stop {u} || systemctl --user kill -s KILL {u}")
            desc.append(f"unit {x['unit']} cwd {x.get('cwd')}")
        elif x.get("name"):
            cmds.append(f"docker kill {shlex.quote(x['name'])}")
            desc.append(f"container {x['name']}")
        elif x.get("pid"):
            pid = int(x["pid"])
            cmds.append(f"kill -TERM {pid}; sleep 5; kill -KILL {pid} 2>/dev/null")
            desc.append(f"pid {pid} {x.get('comm')} cwd {x.get('cwd')}")
    if not cmds:
        return []
    script = "\n".join(c + " >/dev/null 2>&1; true" for c in cmds) + "\n"
    r = run(SSH_H + [HOST, "bash -s"], inp=script, timeout=1800)
    log(f"KILL ({why}): {len(cmds)} item(s), rc {r.returncode}: " + "; ".join(desc)[:900])
    return desc


def _expand_braces(s):
    while True:
        mb = re.search(r"\{([^{}]*,[^{}]*)\}", s)
        if not mb:
            return s
        pre, post = s[:mb.start()], s[mb.end():]
        tok0 = re.search(r"\S*$", pre).group(0)
        tok1 = re.match(r"\S*", post).group(0)
        s = pre[:len(pre) - len(tok0)] + " ".join(tok0 + a + tok1 for a in mb.group(1).split(",")) + post[len(tok1):]


def _lane_of(line, default):
    if "|" in line:
        f = line.rsplit("|", 1)[-1].strip()
        if f and len(f) <= 40:
            return f
    m = re.match(r"^\[?([A-Z][A-Z0-9_/-]{2,30})[ \]:]", line.strip())
    return m.group(1) if m else default


def owner_lane(text):
    """owner lane of a killed item: newest pending_results line (else lane file) naming its dir, unit or run name"""
    srcs = [("", [_expand_braces(l) for l in open(f"{T}/pending_results.txt", errors="replace").read().splitlines()
                  if "EPYC6-RETIRE" not in l])]
    for lf in sorted(glob.glob(f"{T}/lanes/*.md")):
        if "RETIRE" not in lf:
            srcs.append((os.path.basename(lf)[:-3], open(lf, errors="replace").read().splitlines()))
    keys = []
    for k in re.findall(r"(oth-ubuntu-\d+|/srv/opentallas-scratch2?/[^\s'\";|]+)", text or ""):
        if k.startswith("oth-"):
            keys.append(k)
            continue
        k = k.rstrip("/")
        while k.count("/") >= 5:
            keys.append(k)
            k = k.rsplit("/", 1)[0]
    for k in re.findall(r"/srv/opentallas-scratch2?/(?:claude|codex)/[^/\s]+/([^/\s'\";|]{10,})", text or ""):
        keys.append(re.sub(r"^wt-", "", k))
    keys += re.findall(r"ref_gate/([\w.]+?)-\d{8}-\d{6}", text or "") + re.findall(r"ref_gate_([\w.]+?)_\d{8}-\d{6}", text or "")
    keys += re.findall(r"gate_\w+?_([\w.]+?)-\d{8}-\d{6}", text or "")
    for k in keys:
        for lane, lines in srcs:
            for l in reversed(lines):
                if k in l:
                    return _lane_of(l, lane or "?")
    return "?"


def deadline_kill(jobs):
    """OWNER 10-21: at the 14:15 PT deadline kill everything still running on ot-epyc6 and note it for relaunch"""
    notes = []
    for n, d in sorted(jobs.items()):
        if TERMINAL.match(str(d.get("status"))):
            continue
        r = run(["python3", f"{DAEMON_WT}/tools/closure_loop/closure_loop.py", "cancel", n, "--why",
                 "EPYC6-RETIRE deadline 14:15 (owner 10-21): " + KILL_TAG], timeout=600, cwd=DAEMON_WT)
        log(f"DEADLINE: cancel daemon job {n} ({d.get('status')}) rc {r.returncode} {(r.stdout + r.stderr)[-200:]!r}")
        lane = (d.get("spec") or {}).get("owner") or "?"
        notes.append(f"ot-epyc6 closure-loop job {n} (was {d.get('status')}, run {d.get('run')}) | {KILL_TAG} "
                     f"(EPYC6-RETIRE deadline 14:15, owner 10-21; daemon status CANCELLED; resubmit/retry on the fleet) | {lane}\n")
    time.sleep(30)
    st = host_py("remote_host_state.py", timeout=300)
    items = st["units"] + st["docker"] + st["procs"] + st["stale"]
    killed = kill_items(items, "deadline 14:15")
    for x in st["units"] + st["docker"]:       # one pending line per job-level item (units/containers); plain procs belong to them
        what = f"ot-run unit {x['unit']} cwd {x.get('cwd')} argv {x.get('argv', '')[:160]}" if x.get("unit") else \
            f"docker container {x['name']} mounts {' '.join(x.get('mounts', [])[:3])}"
        lane = owner_lane(" ".join([x.get("cwd") or "", x.get("unit") or "", x.get("name") or "", x.get("argv") or ""] + x.get("mounts", [])))
        notes.append(f"ot-epyc6:{what} | {KILL_TAG} (EPYC6-RETIRE deadline 14:15, owner 10-21; partial dir copied to "
                     f"agidock:{DEST}<path> when named) | {lane}\n")
    if notes:
        with open(f"{T}/pending_results.txt", "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.writelines(notes)
    open(f"{STATE}/DEADLINE_KILLED", "a").write(f"{now()} {len(notes)} notes, {len(killed)} kills\n")
    log(f"DEADLINE: {len(notes)} pending_results lines ({KILL_TAG}), {len(killed)} host items killed")
    return st


# ---------------------------------------------------------------- C2
def manifests():
    out = {}
    for mp in glob.glob(f"{CA}/*/*/manifest.json"):
        d = jload(mp, None)
        if isinstance(d, dict) and d.get("schema") == "closed-archive/1" and d.get("host") == HOST:
            out[d["job"]] = (os.path.relpath(os.path.dirname(mp), CA), d)
    return out


def check_closed(jobs, args):
    why = []
    closed = sorted(n for n, d in jobs.items() if d.get("status") == "CLOSED")
    man = manifests()
    todo = [n for n in closed if n not in man]
    if todo and not args.no_copy:
        log(f"C2: archiving {len(todo)} CLOSED job(s) without a manifest: {' '.join(todo)[:600]}")
        r = run(["python3", "-I", f"{CA}/_tools/archive.py", "jobs"] + todo, timeout=6 * 3600, cwd="/")
        log(f"C2: archive.py rc {r.returncode} {(r.stdout + r.stderr)[-400:]!r}")
        man = manifests()
    for n in closed:
        if n not in man:
            why.append(f"no closed_archive manifest for {n}")
        elif man[n][1].get("status") not in ("archived",):
            mstat = man[n][1].get("status")
            if mstat == "missing":   # run dir / odb gone on the host at archive time: nothing left there to save
                log(f"C2 note: {n} manifest status missing ({man[n][1].get('missing_reason')})")
            else:
                why.append(f"{n} manifest status {mstat}")
    rels = sorted({man[n][0] for n in closed if n in man})
    if not rels:
        return not why, why
    # push (append-only, like backup_to_archive.sh for closed_archive)
    if not args.no_copy:
        lst = f"{STATE}/closed_dirs.lst"
        open(lst, "w").write("".join(r + "/\n" for r in rels))
        cmd = ["nice", "-n", "15", "ionice", "-c3", "rsync", "-aH", "-r", "--partial", "--files-from=" + lst,
               "--exclude", "*.lock", "-e", " ".join(SSH_A), CA + "/", f"{AGI}:{BACKUP}/"]
        r = run(cmd, timeout=12 * 3600)
        if r.returncode not in (0, 24):
            why.append(f"rsync closed dirs rc {r.returncode}: {r.stderr[-300:]}")
            return False, why
    # count + size
    items = []
    for n in closed:
        if n not in man or man[n][1].get("status") != "archived":
            continue
        rel, d = man[n]
        for nm in ("manifest.json", "job.json", "spec.json"):
            p = f"{CA}/{rel}/{nm}"
            if os.path.exists(p):
                items.append([BACKUP, FROZEN, f"{rel}/{nm}", os.path.getsize(p)])
        for e in d.get("files", []):
            if e.get("missing"):
                continue
            items.append([BACKUP, FROZEN, f"{rel}/{jrel(e)}", e["stored_size"]])
    res = {}
    for i in range(0, len(items), 20000):
        res.update(agi_py("closed", items[i:i + 20000], timeout=3600))
    bad = {k: v for k, v in res.items() if v != "ok"}
    for k, v in list(bad.items())[:20]:
        why.append(f"AGIdock closed copy {k}: {v}")
    if len(bad) > 20:
        why.append(f"... {len(bad)} closed-archive files not on AGIdock")
    log(f"C2: {len(closed)} CLOSED jobs, {len(rels)} archive dirs, {len(items)} files checked on AGIdock, {len(bad)} bad")
    if bad or args.no_hash:
        if args.no_hash:
            why.append("final-view sha256 not checked (--no-hash)")
        return not why, why
    # sha256 of final views: AGIdock copy vs local copy (or vs REMOTE_ONLY.json for offloaded jobs); cached
    cache_p = f"{STATE}/closed_sha_ok.json"
    cache = jload(cache_p, {})
    want = {}          # remote path -> expected sha
    for n in closed:
        if n not in man or man[n][1].get("status") != "archived":
            continue
        rel, d = man[n]
        ro = {e["path"]: e["sha256"] for e in jload(f"{CA}/{rel}/REMOTE_ONLY.json", {}).get("files", [])}
        for e in d.get("files", []):
            if e.get("missing") or not FINAL_ROLE.match(str(e.get("role") or "")):
                continue
            key = f"{rel}/{jrel(e)}"
            if cache.get(key) == e["stored_size"]:
                continue
            loc = f"{CA}/{key}"
            if os.path.isfile(loc) and not os.path.islink(loc):
                exp = sha256(loc)
            elif jrel(e) in ro:
                exp = ro[jrel(e)]
            else:
                why.append(f"no reference sha for {key}")
                continue
            remote = f"{FROZEN}/{key}" if jrel(e) in ro else f"{BACKUP}/{key}"
            want[remote] = (exp, key, e["stored_size"])
    paths = sorted(want)
    for i in range(0, len(paths), 2000):
        got = agi_py("sha", paths[i:i + 2000], timeout=6 * 3600)
        for p in paths[i:i + 2000]:
            exp, key, size = want[p]
            alt = p.replace(FROZEN, BACKUP, 1) if p.startswith(FROZEN) else p.replace(BACKUP, FROZEN, 1)
            if got.get(p) != exp:
                g2 = agi_py("sha", [alt], timeout=3600).get(alt)
                if g2 != exp:
                    why.append(f"sha mismatch {key}")
                    continue
            cache[key] = size
        jsave(cache_p, cache)
    log(f"C2: final-view sha256 checked {len(paths)} new, {len(cache)} verified total")
    return not why, why


def jrel(e):
    """a manifest file's path relative to the job dir: gen_gds output lives in <job>/generated/, the rest in <job>/run/"""
    return e["stored"] if e.get("generated") else "run/" + e["stored"]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


# ---------------------------------------------------------------- deadline (independent of the long archive-pass lock)
DEADLINE_CHECKS = False


def deadline_due():
    return dt.datetime.now().astimezone() >= DEADLINE


def enforce_deadline(*, dry_run=False):
    """Record the current partial archive/inventory and stop exact jobs after the owner deadline.

    This deliberately never acquires watch.lock, copies bulk data, or calls DELETE.
    Source directories remain intact for the independent C2/C3 final copy and verification.
    """
    if not deadline_due() or dry_run:
        return False
    os.makedirs(STATE, exist_ok=True)
    with open(f"{STATE}/deadline.lock", "a") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        done = f"{STATE}/deadline_complete.json"
        if os.path.exists(done):
            return True
        # Do not stop anything unless both SSH and provider identify the intended machine.
        identity_ok, identity = verify_identity()
        if not identity_ok:
            log(f"DEADLINE identity refused: {identity}")
            return False
        st = host_py("remote_host_state.py", timeout=300)
        if st.get("hostname") != SSH_HOSTNAME or st.get("docker_error"):
            log("DEADLINE inventory refused: wrong hostname or unknown Docker state")
            return False
        jobs = daemon_jobs()
        prior = jload(f"{STATE}/deadline_partial_snapshot.json", {})
        dirs = sorted(work_dirs(st) | set(prior.get("observed_dirs", [])))
        # A separate receipt avoids racing the archive pass's observed_dirs.json writer.
        # Every later C3 pass merges these live job roots before it may approve DELETE.
        receipt = dict(at=now(), deadline=DEADLINE.isoformat(), identity=identity,
                       observed_dirs=dirs, inventory=st, jobs=jobs,
                       partial_archive_roots=jload(f"{STATE}/roots.json", {}),
                       archive_destination=f"{AGI}:{DEST}",
                       action="exact cancel only; source retained for final copy/hash verification")
        jsave(f"{STATE}/deadline_partial_snapshot.json", receipt)
        log(f"DEADLINE recorded partial archive + {len(dirs)} live directories; cancelling exact jobs")
        deadline_kill(jobs)
        after = host_py("remote_host_state.py", timeout=300)
        active = [x for k in ("units", "docker", "procs", "stale") for x in after.get(k, [])]
        pending = [n for n, d in daemon_jobs().items() if not TERMINAL.match(str(d.get("status")))]
        if after.get("hostname") != SSH_HOSTNAME or after.get("docker_error") or active or pending:
            log(f"DEADLINE cancellation incomplete: {len(active)} host items / {len(pending)} daemon jobs; retry next tick")
            return False
        jsave(done, dict(at=now(), deadline=DEADLINE.isoformat(), identity=identity,
                         partial_snapshot=f"{STATE}/deadline_partial_snapshot.json",
                         delete_attempted=False))
        return True


def deadline_checkpoint():
    if DEADLINE_CHECKS and deadline_due():
        try:
            enforce_deadline()
        except Exception as e:
            # A temporary control-plane error must not interrupt preservation copies.
            log(f"DEADLINE checkpoint retry needed: {e}")


def run_copy_poll(command, *, env, timeout):
    """Keep an archive copy running while checking the deadline at most every 15 s."""
    started = time.monotonic()
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, env=env)
    try:
        while True:
            deadline_checkpoint()
            remaining = timeout - (time.monotonic() - started)
            if remaining <= 0:
                raise subprocess.TimeoutExpired(command, timeout)
            try:
                out, err = proc.communicate(timeout=min(15, remaining))
                return subprocess.CompletedProcess(command, proc.returncode, out, err)
            except subprocess.TimeoutExpired:
                continue
    except BaseException:
        # This is only the exact ssh client started above, never another job/client.
        proc.kill()
        proc.communicate()
        raise


# ---------------------------------------------------------------- C3
def pending_roots():
    r = run(["python3", "-I", f"{LANE}/extract_pending.py"], timeout=120, cwd="/tmp")
    cand = json.loads(r.stdout)
    return cand


def resolve(paths):
    return host_py("resolve_remote.py", json.dumps(sorted(paths)), timeout=3600)


def copy_roots(roots, final):
    """rsync each root's walk list ot-epyc6 -> AGIdock (agent-forwarded key, never stored on the host); verify"""
    summ = host_py("remote_walk.py", json.dumps(dict(roots=sorted(roots), hash=final)), timeout=3 * 3600)
    agent = run(["ssh-agent", "-s"], timeout=30).stdout
    env = dict(os.environ)
    for k, v in re.findall(r"(SSH_AUTH_SOCK|SSH_AGENT_PID)=([^;]+);", agent):
        env[k] = v
    run(["ssh-add", "-q", AGI_KEY], timeout=30, env=env)
    errs = {}

    def one(root):
        deadline_checkpoint()
        s = summ[root]
        if not s["exists"]:
            return root, "gone"
        dst = DEST + root
        fr = run(SSH_A + [AGI, "df -B1 --output=avail /archive | tail -1"], timeout=60).stdout.strip()
        if not fr.isdigit() or int(fr) - s["bytes"] < AGI_FLOOR:
            return root, f"AGIdock /archive free {int(fr) / 1e9 if fr.isdigit() else -1:.0f} GB < floor + {s['bytes'] / 1e9:.0f} GB (copy held)"
        cmd = (f"cut -f1 /tmp/e6r/lists/{s['id']}.lst | nice -n 10 ionice -c3 rsync -a --partial --mkpath --files-from=- "
               f"-e 'ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30' "
               f"{shlex.quote(root)}/ {AGI}:{shlex.quote(dst)}/")
        for attempt in range(3):
            r = run_copy_poll(["ssh", "-A", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=30",
                               HOST, cmd], env=env, timeout=12 * 3600)
            if r.returncode in (0, 24):     # 24 = files vanished during transfer (live job): next pass recopies
                return root, None
            time.sleep(20)
        return root, f"rsync rc {r.returncode}: {r.stderr[-200:]}"
    try:
        with cf.ThreadPoolExecutor(6) as ex:
            for root, e in ex.map(one, sorted(roots)):
                if e and e != "gone":
                    errs[root] = e
    finally:
        run(["ssh-agent", "-k"], timeout=30, env=env)
    ver = {}
    if final:
        payload = {}
        for root in roots:
            s = summ[root]
            if not s["exists"]:
                continue
            r = run(SSH_H + [HOST, f"cat /tmp/e6r/lists/{s['id']}.lst"], timeout=600)
            items = [l.split("\t") for l in r.stdout.splitlines() if "\t" in l]
            if any(len(x) != 3 or not x[2] for x in items):
                raise RuntimeError(f"final C3 source hash manifest missing for {root}")
            payload[DEST + root] = [[a, b if b == "L" else int(b), h] for a, b, h in items]
        if payload:
            ver = agi_py("list", payload, timeout=3 * 3600)
    return summ, errs, ver


def note_pending(roots_map, summ):
    """append one pending_results line per archived root (once), pointing the owning lane at the AGIdock copy"""
    done_p = f"{STATE}/noted.json"
    done = jload(done_p, {})
    lines = []
    tsv = open(f"{LANE}/archived_paths.tsv", "a")
    for root, refs in sorted(roots_map.items()):
        if root in done or not summ.get(root, {}).get("exists"):
            continue
        lanes = sorted({r.get("lane") or "?" for r in refs})
        src = "; ".join(f"{r['src']}:{r['line_no']}" for r in refs[:4]) if refs and "src" in refs[0] else "live job work dir"
        s = summ[root]
        lines.append(f"agidock:{DEST}{root} | EPYC6-RETIRE copy of ot-epyc6:{root} ({s['files']} files, "
                     f"{s['bytes'] / 1e9:.2f} GB; regenerable src/obj bulk skipped; host terminated) for {src} | "
                     f"{', '.join(lanes)[:60]}\n")
        tsv.write(f"{now()}\tot-epyc6:{root}\tagidock:{DEST}{root}\t{s['files']}\t{s['bytes']}\t{src}\n")
        done[root] = now()
    tsv.close()
    if lines:
        with open(f"{T}/pending_results.txt", "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.writelines(lines)
        jsave(done_p, done)
        log(f"C3: noted {len(lines)} archived path(s) in pending_results.txt")


def check_pending(idle, st, args):
    why = []
    obs_p = f"{STATE}/observed_dirs.json"
    obs = jload(obs_p, {})
    for d in jload(f"{STATE}/deadline_partial_snapshot.json", {}).get("observed_dirs", []):
        obs.setdefault(d, now())
    for d in work_dirs(st):
        obs.setdefault(d, now())
    jsave(obs_p, obs)
    cand = pending_roots()
    res = resolve({c["path"] for c in cand} | set(obs))
    roots_map = {}
    skipped = []
    for c in cand + [dict(path=d) for d in obs]:
        v = res.get(c["path"]) or {}
        d = v.get("dir")
        if not d:
            continue                           # not on ot-epyc6 (another host's path)
        if v.get("depth", 0) < 5:              # resolved to an umbrella dir /srv/<root>/<user>/<proj>
            if d.rstrip("/") != c["path"].rstrip("/"):
                continue                       # walked up: the named path is on another host
            if v.get("kb", 0) * 1024 > TOP_CAP_BYTES:
                skipped.append(f"{d} ({v.get('kb', 0) / 1e6:.0f} GB umbrella dir)")
                continue
        roots_map.setdefault(d, [])
        if "src" in c:
            roots_map[d].append(c)
    roots = sorted(roots_map)
    roots = [r for r in roots if not any(r != a and r.startswith(a + "/") for a in roots)]
    for r in list(roots_map):
        if r not in roots:
            a = next(a for a in roots if r.startswith(a + "/"))
            roots_map[a].extend(roots_map.pop(r))
    if skipped:   # non-blocking: a pending line that names a whole >50 GB project dir is reported for a lane decision
        log("C3 note: not auto-copied (umbrella dir > 50 GB named by a pending line): " + "; ".join(sorted(set(skipped)))[:600])
    log(f"C3: {len(cand)} pending refs + {len(obs)} observed work dirs -> {len(roots)} roots on ot-epyc6")
    jsave(f"{STATE}/roots.json", {r: [dict(src=c.get('src'), line_no=c.get('line_no'), lane=c.get('lane')) for c in roots_map[r]] for r in roots})
    if args.no_copy:
        why.append("copy skipped (--no-copy)")
        return False, why
    summ, errs, ver = copy_roots(roots, final=idle)
    tot = sum(s["bytes"] for s in summ.values())
    log(f"C3: copied {len(roots)} roots, {tot / 1e9:.1f} GB listed, {len(errs)} rsync errors; final={idle}")
    for r, e in errs.items():
        why.append(f"copy {r}: {e}")
    if not idle:
        why.append("final copy waits for C1 (jobs still running)")
        return False, why
    for dst, v in ver.items():
        if not v["ok"]:
            why.append(f"AGIdock copy {dst}: {v['missing']} missing / {v['size_mismatch']} size / {v.get('hash_mismatch', 0)} hash mismatch of {v['n']} e.g. {v['examples'][:2]}")
    if not why:
        note_pending(roots_map, summ)
    return not why, why


# ---------------------------------------------------------------- C4 / C5
def check_repo():
    r = run(["git", "-C", "/home/ubuntu/OpenTallas", "ls-remote", "origin", f"refs/heads/{BRANCH}"], timeout=120)
    ok = bool(r.stdout.strip())
    return ok, ([] if ok else [f"branch {BRANCH} not on origin"])


def daemon_state():
    src = open(f"{DAEMON_WT}/tools/closure_loop/closure_loop.py").read()
    m = re.search(r'^TOOL_REF_HOST = "([^"]+)"', src, re.M)
    mt = os.path.getmtime(f"{DAEMON_WT}/tools/closure_loop/closure_loop.py")
    r = run(["systemctl", "--user", "show", "closure-loop", "-p", "ExecMainStartTimestampMonotonic", "-p", "ActiveState",
             "-p", "MainPID"], timeout=60)
    kv = dict(l.split("=", 1) for l in r.stdout.splitlines() if "=" in l)
    pid = kv.get("MainPID", "0")
    started = None
    if pid != "0":
        try:
            ticks = int(open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[19])
            boot = time.time() - float(open("/proc/uptime").read().split()[0])
            started = boot + ticks / os.sysconf("SC_CLK_TCK")
        except (OSError, IndexError, ValueError):
            pass
    return m and m.group(1), mt, started, kv.get("ActiveState")


def check_daemon():
    """EPYC6: TOOL_REF_HOST is ot-epyc5 since EPYC4-RETIRE (never ot-epyc6), so no daemon restart is needed; check that the
    live daemon file does not name ot-epyc6 as reference and that hosts.json keeps ot-epyc6 smoke_only (read per pass)."""
    ref, mt, started, active = daemon_state()
    why = []
    if ref == HOST:
        why.append(f"live daemon file has TOOL_REF_HOST {HOST}")
    src = open(f"{DAEMON_WT}/tools/closure_loop/closure_loop.py").read()
    for m in re.finditer(r'^([A-Z_]*REF[A-Z_]*)\s*=\s*"([^"]+)"', src, re.M):
        if m.group(2) == HOST:
            why.append(f"live daemon {m.group(1)} = {HOST}")
    hj = jload(f"{DAEMON_WT}/tools/closure_loop/hosts.json", {})
    cfg = next((h for h in hj.get("hosts", []) if h["name"] == HOST), None)
    if cfg is not None and not cfg.get("smoke_only"):
        why.append("live hosts.json: ot-epyc6 is not smoke_only (daemon may place new jobs there)")
    held = open("/home/ubuntu/.config/ot-run/held_hosts").read() if os.path.exists("/home/ubuntu/.config/ot-run/held_hosts") else ""
    if not re.search(r"^ot-epyc6\b", held, re.M):
        why.append("ot-run held_hosts no longer lists ot-epyc6 (ot-run may place new jobs there)")
    return not why, why


# ---------------------------------------------------------------- termination
def cherry(method, path=""):
    key = os.environ.get("CHERRY_SERVERS_API_KEY")
    if not key:
        for f in ("/home/ubuntu/.bashrc", "/home/ubuntu/.profile", "/home/ubuntu/.config/cherry.env"):
            try:
                m = re.search(r"CHERRY_SERVERS_API_KEY=['\"]?([^'\"\s]+)", open(f).read())
            except OSError:
                m = None
            if m:
                key = m.group(1)
                break
    if not key:
        raise RuntimeError("CHERRY_SERVERS_API_KEY not available")
    cfg = f'header = "Authorization: Bearer {key}"\n'       # passed on stdin: never on argv / in logs
    r = subprocess.run(["curl", "-s", "-m", "60", "-K", "-", "-X", method, "-w", "\n%{http_code}",
                        f"https://api.cherryservers.com/v1/servers/{CHERRY_ID}{path}"],
                       input=cfg, capture_output=True, text=True, timeout=90)
    body, _, code = r.stdout.rpartition("\n")
    return int(code or 0), body


def verify_identity():
    code, body = cherry("GET")
    if code != 200:
        return False, f"Cherry GET {code}"
    d = json.loads(body)
    ips = [i.get("address") for i in d.get("ip_addresses", [])]
    sshcfg = run(["ssh", "-G", HOST], timeout=30).stdout
    hn = re.search(r"^hostname (\S+)", sshcfg, re.M)
    ok = (d.get("id") == CHERRY_ID and d.get("hostname") == CHERRY_HOSTNAME and IP in ips and hn and hn.group(1) == IP)
    return ok, f"id {d.get('id')} hostname {d.get('hostname')} ips {ips} region {(d.get('region') or {}).get('name')} ssh {hn and hn.group(1)}"


def edit_file(path, fn, tag="bak-epyc6retire-1021"):
    if not os.path.exists(path):
        return False
    src = open(path).read()
    new = fn(src)
    if new == src:
        return False
    bak = f"{path}.{tag}"
    if not os.path.exists(bak):
        open(bak, "w").write(src)
        os.chmod(bak, os.stat(path).st_mode & 0o777)
    mode = os.stat(path).st_mode & 0o777
    open(path + ".tmp-e6r", "w").write(new)
    os.chmod(path + ".tmp-e6r", mode)
    os.replace(path + ".tmp-e6r", path)
    return True


def _drop_name(s, var):
    """remove "ot-epyc6", from the one-line `VAR = [...]` list (whatever else it holds)"""
    return re.sub(r'^(%s = \[[^\]\n]*?)"ot-epyc6",\s*' % var, r"\1", s, count=1, flags=re.M)


def retire_configs():
    done = []
    def hosts_json(src):
        d = json.loads(src)
        d["hosts"] = [h for h in d["hosts"] if h["name"] != HOST]
        rh = d.get("retired_hosts") or []
        if HOST not in rh:
            rh.append(HOST)
        d["retired_hosts"] = rh
        return json.dumps(d, indent=1) + "\n"
    if edit_file(f"{DAEMON_WT}/tools/closure_loop/hosts.json", hosts_json):
        done.append("daemon hosts.json")
    if edit_file("/home/ubuntu/bin/ot-run", lambda s: _drop_name(s, "HOSTS")):
        done.append("ot-run HOSTS")
    if edit_file("/home/ubuntu/bin/ot-sizes-sync", lambda s: _drop_name(s, "HOSTS")):
        done.append("ot-sizes-sync HOSTS")
    if edit_file("/home/ubuntu/.config/ot-run/held_hosts", lambda s: "".join(l for l in s.splitlines(True) if not l.startswith("ot-epyc6"))):
        done.append("held_hosts")
    def reaper(s):
        s = _drop_name(s, "STATIC_HOSTS")
        return re.sub(r'^(RETIRED = \{[^}\n]*?)"localhost"\}', r'\1"ot-epyc6", "localhost"}', s, count=1, flags=re.M) \
            if '"ot-epyc6"' not in (re.search(r"^RETIRED = \{[^}\n]*\}", s, re.M) or [""])[0] else s
    if edit_file("/home/ubuntu/bin/ot-reaper.py", reaper):
        done.append("ot-reaper STATIC_HOSTS/RETIRED")
    def fv(src):
        d = json.loads(src)
        d["hosts"] = [h for h in d["hosts"] if h.get("id") != HOST]
        return json.dumps(d, indent=1) + "\n"
    if edit_file("/home/ubuntu/.local/share/fleet-viz/fleet_hosts.json", fv):
        done.append("fleet-viz fleet_hosts.json")
    def sshcfg(s):
        s = re.sub(r"^(Host [^\n]*?) ot-epyc6(?= |$)", r"\1", s, flags=re.M)          # ControlMaster group line
        s = re.sub(r"^Host ot-epyc6$", "Host ot-epyc6-RETIRED", s, flags=re.M)           # the host entry
        return s
    if edit_file("/home/ubuntu/.ssh/config", sshcfg):
        done.append("ssh config (Host ot-epyc6-RETIRED)")
    for f in ("/home/ubuntu/bin/ssh-mux-heal", "/home/ubuntu/bin/fleet-objtrim"):
        if edit_file(f, lambda s: re.sub(r"^(for h in [^;\n]*?) ot-epyc6(?= )", r"\1", s, count=1, flags=re.M)):
            done.append(os.path.basename(f))
    return done


def remove_cron():
    r = run(["crontab", "-l"], timeout=30)
    keep = "".join(l + "\n" for l in r.stdout.splitlines() if "epyc6_retire.py" not in l)
    run(["crontab", "-"], inp=keep, timeout=30)


def terminate():
    ok, info = verify_identity()
    log(f"TERMINATE: identity {'OK' if ok else 'MISMATCH'}: {info}")
    if not ok:
        return False
    code, body = cherry("DELETE")
    log(f"TERMINATE: DELETE /v1/servers/{CHERRY_ID} -> HTTP {code} {body[:200]!r}")
    if code not in (200, 202, 204):
        return False
    gone = False
    for _ in range(40):
        time.sleep(30)
        c, b = cherry("GET")
        state = ""
        if c == 200:
            try:
                state = f"{json.loads(b).get('state')} {json.loads(b).get('status')}"
            except ValueError:
                pass
        if c == 404 or re.search(r"terminat|delet", str(state).lower()):
            gone = True
            log(f"TERMINATE: confirmed (GET {c} state {state!r})")
            break
    if not gone:
        log("TERMINATE: DELETE accepted but server not yet reported gone after 20 min; will re-check next pass")
        return False
    return True


def finish():
    t = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    done = retire_configs()
    with open(f"{T}/HANDOFF.md", "a") as f:
        f.write(f"- [EPYC6-RETIRE] 10-21 ot-epyc6 TERMINATED {t}, saves 2.68 EUR/h (Cherry 1036642 'sacred-porpoise', Stockholm, "
                f"185.189.44.151; owner order 10-19 21:35, deadline 10-21 14:15). Closed results verified on AGIdock {BACKUP} (+frozen); "
                f"pending dirs copied to {DEST} (archived_paths.tsv in lanes/epyc6-retire). Live configs retired: "
                f"{', '.join(done) or 'none needed'}. Repo branch {BRANCH} for ROOT4 to merge.\n")
    with open(f"{T}/lanes/EPYC6-RETIRE.md", "a") as f:
        f.write(f"\n## TERMINATED {t}\n- ot-epyc6 (Cherry {CHERRY_ID}) deleted via API; saves 2.68 EUR/h.\n"
                f"- live configs retired: {', '.join(done) or 'none'} (backups *.bak-epyc6retire-1021).\n"
                f"- archived pending dirs: lanes/epyc6-retire/archived_paths.tsv; pending_results lines tagged EPYC6-RETIRE copy.\n"
                f"- watcher cron removed.\n"
                + (f"- deadline kills: see pending_results lines '{KILL_TAG}'.\n" if os.path.exists(f"{STATE}/DEADLINE_KILLED") else ""))
    remove_cron()
    log(f"DONE: configs {done}; HANDOFF + lane file updated; cron removed")


def main():
    global DEADLINE_CHECKS
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-copy", action="store_true")
    ap.add_argument("--no-hash", action="store_true")
    ap.add_argument("--deadline-only", action="store_true", help="exact deadline cancellation, independent archive lock; never DELETE")
    ap.add_argument("--wait-lock", action="store_true", help="block on the pass lock (deadline cron line)")
    args = ap.parse_args()
    DEADLINE_CHECKS = not (args.dry_run or args.no_copy)
    if args.deadline_only:
        enforce_deadline(dry_run=args.dry_run or args.no_copy)
        return
    check_idle.dry = args.dry_run
    os.makedirs(STATE, exist_ok=True)
    lk = open(f"{STATE}/watch.lock", "w")
    try:
        fcntl.flock(lk, fcntl.LOCK_EX | (0 if args.wait_lock else fcntl.LOCK_NB))
    except OSError:
        print("another pass is running")
        return
    if os.path.exists(f"{STATE}/TERMINATED"):
        log("pass: server already terminated; finishing")
        finish()
        return
    if os.path.exists(f"{STATE}/DELETE_SENT"):
        c, b = cherry("GET")                 # a DELETE was sent: confirm it is gone, else re-send after identity check
        state = ""
        try:
            state = f"{json.loads(b).get('state')} {json.loads(b).get('status')}" if c == 200 else ""
        except ValueError:
            pass
        if c == 404 or re.search(r"terminat|delet", state.lower()):
            log(f"TERMINATE: confirmed on re-check (GET {c} state {state!r})")
            open(f"{STATE}/TERMINATED", "w").write(now())
            finish()
        elif terminate():
            open(f"{STATE}/TERMINATED", "w").write(now())
            finish()
        return
    log(f"==== pass start {'DRY-RUN ' if args.dry_run else ''}{'NO-COPY ' if args.no_copy else ''}{'NO-HASH' if args.no_hash else ''}")
    res = {}
    jobs = daemon_jobs()
    try:
        ok1, w1, st = check_idle(jobs)
    except Exception as e:
        log(f"C1 error: {e}")
        return
    res["C1 idle"] = (ok1, w1)
    if not ok1 and deadline_due() and DEADLINE_CHECKS:
        enforce_deadline()
        jobs = daemon_jobs()
        ok1, w1, st = check_idle(jobs)
        res["C1 idle"] = (ok1, w1)
    for name, fn in (("C2 closed", lambda: check_closed(jobs, args)), ("C3 pending", lambda: check_pending(ok1, st, args)),
                     ("C4 repo", check_repo), ("C5 daemon", check_daemon)):
        try:
            res[name] = fn()
        except Exception as e:
            res[name] = (False, [f"error: {e}"])
    for k, (ok, why) in res.items():
        log(f"{k}: {'PASS' if ok else 'WAIT'}" + ("" if ok else f" ({len(why)}): " + " | ".join(why[:8])[:900]))
    jsave(f"{STATE}/last_pass.json", {k: dict(ok=ok, why=why[:200]) for k, (ok, why) in res.items()} | dict(at=now()))
    if not all(ok for ok, _ in res.values()):
        log("==== pass end: WAIT")
        return
    if args.dry_run:
        log("==== pass end: ALL CONDITIONS HOLD -- dry run, no DELETE")
        return
    ok1b, w1b, _ = check_idle(daemon_jobs())      # the pass can take hours: re-check idleness right before the DELETE
    if not ok1b:
        log(f"C1 re-check before DELETE: WAIT ({len(w1b)}): " + " | ".join(w1b[:5])[:600])
        return
    open(f"{STATE}/DELETE_SENT", "w").write(now())
    if terminate():
        open(f"{STATE}/TERMINATED", "w").write(now())
        finish()


if __name__ == "__main__":
    main()
