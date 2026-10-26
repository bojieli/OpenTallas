#!/usr/bin/env python3
"""OOMADJ_999_1022: remove oom_score_adj -1000 from the fleet job helpers.  Run as root ON a fleet host, with
ot-protect-die alongside:   sudo python3 install_oomadj_999.py [--check]

Why: -1000 (OOM_SCORE_ADJ_MIN) exempts a process from the memcg OOM killer too.  A die job that reached its own
scope MemoryMax / docker --memory then livelocked (neither finished nor failed) and flooded kern.log with memcg dumps
(ep5 +44 GB in 13 min, 2026-10-22).  Now: die jobs -999 (the global OOM killer / earlyoom still pick every other
process first), every other ot-heavy job explicitly 0, so a job at its own cap fails visibly.

Patches, each marker-checked, validated (bash -n / compile) before any file changes, replaced atomically (new inode:
running waiters keep their copy), backed up in /var/tmp/ot-heavy/oomadj-999-backup-<UTC>:
  /usr/local/bin/ot-heavy              non-die job: echo 0 > /proc/self/oom_score_adj before the scope starts
  /usr/local/lib/ot-heavy/bin/docker   die: --oom-score-adj=-999; non-die: negative values -> 0, default 0
  /usr/local/bin/ot-protect-die        repo copy (-999; legacy -1000 processes left untouched, reported)
  ot-die-protection.service            OOMScoreAdjust=-999; restarted (it never signals a job)
  /etc/ot-oomadj-legacy-cutoff         epoch now, written once: -1000 processes started earlier are legacy
Never stops, signals or re-adjusts a running job: processes already at -1000 stay there (reported only).
"""
import hashlib, json, os, re, shutil, subprocess, sys, tempfile, time
from pathlib import Path

MARK = "OOMADJ_999_1022"
HEAVY = "/usr/local/bin/ot-heavy"
DOCKER = "/usr/local/lib/ot-heavy/bin/docker"
PROTECT = "/usr/local/bin/ot-protect-die"
SERVICE = "/etc/systemd/system/ot-die-protection.service"
CUTOFF = "/etc/ot-oomadj-legacy-cutoff"

HEAVY_ANCHOR = "    exec systemd-run --user --scope"
HEAVY_BLOCK = (
    "    # " + MARK + ": a non-die job starts at oom_score_adj 0 (its launcher may sit in a protected die tree at -999,\n"
    "    # or a legacy -1000 one, which would make the job un-killable by its own scope's memcg OOM: livelock at the cap).\n"
    "    if [ \"${OT_HEAVY_PRIO:-}\" != die ]; then echo 0 > /proc/self/oom_score_adj 2>/dev/null || true; fi\n")


def patch_heavy(s):
    if MARK in s:
        return s
    if s.count(HEAVY_ANCHOR) != 1:
        raise ValueError("unknown ot-heavy layout (systemd-run scope anchor)")
    return s.replace(HEAVY_ANCHOR, HEAVY_BLOCK + HEAVY_ANCHOR)


DOCKER_OLD_CASES = (
    '    --oom-score-adj=*) if [ "${OT_HEAVY_PRIO:-}" != die ]; then out+=("$a"); fi;;\n'
    '    --oom-score-adj) if [ "${OT_HEAVY_PRIO:-}" != die ]; then out+=("$a" "${rest[$((j+1))]}"); fi; j=$((j+1));;\n')
DOCKER_CASES = (
    '    --oom-score-adj=*) hadj=1; [ "${OT_HEAVY_PRIO:-}" = die ] || out+=("--oom-score-adj=$(oadj "${a#--oom-score-adj=}")");;\n'
    '    --oom-score-adj) hadj=1; [ "${OT_HEAVY_PRIO:-}" = die ] || out+=("$a" "$(oadj "${rest[$((j+1))]}")"); j=$((j+1));;\n')
DOCKER_OLD_DIE = ('# DIE_WATCHDOG_1021: Docker daemon starts outside the caller scope; explicitly inherit die immunity.\n'
                  'if [ "${OT_HEAVY_PRIO:-}" = die ]; then out=("--oom-score-adj=-1000" "--label=opentallas.priority=die" "${out[@]}"); fi\n')
DOCKER_DIE = (
    '# ' + MARK + ': Docker daemon starts outside the caller scope, so the adjustment is explicit: a die container -999\n'
    '# (never -1000: that also exempts it from its own --memory cgroup OOM, a livelock at the cap), anything else >= 0.\n'
    'if [ "${OT_HEAVY_PRIO:-}" = die ]; then out=("--oom-score-adj=-999" "--label=opentallas.priority=die" "${out[@]}")\n'
    'elif [ -z "$hadj" ]; then out=("--oom-score-adj=0" "${out[@]}"); fi\n')
DOCKER_FN_ANCHOR = 'j=0; n=${#rest[@]}\n'
DOCKER_FN = ('# ' + MARK + ': a non-die container never runs below oom_score_adj 0\n'
             'hadj=; oadj() { case "$1" in -*) echo 0;; *) echo "$1";; esac; }\n')
DOCKER_EXEC = 'exec "$REAL" "${pre[@]}" "--memory-swap=$lim" "${out[@]}"'


def patch_docker(s):
    if MARK in s:
        return s
    for a in (DOCKER_FN_ANCHOR, DOCKER_EXEC, "    --memory=*)"):
        if s.count(a) != 1:
            raise ValueError("unknown docker shim layout: " + a.strip())
    s = s.replace(DOCKER_FN_ANCHOR, DOCKER_FN + DOCKER_FN_ANCHOR)
    if DOCKER_OLD_CASES in s:                      # DIE_WATCHDOG_1021 layout
        s = s.replace(DOCKER_OLD_CASES, DOCKER_CASES)
    else:
        s = s.replace("    --memory=*)", DOCKER_CASES + "    --memory=*)")
    olds = [o for o in (DOCKER_OLD_DIE, DOCKER_OLD_DIE.replace("=-1000", "=-999")) if o in s]
    if olds:                                       # install_die_protection.py block (pre- or post-1022 value)
        s = s.replace(olds[0], DOCKER_DIE)
    else:
        s = s.replace(DOCKER_EXEC, DOCKER_DIE + DOCKER_EXEC)
    return s


def patch_service(s):
    return s.replace("OOMScoreAdjust=-1000", "OOMScoreAdjust=-999")


def atomic_write(dst, data, mode):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(dst), prefix="." + os.path.basename(dst) + ".")
    with os.fdopen(fd, "w") as f:
        f.write(data)
    os.chmod(tmp, mode)
    os.replace(tmp, dst)


def bash_ok(text):
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as t:
        t.write(text)
    try:
        return subprocess.run(["bash", "-n", t.name]).returncode == 0
    finally:
        os.unlink(t.name)


def main():
    check = "--check" in sys.argv[1:]
    if os.geteuid() != 0 and not check:
        raise SystemExit("root required")
    src = Path(__file__).with_name("ot-protect-die").read_text()
    if "TARGET = '-999'" not in src:
        raise SystemExit("ot-protect-die beside the installer is not the -999 version; nothing installed")
    compile(src, "ot-protect-die", "exec")
    plan = []
    for path, fn in ((HEAVY, patch_heavy), (DOCKER, patch_docker)):
        if not os.path.exists(path):
            continue
        before = Path(path).read_text()
        after = fn(before)
        if not bash_ok(after):
            raise SystemExit(f"patched {path} fails bash -n; nothing installed")
        plan.append((path, before, after))
    if os.path.exists(PROTECT):
        plan.append((PROTECT, Path(PROTECT).read_text(), src))
    svc = Path(SERVICE).read_text() if os.path.exists(SERVICE) else None
    if check:
        print(json.dumps({p: ("change" if b != a else "same") for p, b, a in plan}, sort_keys=True))
        return
    bk = Path("/var/tmp/ot-heavy/oomadj-999-backup-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    bk.mkdir(parents=True)
    if not os.path.exists(CUTOFF):                # first install only: the cutoff never moves forward
        atomic_write(CUTOFF, "%d\n" % int(time.time()), 0o644)
    proof = []
    for path, before, after in plan:
        shutil.copy2(path, bk / os.path.basename(path))
        if after != before:
            atomic_write(path, after, os.stat(path).st_mode & 0o7777)
        proof.append(dict(path=path, changed=after != before, sha256=hashlib.sha256(after.encode()).hexdigest()))
    if svc is not None:
        shutil.copy2(SERVICE, bk / os.path.basename(SERVICE))
        if patch_service(svc) != svc:
            atomic_write(SERVICE, patch_service(svc), 0o644)
            subprocess.run(["systemctl", "daemon-reload"], check=True)
        # the watcher holds the old code in memory: restart it (it never signals a job)
        subprocess.run(["systemctl", "restart", "ot-die-protection.service"], check=True)
    print("OOMADJ_999_OK " + json.dumps(dict(host=os.uname().nodename, backup=str(bk), cutoff=Path(CUTOFF).read_text().strip(),
                                             files=proof, service=svc is not None), sort_keys=True))


if __name__ == "__main__":
    main()
