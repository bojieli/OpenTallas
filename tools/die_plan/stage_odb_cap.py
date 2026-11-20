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
# FLOW-FIX-2045 (COORD, FABLE-PD-HEAD-2040): make lists 2_1..2_4, 3_1..3_5 and 4_1_cts as prerequisites of the boundary files, so a make that starts after the watcher deleted
# them rebuilds the chain from floorplan (the wave route job re-ran floorplan + place in 223 of 223 route logs on 11-19; the hd_tile private proofs re-ran CTS in an FF-only session and skipped the
# TT setup repair and the hold gate).  The early-stage rules therefore run only for a run that has ended (once(ended=True) / --ended, called by a reaper on a dead kit), never from the live watcher.
EARLY_RULES = (
    (re.compile(r"^2_[1-4]_.*\.odb$"), "2_floorplan.odb"),
    (re.compile(r"^3_[1-5]_.*\.odb$"), "3_place.odb"),
    (re.compile(r"^4_1_cts\.odb$"), "4_cts.odb"),
)
RULES = (  # (regex of the victim, successor file that must exist)
    # LATE-ECO 11-18 (COORD: 11 of 12 late ECOs died in prd_mk.sh "lacks 5_2_route.odb"): 5_2_route.odb is the route-keeping ECO seed
    # (prd_mk OT_PRD_FROM=route, eco_loop's default for R-MINIMAL near misses) and is KEPT like the other step anchors.
    (re.compile(r"^5_3_fillcell\.odb$"), "5_route.odb"),
    (re.compile(r"^5_route\.odb$"), "6_final.odb"),
    (re.compile(r"^6_1_fill\.odb$"), "6_final.odb"),
)
BOUNDARIES = ("2_floorplan.odb", "3_place.odb", "4_cts.odb", "5_1_grt.odb")
EXTRA_SUCCESSOR = {"5_route.odb": "6_final.v", "6_1_fill.odb": "6_final.v"}
FINISH = ("5_3_fillcell.odb", "5_route.odb", "6_1_fill.odb", "6_final.odb")      # the finish stages write byte-identical ODBs (KIT-SLIM-1118)
LOG_GZ_BYTES = 100 << 20
LOG_TAIL_BYTES = 20 << 20
# FLOW-FIX-2045: the pattern was `eco|...` as a SUBSTRING: the docker command line of every live kit carries run_kit.sh text ("... recorded in lec/lec.json ...", "r-ECO-rded"), so every live kit
# counted as an ECO / resume process and its watcher skipped every pass (STAGE-CAP skip ... eco/resume process active) for the whole run.  ECO as a word only (eco, eco_loop, ECO_x).
BUSY_CMD = re.compile(r"(?<![A-Za-z])eco(?![A-Za-z])|kit_resume|resume\.json", re.I)


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


def plan(base, now=None, open_files=(), min_age=MIN_AGE_S, ended=False):
    """-> [(path, size)] the deletable stage ODBs of one results base dir (pure: files given in open_files are skipped).  ended: the run is over, the early-stage rules apply too"""
    rules = EARLY_RULES + RULES       # FLOW-FIX-2045: early-stage victims are zero-byte placeholders while the run lives (once()), deleted only for an ended run
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
        for rx, succ in rules:
            if not rx.match(n):
                continue
            if succ in names and ok(succ) and (EXTRA_SUCCESSOR.get(n) is None or ok(EXTRA_SUCCESSOR[n])):
                p = os.path.join(base, n)
                try:
                    st = os.lstat(p)
                except OSError:
                    break
                if st.st_size > 0 and st.st_nlink == 1 and not os.path.islink(p) and p not in open_files and now - st.st_mtime >= min_age:      # a zero-byte file is a placeholder already
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


def capped_missing(kit):
    """FLOW-FIX-2045: names of the early-stage ODBs this kit's STAGE-CAP log says it deleted (older watchers) that are absent from every results base of the kit now.
    -> sorted [name]"""
    names = set()
    try:
        for ln in open(os.path.join(kit, "stage_odb_cap.log"), errors="replace"):
            m = re.search(r"STAGE-CAP deleted \S*/([^/\s]+\.odb) \d+", ln)
            if m and any(rx.match(m.group(1)) for rx, _ in EARLY_RULES):
                names.add(m.group(1))
    except OSError:
        return []
    bases = glob.glob(os.path.join(kit, "run", "results", "asap7", "*", "base"))
    return sorted(n for n in names if bases and not any(os.path.exists(os.path.join(b, n)) for b in bases))


def guard(kit, need="4_cts.odb", log=print):
    """FLOW-FIX-2045 (item 2): the next make would silently rebuild the chain from floorplan.  Returns 0 when nothing the make needs is missing; 13 (loud) when an early-stage ODB the cap
    deleted is missing while a boundary file >= need exists (the rebuild would run in a new corner session and skip the CTS-to-GRT steps of the flow); 0 with a STAGE-ODB-REBUILD line when only
    earlier boundaries exist (a place-then-route kit: the rebuild is slow but the whole flow runs).  OT_ALLOW_STAGE_REBUILD=1 lets it through."""
    miss = capped_missing(kit)
    if not miss:
        return 0
    bases = glob.glob(os.path.join(kit, "run", "results", "asap7", "*", "base"))
    order = BOUNDARIES.index(need) if need in BOUNDARIES else 2
    late = [b for b in BOUNDARIES[order:] if any(os.path.getsize(os.path.join(x, b)) > 0 for x in bases if os.path.exists(os.path.join(x, b)))]
    if not late:
        log("STAGE-ODB-REBUILD %d early-stage ODB(s) deleted by STAGE-CAP are missing (%s ...): make re-runs floorplan / place in this run (set .keep_stage_odbs in the kit to stop the cap)" % (len(miss), ", ".join(miss[:3])))
        return 0
    if os.environ.get("OT_ALLOW_STAGE_REBUILD") == "1":
        log("STAGE-ODB-REBUILD allowed (OT_ALLOW_STAGE_REBUILD=1): %s" % ", ".join(miss[:4]))
        return 0
    log("FAIL_STAGE_ODB_MISSING %s exists but %d early-stage ODB(s) STAGE-CAP deleted are missing (%s): the next make would rebuild floorplan, place and CTS in a fresh session and skip the "
        "TT setup repair / hold gate; refusing. Re-run from the place job on a kit with .keep_stage_odbs, or OT_ALLOW_STAGE_REBUILD=1 to rebuild on purpose" % (late[0], len(miss), ", ".join(miss[:4])))
    return 13


def placeholder(path):
    """FLOW-FIX-2045: empty the file in place and give it back its mtime (and atime): make still finds the prerequisite present and not newer than its target, so no later make
    re-runs the stage, while the 0.4-0.6 GB per ODB are freed.  Only a file with one link (the caller checked): truncating a hardlink would empty its twin."""
    st = os.stat(path)
    with open(path, "r+b") as f:
        f.truncate(0)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))


def is_early(name):
    return any(rx.match(name) for rx, _ in EARLY_RULES)


def once(base, kit=None, dry=False, now=None, log=print, scan=open_procs, alive=lambda: True, ended=False):
    why = kept_by_env(kit or base)
    if why:
        return []
    files, busy = scan(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(base)))) if kit is None else kit)
    if busy:
        log("STAGE-CAP skip %s: eco/resume process active: %s" % (base, busy[0]))
        return []
    done = []
    for p, size in plan(base, now, files, ended=ended):
        if not alive():      # the kit's run_kit.sh has ended: the job's publish may be walking this tree, never delete under it
            log("STAGE-CAP parent gone: no more deletions"); break
        keep_name = is_early(os.path.basename(p)) and not ended       # a live run: a make prerequisite stays as an empty placeholder with its old mtime
        if dry:
            log("STAGE-CAP would %s %s %d" % ("placeholder" if keep_name else "delete", p, size)); done.append((p, size)); continue
        try:
            if keep_name:
                placeholder(p); done.append((p, size)); log("STAGE-CAP placeholder %s %d" % (p, size))
            else:
                os.unlink(p); done.append((p, size)); log("STAGE-CAP deleted %s %d" % (p, size))
        except OSError as e:
            log("STAGE-CAP keep %s: %s" % (p, e))
    if not dry:       # what the deletion rules do not remove yet (successor still being written): identical finish ODBs share one inode meanwhile
        for p, size in link_dups(base, now, files):
            log("STAGE-CAP linked %s (%d bytes shared)" % (p, size))
    return done


def replace_watchers(log=print, dry=False):
    """FLOW-FIX-2045: ship this script into the watchers of kits that are running now.  For every process `python3 -I <kit>/stage_odb_cap.py --watch ROOT --kit K ... --parent P` on this host:
    refresh <kit>/stage_odb_cap.py from this file (copy then mv: a new inode), start a new watcher with the same arguments, then stop the old one (exact pid; it only watches).  -> [(old pid, new pid)]"""
    me = os.path.abspath(__file__)
    src = open(me, "rb").read()
    out = []
    for p in glob.glob("/proc/[0-9]*"):
        try:
            av = open(p + "/cmdline", "rb").read().decode("utf-8", "replace").split("\0")
        except OSError:
            continue
        av = [a for a in av if a != ""]
        if len(av) < 5 or not av[0].endswith("python3") or "--watch" not in av or not av[2].endswith("/stage_odb_cap.py") or av[1] != "-I":
            continue
        script, pid = av[2], int(p[6:])
        if os.path.abspath(script) == me:
            continue
        if dry:
            log("WATCHER would replace pid %d %s" % (pid, script)); out.append((pid, 0)); continue
        try:
            new = script + ".new"
            with open(new, "wb") as f:
                f.write(src)
            os.chmod(new, os.stat(script).st_mode & 0o7777)
            os.replace(new, script)
            import subprocess
            kitdir = os.path.dirname(script)
            lf = open(os.path.join(kitdir, "stage_odb_cap.log"), "a")
            np = subprocess.Popen(["python3", "-I", script] + av[3:], stdout=lf, stderr=lf, stdin=subprocess.DEVNULL, start_new_session=True, cwd=kitdir)
            os.kill(pid, 15)
            out.append((pid, np.pid)); log("WATCHER replaced pid %d -> %d %s" % (pid, np.pid, script))
        except OSError as e:
            log("WATCHER keep pid %d: %s" % (pid, e))
    return out


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
    ap.add_argument("--replace-watchers", action="store_true", help="restart the watchers of running kits on this host with this script (FLOW-FIX-2045)")
    ap.add_argument("--ended", action="store_true", help="the kit's run is over: the early-stage ODBs (2_x, 3_x, 4_1) may go too (never from a live watcher)")
    ap.add_argument("--guard", metavar="KIT", help="exit 13 when the next make would rebuild from floorplan after STAGE-CAP deleted early-stage ODBs (see guard())")
    ap.add_argument("--need", default="4_cts.odb"); ap.add_argument("--parent", type=int, default=0, help="pid of the run_kit.sh that started this watcher: the watcher stops deleting when it ends")
    a = ap.parse_args(argv)
    lg = lambda m: print(time.strftime("%F %T"), m, file=sys.stderr, flush=True)
    if a.replace_watchers:
        replace_watchers(lg, a.dry)
        return 0
    if a.guard:
        return guard(a.guard, a.need, lg)
    if a.once:
        once(a.once, a.kit, a.dry, log=lg, ended=a.ended)
    elif a.watch:
        watch(a.watch, a.kit, a.interval, a.max_hours, lg, a.parent)
    else:
        ap.error("--watch or --once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
