#!/usr/bin/env python3
"""kit_slim.py ROOT... [--apply] [--exported FILE] [--min-age-s N]   (KIT-SLIM-1118, OWNER: live kit builds took 2.2 TB on epyc10)

Measured on epyc10/epyc9/intel1 (10 attempt dirs each): per attempt 55-70% of the bytes were bind_sinks.json (2.36 GB, one fresh copy per attempt
under rtl/closure/bind), then the 4 byte-identical final ODBs (5_route/5_3_fillcell/6_1_fill/6_final), the 2_x/3_x sub-stage ODBs, the eco_* copy of
the results, and (rare) the 5 GB yosys native metadata JSON.  Four rules, each only on an attempt with no live process under it:
  1 sub-stage ODBs (2_1..2_4 once 2_floorplan.odb exists, 3_1..3_5 once 3_place.odb exists) are deleted;
  2 byte-identical big files (ODB/DEF/SPEF/lib >= 1 MB) inside one attempt become hardlinks of one inode (same names stay, atomic replace);
  3 1_2_yosys_native_metadata.json >= 64 MB is gzipped (nothing reads it back: only native_bb.py writes it);
  4 an attempt older than the newest attempt of the same item, or any attempt of an item named in the --exported ledger file, keeps only
    files < 8 MB and logs/reports (all heavy files go).
Every touched path first passes ot_delete_guard.refuse() (protected bind/src of record, live open file/cmdline); a refusal is a SKIP.  Default is a dry run.
Never rm -rf: single-file unlink after the guard, or os.replace for links/gzip."""
import filecmp, gzip, importlib.util, json, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))
MB = 1 << 20
SUB = {"2_floorplan.odb": ("2_1_floorplan.odb", "2_2_floorplan_macro.odb", "2_3_floorplan_tapcell.odb", "2_4_floorplan_pdn.odb"),
       "3_place.odb": ("3_1_place_gp_skip_io.odb", "3_2_place_iop.odb", "3_3_place_gp.odb", "3_4_place_resized.odb", "3_5_place_dp.odb")}
LINK_EXT = (".odb", ".def", ".spef", ".lib")
YOSYS_META = "1_2_yosys_native_metadata.json"
KEEP_EXT = (".log", ".rpt")
ATTEMPT = re.compile(r"^attempt_(\d+)$")


def load_guard():
    for c in (os.path.join(HERE, "ot_delete_guard.py"), os.environ.get("OT_DELETE_GUARD", "")):
        if c and os.path.isfile(c):
            sp = importlib.util.spec_from_file_location("ot_delete_guard", c)
            m = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(m)
            return m
    raise SystemExit("kit_slim: ot_delete_guard.py not found")


class Ctx:
    def __init__(self, apply=False, guard=None, protected=None, ptext=None, min_age=600, exported=(), now=None):
        self.apply, self.g, self.min_age, self.exported = apply, guard, min_age, set(exported)
        self.now = now or time.time()
        self.protected, self.ptext = protected, ptext
        self.freed = {}
        self.skipped = []

    def refused(self, path):
        if self.g is None:
            return None
        return self.g.refuse(path, self.protected, self.ptext) if self.protected is not None else self.g.refuse(path)

    def ok(self, path):
        why = self.refused(path)
        if why:
            self.skipped.append((path, why))
            return False
        return True

    def credit(self, cls, n):
        self.freed[cls] = self.freed.get(cls, 0) + n


def files(attempt):
    for dp, dns, fns in os.walk(attempt):
        for f in fns:
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if os.path.isfile(p) and not os.path.islink(p):
                yield p, st


def live(attempt, ctx):
    return ctx.ptext is not None and (attempt in ctx.ptext or attempt + "/" in ctx.ptext)


def unlink(p, st, cls, ctx):
    if not ctx.ok(p):
        return
    if ctx.apply:
        try:
            os.unlink(p)
        except OSError:
            return
    ctx.credit(cls, st.st_size if st.st_nlink == 1 else 0)


def rule_substage(attempt, fl, ctx):
    by = {}
    for p, st in fl:
        by.setdefault(os.path.dirname(p), {})[os.path.basename(p)] = (p, st)
    for d, names in by.items():
        for succ, subs in SUB.items():
            s = names.get(succ)
            if not s or s[1].st_size == 0:
                continue
            for n in subs:
                if n in names and names[n][1].st_mtime <= s[1].st_mtime:
                    unlink(names[n][0], names[n][1], "substage_odb", ctx)
                    names.pop(n)


def rule_hardlink(attempt, fl, ctx):
    groups = {}
    for p, st in fl:
        if p.endswith(LINK_EXT) and st.st_size >= MB:
            groups.setdefault(st.st_size, []).append((p, st))
    for lst in groups.values():
        lst.sort(key=lambda x: (-x[1].st_mtime, x[0]))
        masters = []
        for p, st in lst:
            for mp, mst in masters:
                if (mst.st_dev, mst.st_ino) == (st.st_dev, st.st_ino):
                    break
                if p.rsplit(".", 1)[-1] == mp.rsplit(".", 1)[-1] and filecmp.cmp(mp, p, shallow=False):
                    if ctx.ok(p):
                        if ctx.apply:
                            tmp = p + ".kslim"
                            try:
                                os.link(mp, tmp)
                                os.replace(tmp, p)
                            except OSError:
                                try:
                                    os.unlink(tmp)
                                except OSError:
                                    pass
                                break
                        ctx.credit("dup_hardlink", st.st_size if st.st_nlink == 1 else 0)
                    break
            else:
                masters.append((p, st))


def rule_yosys_meta(attempt, fl, ctx):
    for p, st in fl:
        if os.path.basename(p) == YOSYS_META and st.st_size >= 64 * MB and ctx.ok(p):
            gz = p + ".gz"
            if ctx.apply:
                try:
                    with open(p, "rb") as a, gzip.open(gz + ".tmp", "wb", 3) as b:
                        shutil.copyfileobj(a, b, 1 << 20)
                    os.replace(gz + ".tmp", gz)
                    n = os.path.getsize(gz)
                    os.unlink(p)
                except OSError:
                    continue
            else:
                n = st.st_size // 10
            ctx.credit("yosys_meta_gzip", max(0, st.st_size - n))


def rule_old(attempt, fl, ctx):
    for p, st in fl:
        n = os.path.basename(p)
        if st.st_size >= 8 * MB and not n.endswith(KEEP_EXT):
            unlink(p, st, "old_attempt_heavy", ctx)


def slim_attempt(attempt, old, ctx):
    if live(attempt, ctx):
        ctx.skipped.append((attempt, "live process under attempt"))
        return
    fl = [(p, st) for p, st in files(attempt) if ctx.now - st.st_mtime >= ctx.min_age]
    if old:
        rule_old(attempt, fl, ctx)
        return
    rule_substage(attempt, fl, ctx)
    rule_yosys_meta(attempt, fl, ctx)
    fl = [(p, st) for p, st in files(attempt) if ctx.now - st.st_mtime >= ctx.min_age]
    rule_hardlink(attempt, fl, ctx)


def find_attempts(root):
    """-> {item_dir: [(n, attempt_dir)...]} without descending into an attempt"""
    out = {}
    for dp, dns, _ in os.walk(root):
        keep = []
        for d in dns:
            m = ATTEMPT.match(d)
            if m:
                out.setdefault(dp, []).append((int(m.group(1)), os.path.join(dp, d)))
            else:
                keep.append(d)
        dns[:] = keep
    return out


def run(roots, ctx):
    for r in roots:
        for item_dir, lst in find_attempts(r).items():
            lst.sort()
            item = os.path.basename(item_dir)
            exported = item in ctx.exported
            for i, (n, a) in enumerate(lst):
                slim_attempt(a, exported or i < len(lst) - 1, ctx)
    return ctx


def main(argv):
    apply = "--apply" in argv
    exp, age, roots, i = [], 600, [], 0
    while i < len(argv):
        a = argv[i]
        if a == "--exported":
            i += 1
            for ln in open(argv[i]):
                exp += ln.split()
        elif a == "--min-age-s":
            i += 1
            age = int(argv[i])
        elif a != "--apply":
            roots.append(os.path.abspath(a))
        i += 1
    if not roots:
        print(__doc__)
        return 2
    g = load_guard()
    lst = os.environ.get("OT_GUARD_LIST")
    prot = None
    if lst:
        prot, err = g.load_list(lst)
        if prot is None:
            print("SKIP all: guard list unreadable: %s" % err)
            return 0
    ctx = Ctx(apply, g, prot, g.live_text(), age, exp)
    run(roots, ctx)
    for p, why in ctx.skipped[:50]:
        print("SKIP %s: %s" % (p, why))
    print(json.dumps({"apply": apply, "freed_gb": {k: round(v / 1e9, 2) for k, v in sorted(ctx.freed.items())},
                      "total_gb": round(sum(ctx.freed.values()) / 1e9, 2), "skipped": len(ctx.skipped)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
