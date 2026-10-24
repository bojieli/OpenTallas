#!/usr/bin/env python3
"""Cell estimator for die-plan partition types (PLAN-TOOL4, COORD 10-23 19:5x).

The G0 hard-core rule (a type over CORE_CELLS_MAX = 400k std cells must list hard_cores[]) needs a cell estimate for
every type.  Most plans carry none (S81 168, QC 56, KV 49, HBM 60 types without type.cells), but every die already has
an estimate in a side file.  This module reads them, best source first, and returns {type: (cells, basis)}:

  1. "plan"       type.cells
  2. "contents"   sum of contents[].cells (every content carries one)
  3. "by_type"    a table keyed by TYPE name:      {"<type>": N | {"cells": N} | {"flat_k": K}}
                  (also nested under "cells_per_type" / "per_type"; QC plan_notes.json cells_per_type)
  4. "by_part"    a table keyed by PARTITION name: same values; the type takes the MAX over its instances
                  (S81 cells_est.json); per_type rows with "rep": "<partition>" map through that partition
                  (KV l1_cores_v3*.json: per_type{..., rep, flat_k} keyed by older type names)
  5. "modules"    a module table {"masters": {"<module>": {"cells": N}}} or {"<module>": N}, or a Yosys `stat`
                  report (=== module === ... Number of cells: N); the type sums its contents[].module and
                  hard_cores[].module (a hard core's module counted once per core) - basis says how many of the
                  contents were found ("modules 37/40"; a partial sum is a LOWER bound)
  A type found in no source has no estimate (G0 WARNs with the list).

Sources: every path given with --evidence / evidence=..., plus these files when they sit in the plan directory:
  cells_est.json, plan_notes.json, l1_cores_v31.json, l1_cores_v3.json, cells_evidence.json, inputs/cells_evidence.json,
  cells/*.json, cells/*.stat.

    python3 tools/die_plan/cells.py PLAN.json [--evidence FILE ...] [--json OUT]   # table + types > 400k w/o cores
"""
import argparse
import json
import re
import sys
from pathlib import Path

CORE_CELLS_MAX = 400_000
AUTO = ("cells_est.json", "plan_notes.json", "l1_cores_v31.json", "l1_cores_v3.json", "cells_evidence.json",
        "inputs/cells_evidence.json")
RANK = {"plan": 0, "contents": 1, "by_type": 2, "by_part": 3, "modules": 4}


def _val(v):
    """cells from a table value: N | {"cells": N} | {"flat_k": K} (thousands)."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, dict):
        if isinstance(v.get("cells"), (int, float)):
            return int(v["cells"])
        if isinstance(v.get("flat_k"), (int, float)):
            return int(round(v["flat_k"] * 1000))
    return None


def parse_stat(text):
    """Yosys `stat` report -> {module: cells} (the per-module 'Number of cells', hierarchy totals not summed)."""
    out, mod = {}, None
    for ln in text.splitlines():
        m = re.match(r"^===\s*(\S+)\s*===", ln.strip())
        if m:
            mod = m.group(1).lstrip("\\")
            continue
        m = re.match(r"^\s*Number of cells:\s*(\d+)", ln)
        if m and mod and mod not in out:
            out[mod] = int(m.group(1))
    # design-hierarchy block: "=== design hierarchy ===" ... "<top>  1" + total "Number of cells: N" -> top total
    m = re.search(r"=== design hierarchy ===.*?\n\s*(\S+)\s+1\s*\n.*?Number of cells:\s*(\d+)", text, re.S)
    if m:
        out[m.group(1).lstrip("\\")] = int(m.group(2))
    out.pop("design", None)
    return out


def load_source(path, types, parts):
    """-> list of (kind, table) with kind in by_type / by_part / modules."""
    p = Path(path)
    if p.suffix == ".stat" or p.name.endswith(".stat.txt"):
        return [("modules", parse_stat(p.read_text(errors="replace")))]
    js = json.loads(p.read_text())
    if not isinstance(js, dict):
        return []
    res = []
    if isinstance(js.get("masters"), dict):
        res.append(("modules", {m: c for m, v in js["masters"].items() if (c := _val(v)) is not None}))
    for key in ("cells_per_type", "per_type"):
        sub = js.get(key)
        if not isinstance(sub, dict):
            continue
        bt = {k: c for k, v in sub.items() if k in types and (c := _val(v)) is not None}
        bp = {v["rep"]: c for v in sub.values() if isinstance(v, dict) and v.get("rep") in parts
              and (c := _val(v)) is not None}
        if bp and len(bp) >= len(bt):           # names of an older plan version: go through the rep partition
            res.append(("by_part", bp))
        elif bt:
            res.append(("by_type", bt))
    flat = {k: c for k, v in js.items() if (c := _val(v)) is not None}
    if flat:
        nt, npart = len(set(flat) & set(types)), len(set(flat) & set(parts))
        if npart > nt:
            res.append(("by_part", {k: c for k, c in flat.items() if k in parts}))
        elif nt:
            res.append(("by_type", {k: c for k, c in flat.items() if k in types}))
        elif not js.get("masters"):
            res.append(("modules", flat))
    return res


def discover(plan_dir):
    if plan_dir is None:
        return []
    d = Path(plan_dir)
    fs = [d / f for f in AUTO if (d / f).is_file()]
    if (d / "cells").is_dir():
        fs += sorted((d / "cells").glob("*.json")) + sorted((d / "cells").glob("*.stat"))
    return fs


def estimate(raw, plan_dir=None, evidence=(), auto=True):
    """raw plan dict -> ({type: (cells, basis)}, [sources used])."""
    types = raw["partition_types"]
    parts = {p["name"]: p["type"] for p in raw["partitions"]}
    files = list(evidence) + (discover(plan_dir) if auto else [])
    srcs = []
    for f in files:
        try:
            for kind, tab in load_source(f, types, parts):
                if tab:
                    srcs.append((kind, tab, str(f)))
        except (OSError, ValueError) as e:
            print(f"cells: {f}: {e}", file=sys.stderr)
    by_type, by_part, mods = {}, {}, {}
    for kind, tab, f in srcs:
        if kind == "by_type":
            for k, c in tab.items():
                by_type.setdefault(k, (c, f))
        elif kind == "by_part":
            for pn, c in tab.items():
                tn = parts[pn]
                if tn not in by_part or c > by_part[tn][0]:
                    by_part[tn] = (c, f)
        else:
            for m, c in tab.items():
                mods.setdefault(m, c)
    out = {}
    for tn, t in types.items():
        if "cells" in t:
            out[tn] = (int(t["cells"]), "plan")
            continue
        cs = t.get("contents", [])
        if cs and all("cells" in c for c in cs):
            out[tn] = (sum(int(c["cells"]) for c in cs), "contents")
            continue
        if tn in by_type:
            out[tn] = (by_type[tn][0], f"by_type {Path(by_type[tn][1]).name}")
            continue
        if tn in by_part:
            out[tn] = (by_part[tn][0], f"by_part {Path(by_part[tn][1]).name}")
            continue
        if mods:
            items = [(c.get("module"), c.get("cells")) for c in cs]
            have = {c.get("module") for c in cs}
            items += [(h.get("module"), None) for h in t.get("hard_cores", []) if h.get("module") not in have]
            n = found = 0
            tot = 0
            for m, own in items:
                if m is None:
                    continue
                n += 1
                c = own if own is not None else mods.get(m)
                if c is None:
                    m2 = re.sub(r"__.*$", "", m)          # split / variant suffixes (<module>__<piece>)
                    c = mods.get(m2)
                if c is not None:
                    found += 1
                    tot += int(c)
            if found:
                out[tn] = (tot, f"modules {found}/{n}" + ("" if found == n else " (lower bound)"))
    return out, [f for _, _, f in srcs]


def over_cap(raw, est):
    """types over CORE_CELLS_MAX with no hard_cores[]: [(type, cells, basis, instances)]."""
    n = {}
    for p in raw["partitions"]:
        n[p["type"]] = n.get(p["type"], 0) + 1
    return sorted([(tn, c, b, n.get(tn, 0)) for tn, (c, b) in est.items()
                   if c > CORE_CELLS_MAX and not raw["partition_types"][tn].get("hard_cores")],
                  key=lambda r: -r[1])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("--evidence", action="append", default=[])
    ap.add_argument("--no-auto", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    est, used = estimate(raw, Path(a.plan).resolve().parent, a.evidence, not a.no_auto)
    oc = over_cap(raw, est)
    missing = sorted(set(raw["partition_types"]) - set(est))
    rep = dict(plan=a.plan, types=len(raw["partition_types"]), estimated=len(est), missing=missing, sources=used,
               over_cap_no_cores=[dict(type=t, cells=c, basis=b, instances=n) for t, c, b, n in oc],
               cells={t: dict(cells=c, basis=b) for t, (c, b) in sorted(est.items())})
    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"{len(est)}/{len(raw['partition_types'])} types estimated; {len(oc)} over {CORE_CELLS_MAX} w/o hard_cores")
    for t, c, b, n in oc:
        print(f"  OVER {t}: {c} cells x{n} ({b})")
    if missing:
        print(f"  no estimate ({len(missing)}): {', '.join(missing[:20])}{' ...' if len(missing) > 20 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
