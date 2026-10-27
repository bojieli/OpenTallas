#!/usr/bin/env python3
"""Plan-directory pin views as REAL copies (COORD ruling KV-CORES-R6, 2026-10-27).

A tool that derives a new plan directory from an existing one must never write through a shared symlink into another
plan's views (KV-CORES-R5 finding: kv_core_slice --heads copied the plan dir with symlinks=True and rewrote four head
views inside the kv-core-slice-1 pd_slice/cores that three other plans read).  Rule implemented here:

  snapshot(src, dst)   copy the plan dir; every view dir (cores/) and every plan-referenced pins_file becomes a REAL
                       copy (no symlink, no hard link); other read-only inputs may stay symlinks.  Writes
                       dst/views.sha256 (sha256sum format) over all view files.
  safe_write(dst, rel, text)
                       the only way a tool writes into a derived plan dir: refuses (PlanViewError) when any directory
                       component between dst and the file is a symlink or the path resolves outside dst; a final-path
                       symlink (e.g. a linked plan json) is unlinked and replaced by a real file, never written through.
                       A write under a view dir refreshes views.sha256.
  verify(dst)          [] when views.sha256 matches the view files and no view is a symlink / outside dst; else a list
                       of findings.

    plan_views.py verify PLAN_DIR       (exit 1 on any finding)
"""
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path

VIEW_DIRS = ("cores",)
SHA_LIST = "views.sha256"


class PlanViewError(RuntimeError):
    pass


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _plan_pin_files(dst):
    out = set()
    for pj in Path(dst).glob("*.json"):
        try:
            P = json.loads(pj.read_text())
        except (ValueError, OSError, UnicodeDecodeError):
            continue
        if not isinstance(P, dict):
            continue
        for t in (P.get("partition_types") or {}).values():
            for hc in (t or {}).get("hard_cores", []) if isinstance(t, dict) else []:
                pf = hc.get("pins_file") if isinstance(hc, dict) else None
                if pf and not os.path.isabs(pf) and ".." not in Path(pf).parts:
                    out.add(pf)
    return sorted(out)


def _check_inside(dst, rel):
    """dst/rel with no symlinked DIRECTORY component and resolving inside dst."""
    dst = Path(dst)
    rel = Path(rel)
    if rel.is_absolute() or ".." in rel.parts:
        raise PlanViewError(f"{rel}: path must be relative to the plan dir without '..'")
    cur = dst
    for part in rel.parts[:-1]:
        cur = cur / part
        if cur.is_symlink():
            raise PlanViewError(f"{rel}: directory component {cur} is a symlink -> {os.readlink(cur)}; "
                                "refusing to write into another plan's views (snapshot the plan dir first)")
    p = dst / rel
    if not str(p.parent.resolve()).startswith(str(dst.resolve()) + os.sep) and p.parent.resolve() != dst.resolve():
        raise PlanViewError(f"{rel}: resolves outside {dst}")
    return p


def _is_view(rel):
    return Path(rel).parts[0] in VIEW_DIRS or Path(rel).name.endswith("_pins.json") or "_pins_" in Path(rel).name


def view_files(dst):
    dst = Path(dst)
    files = set()
    for vd in VIEW_DIRS:
        d = dst / vd
        if d.is_dir():
            for p in d.rglob("*"):
                if p.is_file() or p.is_symlink():
                    files.add(p.relative_to(dst).as_posix())
    files.update(pf for pf in _plan_pin_files(dst) if (dst / pf).exists() or (dst / pf).is_symlink())
    return sorted(files)


def write_sha_list(dst):
    dst = Path(dst)
    lines = [f"{_sha(dst / f)}  {f}" for f in view_files(dst)]
    tmp = dst / (SHA_LIST + ".tmp")
    tmp.write_text("\n".join(lines) + ("\n" if lines else ""))
    tmp.replace(dst / SHA_LIST)
    return len(lines)


def _materialise(p):
    """replace symlink / hard-linked file p by a real private copy of its content."""
    if p.is_symlink():
        tgt = p.resolve()
        p.unlink()
        if tgt.is_dir():
            shutil.copytree(tgt, p, symlinks=False)
        else:
            shutil.copy2(tgt, p)
    elif p.is_file() and p.stat().st_nlink > 1:
        tmp = p.with_name(p.name + ".cp")
        shutil.copy2(p, tmp)
        tmp.replace(p)


def snapshot(src, dst, ignore=None):
    """copy plan dir src -> dst (dst must not exist); views become real copies; returns the view-file count."""
    src, dst = Path(src), Path(dst)
    if dst.exists() or dst.is_symlink():
        raise PlanViewError(f"{dst} exists")
    shutil.copytree(src, dst, symlinks=True, ignore=ignore)
    for vd in VIEW_DIRS:
        d = dst / vd
        if d.is_symlink():
            _materialise(d)
        if d.is_dir():
            for p in sorted(d.rglob("*")):
                if p.is_symlink() or (p.is_file() and p.stat().st_nlink > 1):
                    _materialise(p)
    for pf in _plan_pin_files(dst):
        p = _check_inside(dst, pf)
        if p.is_symlink() or p.exists():
            _materialise(p)
    return write_sha_list(dst)


def safe_write(dst, rel, text):
    p = _check_inside(dst, rel)
    if p.is_symlink():
        p.unlink()
    elif p.exists() and p.stat().st_nlink > 1:
        p.unlink()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    if _is_view(rel) or (Path(dst) / SHA_LIST).exists():
        write_sha_list(dst)
    return p


def verify(dst):
    dst = Path(dst)
    bad = []
    lst = dst / SHA_LIST
    if not lst.exists():
        return [f"{SHA_LIST} missing"]
    want = {}
    for ln in lst.read_text().splitlines():
        if ln.strip():
            h, f = ln.split(None, 1)
            want[f.strip()] = h
    have = view_files(dst)
    for f in have:
        p = dst / f
        try:
            _check_inside(dst, f)
        except PlanViewError as e:
            bad.append(str(e))
            continue
        if p.is_symlink():
            bad.append(f"{f}: symlink -> {os.readlink(p)} (views must be real copies)")
            continue
        if p.stat().st_nlink > 1:
            bad.append(f"{f}: hard link (nlink {p.stat().st_nlink})")
        if f not in want:
            bad.append(f"{f}: not in {SHA_LIST}")
        elif want[f] != _sha(p):
            bad.append(f"{f}: sha {_sha(p)[:12]} != listed {want[f][:12]}")
    for f in sorted(set(want) - set(have)):
        bad.append(f"{f}: listed but missing")
    return bad


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "verify":
        print(__doc__)
        return 2
    bad = verify(argv[1])
    for b in bad:
        print("FAIL", b)
    print("PLAN_VIEWS", "PASS" if not bad else "FAIL", argv[1], len(view_files(argv[1])), "view files")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
