#!/usr/bin/env python3
"""view_by_hash: build a frozen view's evidence files by CONTENT HASH, never by path (KV-R 11-16, FABLE-FLOW-2000).

A view's provenance.json records the sha256 of every file it freezes: export.signoff_sha256, export.files_sha256{lef, libs, pins},
kit.face_guard_sha256 (the face tool the child was signed with).  Copying a file by path (kit/face_guard.py, a neighbour view) can
silently take bytes that were edited after the sign-off (w652/w653/w672: 5083985a instead of the frozen 7ecd3a0d, which failed
hard_landing.prove at gen).  This tool resolves each needed file by the sha the provenance names, from explicit source roots,
and refuses (exit 1) when no source file has exactly those bytes.  It never edits provenance or signoff.

  view_by_hash.py check VIEW_DIR                  verify landing_evidence/ and view files against provenance + manifest (no write)
  view_by_hash.py stage VIEW_DIR --src ROOT...    (re)write landing_evidence/{face_guard_source.py, signoff.json, lef, lib} from the
                                                  first ROOT file whose sha256 equals the recorded one; refresh manifest.json sha256
Stdlib only.  Exit 0 = every file matches, 1 = a mismatch / a hash with no source.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def wanted(prov, master):
    """{evidence file name: sha256 recorded by provenance}"""
    exp = prov.get("export") or {}
    out = {"signoff.json": exp.get("signoff_sha256"),
           "face_guard_source.py": (prov.get("kit") or {}).get("face_guard_sha256")}
    for name, sha in (exp.get("files_sha256") or {}).items():
        if name in (f"{master}.lef", f"{master}_tt.lib"):
            out[name] = sha
    return {k: v for k, v in out.items() if v}


def index(roots, names):
    """{sha256: path} over files of the given base names (or any *.py/*.lef/*.lib/*.json when names is None) under the roots"""
    idx = {}
    for root in roots:
        for dp, _dn, fn in os.walk(root):
            for f in fn:
                if names is not None and f not in names and not any(f.endswith(n) for n in names):
                    continue
                p = os.path.join(dp, f)
                try:
                    idx.setdefault(digest(p), p)
                except OSError:
                    pass
    return idx


def check(view):
    view = Path(view)
    le = view / "landing_evidence"
    prov = json.loads((le / "provenance.json").read_text())
    man = json.loads((le / "manifest.json").read_text())
    master = man["master"]
    errs = []
    for name, sha in wanted(prov, master).items():
        f = le / name
        if not f.is_file():
            errs.append(f"{name}: missing")
        elif digest(f) != sha:
            errs.append(f"{name}: {digest(f)[:8]} != provenance {sha[:8]}")
    for name, sha in man["sha256"].items():
        if (le / name).is_file() and digest(le / name) != sha:
            errs.append(f"manifest {name}: stale hash")
    return errs


def stage(view, roots):
    view = Path(view)
    le = view / "landing_evidence"
    prov = json.loads((le / "provenance.json").read_text())
    man = json.loads((le / "manifest.json").read_text())
    master = man["master"]
    need = {n: s for n, s in wanted(prov, master).items() if not ((le / n).is_file() and digest(le / n) == s)}   # only wrong/missing files
    idx = index(roots, None) if need else {}
    missing = [f"{n} {s[:8]}" for n, s in need.items() if s not in idx]
    if missing:
        raise SystemExit("view_by_hash: no source file has the recorded bytes for: " + ", ".join(missing))
    for name, sha in need.items():
        dst = le / name
        if dst.is_file() and digest(dst) == sha:
            continue
        if dst.exists():
            os.chmod(dst, 0o644)
        dst.write_bytes(Path(idx[sha]).read_bytes())
    for name in man["sha256"]:
        if (le / name).is_file():
            man["sha256"][name] = digest(le / name)
    (le / "manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    return check(view)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("view")
    s = sub.add_parser("stage")
    s.add_argument("view")
    s.add_argument("--src", nargs="+", required=True)
    a = ap.parse_args(argv)
    errs = check(a.view) if a.cmd == "check" else stage(a.view, a.src)
    for e in errs:
        print("VIEW-HASH MISMATCH", e)
    print("VIEW-HASH", "FAIL" if errs else "OK", a.view)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
