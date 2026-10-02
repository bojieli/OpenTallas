#!/usr/bin/env python3
"""Run a heavy job on an AGIdock worker VM as if it ran here.

Usage (from the worktree the job would run in):
    [OT_GATE_MIN_GB=<peak GB + margin>] /tmp/claude-1000/remote_gate.sh <command> [args...]

What it does:
  1. waits for a worker with room in /tmp/claude-1000/agd_pool.json: jobs are packed by declared memory
     (8 GB slots, plus a live free-memory check); a job larger than the biggest worker is refused -- use orfs_gate.sh;
  2. pushes the worktree's HEAD commit to the worker's mirror, checks it out at the SAME absolute
     path, and copies the worktree's modified and untracked files over, so the job sees the same
     tree and records the same commit and dirty state;
  3. copies absolute-path arguments that exist here (inputs, scratch dirs) to the same path there;
  4. runs the command there with OT_*/OPENTALLAS_* environment, streaming its output;
  5. copies back every file the job changed or created in the worktree, and the parent directory
     of every absolute-path argument (the job's outputs), then exits with the job's status.
Extra ignored inputs a job needs (e.g. build/models) can be listed in OT_REMOTE_SYNC (space separated,
relative to the worktree). Set OT_REMOTE_DRYRUN=1 to print the plan only.
"""
import fcntl, json, os, shlex, signal, subprocess, sys, time, uuid

POOL = "/tmp/claude-1000/agd_pool.json"
SLOTS = "/tmp/claude-1000/agd_slots"
KEY = os.path.expanduser("~/.ssh/agidock_ot")
SSH = ["ssh", "-i", KEY, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
       "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=60"]
RSYNC_E = "ssh " + " ".join(shlex.quote(a) for a in SSH[1:])
ROOTS = ("/tmp/claude-1000/", "/home/ubuntu/")
HOST_IMAGE = "ot-host:22.04"


def log(*a):
    print("[remote_gate]", *a, file=sys.stderr, flush=True)


def sh(cmd, **kw):
    return subprocess.run(cmd, **kw)


def ssh(ip, script, **kw):
    return sh(SSH + ["ubuntu@" + ip, script], **kw)


BAD = {}
T0 = time.time()
STATUS = "/tmp/claude-1000/agd_status.json"


def worker_status(pool):
    """Load, cores and free memory of every worker, refreshed at most every 30 s and shared by all
    waiters through one cache file (so 50 waiters do not each ssh to every worker every poll)."""
    with open(STATUS + ".lock", "a+") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        try:
            st = json.load(open(STATUS))
        except Exception:
            st = {}
        if time.time() - st.get("_t", 0) > 30:
            probe = "echo $(cut -d' ' -f1 /proc/loadavg) $(nproc) $(awk '/MemAvailable/{print int($2/1048576)}' /proc/meminfo)"
            procs = {ip: subprocess.Popen(SSH + ["ubuntu@" + ip, probe], stdout=subprocess.PIPE,
                                          stderr=subprocess.DEVNULL, text=True)
                     for ip, vm in pool.items() if not vm.get("disabled")}
            st = {"_t": time.time()}
            for ip, p in procs.items():
                try:
                    out = p.communicate(timeout=25)[0].split()
                    st[ip] = {"load": float(out[0]), "cpus": int(out[1]), "free_gb": int(out[2])}
                except Exception:
                    p.kill()
            t = STATUS + ".tmp"; json.dump(st, open(t, "w")); os.replace(t, STATUS)
        return st


def load_pool():
    """The pool file, falling back to its backup if a full disk left it empty or torn."""
    for p in (POOL, POOL + ".bak"):
        try:
            d = json.load(open(p))
            if d:
                return d
        except Exception:
            pass
    return {}


def acquire(min_gb, cwd):
    """Pack jobs by declared memory AND by CPU: each worker has one 8 GB slot per 8 GB of RAM; a job
    takes ceil(floor / 8) slots, and is admitted only if the worker has that much memory actually free
    and its 1-minute load is below its core count. Candidates are tried least-loaded first, so work
    spreads over the pool instead of piling onto the machine with the most free memory."""
    import hashlib
    os.makedirs(SLOTS, exist_ok=True)
    need = max(1, -(-min_gb // 8))
    while True:
        pool = load_pool()
        st = worker_status(pool)
        cands = []
        for ip, vm in pool.items():
            s_ = st.get(ip)
            if (vm.get("disabled") or ip in os.environ.get("OT_GATE_EXCLUDE", "").split(",") or vm.get("physical_ram_gb", vm["ram_gb"]) - 2 < min_gb or BAD.get(ip, 0) > time.time()
                    or not s_ or s_["free_gb"] < min_gb
                    # a job too big for the 32 GB workers can only run on the few big hosts, which small jobs
                    # keep CPU-saturated (load 120-150 on 28 cores from oversubscribed router threads); memory alone decides
                    or (min_gb <= 30 and s_["load"] >= s_["cpus"])):
                continue
            cands.append((s_["load"] / s_["cpus"], ip, vm))
        for _, ip, vm in sorted(cands):
            held = []
            for k in range(1, vm["ram_gb"] // 8 + 1):
                f = open(f"{SLOTS}/{ip}.{k}", "a+")
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held.append(f)
                except OSError:
                    f.close()
                if len(held) == need:
                    break
            if len(held) == need:
                # one job per worktree per worker: jobs from one worktree share its checkout path there
                w = open(f"{SLOTS}/{ip}.wt.{hashlib.md5(cwd.encode()).hexdigest()[:12]}", "a+")
                try:
                    fcntl.flock(w, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    held.append(w)
                    # count this admission against the cached load so the next waiter sees it at once
                    with open(STATUS + ".lock", "a+") as lk:
                        fcntl.flock(lk, fcntl.LOCK_EX)
                        try:
                            c = json.load(open(STATUS)); c[ip]["load"] += 4; c[ip]["free_gb"] -= min_gb
                            t = STATUS + ".tmp"; json.dump(c, open(t, "w")); os.replace(t, STATUS)
                        except Exception:
                            pass
                    return ip, held
                except OSError:
                    w.close()
            for f in held:
                f.close()
        # nothing remote fits: after 10 minutes, fall back to THIS machine when it has room
        # (one of the shared local gate slots, enough free memory, and load below its core count)
        if time.time() - T0 > 600:
            try:
                load = os.getloadavg()[0]
                free = int(open("/proc/meminfo").read().split("MemAvailable:")[1].split()[0]) // 1048576
            except Exception:
                load, free = 1e9, 0
            if os.environ.get("OT_ALLOW_LOCAL") == "1" and load < 0.6 * os.cpu_count() and free >= min_gb + 10:
                for i in range(1, 6):
                    f = open(f"/tmp/claude-1000/orfs_slots/slot{i}", "a+")
                    try:
                        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        return "local", [f]
                    except OSError:
                        f.close()
        time.sleep(20)


def main():
    cmd = sys.argv[1:]
    if not cmd:
        sys.exit(__doc__)
    min_gb = int(os.environ.get("OT_GATE_MIN_GB", "20"))
    biggest = max((v["ram_gb"] for v in load_pool().values() if not v.get("disabled")), default=32)
    if min_gb > biggest - 2:
        sys.exit(f"[remote_gate] OT_GATE_MIN_GB={min_gb} exceeds the largest worker ({biggest} GB); use orfs_gate.sh")
    cwd = os.getcwd()
    top = sh(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if top != cwd:
        sys.exit(f"[remote_gate] run from the worktree root ({top!r}), not {cwd!r}")
    head = sh(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    dirty = sh(["git", "ls-files", "-m", "-o", "--exclude-standard", "-z"], capture_output=True,
               check=True).stdout.split(b"\0")
    dirty = [p.decode() for p in dirty if p and os.path.isfile(os.path.join(cwd, p.decode()))]
    deleted = [p for p in sh(["git", "ls-files", "-d", "-z"], capture_output=True).stdout.decode().split("\0") if p]
    abs_args = []
    for a in cmd:
        for tok in [a] + ([a.split("=", 1)[1]] if "=" in a else []):
            if tok.startswith(ROOTS) and not tok.startswith(cwd + "/") and tok != cwd:
                abs_args.append(tok.rstrip("/"))
    extra = os.environ.get("OT_REMOTE_SYNC", "").split()
    envs = {k: v for k, v in os.environ.items() if k.startswith(("OT_", "OPENTALLAS_"))}
    if os.environ.get("OT_REMOTE_DRYRUN"):
        print(json.dumps(dict(cwd=cwd, head=head, dirty=dirty, deleted=deleted, abs_args=abs_args,
                              extra=extra, env=envs, cmd=cmd), indent=1))
        return 0
    while True:
        ip, held = acquire(min_gb, cwd)
        if ip == "local":
            log(f"no worker has room after 10 min; running on this machine (floor {min_gb} GB): {' '.join(cmd)[:160]}")
            rc = subprocess.run(cmd).returncode
            for f in held:
                f.close()
            return rc
        # a worker that cannot be reached or prepared is skipped for 10 minutes; the job tries another
        if ssh(ip, "test -d ~/repo.git || git init -q --bare ~/repo.git; docker image inspect ot-host:22.04 >/dev/null",
               capture_output=True).returncode == 0:
            break
        log(f"worker {ip} is not usable right now; trying another")
        BAD[ip] = time.time() + 600
        for f in held:
            f.close()
    job = uuid.uuid4().hex[:10]
    log(f"worker {ip} (floor {min_gb} GB), job {job}: {' '.join(cmd)[:200]}")
    # 1. the commit, through a bare mirror on the worker
    ssh(ip, "test -d ~/repo.git || git init -q --bare ~/repo.git", check=True)
    # one push at a time per worker (parallel first pushes of the full history drop connections), retried
    with open(f"{SLOTS}/{ip}.push", "a+") as pl:
        fcntl.flock(pl, fcntl.LOCK_EX)
        for attempt in range(4):
            if sh(["git", "push", "-q", "-f", f"ubuntu@{ip}:repo.git", f"{head}:refs/jobs/{job}"],
                  env={**os.environ, "GIT_SSH_COMMAND": RSYNC_E}).returncode == 0:
                break
            log(f"worker {ip}: push attempt {attempt + 1} failed; retrying"); time.sleep(20)
        else:
            sys.exit(f"[remote_gate] could not push {head} to {ip}")
    q = shlex.quote
    ssh(ip, f"""set -e
if [ -e {q(cwd)}/.git ]; then
  test "$(git -C {q(cwd)} rev-parse HEAD)" = {head}
  test -z "$(git -C {q(cwd)} status --porcelain --untracked-files=normal)"
else
  test ! -e {q(cwd)}
  mkdir -p {q(os.path.dirname(cwd))}
  git --git-dir ~/repo.git worktree add -q --detach {q(cwd)} {head}
fi
cd {q(cwd)}; {'git rm -q --cached -- ' + ' '.join(q(p) for p in deleted) + ' >/dev/null; rm -f -- ' + ' '.join(q(p) for p in deleted) if deleted else 'true'}
touch ~/.job_{job}_start""", check=True)
    # 2. the dirty files, extra ignored inputs, and absolute-path inputs
    if dirty:
        sh(["rsync", "-a", "--from0", "--files-from=-", "-e", RSYNC_E, cwd + "/", f"ubuntu@{ip}:{cwd}/"],
           input="\0".join(dirty).encode(), check=True)
    for rel in extra:
        sh(["rsync", "-a", "-e", RSYNC_E, os.path.join(cwd, rel), f"ubuntu@{ip}:{os.path.dirname(os.path.join(cwd, rel))}/"], check=True)
    for p in abs_args:
        if os.path.exists(p):
            ssh(ip, f"mkdir -p {q(os.path.dirname(p))}")
            sh(["rsync", "-a", "-e", RSYNC_E, p, f"ubuntu@{ip}:{os.path.dirname(p)}/"])
        else:
            ssh(ip, f"mkdir -p {q(os.path.dirname(p))}")
    # 3. run
    env_s = " ".join(f"{k}={q(v)}" for k, v in envs.items())
    inner = ' '.join(q(c) for c in cmd)
    inner = 'python3 ' + q(cwd + '/tools/native_build_unlimited_exec.py') + ' -- ' + inner
    if os.environ.get("OT_REMOTE_NATIVE"):
        run_s = f"cd {q(cwd)} && env {env_s} prlimit --fsize=unlimited:unlimited --as=unlimited:unlimited --cpu=unlimited:unlimited -- {inner}"
    else:  # inside a container matching this machine (Ubuntu 22.04, its simulators and Python packages)
        env_flags = " ".join(f"-e {k}={q(v)}" for k, v in envs.items())
        run_s = (f"docker run --ulimit fsize=-1:-1 --ulimit as=-1:-1 --ulimit cpu=-1:-1 --rm --name otjob-{job} --network host -u $(id -u):$(id -g) "
                 f"--group-add $(stat -c %g /var/run/docker.sock) -v /home/ubuntu:/home/ubuntu -v /tmp:/tmp "
                 f"-v /var/run/docker.sock:/var/run/docker.sock -e HOME=/home/ubuntu {env_flags} "
                 f"-w {q(cwd)} {HOST_IMAGE} {inner}")
    def _stop(signum, frame):
        ssh(ip, f"docker kill otjob-{job} >/dev/null 2>&1; true")
        sys.exit(128 + signum)
    signal.signal(signal.SIGTERM, _stop); signal.signal(signal.SIGINT, _stop)
    if not os.environ.get("OT_REMOTE_NATIVE"):  # wait for the host-matching image if a worker is still loading it
        while ssh(ip, f"docker image inspect {HOST_IMAGE} >/dev/null 2>&1").returncode != 0:
            log(f"worker {ip}: waiting for {HOST_IMAGE}"); time.sleep(30)
    rc = ssh(ip, run_s).returncode
    # 4. bring back what changed in the worktree, and every absolute-path argument's directory
    # only files the JOB wrote (newer than the start marker; pushed dirty files keep their older mtimes), and -u
    # so a local file edited while the job ran is never overwritten by the stale launch-time copy
    changed = ssh(ip, f"cd {q(cwd)} && find . -path ./.git -prune -o -type f -newer ~/.job_{job}_start -print",
                  capture_output=True, text=True).stdout.split("\n")
    changed = sorted({c[2:] if c.startswith("./") else c for c in changed if c.strip()})
    if changed:
        sh(["rsync", "-a", "-u", "--files-from=-", "-e", RSYNC_E, f"ubuntu@{ip}:{cwd}/", cwd + "/"],
           input="\n".join(changed), text=True)
    for p in abs_args:
        d = p if ssh(ip, f"test -d {q(p)}").returncode == 0 else os.path.dirname(p)
        os.makedirs(d, exist_ok=True)
        sh(["rsync", "-a", "-u", "-e", RSYNC_E, f"ubuntu@{ip}:{d}/", d + "/"])
    ssh(ip, f"rm -f ~/.job_{job}_start; git --git-dir ~/repo.git update-ref -d refs/jobs/{job}")
    log(f"worker {ip} job {job} finished rc={rc}; {len(changed)} worktree files returned")
    for f in held:
        f.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())
