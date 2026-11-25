#!/usr/bin/env python3
"""lec_part.py: cone-level partitioned LEC (LEC-PART-1, COORD 11-25).

A whole-design lec.py run proves every compare point in one correspondence problem: one wrong class anywhere keeps the
whole run going for hours (s81_head hd_mesh: 10.5 h, 149k points).  This driver splits the compare points into
partitions and proves each partition on the sequential cone of influence of its points only (lec.py OT_LEC_PART_RE,
coi_partition), each as its own ot-run unit, in parallel.

  1. AIG pre-pass: lec.py OT_LEC_AIG_ONLY=1 into OUT/base (skipped when OUT/base already holds the four AIG/map files).
  2. Partitions: --part-re RE (repeatable, one partition each) or --parts N (group the point names by instance prefix
     of --depth levels, pack the groups into N bins by point count).  The LAST partition is always "everything not in
     an earlier partition" (include .*, exclude the union of the others), so the partitions cover every point by
     construction; lec_part.json records the coverage check against the point list of the base AIGs.
  3. One ot-run per partition: lec.py --reuse on a copy of the base AIGs, OT_LEC_PART_RE / OT_LEC_PART_EXCLUDE_RE set.
  4. Merge into OUT/lec_part.json: verdict EQUIVALENT only when every partition is EQUIVALENT and the selected point
     lists cover every point; else the worst partition verdict.

Soundness: a partition's kept latch set is closed under the next-state relation (coi_partition), so a selected point
proved in the cut AIG is proved for the whole design; each partition is a complete lec.py proof of its own (hints are
still proved, never waived).

    python3 -I tools/die_plan/lec_part.py KIT --netlist N --out DIR [--hints H] [--parts 8 --depth 4 | --part-re RE ...]
        [--hosts H] [--mem 60] [--threads 8] [--jobs 8] [--crit] [--env K=V ...] [--dry]"""
import argparse
import collections
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEC = HERE / "lec.py"
BASE_FILES = ("gold.aig", "gold.map", "gate.aig", "gate.map", "gold.ys.log", "gold_b.ys.log", "gate.ys.log",
              "gate_b.ys.log")
RANK = {"EQUIVALENT": 0, "UNPROVEN": 1, "NOT EQUIVALENT": 2, "KEEP FAIL": 2, "LINT FAIL": 2}


def _lec_module():
    spec = importlib.util.spec_from_file_location("lec_for_part", LEC)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def point_names(base):
    """every compare point key of both sides (cps of key_points) -> sorted list"""
    lec = _lec_module()
    pts = set()
    for side in ("gold", "gate"):
        _, cps, _, _, _ = lec.key_points(lec.read_aig(base / f"{side}.aig"), lec.read_map(base / f"{side}.map"))
        pts |= set(cps)
    return sorted(pts)


def prefix(key, depth):
    kind, _, name = key.partition(":")
    parts = re.split(r"\.(?![^\[]*\])", name)
    return kind, ".".join(parts[:depth])


def auto_parts(points, n, depth):
    """group by (kind-free) instance prefix, greedy largest-first bin packing into n-1 bins; the rest bin is added by
    plan().  -> [include regex]"""
    groups = collections.Counter(prefix(p, depth)[1] for p in points)
    if n <= 1 or len(groups) <= 1:
        return []
    bins = [[0, []] for _ in range(n - 1)]
    for g, c in sorted(groups.items(), key=lambda x: (-x[1], x[0]))[: max(n - 1, 0) * 64]:
        b = min(bins, key=lambda x: x[0])
        b[0] += c
        b[1].append(g)
    return ["^(ff|bb|po):(" + "|".join(re.escape(g) for g in sorted(b[1])) + r")(\.|\[|$)" for b in bins if b[1]]


def plan(includes):
    """explicit include regexes + the rest partition -> [(include, exclude)]"""
    parts = [(r, None) for r in includes]
    rest_exc = "|".join(f"(?:{r})" for r in includes) or None
    parts.append((".*", rest_exc))
    return parts


def selected(points, inc, exc):
    i, e = re.compile(inc), re.compile(exc) if exc else None
    return [p for p in points if i.search(p) and not (e and e.search(p))]


def run_unit(cmd, log, dry):
    if dry:
        log.write_text(" ".join(cmd) + "\n")
        return None
    return subprocess.Popen(cmd, stdout=log.open("w"), stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)


def otrun(a, wd, env, lec_args):
    cmd = ["ot-run", "--hosts", a.hosts] if a.hosts else ["ot-run"]
    if a.crit:
        cmd.append("--crit")
    cmd += ["--mem", str(a.mem), "--threads", str(a.threads), "--disk", str(a.disk), "--dir", str(wd), "--",
            "env", *[f"{k}={v}" for k, v in env.items()], sys.executable, "-I", str(LEC), *lec_args]
    return cmd


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit")
    ap.add_argument("--netlist", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hints")
    ap.add_argument("--parts", type=int, default=8)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--part-re", action="append", default=[])
    ap.add_argument("--hosts")
    ap.add_argument("--mem", type=int, default=60)
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--disk", type=int, default=3)
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--crit", action="store_true")
    ap.add_argument("--env", action="append", default=[], help="K=V passed to every lec.py (e.g. OT_LEC_SUPERSET_VEC=1)")
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    base = out / "base"
    env = dict(e.split("=", 1) for e in a.env)
    lec_args = [str(Path(a.kit).resolve()), "--netlist", str(Path(a.netlist).resolve()), "--jobs", str(a.jobs)]
    if a.hints:
        lec_args += ["--hints", str(Path(a.hints).resolve())]
    out.mkdir(parents=True, exist_ok=True)
    if not all((base / f).is_file() for f in BASE_FILES[:4]):
        p = run_unit(otrun(a, out, dict(env, OT_LEC_AIG_ONLY="1"), lec_args + ["--out", str(base)]),
                     out / "base.otrun.log", a.dry)
        if p is not None:
            p.wait()
        if a.dry:
            print(f"DRY: AIG pre-pass -> {out / 'base.otrun.log'}")
            return 0
        if not all((base / f).is_file() for f in BASE_FILES[:4]):
            print(f"lec_part: AIG pre-pass left no AIGs in {base} (see base.otrun.log)", file=sys.stderr)
            return 3
    points = point_names(base)
    includes = a.part_re or auto_parts(points, a.parts, a.depth)
    parts = plan(includes)
    cover = collections.Counter()
    rows = []
    for n, (inc, exc) in enumerate(parts):
        sel = selected(points, inc, exc)
        cover.update(sel)
        rows.append(dict(part=n, include=inc, exclude=exc, points=len(sel)))
    missing = [p for p in points if not cover[p]]
    if missing:
        print(f"lec_part: partition plan misses {len(missing)} points: {missing[:5]}", file=sys.stderr)
        return 3
    procs = []
    for r in rows:
        if not r["points"]:
            r["verdict"] = "EMPTY"
            continue
        wd = out / f"p{r['part']}"
        lo = wd / "lec"
        lo.mkdir(parents=True, exist_ok=True)
        for f in BASE_FILES:
            if (base / f).is_file() and not (lo / f).is_file():
                shutil.copyfile(base / f, lo / f".{f}.part")
                os.replace(lo / f".{f}.part", lo / f)
        penv = dict(env, OT_LEC_PART_RE=r["include"])
        if r["exclude"]:
            penv["OT_LEC_PART_EXCLUDE_RE"] = r["exclude"]
        procs.append((r, run_unit(otrun(a, wd, penv, lec_args + ["--out", str(lo), "--reuse"]),
                                  wd / "otrun.log", a.dry)))
    if a.dry:
        print(json.dumps(dict(points=len(points), parts=rows), indent=1))
        return 0
    worst = "EQUIVALENT"
    for r, p in procs:
        p.wait()
        lj = out / f"p{r['part']}" / "lec" / "lec.json"
        try:
            j = json.loads(lj.read_text())
        except (OSError, ValueError):
            j = dict(verdict="UNPROVEN", reason="no lec.json")
        r.update(verdict=j.get("verdict"), counts=j.get("counts"), reason=j.get("reason"),
                 failing_first=[f.get("point") for f in (j.get("failing") or [])[:20]],
                 t_total_s=j.get("t_total_s"), partition=j.get("partition"))
        if RANK.get(r["verdict"], 1) > RANK.get(worst, 0):
            worst = r["verdict"]
    rec = dict(schema="opentallas.lec_part.v1", kit=str(Path(a.kit).resolve()), netlist=str(Path(a.netlist).resolve()),
               points=len(points), covered=len(points) - len(missing), verdict=worst, parts=rows)
    (out / "lec_part.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"LEC-PART {worst}: {len(rows)} partitions, {len(points)} points; " +
          ", ".join(f"p{r['part']} {r.get('verdict')}" for r in rows))
    return {"EQUIVALENT": 0, "UNPROVEN": 2}.get(worst, 1)


if __name__ == "__main__":
    sys.exit(main())
