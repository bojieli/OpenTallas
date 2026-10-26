#!/usr/bin/env python3
"""S81-HEAD (10-24): renamed copies of the CLOSED head element views for the head tile kit.

Both closed views (physical/dsrom_fh_safe/closed/elemA, elemB) are MACRO / cell `ot_dsrom_head_elem` with different
sizes and timing, so one design cannot hold both under that name.  This writes, per element E in {A, B},
physical/die_plan/s81_head/cores/views/ot_s81hd_elemE_cv/ot_s81hd_elemE_cv{.lef,_ss.lib,_ff.lib,_tt.lib}: byte copies
in which only the macro / FOREIGN / END names (LEF) and the library / cell names (liberty) change, plus MANIFEST.json
with the sha256 of every source and output.  --check verifies the outputs against the sources (exit 1 on drift).

    python3 tools/s81_head/hd_cv_views.py [--check]
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "physical/dsrom_fh_safe/closed"
OUT = ROOT / "physical/die_plan/s81_head/cores/views"
OLD = "ot_dsrom_head_elem"


def sha(b):
    return hashlib.sha256(b).hexdigest()


def rename_lef(t, new):
    n = 0
    t, k = re.subn(rf"^MACRO {OLD}$", f"MACRO {new}", t, flags=re.M); n += k
    t, k = re.subn(rf"^  FOREIGN {OLD} ", f"  FOREIGN {new} ", t, flags=re.M); n += k
    t, k = re.subn(rf"^END {OLD}$", f"END {new}", t, flags=re.M); n += k
    assert n == 3 and OLD + "\n" not in t, n
    return t


def rename_lib(t, new, corner):
    t, a = re.subn(rf"^library \({OLD}_{corner}\)", f"library ({new}_{corner})", t, flags=re.M)
    t, b = re.subn(rf'^  cell \("{OLD}"\)', f'  cell ("{new}")', t, flags=re.M)
    assert a == 1 and b == 1, (a, b)
    return t


def build():
    man = {}
    for e in ("A", "B"):
        new = f"ot_s81hd_elem{e}_cv"
        d = OUT / new
        files = {f"{OLD}.lef": (f"{new}.lef", lambda t: rename_lef(t, new))}
        for c in ("ss", "ff", "tt"):
            files[f"{OLD}_{c}.lib"] = (f"{new}_{c}.lib", lambda t, c=c: rename_lib(t, new, c))
        ent = {}
        for s, (o, fn) in files.items():
            src = (SRC / f"elem{e}" / s).read_bytes()
            ent[o] = dict(source=str((SRC / f"elem{e}" / s).relative_to(ROOT)), source_sha256=sha(src),
                          sha256=None, data=fn(src.decode()).encode())
        man[new] = (d, ent)
    return man


def main():
    check = "--check" in sys.argv
    bad = 0
    record = {}
    for new, (d, ent) in build().items():
        d.mkdir(parents=True, exist_ok=True)
        rec = {}
        for o, v in ent.items():
            p = d / o
            if check:
                if not p.is_file() or p.read_bytes() != v["data"]:
                    print("DRIFT", p); bad += 1
            else:
                p.write_bytes(v["data"])
            rec[o] = dict(source=v["source"], source_sha256=v["source_sha256"], sha256=sha(v["data"]))
        record[new] = rec
        if not check:
            (d / "MANIFEST.json").write_text(json.dumps(dict(
                tool="tools/s81_head/hd_cv_views.py", rule="names only: LEF MACRO/FOREIGN/END, liberty library/cell",
                closed_job={"ot_s81hd_elemA_cv": "dshead-elemA-ss-f11f3cc47", "ot_s81hd_elemB_cv": "dshead-elemB-ss-a318fdf47"}[new],
                files=rec), indent=1) + "\n")
    print("CHECK", "FAIL" if bad else "PASS") if check else print("wrote", ", ".join(record))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
