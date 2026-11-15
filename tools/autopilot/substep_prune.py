#!/usr/bin/env python3
"""SUBSTEP-1 forward fix (COORD 11-05 10:53, PRUNE-1108 10:52 ASK, ruled YES as worded).

The wave tick removes, in TERMINAL kit-wave attempts only, the sub-step ODBs 2_[1-4]_*.odb and 3_[1-5]_*.odb that
nothing reads once the step boundary ODB (2_floorplan.odb / 3_place.odb) exists: kit_resume needs only STEP_OUT +
STEP_LOGS, run_kit resumes step-level from the previous boundary ODB (PRUNE-1108 10:52 RESULT, code read on main).

An attempt qualifies (hub side, candidates()) when its state row is FAIL or CANCELLED, or its queue verdict is
FAIL/CANCELLED/REJECTED, or it is not the newest attempt of its item (superseded), and it was last updated >= 6 h ago.
Per attempt dir, ON THE HOST (remote_main(), re-checked at removal):
  - skipped when the dir or any ancestor holds .keep; when the dir is, holds, or lies under a PROTECTED-DBS path
    of that host (union of lanes/PROTECTED-DBS.txt and the root PROTECTED-DBS.txt); when any signoff.json under it reads SIGNED, LOCAL_PASS or NEEDS_PARENT; when any file under it was
    modified < idle_h ago; when a running container mounts it (or a parent/child) or a process has its cwd there;
  - a file goes only if its name matches, st_nlink == 1, and the boundary ODB in the same dir exists, is non-empty
    and is not older than the file.
Everything else stays, latest attempts included.  Every removal is listed in <ap_dir>/kit_wave_substep_prune.tsv.
Die/global option substep_prune: false turns it off.
"""
import json
import os
import re
import sys
import time

IDLE_H = 6.0
MAX_DIRS_PER_TICK = 60
RECHECK_H = 2.0          # an attempt skipped as idle/live is looked at again after this long, so it cannot starve the rest
MANIFEST = "kit_wave_substep_prune.tsv"
SIGNED_RE = re.compile(r'"\w*(?:status|verdict|result)"\s*:\s*"(SIGNED|LOCAL_PASS\w*|NEEDS_PARENT)"')
SUB_RE = {"2": re.compile(r"^2_[1-4]_.*\.odb$"), "3": re.compile(r"^3_[1-5]_.*\.odb$")}
BOUNDARY = {"2": "2_floorplan.odb", "3": "3_place.odb"}
ATTEMPT_RE = re.compile(r"^(/srv/.*/kit-wave/.*/attempt_\d+)(?:/|$)")
TERMINAL_Q = ("FAIL", "CANCELLED", "REJECTED")
PERMANENT = ("keep", "protected", "signed", "missing")   # skip reasons that never change: not re-checked


def candidates(st, now=None, idle_h=IDLE_H):
    """-> [(key, host, dir)] terminal attempts, idle >= idle_h by state time, not pruned/skipped for good yet."""
    now = time.time() if now is None else now
    items = (st or {}).get("items") or {}
    newest = {}
    for r in items.values():
        k = (r.get("die"), r.get("event"), r.get("item"))
        try:
            newest[k] = max(newest.get(k, 0), int(r.get("attempt") or 0))
        except ValueError:
            pass
    out = []
    for key, r in items.items():
        if r.get("substep_pruned") or now - float(r.get("substep_checked") or 0) < RECHECK_H * 3600:
            continue
        try:
            att = int(r.get("attempt") or 0)
            upd = float(r.get("updated") or 0)
        except ValueError:
            continue
        terminal = (r.get("status") in ("FAIL", "CANCELLED") or r.get("q_status") in TERMINAL_Q
                    or att < newest.get((r.get("die"), r.get("event"), r.get("item")), 0))
        if not terminal or r.get("status") in ("RUNNING", "GEN", "PLACE") or now - upd < idle_h * 3600:
            continue
        ev = r.get("evidence") or ""
        host, sep, path = ev.partition(":")
        if not sep or not path.startswith("/srv/") or "/kit-wave/" not in path or "/attempt_" not in path:
            continue
        m = ATTEMPT_RE.match(path)              # evidence may name a file inside the attempt (geom/auto_geom.json)
        if m:
            out.append((key, host, m.group(1)))
    return out


PROTECTED_FILES = ("lanes/PROTECTED-DBS.txt", "PROTECTED-DBS.txt")   # the PROTECTED union (COORD 11-05 11:1x)


def protected_for(text, host):
    """PROTECTED-DBS rows of this host -> [path].  text may be several files joined; a row is host<sep>path[<sep>note],
    sep a TAB (lanes/ list), spaces or ':' (root list)."""
    out = []
    for ln in (text or "").splitlines():
        if ln.lstrip().startswith("#"):
            continue
        f = ln.split()
        if f and ":/" in f[0]:                  # root list also writes host:/path in one token
            f = f[0].split(":", 1) + f[1:]
        if len(f) >= 2 and f[0] == host and f[1].startswith("/"):
            out.append(f[1].rstrip("/"))
    return out


def _related(a, b):
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def live_paths():
    """-> (cwds, mounts): cwd of every readable process, every running container's mount sources (host side).
    None for mounts = docker unreadable: then everything counts as live and nothing is removed."""
    cwds = set()
    for p in os.listdir("/proc"):
        if p.isdigit():
            try:
                cwds.add(os.readlink(f"/proc/{p}/cwd"))
            except OSError:
                pass
    out = set()
    try:
        import subprocess
        ids = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60).stdout.split()
        if ids:
            fmt = "{{range .Mounts}}{{.Source}}\n{{end}}"
            r = subprocess.run(["docker", "inspect", "--format", fmt] + ids, capture_output=True, text=True, timeout=120)
            out |= {x.strip() for x in r.stdout.splitlines() if x.strip()}
    except Exception:
        return cwds, None
    return cwds, out


def is_live(d, live):
    """a process cwd at or under d; a container mount at, under, or above d inside a kit-wave tree."""
    cwds, mounts = live
    if mounts is None:
        return True
    if any(c == d or c.startswith(d + "/") for c in cwds):
        return True
    for m in mounts:
        m = m.rstrip("/")
        if m == d or m.startswith(d + "/") or (d.startswith(m + "/") and "/kit-wave/" in m + "/"):
            return True
    return False


def judge_dir(d, protected, live, now, idle_h=IDLE_H, dry=False):
    """-> (verdict, removed [(path, bytes)]).  verdict 'done' or 'skip:<why>'."""
    if not os.path.isdir(d):
        return "skip:missing", []
    a = d
    while a not in ("/", ""):
        if os.path.exists(os.path.join(a, ".keep")):
            return "skip:keep", []
        a = os.path.dirname(a)
    if any(_related(d, p) for p in protected):
        return "skip:protected", []
    if is_live(d, live) or is_live(os.path.realpath(d), live):
        return "skip:live", []
    subs, newest = [], 0.0
    for root, dirs, files in os.walk(d):
        if ".keep" in files:
            return "skip:keep", []
        for f in files:
            p = os.path.join(root, f)
            try:
                s = os.lstat(p)
            except OSError:
                continue
            newest = max(newest, s.st_mtime)
            if f == "signoff.json":
                try:
                    with open(p, errors="replace") as fh:
                        hit = SIGNED_RE.search(fh.read(1 << 20))
                    if hit:
                        return "skip:signed", []
                except OSError:
                    return "skip:signed", []      # unreadable sign-off: keep the attempt
            for step, rx in SUB_RE.items():
                if rx.match(f):
                    subs.append((p, step))
    if now - newest < idle_h * 3600:
        return "skip:idle", []
    removed = []
    for p, step in subs:
        b = os.path.join(os.path.dirname(p), BOUNDARY[step])
        try:
            s, bs = os.lstat(p), os.stat(b)
        except OSError:
            continue
        if not os.path.isfile(p) or os.path.islink(p) or s.st_nlink != 1 or bs.st_size <= 0 or bs.st_mtime < s.st_mtime:
            continue
        if not dry:
            try:
                os.unlink(p)
            except OSError:
                continue
        removed.append((p, s.st_size))
    return "done", removed


def remote_main(argv=None):
    """request JSON {dirs, protected, idle_h, dry} (module global _REQ when sent as a program, else stdin)
    -> stdout one JSON line per dir {dir, verdict, removed}."""
    req = globals().get("_REQ") or json.load(sys.stdin)
    live = (set(req["live"]), set()) if "live" in req else live_paths()   # "live": tests only (no docker)
    now = time.time()
    for d in req["dirs"]:
        v, rm = judge_dir(d, req.get("protected") or [], live, now, float(req.get("idle_h", IDLE_H)), bool(req.get("dry")))
        print(json.dumps({"dir": d, "verdict": v, "removed": rm}), flush=True)
    return 0


def tick(AP, cfg, st, ap_dir, ssh_argv, read_protected, _live=None):
    """hub side, once per wave tick.  ssh_argv(host) -> argv prefix ([] = local); read_protected(rel) -> text of a
    coord/state file; every file of PROTECTED_FILES must read non-empty, else nothing is removed this tick."""
    if cfg.get("substep_prune") is False:
        return
    # KW-FIX-44 11-10 (COORD): a terminated host (kit_wave.json retired_hosts: epyc5/epyc6 since 11-09) is never asked;
    # its rows were retried every tick ('Could not resolve hostname').  The rows themselves are left as they are.
    gone = set(cfg.get("retired_hosts") or [])
    cand = [c for c in candidates(st) if c[1] not in gone and ((cfg.get("dies") or {}).get(st["items"][c[0]].get("die"))
            or {}).get("substep_prune", True) is not False][:MAX_DIRS_PER_TICK]
    if not cand:
        return
    texts = {rel: read_protected(rel) or "" for rel in PROTECTED_FILES}
    empty = [rel for rel, t in texts.items() if not t.strip()]
    if empty:
        AP.log(f"KIT-WAVE SUBSTEP-1 skipped: {', '.join(empty)} unreadable or empty")
        return
    prot_txt = "\n".join(texts.values())
    with open(os.path.abspath(__file__)) as fh:
        code = fh.read()
    by_host = {}
    for key, host, d in cand:
        by_host.setdefault(host, []).append((key, d))
    man = os.path.join(str(ap_dir), MANIFEST)
    for host, rows in sorted(by_host.items()):
        req = json.dumps({"dirs": [d for _, d in rows], "protected": protected_for(prot_txt, host),
                          "idle_h": IDLE_H, "dry": bool(AP.DRY), **({"live": _live} if _live is not None else {})})
        # the module itself is the remote program, read by python3 -I - from stdin, with the request appended as _REQ
        tail = "\nif __name__ == \"__main__\":\n    sys.exit(remote_main())\n"
        assert code.endswith(tail), "substep_prune.py must end with its __main__ block"
        prog = code.replace("\nif __name__ == \"__main__\":\n    sys.exit(remote_main())\n", "\n") + \
            f"\n_REQ = json.loads({req!r})\nsys.exit(remote_main())\n"
        rc, out, err = AP.sh(ssh_argv(host) + ["python3", "-I", "-"], timeout=600, input=prog)
        if rc != 0:
            AP.log(f"KIT-WAVE SUBSTEP-1 {host}: rc {rc}: {(err or '').strip()[:160]}")
            continue
        res = {}
        for ln in (out or "").splitlines():
            try:
                j = json.loads(ln)
                res[j["dir"]] = j
            except (ValueError, KeyError):
                pass
        freed, nf = 0, 0
        lines = []
        for key, d in rows:
            j = res.get(d)
            if not j:
                continue
            v = j["verdict"]
            for p, b in j["removed"]:
                freed += b
                nf += 1
                lines.append(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\t{host}\t{p}\t{b}\t{st['items'][key].get('die')}"
                             f"\t{st['items'][key].get('item')}@{st['items'][key].get('attempt')}\n")
            if AP.DRY:
                continue
            if v == "done" or v.split(":", 1)[-1] in PERMANENT:
                st["items"][key]["substep_pruned"] = f"{v} {time.strftime('%m-%d %H:%M')}"
            else:
                st["items"][key]["substep_checked"] = time.time()
        if lines and not AP.DRY:
            with open(man, "a") as f:
                f.writelines(lines)
        if nf:
            AP.log(f"KIT-WAVE SUBSTEP-1 {host}: {nf} sub-step ODBs, {freed / 1e9:.1f} GB "
                   f"{'would be ' if AP.DRY else ''}removed in {len(rows)} terminal attempts ({MANIFEST})")


if __name__ == "__main__":
    sys.exit(remote_main())
