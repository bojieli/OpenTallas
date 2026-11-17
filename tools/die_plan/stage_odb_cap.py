#!/usr/bin/env python3
"""stage_odb_cap: bound the stage-ODB checkpoints a running kit leaves behind (FLEET-OPS-R, FABLE-FLOW-2200; COORD rule 11-17).
A route kit at S81 slice scale writes about 19 GB of stage ODBs, 8 GB of them identical-size final stages (5_3_fillcell, 5_route, 6_1_fill, 6_final).
Rule, applied to NEW stage writes only (a watcher inside the kit; never a sweep of old results):
  KEPT always: 1_synth, the step boundaries kit_resume reads (2_floorplan, 3_place, 4_cts, 5_1_grt = the diagnosis anchors post-CTS / GRT) and the latest final (6_final.odb, .def, .spef, .v).
  DELETED once the SUCCESSOR stage is written, non-empty, older than MIN_AGE_S and nothing has the file open:
    2_[1-4]_*.odb after 2_floorplan.odb | 3_[1-5]_*.odb after 3_place.odb | 4_1_cts.odb after 4_cts.odb |
    5_2_route.odb after 5_3_fillcell.odb | 5_3_fillcell.odb after 5_route.odb | 5_route.odb and 6_1_fill.odb after 6_final.odb (+ 6_final.v).
  SKIPPED: OT_KEEP_STAGE_ODBS=1 (ECO / debug lanes), a .keep_stage_odbs file in the kit, a file any process has open, a kit while an ECO / resume process
  has its directory as cwd or open file.  Every deletion is logged (name, size) to stderr; nothing outside <base>/<stage>.odb names is touched.
usage: stage_odb_cap.py --watch RESULTS_ROOT [--kit DIR] [--interval 60] [--max-hours 36]      (RESULTS_ROOT = <kit>/run/results/asap7)
       stage_odb_cap.py --once BASE_DIR                                                           (one pass, prints what it would delete with --dry)"""
import argparse, glob, os, re, sys, time

MIN_AGE_S = 120
RULES = (  # (regex of the victim, successor file that must exist)
    (re.compile(r"^2_[1-4]_.*\.odb$"), "2_floorplan.odb"),
    (re.compile(r"^3_[1-5]_.*\.odb$"), "3_place.odb"),
    (re.compile(r"^4_1_cts\.odb$"), "4_cts.odb"),
    (re.compile(r"^5_2_route\.odb$"), "5_3_fillcell.odb"),
    (re.compile(r"^5_3_fillcell\.odb$"), "5_route.odb"),
    (re.compile(r"^5_route\.odb$"), "6_final.odb"),
    (re.compile(r"^6_1_fill\.odb$"), "6_final.odb"),
)
EXTRA_SUCCESSOR = {"5_route.odb": "6_final.v", "6_1_fill.odb": "6_final.v"}
BUSY_CMD = re.compile(r"eco|kit_resume|resume\.json", re.I)


def open_procs(prefix):
    """-> (set of open file paths under prefix, [cmdline of processes with cwd under prefix that look like eco / resume])"""
    files, busy = set(), []
    me = os.getpid()
    for p in glob.glob("/proc/[0-9]*"):
        if int(p[6:]) == me:
            continue
        try:
            cwd = os.readlink(p + "/cwd")
        except OSError:
            cwd = ""
        try:
            for f in os.listdir(p + "/fd"):
                try:
                    t = os.readlink(p + "/fd/" + f)
                except OSError:
                    continue
                if t.startswith(prefix):
                    files.add(t)
        except OSError:
            pass
        if cwd.startswith(prefix):
            try:
                cmd = open(p + "/cmdline", "rb").read().replace(b"\0", b" ").decode("latin1")
            except OSError:
                cmd = ""
            if BUSY_CMD.search(cmd):
                busy.append(cmd[:120])
    return files, busy


def kept_by_env(kit):
    if os.environ.get("OT_KEEP_STAGE_ODBS") == "1":
        return "OT_KEEP_STAGE_ODBS=1"
    d = kit
    while d and d != "/":
        if os.path.exists(os.path.join(d, ".keep_stage_odbs")) or os.path.exists(os.path.join(d, ".keep")):
            return "keep file in " + d
        d = os.path.dirname(d)
    return ""


def plan(base, now=None, open_files=(), min_age=MIN_AGE_S):
    """-> [(path, size)] the deletable stage ODBs of one results base dir (pure: files given in open_files are skipped)"""
    now = now or time.time()
    out = []
    try:
        names = set(os.listdir(base))
    except OSError:
        return out
    def ok(n):
        try:
            st = os.stat(os.path.join(base, n))
        except OSError:
            return False
        return st.st_size > 0 and now - st.st_mtime >= min_age
    for n in sorted(names):
        for rx, succ in RULES:
            if not rx.match(n):
                continue
            if succ in names and ok(succ) and (EXTRA_SUCCESSOR.get(n) is None or ok(EXTRA_SUCCESSOR[n])):
                p = os.path.join(base, n)
                try:
                    st = os.lstat(p)
                except OSError:
                    break
                if st.st_nlink == 1 and not os.path.islink(p) and p not in open_files and now - st.st_mtime >= min_age:
                    out.append((p, st.st_size))
            break
    return out


def once(base, kit=None, dry=False, now=None, log=print, scan=open_procs):
    why = kept_by_env(kit or base)
    if why:
        return []
    files, busy = scan(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(base)))) if kit is None else kit)
    if busy:
        log("STAGE-CAP skip %s: eco/resume process active: %s" % (base, busy[0]))
        return []
    done = []
    for p, size in plan(base, now, files):
        if dry:
            log("STAGE-CAP would delete %s %d" % (p, size)); done.append((p, size)); continue
        try:
            os.unlink(p); done.append((p, size)); log("STAGE-CAP deleted %s %d" % (p, size))
        except OSError as e:
            log("STAGE-CAP keep %s: %s" % (p, e))
    return done


def watch(root, kit, interval, max_hours, log=print):
    t0 = time.time()
    while time.time() - t0 < max_hours * 3600:
        for base in glob.glob(os.path.join(root, "*", "base")):
            once(base, kit, False, log=log)
            # finished: the final is old and everything beyond it is gone -> nothing more to do for this kit
        time.sleep(interval)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--watch"); ap.add_argument("--once"); ap.add_argument("--kit"); ap.add_argument("--interval", type=float, default=60)
    ap.add_argument("--max-hours", type=float, default=36); ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    lg = lambda m: print(time.strftime("%F %T"), m, file=sys.stderr, flush=True)
    if a.once:
        once(a.once, a.kit, a.dry, log=lg)
    elif a.watch:
        watch(a.watch, a.kit, a.interval, a.max_hours, lg)
    else:
        ap.error("--watch or --once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
