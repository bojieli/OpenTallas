# EPYC6-RETIRE: runs ON ot-epyc6 (python3 - < this file). Prints one JSON object describing job activity:
#   units   ot-heavy scopes (oth-*.scope) with live processes
#   docker  running containers (name, age s, bind-mount sources)
#   procs   ubuntu processes that look like job work (EDA tools, sims, builds, scratch-dir scripts)
# Everything older than 48 h is reported under "stale" (owner rule 10-09: nothing legitimately runs > 48 h).
import glob, json, os, re, subprocess, time

STALE_S = 48 * 3600
HZ = os.sysconf("SC_CLK_TCK")
with open("/proc/uptime") as uptime:
    BOOT = time.time() - float(uptime.read().split()[0])
UID = os.getuid()
TOOLS = re.compile(r"^(openroad|yosys|yosys-abc|iverilog|ivl|ivlpp|vvp|verilator.*|cc1plus|cc1|g\+\+|c\+\+|ld|make|klayout|"
                   r"docker|ot-heavy|timeout|zstd|rsync|tar|V[A-Za-z0-9_]+)$")
SKIP_ARGS = re.compile(r"Streamed to each host|python3 -u - |^sshd|^-bash$|^bash -l$|sleep infinity|/tmp/e6r/|/archive/epyc6-retire-1021")


def rd(p, n=8192):
    try:
        with open(p, "rb") as f:
            return f.read(n).decode("utf-8", "replace")
    except OSError:
        return ""


def pstat(pid):
    s = rd(f"/proc/{pid}/stat", 1024)
    i = s.rfind(")")
    if i < 0:
        return None
    f = s[i + 2:].split()
    return s[s.find("(") + 1:i], int(f[1]), time.time() - (BOOT + int(f[19]) / HZ)


def start_ticks(pid):
    try:
        return int(rd(f"/proc/{pid}/stat", 1024).rsplit(")", 1)[1].split()[19])
    except (ValueError, IndexError):
        return None


def argv(pid):
    return " ".join(a for a in rd(f"/proc/{pid}/cmdline", 4096).split("\0") if a)


def cwd(pid):
    try:
        return os.readlink(f"/proc/{pid}/cwd")
    except OSError:
        return ""


def inventory():
    out = dict(t=time.time(), hostname=os.uname().nodename, units=[], docker=[], procs=[], stale=[])
    for d in glob.glob("/sys/fs/cgroup/user.slice/user-*.slice/user@*.service/app.slice/oth-*.scope"):
        procs = rd(d + "/cgroup.procs", 4096).split()
        if not procs:
            continue
        st = pstat(procs[0])
        if not st:
            continue
        rec = dict(unit=os.path.basename(d)[:-6], age=int(st[2]), cwd=cwd(procs[0]), argv=argv(procs[0])[:400], nproc=len(procs), cg_inode=os.stat(d).st_ino,
                   leader_pid=int(procs[0]), start_ticks=start_ticks(procs[0]))
        (out["stale"] if st[2] > STALE_S else out["units"]).append(rec)
    
    try:
        ids = subprocess.run(["docker", "ps", "-q", "--no-trunc"], capture_output=True, text=True, timeout=30).stdout.split()
        if ids:
            fmt = "{{.Name}}\t{{.State.StartedAt}}\t{{range .Mounts}}{{.Source}} {{end}}\t{{.Id}}"
            for l in subprocess.run(["docker", "inspect", "--format", fmt] + ids, capture_output=True, text=True, timeout=60).stdout.splitlines():
                f = l.split("\t")
                if len(f) < 3:
                    continue
                try:
                    import calendar
                    t0 = calendar.timegm(time.strptime(f[1][:19], "%Y-%m-%dT%H:%M:%S"))
                except ValueError:
                    t0 = time.time()
                rec = dict(name=f[0].lstrip("/"), age=int(time.time() - t0), mounts=f[2].split(), id=f[3] if len(f) > 3 else None, started_at=f[1])
                (out["stale"] if rec["age"] > STALE_S else out["docker"]).append(rec)
    except Exception as e:  # docker unavailable -> report, the caller treats it as "unknown" (blocking)
        out["docker_error"] = str(e)[:200]
    
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            if os.stat(f"/proc/{pid}").st_uid != UID:
                continue
        except OSError:
            continue
        st = pstat(pid)
        if not st:
            continue
        comm, ppid, age = st
        a = argv(pid)
        if not a or SKIP_ARGS.search(a) or comm in ("sshd", "sshd-session", "systemd", "(sd-pam)", "sleep", "dbus-daemon", "ps", "tmux: server", "tmux"):
            continue
        if TOOLS.match(comm) or "/srv/opentallas-scratch" in a or "/srv/opentallas-scratch" in cwd(pid) or "ref_gate" in a or "closure-loop" in a:
            rec = dict(pid=int(pid), ppid=ppid, comm=comm, age=int(age), args=a[:300], cwd=cwd(pid), start_ticks=start_ticks(pid))
            (out["stale"] if age > STALE_S else out["procs"]).append(rec)
    return out


if __name__ == "__main__":
    print(json.dumps(inventory()))
