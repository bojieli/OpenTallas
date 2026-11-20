#!/usr/bin/env python3
"""Rebuild a type's clock sink bins from a PLACED kit (QC-PLAN-R3, COORD 11-20 / FABLE-CLOSURE lever 4).

Density taps are solved from clock.sink_bins_file.  When the bins were taken from an older build (other RTL, other macro
sites), the taps are planned for the wrong load: PRECHECK STALE-BINS on QC N46R3, e.g. sle_st_a_v1 kits see 25,855 clock
sinks where the plan bins hold 97,712 (0.26x), sle_ctl 1.69x.  This tool reads the newest placed DB of the type
(3_place.odb), takes every standard-cell sink on the die clock nets (clk, clk_t<i>; macro clock pins and edge-clock
fclk_in* ring flops are not on those nets), and writes the bins file in the existing form
{bin_um, n, bins: [[x_centre, y_centre, count]], type, placed_kit, source}.

  dump  ODB OUT.tsv [--image openroad/orfs:latest]   (docker OpenROAD; one line per sink: net inst master x y, um)
  bins  TSV --type T --out FILE [--bin-um 10.8] [--placed-kit K] [--source S]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

NET_RE = r"^clk(_t[0-9]+)?$"

TCL = r"""read_db /in/db.odb
set blk [ord::get_db_block]
set dbu [$blk getDbUnitsPerMicron]
set f [open /out/sinks.tsv w]
foreach net [$blk getNets] {
  set n [$net getName]
  if {![regexp {%s} $n]} continue
  foreach it [$net getITerms] {
    if {![$it isInputSignal]} continue
    set i [$it getInst]; set m [$i getMaster]
    if {[$m isBlock]} continue
    set b [$i getBBox]
    puts $f [format "%%s\t%%s\t%%s\t%%.3f\t%%.3f" $n [$i getName] [$m getName] [expr {([$b xMin] + [$b xMax]) / 2.0 / $dbu}] [expr {([$b yMin] + [$b yMax]) / 2.0 / $dbu}]]
  }
}
close $f
""" % NET_RE


def dump(odb, out, image="openroad/orfs:latest"):
    odb = Path(odb).resolve(); out = Path(out).resolve()
    with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as td:
        Path(td, "dump.tcl").write_text(TCL)
        cmd = ["docker", "run", "--rm", "-v", f"{odb}:/in/db.odb:ro", "-v", f"{td}:/out", image, "bash", "-lc",
               "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /out/dump.tcl > /out/log 2>&1; "
               "rc=$?; chown -R %d:%d /out; exit $rc" % (os.getuid(), os.getgid())]
        rc = subprocess.call(cmd)
        if rc:
            sys.stderr.write(Path(td, "log").read_text()[-2000:] if Path(td, "log").exists() else "")
            raise SystemExit(f"openroad dump rc {rc}")
        out.write_text(Path(td, "sinks.tsv").read_text())
    return out


def bins(rows, bin_um=10.8):
    """rows [(x, y)] -> [[x_centre, y_centre, count]] sorted by (x, y), the binsrep form"""
    acc = {}
    for x, y in rows:
        k = (round((math.floor(x / bin_um) + .5) * bin_um, 3), round((math.floor(y / bin_um) + .5) * bin_um, 3))
        acc[k] = acc.get(k, 0) + 1
    return [[x, y, n] for (x, y), n in sorted(acc.items())]


def read_tsv(path):
    out = []
    for line in Path(path).read_text().splitlines():
        p = line.split("\t")
        if len(p) == 5:
            out.append((float(p[3]), float(p[4])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump"); d.add_argument("odb"); d.add_argument("out"); d.add_argument("--image", default="openroad/orfs:latest")
    b = sub.add_parser("bins"); b.add_argument("tsv"); b.add_argument("--type", required=True); b.add_argument("--out", required=True)
    b.add_argument("--bin-um", type=float, default=10.8); b.add_argument("--placed-kit", default=""); b.add_argument("--source", default="")
    a = ap.parse_args(argv)
    if a.cmd == "dump":
        dump(a.odb, a.out, a.image); print("DUMP", a.out, len(read_tsv(a.out)))
        return 0
    rows = read_tsv(a.tsv)
    if not rows:
        raise SystemExit("no clock sinks in " + a.tsv)
    doc = dict(bin_um=a.bin_um, n=len(rows), bins=bins(rows, a.bin_um), type=a.type, placed_kit=a.placed_kit or a.type,
               source=a.source or f"sink_bins_from_place.py {a.tsv}")
    Path(a.out).write_text(json.dumps(doc) + "\n")
    print("BINS", a.type, doc["n"], len(doc["bins"]), a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
