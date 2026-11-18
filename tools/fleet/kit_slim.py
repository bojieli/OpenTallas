#!/usr/bin/env python3
"""kit_slim.py [--apply] [--link ROOT...] [--strip ROOT...] [--state kit_wave_state.json --ids store_ids.txt] [--min-age-s N]
KIT-SLIM-1118 (OWNER: live kit builds took 2.2 TB on epyc10; COORD 11-18 decision: the delete guard stays as it is).

Measured: 55-70% of a kit attempt is bind_sinks.json (2.36 GB, one fresh copy per attempt), then identical final ODBs, 2_x/3_x sub-stage ODBs, eco copies.

--link ROOT   (no guard exception: a hardlink deletes nothing; any die) the byte-identical big files become ONE inode:
              bind_sinks.json (and any json >= 256 MB) across ALL attempts under ROOT (sampled fingerprint, then full sha256 of the candidates only),
              and ODB/DEF/SPEF/lib >= 1 MB that are byte-identical inside one attempt (5_route / 5_3_fillcell / 6_1_fill / 6_final).  Atomic os.replace of a
              same-device hardlink; files younger than --min-age-s (default 600) or in an attempt with a live process are left alone.
--strip ROOT  (needs --state and --ids; non-HBM dies only) attempts qualify from the state rows, never by pattern:
                old      row FAIL / CANCELLED / SUPERSEDED, a newer attempt of the same item exists, updated > 6 h ago  -> every file >= 8 MB that is not a
                         .log/.rpt goes (reports and small json stay);
                finished any qualifying row without a newer attempt -> only sub-stage ODBs go: 2_1..2_4 once 2_floorplan.odb exists, 3_1..3_5 once 3_place.odb.
              For each qualifying attempt dir an EXACT allow entry (1 h) is written, then ot_delete_guard.refuse(dir) must pass (protected path inside, live
              process, ot-run unit -> skipped), the attempt must hold no SIGNED signoff.json missing from the signed-store ids (store ledger), and gzip-able
              yosys metadata >= 64 MB is gzipped.  Single-file unlink after the dir check (the auto_retire strip_keep_reports precedent), never rm -rf.
Dry run unless --apply; prints JSON with GB per class."""
import filecmp, gzip, hashlib, importlib.util, json, os, re, shutil, sys, time

HERE = os.path.dirname(os.path.realpath(__file__))
MB = 1 << 20
SUB = {"2_floorplan.odb": ("2_1_floorplan.odb", "2_2_floorplan_macro.odb", "2_3_floorplan_tapcell.odb", "2_4_floorplan_pdn.odb"),
       "3_place.odb": ("3_1_place_gp_skip_io.odb", "3_2_place_iop.odb", "3_3_place_gp.odb", "3_4_place_resized.odb", "3_5_place_dp.odb")}
LINK_EXT = (".odb", ".def", ".spef", ".lib")
YOSYS_META = "1_2_yosys_native_metadata.json"
KEEP_EXT = (".log", ".rpt")
ATTEMPT = re.compile(r"^attempt_(\d+)$")
OLD_STATUS = frozenset({"FAIL", "CANCELLED", "SUPERSEDED"})
OLD_AFTER_S = 6 * 3600
BIG_JSON = 256 * MB


def load_guard():
    for c in (os.path.join(HERE, "ot_delete_guard.py"), os.environ.get("OT_DELETE_GUARD", "")):
        if c and os.path.isfile(c):
            sp = importlib.util.spec_from_file_location("ot_delete_guard", c)
            m = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(m)
            return m
    raise SystemExit("kit_slim: ot_delete_guard.py not found")


class Ctx:
    def __init__(self, apply=False, guard=None, protected=None, ptext="", min_age=600, ids=None, now=None):
        self.apply, self.g, self.protected, self.ptext, self.min_age = apply, guard, protected, ptext or "", min_age
        self.ids, self.now = ids, now or time.time()
        self.freed, self.skipped = {}, []

    def credit(self, cls, n):
        self.freed[cls] = self.freed.get(cls, 0) + n

    def skip(self, p, why):
        self.skipped.append((p, why))


def files(d):
    for dp, dns, fns in os.walk(d):
        for f in fns:
            p = os.path.join(dp, f)
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if not os.path.islink(p) and os.path.isfile(p):
                yield p, st


def is_live(attempt, ctx):
    return attempt in ctx.ptext


def die_of(path):
    m = re.search(r"/runs/([^/]+)/", path)
    return m.group(1) if m else ""


def is_hbm(path):
    return die_of(path).startswith("hbm") or "/hbm/" in path


def relink(master, p, tmpsuffix=".kslim"):
    tmp = p + tmpsuffix
    try:
        os.link(master, tmp)
        os.replace(tmp, p)
        return True
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False


def same_inode(a, b):
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def sha256(path, chunk=8 * MB):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def fingerprint(path, size):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        step = max(1, size // 200)
        for off in range(0, size, step):
            f.seek(off)
            h.update(f.read(65536))
    return h.hexdigest()


# ---- --link ------------------------------------------------------------------------------------------------------
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


def link_attempt_dups(fl, ctx):
    groups = {}
    for p, st in fl:
        if p.endswith(LINK_EXT) and st.st_size >= MB:
            groups.setdefault(st.st_size, []).append((p, st))
    for lst in groups.values():
        lst.sort(key=lambda x: (-x[1].st_mtime, x[0]))
        masters = []
        for p, st in lst:
            for mp, mst in masters:
                if same_inode(mst, st):
                    break
                if p.rsplit(".", 1)[-1] == mp.rsplit(".", 1)[-1] and filecmp.cmp(mp, p, shallow=False):
                    if not ctx.apply or relink(mp, p):
                        ctx.credit("dup_odb_hardlink", st.st_size if st.st_nlink == 1 else 0)
                    break
            else:
                masters.append((p, st))


def link_big_json(cands, ctx):
    """cands: [(path, st)] bind_sinks.json / big json across attempts -> one inode per distinct content"""
    by = {}
    for p, st in cands:
        by.setdefault(st.st_size, []).append((p, st))
    for sz, lst in by.items():
        fp = {}
        for p, st in lst:
            try:
                fp.setdefault(fingerprint(p, sz), []).append((p, st))
            except OSError:
                pass
        for grp in fp.values():
            if len(grp) < 2:
                continue
            grp.sort(key=lambda x: (-x[1].st_nlink, x[1].st_mtime))      # master: the inode already most shared, then oldest
            sums = {}
            for p, st in grp:
                try:
                    sums.setdefault(sha256(p), []).append((p, st))
                except OSError:
                    pass
            for same in sums.values():
                mp, mst = same[0]
                for p, st in same[1:]:
                    if same_inode(mst, st):
                        continue
                    if not ctx.apply or relink(mp, p):
                        ctx.credit("bind_sinks_hardlink", st.st_size if st.st_nlink == 1 else 0)


def run_link(roots, ctx):
    big = []
    for r in roots:
        for item_dir, lst in find_attempts(r).items():
            for n, a in sorted(lst):
                if is_live(a, ctx):
                    ctx.skip(a, "live process under attempt")
                    continue
                fl = [(p, st) for p, st in files(a) if ctx.now - st.st_mtime >= ctx.min_age]
                big += [(p, st) for p, st in fl if st.st_size >= BIG_JSON and (os.path.basename(p) == "bind_sinks.json" or p.endswith(".json"))]
                link_attempt_dups(fl, ctx)
    link_big_json(big, ctx)


# ---- --strip -----------------------------------------------------------------------------------------------------
def signed_not_in_store(tree, ids):
    """SIGNED signoff.json files under tree whose sha256 is not in the signed-store ledger (auto_retire.signed_not_in_store rule) -> count"""
    miss = 0
    for p, st in files(tree):
        n = os.path.basename(p)
        if (n != "signoff.json" and not n.endswith(".signoff.json")) or st.st_size > 8e6:
            continue
        try:
            t = open(p, errors="replace").read()
            if json.loads(t).get("verdict") != "SIGNED":
                continue
        except (OSError, ValueError, AttributeError):
            continue
        if hashlib.sha256(t.encode(errors="replace")).hexdigest() not in ids:
            miss += 1
    return miss


def candidates(state_items, now, roots=()):
    """-> [(attempt_dir, 'old'|'finished')] from kit_wave_state rows: non-HBM, FAIL/CANCELLED/SUPERSEDED, dir exists here, updated > 6 h ago"""
    rows, newest = {}, {}
    for k, v in state_items.items():
        w = v.get("work") if isinstance(v, dict) else None
        m = re.search(r"^(.*)/attempt_(\d+)$", w or "")
        if not m:
            continue
        newest[m.group(1)] = max(newest.get(m.group(1), 0), int(m.group(2)))
        if str(v.get("status")) in OLD_STATUS and not is_hbm(w) and (v.get("die") or "").lower() != "hbm":
            try:
                if now - float(v.get("updated") or 0) > OLD_AFTER_S and os.path.isdir(w):
                    rows[w] = (m.group(1), int(m.group(2)))
            except ValueError:
                pass
    out = []
    for w, (item, n) in rows.items():
        sib = [int(x[8:]) for x in (os.listdir(item) if os.path.isdir(item) else []) if ATTEMPT.match(x)]
        out.append((w, "old" if max(sib + [newest.get(item, 0)]) > n else "finished"))
    return out


def strip_files(attempt, kind, ctx):
    allf = list(files(attempt))
    fl = [(p, st) for p, st in allf if ctx.now - st.st_mtime >= ctx.min_age]
    names = {}
    for p, st in allf:                                  # successors count even when young; only the files removed must be old
        names.setdefault(os.path.dirname(p), {})[os.path.basename(p)] = (p, st)
    def drop(p, st, cls):
        if ctx.apply:
            try:
                os.unlink(p)
            except OSError:
                return
        ctx.credit(cls, st.st_size if st.st_nlink == 1 else 0)
    for p, st in fl:
        if os.path.basename(p) == YOSYS_META and st.st_size >= 64 * MB and kind != "old":
            if ctx.apply:
                try:
                    with open(p, "rb") as a, gzip.open(p + ".gz.tmp", "wb", 3) as b:
                        shutil.copyfileobj(a, b, MB)
                    os.replace(p + ".gz.tmp", p + ".gz")
                    n = os.path.getsize(p + ".gz")
                    os.unlink(p)
                except OSError:
                    continue
            else:
                n = st.st_size // 10
            ctx.credit("yosys_meta_gzip", max(0, st.st_size - n))
    if kind == "old":
        for p, st in fl:
            n = os.path.basename(p)
            if st.st_size >= 8 * MB and not n.endswith(KEEP_EXT) and not n.endswith(".gz"):
                drop(p, st, "old_attempt_heavy")
        return
    for d, nm in names.items():
        for succ, subs in SUB.items():
            s = nm.get(succ)
            if s and s[1].st_size > 0:
                for n in subs:
                    if n in nm and nm[n][1].st_mtime <= s[1].st_mtime and ctx.now - nm[n][1].st_mtime >= ctx.min_age:
                        drop(nm[n][0], nm[n][1], "substage_odb")


def run_strip(state_items, ctx, allow_file=None):
    cands = candidates(state_items, ctx.now)
    exp = int(ctx.now + 3600)
    allow = allow_file or getattr(ctx.g, "ALLOW_EXACT", None)
    if ctx.apply and allow and cands:
        os.makedirs(os.path.dirname(allow), exist_ok=True)
        with open(allow, "a") as f:
            for p, _ in cands:
                f.write("%s\t%d\tkit_slim exact attempt (COORD KIT-SLIM-1118 11-18)\n" % (p, exp))
    for p, kind in cands:
        if is_live(p, ctx):
            ctx.skip(p, "live process under attempt")
            continue
        try:
            why = ctx.g.refuse(p, ctx.protected, ctx.ptext) if ctx.protected is not None else ctx.g.refuse(p)
        except TypeError:
            why = ctx.g.refuse(p)
        if why:
            ctx.skip(p, why)
            continue
        miss = signed_not_in_store(p, ctx.ids or set())
        if miss:
            ctx.skip(p, "%d SIGNED unit(s) not in the signed store ledger" % miss)
            continue
        strip_files(p, kind, ctx)


def main(argv):
    ctx_args = {"apply": "--apply" in argv}
    opts, link, strip, cur = {}, [], [], None
    for a in argv:
        if a in ("--link", "--strip"):
            cur = link if a == "--link" else strip
        elif a.startswith("--") and a != "--apply":
            cur = a
        elif a == "--apply":
            pass
        elif isinstance(cur, list):
            cur.append(os.path.abspath(a))
        elif isinstance(cur, str):
            opts[cur] = a
            cur = None
    if not (link or strip) or (strip and not (opts.get("--state") and opts.get("--ids"))):
        print(__doc__)
        return 2
    g = load_guard()
    prot = None
    if os.environ.get("OT_GUARD_LIST"):
        prot, err = g.load_list(os.environ["OT_GUARD_LIST"])
        if prot is None:
            print("SKIP all: guard list unreadable: %s" % err)
            return 0
    ctx = Ctx(ctx_args["apply"], g, prot, g.live_text(), int(opts.get("--min-age-s", 600)))
    if link:
        run_link(link, ctx)
    if strip:
        ctx.ids = {l.strip() for l in open(opts["--ids"]) if l.strip()}
        run_strip(json.load(open(opts["--state"]))["items"], ctx)
    for p, why in ctx.skipped[:40]:
        print("SKIP %s: %s" % (p, why))
    print(json.dumps({"apply": ctx.apply, "freed_gb": {k: round(v / 1e9, 2) for k, v in sorted(ctx.freed.items())},
                      "total_gb": round(sum(ctx.freed.values()) / 1e9, 2), "skipped": len(ctx.skipped)}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
