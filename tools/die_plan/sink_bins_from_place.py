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
  apply PLAN OUT --bins TYPE=FILE [...] [--report R.json]   set clock.sink_bins_file AND re-point the tap-named rows the
        re-derived taps invalidate (retap.py: forwarded clock outputs, reset consumer taps) in the same step.  Run from
        the tree root the bins paths are relative to.
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


def apply_bins(raw, bins_map, plan_path=None, taps_fn=None):
    """Set clock.sink_bins_file of each TYPE in bins_map {type: path} on plan dict raw (in place) and, in the SAME step,
    re-point the tap-named references the re-derived taps invalidate (retap.repoint: forwarded clock outputs and
    reset consumer taps).  -> {type: [[where, key, was, now, um]]}"""
    import copy
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import retap
    old = copy.deepcopy(raw)
    for tn, f in bins_map.items():
        if tn not in raw["partition_types"]:
            raise SystemExit(f"apply: type {tn} not in plan")
        raw["partition_types"][tn].setdefault("clock", {})["sink_bins_file"] = f
    return retap.repoint(old, raw, plan_path, plan_path, types=set(bins_map), taps_fn=taps_fn)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump"); d.add_argument("odb"); d.add_argument("out"); d.add_argument("--image", default="openroad/orfs:latest")
    b = sub.add_parser("bins"); b.add_argument("tsv"); b.add_argument("--type", required=True); b.add_argument("--out", required=True)
    b.add_argument("--bin-um", type=float, default=10.8); b.add_argument("--placed-kit", default=""); b.add_argument("--source", default="")
    p = sub.add_parser("apply"); p.add_argument("plan"); p.add_argument("out")
    p.add_argument("--bins", action="append", required=True, metavar="TYPE=FILE"); p.add_argument("--report")
    a = ap.parse_args(argv)
    if a.cmd == "apply":
        raw = json.loads(Path(a.plan).read_text())
        rep = apply_bins(raw, dict(x.split("=", 1) for x in a.bins), a.plan)
        Path(a.out).write_text(json.dumps(raw, indent=1) + "\n")
        if a.report:
            Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
        print("APPLY bins", len(a.bins), "retap types", len(rep), "refs", sum(len(c) for c in rep.values()))
        return 0
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
