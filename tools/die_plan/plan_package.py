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
import hashlib, json, os, shutil, sys, time
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
    pf = d / meta.get("plan", "die_plan.json")
    if pf.exists():
        probs += plan_abs_problems(pf)
    return probs


def gate(plan, mode=None):
    """bind.py hook: -> (ok, message).  require: not ok when a sibling is a link / resolves outside; warn: ok with a message"""
    mode = (mode or os.environ.get("OT_BIND_PLAN_PACKAGE") or "warn").lower()
    if mode == "off":
        return True, ""
    d = os.path.dirname(os.path.abspath(plan))
    bad = outside_entries(d) + [(r, "abs", w) for r, w in plan_abs_problems(Path(plan))]
    if (Path(d) / "PACKAGE.json").exists():
        bad += [(r, w) for r, w in verify(d) if not any(r == b[0] for b in bad)]
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
        bad = outside_entries(os.path.dirname(os.path.abspath(a[1]))) + [(r, "abs", w) for r, w in plan_abs_problems(Path(a[1]))]
        for r, k, t in bad[:40]:
            print(f"PLAN_PACKAGE_PROBLEM {r}: {k} {t}")
        print("PLAN_PACKAGE_OK" if not bad else f"PLAN_PACKAGE_FAIL {len(bad)}")
        return 1 if bad else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
