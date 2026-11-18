#!/usr/bin/env python3
"""stage_odb_cap: bound the stage-ODB checkpoints a running kit leaves behind (FLEET-OPS-R, FABLE-FLOW-2200; COORD rule 11-17).
A route kit at S81 slice scale writes about 19 GB of stage ODBs, 8 GB of them identical-size final stages (5_3_fillcell, 5_route, 6_1_fill, 6_final).
Rule, applied to NEW stage writes only (a watcher inside the kit; never a sweep of old results):
  KEPT always: 1_synth, the step boundaries kit_resume reads (2_floorplan, 3_place, 4_cts, 5_1_grt = the diagnosis anchors post-CTS / GRT), 5_2_route (the late-ECO seed) and the latest final (6_final.odb, .def, .spef, .v).
  DELETED once the SUCCESSOR stage is written, non-empty, older than MIN_AGE_S and nothing has the file open:
    2_[1-4]_*.odb after 2_floorplan.odb | 3_[1-5]_*.odb after 3_place.odb | 4_1_cts.odb after 4_cts.odb |
    5_3_fillcell.odb after 5_route.odb | 5_route.odb and 6_1_fill.odb after 6_final.odb (+ 6_final.v).
  SKIPPED: OT_KEEP_STAGE_ODBS=1 (ECO / debug lanes), a .keep_stage_odbs file in the kit, a file any process has open, a kit while an ECO / resume process
  has its directory as cwd or open file.  Every deletion is logged (name, size) to stderr; nothing outside <base>/<stage>.odb names is touched.
usage: stage_odb_cap.py --watch RESULTS_ROOT [--kit DIR] [--interval 60] [--max-hours 36]      (RESULTS_ROOT = <kit>/run/results/asap7)
       stage_odb_cap.py --once BASE_DIR                                                           (one pass, prints what it would delete with --dry)"""
import argparse, glob, gzip, os, re, shutil, sys, time

MIN_AGE_S = 120
RULES = (  # (regex of the victim, successor file that must exist)
    (re.compile(r"^2_[1-4]_.*\.odb$"), "2_floorplan.odb"),
    (re.compile(r"^3_[1-5]_.*\.odb$"), "3_place.odb"),
    (re.compile(r"^4_1_cts\.odb$"), "4_cts.odb"),
    # LATE-ECO 11-18 (COORD: 11 of 12 late ECOs died in prd_mk.sh "lacks 5_2_route.odb"): 5_2_route.odb is the route-keeping ECO seed
    # (prd_mk OT_PRD_FROM=route, eco_loop's default for R-MINIMAL near misses) and is KEPT like the other step anchors.
    (re.compile(r"^5_3_fillcell\.odb$"), "5_route.odb"),
    (re.compile(r"^5_route\.odb$"), "6_final.odb"),
    (re.compile(r"^6_1_fill\.odb$"), "6_final.odb"),
)
EXTRA_SUCCESSOR = {"5_route.odb": "6_final.v", "6_1_fill.odb": "6_final.v"}
FINISH = ("5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb")      # the finish stages write byte-identical ODBs (KIT-SLIM-1118)
LOG_GZ_BYTES = 100 << 20
LOG_TAIL_BYTES = 20 << 20
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


def _same(a, b, chunk=8 << 20):
    with open(a, "rb") as fa, open(b, "rb") as fb:
        while True:
            x, y = fa.read(chunk), fb.read(chunk)
            if x != y:
                return False
            if not x:
                return True


def link_dups(base, now=None, open_files=(), min_age=MIN_AGE_S):
    """KIT-SLIM-1118 (COORD): right after a finish stage wrote its ODB, the previous finish-stage ODB with the same bytes becomes a hardlink of it
    (5_3_fillcell -> 5_route -> 6_1_fill -> 6_final, each name kept, no space).  Only files older than min_age, not open, not already one inode.
    -> [(path, size)] linked"""
    now = now or time.time()
    got = []
    have = []
    for n in FINISH:
        p = os.path.join(base, n)
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if st.st_size > 0 and not os.path.islink(p) and p not in open_files and now - st.st_mtime >= min_age:
            have.append((p, st))
    for (pa, sa), (pb, sb) in zip(have, have[1:]):          # older stage a, newer stage b: a becomes a link of b
        if sa.st_size != sb.st_size or (sa.st_dev, sa.st_ino) == (sb.st_dev, sb.st_ino):
            continue
        try:
            if not _same(pa, pb):
                continue
            tmp = pa + ".kslink"
            os.link(pb, tmp)
            os.replace(tmp, pa)
            got.append((pa, sa.st_size if sa.st_nlink == 1 else 0))
        except OSError:
            try:
                os.unlink(pa + ".kslink")
            except OSError:
                pass
    return got


def gzip_logs(kit, now=None, open_files=(), min_age=MIN_AGE_S, big=None, tail=None):
    """KIT-SLIM-1118 (COORD): a run_*.log over 100 MB whose stage has ended (not open, quiet for min_age) is gzipped whole to run_*.log.gz; the log itself
    keeps its last 20 MB behind a one-line pointer, so the failure classifier / tail readers still see the end.  -> [(path, bytes saved)]"""
    now = now or time.time()
    big = LOG_GZ_BYTES if big is None else big
    tail = LOG_TAIL_BYTES if tail is None else tail
    out = []
    for p in glob.glob(os.path.join(kit, "**", "run_*.log"), recursive=True):
        try:
            st = os.lstat(p)
        except OSError:
            continue
        if st.st_size <= big or os.path.islink(p) or p in open_files or now - st.st_mtime < min_age or os.path.exists(p + ".gz"):
            continue
        try:
            with open(p, "rb") as f, gzip.open(p + ".gz.tmp", "wb", 3) as g:
                shutil.copyfileobj(f, g, 1 << 20)
            with open(p, "rb") as f:
                f.seek(max(0, st.st_size - tail))
                data = f.read()
            if os.stat(p).st_mtime != st.st_mtime:               # written meanwhile: leave it
                os.unlink(p + ".gz.tmp"); continue
            with open(p + ".new", "wb") as f:
                f.write(("[KIT-SLIM: head gzipped in %s; last %d MB below]\n" % (os.path.basename(p) + ".gz", tail >> 20)).encode() + data)
            os.replace(p + ".gz.tmp", p + ".gz")
            os.replace(p + ".new", p)
            out.append((p, st.st_size - os.path.getsize(p)))
        except OSError:
            for x in (p + ".gz.tmp", p + ".new"):
                try:
                    os.unlink(x)
                except OSError:
                    pass
    return out


def once(base, kit=None, dry=False, now=None, log=print, scan=open_procs, alive=lambda: True):
    why = kept_by_env(kit or base)
    if why:
        return []
    files, busy = scan(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(base)))) if kit is None else kit)
    if busy:
        log("STAGE-CAP skip %s: eco/resume process active: %s" % (base, busy[0]))
        return []
    done = []
    for p, size in plan(base, now, files):
        if not alive():      # the kit's run_kit.sh has ended: the job's publish may be walking this tree, never delete under it
            log("STAGE-CAP parent gone: no more deletions"); break
        if dry:
            log("STAGE-CAP would delete %s %d" % (p, size)); done.append((p, size)); continue
        try:
            os.unlink(p); done.append((p, size)); log("STAGE-CAP deleted %s %d" % (p, size))
        except OSError as e:
            log("STAGE-CAP keep %s: %s" % (p, e))
    if not dry:       # what the deletion rules do not remove yet (successor still being written): identical finish ODBs share one inode meanwhile
        for p, size in link_dups(base, now, files):
            log("STAGE-CAP linked %s (%d bytes shared)" % (p, size))
    return done


def parent_alive(pid):
    """True while pid (the run_kit.sh that started this watcher) is running; None = no parent given"""
    if not pid:
        return True
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def watch(root, kit, interval, max_hours, log=print, parent=None):
    t0 = time.time()
    while time.time() - t0 < max_hours * 3600:
        if not parent_alive(parent):
            log("STAGE-CAP parent %s gone: watcher ends without deleting (the job's publish walks the tree)" % parent)
            return
        for base in glob.glob(os.path.join(root, "*", "base")):
            once(base, kit, False, log=log, alive=lambda: parent_alive(parent))
            if kit:
                for p, n in gzip_logs(kit, open_files=open_procs(kit)[0]):
                    log("STAGE-CAP gzipped %s (-%d bytes)" % (p, n))
            # finished: the final is old and everything beyond it is gone -> nothing more to do for this kit
        time.sleep(interval)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--watch"); ap.add_argument("--once"); ap.add_argument("--kit"); ap.add_argument("--interval", type=float, default=60)
    ap.add_argument("--max-hours", type=float, default=36); ap.add_argument("--dry", action="store_true")
    ap.add_argument("--parent", type=int, default=0, help="pid of the run_kit.sh that started this watcher: the watcher stops deleting when it ends")
    a = ap.parse_args(argv)
    lg = lambda m: print(time.strftime("%F %T"), m, file=sys.stderr, flush=True)
    if a.once:
        once(a.once, a.kit, a.dry, log=lg)
    elif a.watch:
        watch(a.watch, a.kit, a.interval, a.max_hours, lg, a.parent)
    else:
        ap.error("--watch or --once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
