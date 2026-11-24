#!/usr/bin/env python3
"""FF-LIB-REGEN 11-24: apply the exact off-main FF regens (views_off_main/INDEX.tsv) to a private tree.

usage: apply_off_main.py TREE [--dry-run] [--only MODULE ...]
For every INDEX row whose <TREE>/<view_relpath>/<module>_ff.lib exists:
  - sha == ff_sha256_new -> ALREADY_NEW
  - sha == ff_sha256_old and the sibling _tt.lib sha == tt_sha256 -> copy+mv the new lib (OLD->NEW)
  - otherwise -> SKIP (different view version; never overwritten)
The source libs are read next to this script (views_off_main/<view_relpath>/), and their sha is checked first.
A read-only file is replaced by a mode-0444 copy.  Prints one line per row and a total."""
import argparse, csv, hashlib, os, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "views_off_main"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tree")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    tree = Path(a.tree)
    counts = {}
    with open(HERE / "INDEX.tsv") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))
    for r in rows:
        m = r["module"]
        if a.only and m not in a.only:
            continue
        rel = r["view_relpath"]
        dst = tree / rel / f"{m}_ff.lib"
        tt = tree / rel / f"{m}_tt.lib"
        src = HERE / rel / f"{m}_ff.lib"
        if not dst.exists():
            st = "ABSENT"
        elif dst.is_symlink():
            st = "SKIP_SYMLINK"
        else:
            s = sha(dst)
            if s == r["ff_sha256_new"]:
                st = "ALREADY_NEW"
            elif r["ff_sha256_old"] not in ("", "-") and s == r["ff_sha256_old"] and tt.exists() and sha(tt) == r["tt_sha256"]:
                if sha(src) != r["ff_sha256_new"]:
                    sys.exit(f"source sha mismatch: {src}")
                st = "OLD->NEW"
                if not a.dry_run:
                    mode = dst.stat().st_mode & 0o777
                    tmp = dst.with_name(dst.name + ".ffregen.tmp")
                    shutil.copyfile(src, tmp)
                    os.chmod(tmp, mode)
                    os.replace(tmp, dst)
            else:
                st = "SKIP_OTHER_VERSION"
        counts[st] = counts.get(st, 0) + 1
        print(f"{st}\t{m}\t{dst}")
    print("TOTAL", " ".join(f"{k}={v}" for k, v in sorted(counts.items())), "dry_run" if a.dry_run else "")


if __name__ == "__main__":
    main()
