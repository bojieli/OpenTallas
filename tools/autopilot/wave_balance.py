#!/usr/bin/env python3 -I
"""wave_balance.py -- WAVE-BALANCE-1 (COORD 11-11 23:4x): move a queued kit-wave job to an idle host.

Why.  ot-run "syncs nothing: the inputs must already be on the host".  The autopilot submits every route / CTS / sign-off
job with --dir <kit> (--stage <kit>), so the job can only wait on the host where kit_wave generated the kit; ot-run's
SPILL moves a lane only to a host that admits it NOW, and its RE-PLACE only among hosts that already hold --dir.  At 23:36
epyc9 had load 97/96 and 30 waiters (620 GB) while epyc2 sat at 26/128 and intel1 at 50/112.  A queued waiter never moved.

What.  Each tick (autopilot.tick, after the chain polls) or `wave_balance.py [--apply]` (default: dry run, prints the table):
  * a source host with MORE than waiter_max (8) ot-run waiters is hot;
  * a target host qualifies when it is not excluded (intel2, localhost, the hub, hosts ot-run --status does not list,
    i.e. REFUSED / under the disk floor), its ot-run admission takes the job's --mem now, load1 < 0.8 x cores, and its
    scratch free > kit size + 100 GB;
  * the OLDEST waiting kit-wave job of the hot host moves first, at most max_moves (4) per tick;
  * a job moves only while its waiter has NOT started (no ot-heavy-exit / systemd-run under the waiter's wrapper); the
    check is repeated after the copy and again right after the old client is stopped.  A started stage is never touched.
How a move runs (apply):
  1. source probe: kit + runner size, regular-file list, symlinks that leave the kit (realpath; they are copied as files
     with rsync --copy-unsafe-links, so nothing is ever written through a link into a shared src); refuse above max_kit_gb;
  2. destination checks: kit path absent there, ancestors do not link out of the scratch layout, free > size + 100 GB;
  3. rsync -aH from the source host to the same absolute path on the target (kit dir and runner, as --stage does);
  4. verify: `rsync -anci` against the target is empty (checksums) and the regular-file list (path + size) matches;
  5. re-check the waiter still waits; stop the autopilot unit of the job (its ot-run client cancels its waiter), then TERM
     the exact remaining PIDs of that waiter's tag (wrapper + ot-heavy), never a pattern;
  6. resubmit the SAME unit name with the client's own argv plus --hosts <target> and a fresh client log (the old log
     holds the cancel lines, which the poller would read as a crash); the job record is re-homed (host / kit) and a
     wave_balance entry goes to its history and to jobs/<id>/wave_balance.json (the kit-wave table evidence).
The source copy stays (autoclean / prune own removal); the record names it as moved_from.
Config (autopilot/kit_wave.json "wave_balance"): enabled (false = tick hook off), waiter_max, max_moves, load_frac,
disk_margin_gb, max_kit_gb, min_wait_s, exclude_hosts, target_hosts.  Default OFF: the tick hook runs only when enabled.
"""
import json
import os
import re
import shlex
import sys
import time
from pathlib import Path

WAITER_MAX = 8            # a host with more waiters than this is hot
MAX_MOVES = 4             # per tick
LOAD_FRAC = 0.8           # target load1 must be under this x cores
DISK_MARGIN_GB = 100      # target scratch must exceed kit size + this
MAX_KIT_GB = 40           # same bound as ot-run SPILL (OT_RUN_SPILL_MAX_GB)
MIN_WAIT_S = 120          # a waiter younger than this is still in its first admission loop
STATIC_EXCLUDE = ("intel2", "localhost")     # KW-FIX-45's exclusions: the hub and the local host never take work
OT_TAG_RE = re.compile(r"--tag (otrun-([A-Za-z0-9_.-]+)-(\d+)-\d+)\b")
MEM_RE = re.compile(r"ot-heavy --mem (\d+)\b")
CD_RE = re.compile(r"\bcd (\S+) \|\|")


# ----------------------------------------------------------------------------------------------- pure selection
def parse_waiters(ps_text, hub_node):
    """remote `ps -eo pid=,ppid=,etimes=,args=` -> ot-run queue entries of THIS hub's clients:
    {tag, client_pid, wrapper, heavy: [pids], mem, dir, age_s, started}.  started = a descendant of the wrapper is
    ot-heavy-exit / systemd-run (the command was admitted), or no waiting ot-heavy process is left under it."""
    rows, kids = {}, {}
    for ln in (ps_text or "").splitlines():
        p = ln.split(None, 3)
        if len(p) == 4 and p[0].isdigit() and p[1].isdigit() and p[2].isdigit():
            rows[int(p[0])] = (int(p[1]), int(p[2]), p[3])
            kids.setdefault(int(p[1]), []).append(int(p[0]))

    def descendants(pid):
        out, todo = [], list(kids.get(pid, []))
        while todo:
            c = todo.pop()
            out.append(c)
            todo.extend(kids.get(c, []))
        return out

    res = []
    for pid, (_, age, args) in rows.items():
        if not args.startswith("bash -c"):
            continue
        m = OT_TAG_RE.search(args)
        if not m or m.group(2) != hub_node:
            continue
        mem, cd = MEM_RE.search(args), CD_RE.search(args)
        ds = descendants(pid)
        heavy = [d for d in ds if "/ot-heavy --mem" in rows[d][2] and m.group(1) in rows[d][2]]
        started = any(("ot-heavy-exit" in rows[d][2] or "systemd-run" in rows[d][2]) for d in ds) or not heavy
        res.append({"tag": m.group(1), "client_pid": int(m.group(3)), "wrapper": pid, "heavy": sorted(heavy),
                    "mem": int(mem.group(1)) if mem else 0, "dir": cd.group(1) if cd else "", "age_s": age,
                    "started": started})
    return res


def target_ok(v, mem, threads, kit_gb, cfg):
    """why a status row cannot take the job ('' = it can): admission of --mem now, load < 0.8 x cores, scratch"""
    if not v:
        return "no ot-run status row (refused or unreachable)"
    cores = int(v.get("cores") or 0)
    if int(v.get("admit", 0)) < mem:
        return f"admits {v.get('admit', 0)} GB < {mem}"
    lf = float(cfg.get("load_frac", LOAD_FRAC))
    if cores <= 0 or float(v.get("load", 0)) >= lf * cores:
        return f"load {v.get('load', 0)}/{cores} >= {lf} x cores"
    if threads > 8 and cores < 48:
        return "fewer than 48 cores for a >8-thread job"
    margin = int(cfg.get("disk_margin_gb", DISK_MARGIN_GB))
    if v.get("scratch_gb") is None or int(v["scratch_gb"]) <= kit_gb + margin:
        return f"scratch {v.get('scratch_gb')} GB <= kit {kit_gb:.1f} + {margin}"
    return ""


def plan_moves(cands, status, cfg, hub_names=()):
    """cands: [{id, unit, host, mem, threads, age_s, kit_gb, ...}] of jobs whose waiter waits on its home host.
    status: parse_otrun_status() dict.  -> (moves, skipped): moves = [{cand, to}], skipped = [(cand, why)].
    Oldest waiter first, hot host (> waiter_max waiters) only, at most max_moves; the target's admits / load / scratch
    and the source's waiter count are charged as moves are chosen.  Target = most (free cores x admits)."""
    st = {h: dict(v) for h, v in (status or {}).items()}
    excl = set(STATIC_EXCLUDE) | set(hub_names) | set(cfg.get("exclude_hosts") or ())
    allow = set(cfg.get("target_hosts") or ())
    wmax, cap = int(cfg.get("waiter_max", WAITER_MAX)), int(cfg.get("max_moves", MAX_MOVES))
    min_wait = int(cfg.get("min_wait_s", MIN_WAIT_S))
    waiting = {h: int(v.get("wait_n", 0)) for h, v in st.items()}
    moves, skipped = [], []
    for c in sorted(cands, key=lambda c: (-int(c["age_s"]), c["id"])):
        if len(moves) >= cap:
            skipped.append((c, f"max {cap} moves per tick"))
            continue
        h = c["host"]
        if waiting.get(h, 0) <= wmax:
            skipped.append((c, f"{h} has {waiting.get(h, 0)} waiters (<= {wmax})"))
            continue
        if int(c["age_s"]) < min_wait:
            skipped.append((c, f"waited {c['age_s']} s (< {min_wait})"))
            continue
        if c["kit_gb"] > float(cfg.get("max_kit_gb", MAX_KIT_GB)):
            skipped.append((c, f"kit {c['kit_gb']:.1f} GB > {cfg.get('max_kit_gb', MAX_KIT_GB)}"))
            continue
        best, why = None, []
        for t, v in st.items():
            if t == h or t in excl or (allow and t not in allow):
                continue
            w = target_ok(v, c["mem"], c["threads"], c["kit_gb"], cfg)
            if w:
                why.append(f"{t}: {w}")
                continue
            key = (max(0.0, int(v["cores"]) - float(v.get("load", 0))) * int(v["admit"]), t)
            if best is None or key > best[0]:
                best = (key, t)
        if not best:
            skipped.append((c, "no target: " + "; ".join(why[:6])))
            continue
        v = st[best[1]]
        v["admit"] = int(v["admit"]) - c["mem"]
        v["load"] = float(v.get("load", 0)) + c["threads"]
        v["scratch_gb"] = int(v["scratch_gb"]) - int(c["kit_gb"] + 1)
        waiting[h] = waiting.get(h, 0) - 1
        moves.append({"cand": c, "to": best[1]})
    return moves, skipped


def with_hosts(argv, target):
    """the ot-run client's own argv with --hosts set to target (replaced, or added before the `--` separator)"""
    a = list(argv)
    i = a.index("--") if "--" in a else len(a)
    for k, w in enumerate(a[:i]):
        if w == "--hosts" and k + 1 < i:
            a[k + 1] = target
            return a
    return a[:i] + ["--hosts", target] + a[i:]


# ----------------------------------------------------------------------------------------------- remote probes
SRC_PROBE = r'''
import hashlib, json, os, sys
a = json.loads(sys.argv[1])
def size_tree(p):
    n = 0
    for r, ds, fs in os.walk(p):
        for f in fs:
            q = os.path.join(r, f)
            if not os.path.islink(q):
                try: n += os.lstat(q).st_size
                except OSError: pass
    return n
out = {"bytes": 0, "unsafe": [], "files": 0, "lst": "", "skip": []}
lines = []
for root in a["roots"]:
    if not os.path.exists(root):
        out["error"] = "missing " + root; print("AP_JSON " + json.dumps(out)); sys.exit(0)
    if os.path.isfile(root):
        out["bytes"] += os.lstat(root).st_size; continue
    base = os.path.realpath(root)
    for r, ds, fs in os.walk(root):
        for d in list(ds):
            if os.path.islink(os.path.join(r, d)):
                ds.remove(d); fs.append(d)
        for f in fs:
            q = os.path.join(r, f)
            rel = os.path.relpath(q, root)
            if os.path.islink(q):
                real = os.path.realpath(q)
                if real == base or real.startswith(base + os.sep):
                    continue
                out["skip"].append(os.path.basename(root) + "/" + rel)
                sz = size_tree(real) if os.path.isdir(real) else (os.lstat(real).st_size if os.path.exists(real) else 0)
                out["unsafe"].append([q, real, sz]); out["bytes"] += sz
                continue
            try: s = os.lstat(q).st_size
            except OSError: continue
            out["files"] += 1; out["bytes"] += s
            lines.append("%s/%s %d" % (os.path.basename(root), rel, s))
lines.sort()
out["lst"] = hashlib.md5("\n".join(lines).encode()).hexdigest()
print("AP_JSON " + json.dumps(out))
'''

DST_PROBE = r'''
import hashlib, json, os, sys
a = json.loads(sys.argv[1])
out = {"exists": [os.path.lexists(p) for p in a["paths"]], "free_gb": None, "linked": []}
for p in a["paths"]:
    q = p
    while q != "/" and not os.path.isdir(q): q = os.path.dirname(q)
    s = os.statvfs(q)
    out["free_gb"] = int(s.f_bavail * s.f_frsize / 2**30)
    c = q
    while c.startswith("/srv/") and c.count("/") > 3:       # an ancestor link must stay on the scratch disks
        if os.path.islink(c) and not os.path.realpath(c).startswith("/srv/opentallas-scratch"):
            out["linked"].append([c, os.path.realpath(c)])
        c = os.path.dirname(c)
if a.get("lst"):
    lines, skip = [], set(a.get("skip") or ())
    for p in a["paths"]:
        if not os.path.isdir(p): continue
        for r, ds, fs in os.walk(p):
            for f in fs:
                qq = os.path.join(r, f); rel = os.path.relpath(qq, p)
                if os.path.islink(qq) or (os.path.basename(p) + "/" + rel) in skip: continue
                lines.append("%s/%s %d" % (os.path.basename(p), rel, os.lstat(qq).st_size))
    lines.sort(); out["lst"] = hashlib.md5("\n".join(lines).encode()).hexdigest(); out["files"] = len(lines)
print("AP_JSON " + json.dumps(out))
'''

SSH = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ControlPath=none"]
RSYNC_E = "ssh -o BatchMode=yes -o ControlPath=none"


class Ops:
    """every side effect of a move (tests replace it)"""

    def __init__(self, AP):
        self.AP = AP

    def host(self, h):
        return self.AP.ssh_host(h)

    def ps(self, h):
        rc, out, _ = self.AP.sh(SSH + [self.host(h), "ps -eo pid=,ppid=,etimes=,args="], timeout=60)
        return out if rc == 0 else None

    def py(self, h, code, args, timeout=600):
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-o", "ControlPath=none", self.host(h),
               "python3", "-I", "-", shlex.quote(json.dumps(args))]
        rc, out, err = self.AP.sh(cmd, timeout=timeout, input=code)
        for line in reversed(out.splitlines()):
            if line.startswith("AP_JSON "):
                return json.loads(line[8:])
        return {"error": f"probe rc {rc}: {(err or out).strip()[-300:]}"}

    def copy(self, src, dst, roots):
        """rsync from the source host to the same absolute path on dst -> (rc, text)"""
        q = shlex.quote
        parts = []
        for r in roots:
            r = r.rstrip("/")
            parts.append(f"ssh -n -o BatchMode=yes -o ControlPath=none {q(dst)} mkdir -p {q(os.path.dirname(r))}")
            parts.append(f"if [ -d {q(r)} ]; then rsync -aH --copy-unsafe-links -e {q(RSYNC_E)} {q(r)}/ {q(dst)}:{q(r)}/; "
                         f"else rsync -aH -e {q(RSYNC_E)} {q(r)} {q(dst)}:{q(r)}; fi")
        rc, out, err = self.AP.sh(SSH + [self.host(src), "set -e; " + "; ".join(parts)], timeout=3600)
        return rc, (out + err)[-600:]

    def verify(self, src, dst, roots):
        """checksum itemize from the source to the target -> differing items (empty = identical)"""
        q, diffs = shlex.quote, []
        for r in roots:
            r = r.rstrip("/")
            # a directory root is checked with a trailing slash; the runner file as is
            cmd = (f"if [ -d {q(r)} ]; then rsync -aHnci --copy-unsafe-links --delete -e {q(RSYNC_E)} {q(r)}/ {q(dst)}:{q(r)}/; "
                   f"else rsync -aHnci -e {q(RSYNC_E)} {q(r)} {q(dst)}:{q(r)}; fi")
            rc, out, err = self.AP.sh(SSH + [self.host(src), cmd], timeout=1800)
            if rc != 0:
                diffs.append(f"rsync verify rc {rc}: {(err or out).strip()[-160:]}")
            diffs += [ln for ln in out.splitlines() if ln and (ln[0] in "<>c*" or ln.startswith("deleting"))]
        return diffs

    def stop_unit(self, unit):
        return self.AP.sh(["systemctl", "--user", "stop", unit], timeout=180)[0]

    def kill(self, h, pids):
        if not pids:
            return 0
        return self.AP.sh(SSH + [self.host(h), "kill -TERM " + " ".join(str(int(p)) for p in pids) + " 2>/dev/null; true"],
                          timeout=60)[0]

    def client_argv(self, pid):
        try:
            return [w for w in Path(f"/proc/{int(pid)}/cmdline").read_bytes().decode(errors="replace").split("\0") if w]
        except (OSError, ValueError):
            return []

    def client_unit_ok(self, pid, unit):
        try:
            return f"{unit}.service" in Path(f"/proc/{int(pid)}/cgroup").read_text()
        except (OSError, ValueError):
            return False

    def launch(self, unit, logf, argv):
        return self.AP.launch_unit(unit, logf, argv)


# ----------------------------------------------------------------------------------------------- candidates
def job_roots(j):
    roots = [j["path"].rstrip("/")]
    r = j.get("runner") or ""
    if r and r != j["path"] and not r.startswith(j["path"].rstrip("/") + "/"):
        roots.append(r)
    return roots


def candidates(AP, st, ops, status, hub_node, cfg):
    """RUNNING KIT-WAVE jobs whose ot-run waiter still WAITS (not started) on the job's home host, on a hot host"""
    hot = {h for h, v in (status or {}).items() if int(v.get("wait_n", 0)) > int(cfg.get("waiter_max", WAITER_MAX))}
    out, ps_cache = [], {}
    for j in st["jobs"].values():
        if not (j.get("status") == "RUNNING" and j.get("unit") and j.get("path") and j.get("host") and not j.get("evac")
                and str(j.get("lane", "")).startswith("KIT-WAVE")):
            continue
        h = AP.ssh_host(j["host"])
        if h not in hot:
            continue
        if h not in ps_cache:
            ps_cache[h] = parse_waiters(ops.ps(h), hub_node)
        ws = [w for w in ps_cache[h] if not w["started"] and w["dir"].rstrip("/") == j["path"].rstrip("/")
              and ops.client_unit_ok(w["client_pid"], j["unit"])]
        if not ws:
            continue
        w = max(ws, key=lambda x: x["age_s"])
        out.append({"id": j["id"], "die": j.get("die"), "type": j.get("type"), "unit": j["unit"], "host": h,
                    "path": j["path"].rstrip("/"), "mem": int(j.get("mem_gb") or w["mem"]),
                    "threads": int(j.get("threads") or 8), "age_s": w["age_s"], "waiter": w, "kit_gb": 0.0, "job": j,
                    "hub_node": hub_node})
    return out


# ----------------------------------------------------------------------------------------------- apply
def move_one(AP, st, ops, move, log):
    """copy, verify, stop the unstarted waiter, resubmit pinned -> (ok, note).  Every failure before the stop leaves the
    job exactly as it was."""
    c, t = move["cand"], move["to"]
    j, src, w = c["job"], c["host"], c["waiter"]
    roots = job_roots(j)
    pr = ops.py(src, SRC_PROBE, {"roots": roots})
    if pr.get("error"):
        return False, "source probe: " + pr["error"]
    gb = pr["bytes"] / 2**30
    dp = ops.py(t, DST_PROBE, {"paths": roots})
    if dp.get("error"):
        return False, "target probe: " + dp["error"]
    if any(dp["exists"]):
        return False, "target path exists"
    if dp["linked"]:
        return False, f"target ancestor links out of the scratch layout: {dp['linked'][:2]}"
    if dp["free_gb"] is None or dp["free_gb"] < gb + DISK_MARGIN_GB:
        return False, f"target free {dp['free_gb']} GB < {gb:.1f} + {DISK_MARGIN_GB}"
    rc, txt = ops.copy(src, t, roots)
    if rc:
        return False, "copy rc %d: %s" % (rc, txt[-200:])
    diffs = ops.verify(src, t, roots)
    dq = ops.py(t, DST_PROBE, {"paths": roots, "lst": True, "skip": pr.get("skip")})
    if diffs or dq.get("lst") != pr.get("lst") or dq.get("files") != pr.get("files"):
        return False, "verify failed: %s lst %s/%s files %s/%s" % (diffs[:3], dq.get("lst"), pr.get("lst"),
                                                                    dq.get("files"), pr.get("files"))
    cur = [x for x in parse_waiters(ops.ps(src), c["hub_node"]) if x["tag"] == w["tag"]]
    if not cur or cur[0]["started"]:
        return False, "waiter started or gone before the stop (verified copy kept on %s)" % t
    argv = ops.client_argv(w["client_pid"])
    if not argv or "--dir" not in argv:
        return False, "client argv unreadable"
    new_argv = with_hosts(argv, t)
    ops.stop_unit(c["unit"])
    after = [x for x in parse_waiters(ops.ps(src), c["hub_node"]) if x["tag"] == w["tag"]]
    if after and after[0]["started"]:
        # admitted in the instant before the stop: the command runs on, the autopilot watches its kit logs (ORPHAN path)
        return False, "waiter admitted during the stop; left running on %s" % src
    pids = sorted(set(after[0]["heavy"] + [after[0]["wrapper"]])) if after else []
    ops.kill(src, pids)                     # exact PIDs of this waiter's tag, only if its client's cancel left it behind
    n = int(j.get("attempts") or 1)
    k = len(j.get("wave_balance") or []) + 1
    logf = Path(AP.AP_DIR) / "jobs" / j["id"] / f"a{n}-wb{k}.log"
    if not ops.launch(c["unit"], logf, new_argv):
        return False, "relaunch of %s failed" % c["unit"]
    rec = {"t": time.time(), "from": src, "to": t, "gb": round(gb, 2), "tag": w["tag"], "killed_pids": pids,
           "old_log": j.get("client_log"), "unit": c["unit"], "waited_s": c["age_s"]}
    j.setdefault("wave_balance", []).append(rec)
    j.update(host=t, kit=f"{t}:{j['path']}", client_log=str(logf), started=time.time(), moved_from=src)
    j.pop("probe", None)
    AP.set_status(st, j, "RUNNING", f"WAVE-BALANCE {src} -> {t} ({gb:.1f} GB, waited {c['age_s']} s)")
    try:
        (Path(AP.AP_DIR) / "jobs" / j["id"] / "wave_balance.json").write_text(json.dumps(j["wave_balance"], indent=1))
    except OSError:
        pass
    log(f"WAVE-BALANCE {j['id']} {j.get('die')}/{j.get('type')}: {src} -> {t} {gb:.1f} GB, waited {c['age_s']} s, "
        f"killed pids {pids}, unit {c['unit']} resubmitted --hosts {t}")
    return True, "moved"


def run(AP, st, apply=False, cfg=None, ops=None):
    cfg = cfg if cfg is not None else load_cfg(AP)
    ops = ops or Ops(AP)
    rc, txt, _ = AP.sh([AP.OT_RUN, "--status"], timeout=120)
    if rc:
        return [], []
    status = AP.KW.parse_otrun_status(txt)
    cands = candidates(AP, st, ops, status, os.uname().nodename, cfg)
    for c in cands:
        pr = ops.py(c["host"], SRC_PROBE, {"roots": job_roots(c["job"])})
        c["kit_gb"] = (pr.get("bytes", 0) / 2**30) if not pr.get("error") else 1e9
    moves, skipped = plan_moves(cands, status, cfg, hub_names=(AP.HUB_NAME,) + tuple(AP.HUB_ALIASES.get(AP.HUB_NAME, ())))
    done = []
    for m in moves:
        if apply:
            ok, note = move_one(AP, st, ops, m, AP.log)
            done.append((m, ok, note))
        else:
            done.append((m, None, "dry-run"))
    return done, skipped


def load_cfg(AP):
    try:
        return dict(json.loads((Path(AP.AP_DIR) / "kit_wave.json").read_text()).get("wave_balance") or {})
    except (OSError, ValueError, AttributeError):
        return {}


def step(AP, st):
    """autopilot.tick hook: inert unless kit_wave.json wave_balance.enabled is true -> number of jobs moved"""
    cfg = load_cfg(AP)
    if not cfg.get("enabled"):
        return 0
    done, _ = run(AP, st, apply=not AP.DRY, cfg=cfg)
    return sum(1 for _, ok, _ in done if ok)


def table(done, skipped):
    lines = ["id\tdie/type\twaited_s\tmem_GB\tfrom\tto\tkit_GB\tresult"]
    for m, ok, note in done:
        c = m["cand"]
        lines.append(f"{c['id']}\t{c['die']}/{c['type']}\t{c['age_s']}\t{c['mem']}\t{c['host']}\t{m['to']}\t"
                     f"{c['kit_gb']:.1f}\t{'MOVED' if ok is True else ('WOULD-MOVE' if ok is None else 'FAILED ' + note)}")
    for c, why in skipped:
        lines.append(f"{c['id']}\t{c['die']}/{c['type']}\t{c['age_s']}\t{c['mem']}\t{c['host']}\t-\t{c['kit_gb']:.1f}\tSKIP {why}")
    return "\n".join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--apply", action="store_true", help="really move (default: dry run, prints the table)")
    a = ap.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import autopilot as AP                              # noqa: E402
    AP.DRY = not a.apply
    done, skipped = run(AP, AP.load_state(), apply=a.apply)
    print(table(done, skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
