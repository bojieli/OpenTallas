#!/usr/bin/env python3
"""plan_package.py -- a plan plus every sibling file it is bound with, in ONE self-contained folder (KW-FIX-45 11-12, COORD).

bind (and gen) resolve a plan's sibling files (cores/, cells/, census, die_io.json, macro_pins, sink_bins, r8/, ...) relative
to the plan's folder.  When that folder holds symlinks into other lanes' trees, a lane that composes a plan in its own
folder binds against whatever those links point at today (VISLAYOUT2-QC lost 3 bind cycles to 'legacy landing added_cycles
must be 4').  This tool copies (never links) the plan folder into a package and records the sha256 of every file; bind can
refuse a plan whose siblings resolve outside its folder.

  plan_package.py package PLAN.json --out DIR     copy the plan folder (symlinks dereferenced) + PACKAGE.json
  plan_package.py verify  DIR|PLAN.json           exit 1 if a listed file is missing/changed, a link, or resolves outside
  plan_package.py check   PLAN.json               exit 1 if any entry of the plan folder is a link or resolves outside it

bind.py gate: env OT_BIND_PLAN_PACKAGE = require (bind refuses such a plan) | warn (default: one warning line) | off.
"""
import hashlib, json, os, re, shutil, sys, time
from pathlib import Path

SCHEMA = "opentallas.plan_package.v1"
MAX_ENTRIES = 200_000
SKIP_DIRS = {"__pycache__", ".git"}


def sha256_file(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _walk(root):
    n = 0
    for dp, dn, fn in os.walk(root, followlinks=False):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for name in sorted(fn) + [d for d in dn if os.path.islink(os.path.join(dp, d))]:
            n += 1
            if n > MAX_ENTRIES:
                return
            yield os.path.join(dp, name)


def outside_entries(plan_dir):
    """[(relpath, kind, target)] of entries in the folder that are symlinks or resolve outside it (kind 'link' / 'outside')"""
    root = os.path.realpath(plan_dir)
    bad = []
    for p in _walk(plan_dir):
        rel = os.path.relpath(p, plan_dir)
        real = os.path.realpath(p)
        if os.path.islink(p):
            bad.append((rel, "link", real))
        elif not (real == root or real.startswith(root + os.sep)):
            bad.append((rel, "outside", real))
    return bad


ABS_PREFIXES = ("/srv/", "/home/", "/tmp/", "/mnt/", "/data/", "/opt/", "/work/", "/var/")


def abs_path_values(obj, _path="$"):
    """[(json path, value)] of every string value in a plan JSON that is an absolute file path (KW-FIX-45 11-12, COORD: a per-type
    clock.sink_bins_file pointing into another lane's folder passed verify and then failed bind / G0)"""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out += abs_path_values(v, f"{_path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += abs_path_values(v, f"{_path}[{i}]")
    elif isinstance(obj, str) and obj.startswith(ABS_PREFIXES) and " " not in obj and "\n" not in obj and obj.count("/") >= 2:
        out.append((_path, obj))
    return out


MAX_JSON_BYTES = 300 * 2**20


_ABS_RX = re.compile(r'"\\?/(?:srv|home|tmp|mnt|data|opt|work|var)\\?/')    # a string value starting with an ABS_PREFIXES root


def _abs_problems_one(args):
    """[(file:jsonpath, msg)] of one json / json.gz of the folder (a process-pool worker: the files are independent).  A file whose text
    has no `"/srv/`-style string start cannot hold an absolute path value: the slow recursive json walk is skipped (the 70 MB
    plans of a plan folder almost never carry one).  Per-file cache on (path, size, mtime_ns): a new plan event adds ONE
    70 MB plan to a folder of unchanged older ones."""
    import gzip
    f, d = Path(args[0]), Path(args[1])
    try:
        st = f.stat()
        if st.st_size > MAX_JSON_BYTES:
            return []
    except OSError:
        return []
    rel = f.relative_to(d)
    fkey = None if os.environ.get("OT_BIND_GATE_CACHE", "") == "off" else \
        "f-" + hashlib.sha256(f"{f}\0{st.st_size}\0{st.st_mtime_ns}".encode()).hexdigest()[:40]
    if fkey:
        try:
            return [(x, y) for x, y in json.loads((_cache_dir() / f"{fkey}.json").read_text())]
        except (OSError, ValueError):
            pass
    try:
        text = gzip.open(f, "rt").read() if f.name.endswith(".gz") else f.read_text()
        res = [(f"{rel}:{jp}", f"absolute path {v}") for jp, v in abs_path_values(json.loads(text))] if _ABS_RX.search(text) else []
    except (OSError, ValueError, EOFError):
        return []
    if fkey:
        try:
            c = _cache_dir()
            c.mkdir(parents=True, exist_ok=True)
            tmp = c / f".{fkey}.{os.getpid()}.tmp"
            tmp.write_text(json.dumps(res))
            os.replace(tmp, c / f"{fkey}.json")
        except OSError:
            pass
    return res


def package_abs_problems(d, plan_name=None):
    """absolute paths in EVERY json / json.gz of the package folder (plan, as-built, sidecar, pads, composition ...), not just the
    plan (KW-FIX-45 11-12 COORD: KV vN's as-built named 5 files outside the package; cleanup deleted two and killed a bind).
    [(file:jsonpath, 'absolute path ...')].  BIND-SPEED-1118: the files are parsed in a process pool (QC N4: eight 70 MB plans, one
    core = ~9 min); the result order is the sorted walk order, as before."""
    d = Path(d)
    files = []
    for dp, dn, fn in os.walk(d, followlinks=False):
        dn[:] = sorted(x for x in dn if x not in SKIP_DIRS)
        files += [(str(Path(dp) / name), str(d)) for name in sorted(fn)
                  if name != "PACKAGE.json" and name.endswith((".json", ".json.gz"))]
    out = []
    n = min(len(files), int(os.environ.get("OT_BIND_GATE_JOBS", "") or min(16, os.cpu_count() or 1)))
    if n > 1 and len(files) > 1:
        import concurrent.futures as cf
        try:
            import multiprocessing as mp           # fork: the worker is this module already imported (forkserver, the 3.14 default, re-imports
            #                                         it by name and fails under python -I, where tools/die_plan is not on sys.path)
            with cf.ProcessPoolExecutor(n, mp_context=mp.get_context("fork")) as ex:
                for r in ex.map(_abs_problems_one, files, chunksize=1):
                    out += r
            return out
        except (OSError, RuntimeError):
            out = []                                    # no fork / pool: the serial path below
    for a in files:
        out += _abs_problems_one(a)
    return out


def plan_abs_problems(plan_file):
    try:
        raw = json.loads(Path(plan_file).read_text())
    except (OSError, ValueError):
        return []
    return [(f"{plan_file.name if hasattr(plan_file, 'name') else plan_file}:{jp}", f"absolute path {v}") for jp, v in abs_path_values(raw)]


def _rewrite_abs(obj, ext_dir, out, copied):
    """copy each existing absolute-path file into <out>/_ext/<sha8>_<name> and return the plan with the value rewritten to that
    package-relative path (plan-folder relative: bind/taps resolve plan inputs under the plan folder first)"""
    if isinstance(obj, dict):
        return {k: _rewrite_abs(v, ext_dir, out, copied) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rewrite_abs(v, ext_dir, out, copied) for v in obj]
    if isinstance(obj, str) and abs_path_values(obj) == [] and obj.startswith(ABS_PREFIXES) and False:
        return obj
    if isinstance(obj, str) and obj.startswith(ABS_PREFIXES) and " " not in obj and obj.count("/") >= 2:
        sp = Path(obj)
        if sp.is_file():
            h = sha256_file(sp)[:8]
            rel = f"_ext/{h}_{sp.name}"
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(sp, dst)
            copied[rel] = obj
            return rel
        copied.setdefault("__missing__", []).append(obj)
    return obj


def package(plan, out):
    plan = Path(plan); src = plan.parent; out = Path(out)
    if out.exists() and any(out.iterdir()):
        raise SystemExit(f"plan_package: {out} is not empty")
    other = [(r, w) for r, w in package_abs_problems(src) if not r.startswith(plan.name + ":")]
    if other:
        raise SystemExit(f"plan_package: {len(other)} absolute path(s) in the as-built / sidecar / other json of the package "
                         f"(first {other[0][0]}: {other[0][1]}); make them package-relative at the source")
    files = {}
    for dp, dn, fn in os.walk(src, followlinks=True):
        dn[:] = sorted(d for d in dn if d not in SKIP_DIRS)
        for name in sorted(fn):
            p = Path(dp) / name
            if not p.is_file():
                continue
            rel = p.relative_to(src)
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, dst)                      # a copy, never a link; symlinks are followed
            files[str(rel)] = {"sha256": sha256_file(dst), "bytes": dst.stat().st_size, "origin": os.path.realpath(p)}
    if str(plan.name) not in files:
        raise SystemExit(f"plan_package: {plan.name} was not copied")
    # absolute paths inside the plan JSON: existing files are copied into _ext/ and the value rewritten package-relative;
    # a missing one fails the package (the plan names a file nobody can supply)
    copied = {}
    try:
        raw = json.loads((out / plan.name).read_text())
    except ValueError:
        raw = None
    if raw is not None and abs_path_values(raw):
        new = _rewrite_abs(raw, src, out, copied)
        miss = copied.pop("__missing__", [])
        if miss:
            raise SystemExit(f"plan_package: the plan names {len(miss)} absolute path(s) that do not exist (first {miss[0]})")
        (out / plan.name).write_text(json.dumps(new, indent=1) + "\n")
        for rel, origin in copied.items():
            files[rel] = {"sha256": sha256_file(out / rel), "bytes": (out / rel).stat().st_size, "origin": origin}
        files[str(plan.name)] = {"sha256": sha256_file(out / plan.name), "bytes": (out / plan.name).stat().st_size,
                                 "origin": os.path.realpath(plan), "rewritten_abs_paths": len(copied)}
    meta = {"schema": SCHEMA, "plan": plan.name, "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "source": os.path.realpath(src), "files": files}
    (out / "PACKAGE.json").write_text(json.dumps(meta, indent=1) + "\n")
    return meta


def verify(target):
    t = Path(target)
    d = t if t.is_dir() else t.parent
    pj = d / "PACKAGE.json"
    if not pj.exists():
        return [("PACKAGE.json", "no package manifest (not materialised by plan_package)")]
    meta = json.loads(pj.read_text())
    probs = []
    for rel, e in sorted(meta.get("files", {}).items()):
        p = d / rel
        if not p.exists():
            probs.append((rel, "missing")); continue
        if p.is_symlink():
            probs.append((rel, "is a symlink")); continue
        if sha256_file(p) != e["sha256"]:
            probs.append((rel, "sha256 differs from the package record"))
    probs += [(r, f"{k} -> {tg}") for r, k, tg in outside_entries(d)]
    probs += package_abs_problems(d)
    return probs


def gate(plan, mode=None):
    """bind.py hook: -> (ok, message).  require: not ok when a sibling is a link / resolves outside; warn: ok with a message"""
    mode = (mode or os.environ.get("OT_BIND_PLAN_PACKAGE") or "warn").lower()
    if mode == "off":
        return True, ""
    d = os.path.dirname(os.path.abspath(plan))
    key = _gate_key(d, mode)
    hit = _gate_cache_get(key)
    if hit is not None:
        return hit
    res = _gate_uncached(d, mode)
    _gate_cache_put(key, res)
    return res


def _gate_key(d, mode):
    """BIND-SPEED-1118: the gate parsed EVERY json of the plan folder (QC N4: eight 70 MB plans + inputs, KV: 280k entries) before every
    elab / bind / kit-rtl, ~10 min of single-threaded python per call, and again for each of the kit-rtl types.  Its verdict is a
    function of the folder's files, so it is cached on (folder, mode, every entry's size + mtime_ns) in $OT_BIND_GATE_CACHE
    (default /var/tmp/ot-bind-gate-<uid>; `off` = no cache).  Any file added / removed / rewritten changes the key."""
    if os.environ.get("OT_BIND_GATE_CACHE", "") == "off":
        return None
    h = hashlib.sha256(f"{d}\0{mode}\0".encode())
    try:
        for p in _walk(d):
            st = os.lstat(p)
            h.update(f"{os.path.relpath(p, d)}\0{st.st_size}\0{st.st_mtime_ns}\0".encode())
    except OSError:
        return None
    return h.hexdigest()[:40]


def _cache_dir():
    return Path(os.environ.get("OT_BIND_GATE_CACHE") or f"/var/tmp/ot-bind-gate-{os.getuid()}")


def _gate_cache_get(key):
    if not key:
        return None
    try:
        r = json.loads((_cache_dir() / f"{key}.json").read_text())
        return bool(r["ok"]), str(r["msg"])
    except (OSError, ValueError, KeyError):
        return None


def _gate_cache_put(key, res):
    if not key:
        return
    try:
        c = _cache_dir()
        c.mkdir(parents=True, exist_ok=True)
        tmp = c / f".{key}.{os.getpid()}.tmp"
        tmp.write_text(json.dumps(dict(ok=res[0], msg=res[1])))
        os.replace(tmp, c / f"{key}.json")
    except OSError:
        pass


def _gate_uncached(d, mode):
    bad = outside_entries(d) + [(r, "abs", w) for r, w in package_abs_problems(d)]
    if (Path(d) / "PACKAGE.json").exists():
        # FABLE-FIX-KV-HUB-R3 11-21: set lookup.  The any() scan was quadratic (verify rows x outside entries): a private cp -al KV tree
        # with a stale PACKAGE.json (164k outside entries) spun 4 h here before elab (hroot B2 / B3 binds), in a warn-only gate.
        seen = {b[0] for b in bad}
        bad += [(r, w) for r, w in verify(d) if r not in seen]
        bad = [(b[0], b[1], b[2] if len(b) > 2 else "") for b in bad]
    if not bad:
        return True, ""
    msg = (f"plan folder {d} is not self-contained: {len(bad)} entr{'y' if len(bad) == 1 else 'ies'} link or resolve outside it "
           f"(first: " + "; ".join(f"{r} ({k} {t})".strip() for r, k, t in bad[:5]) + "); run tools/die_plan/plan_package.py package")
    return (mode != "require"), msg


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if len(a) >= 2 and a[0] == "package" and "--out" in a:
        meta = package(a[1], a[a.index("--out") + 1])
        print(f"plan_package: {len(meta['files'])} files copied, sha256 recorded in PACKAGE.json")
        return 0
    if len(a) == 2 and a[0] == "verify":
        probs = verify(a[1])
        for r, w in probs[:40]:
            print(f"PLAN_PACKAGE_PROBLEM {r}: {w}")
        print("PLAN_PACKAGE_OK" if not probs else f"PLAN_PACKAGE_FAIL {len(probs)}")
        return 1 if probs else 0
    if len(a) == 2 and a[0] == "check":
        bad = outside_entries(os.path.dirname(os.path.abspath(a[1]))) + [(r, "abs", w) for r, w in package_abs_problems(os.path.dirname(os.path.abspath(a[1])))]
        for r, k, t in bad[:40]:
            print(f"PLAN_PACKAGE_PROBLEM {r}: {k} {t}")
        print("PLAN_PACKAGE_OK" if not bad else f"PLAN_PACKAGE_FAIL {len(bad)}")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
