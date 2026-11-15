#!/usr/bin/env python3
"""DIE-ROUTE-ABS-1: cut the partition abstract obstruction over the die clock cells placed under it.

A die clock cell (tree repeater / leaf) placed on a site inside a partition outline is a top-owned placement hole with an
M8 -> M1 via stack.  The partition abstract (plan abstract OR closed view) blocks M1-M7 (and implants) over its whole
outline, so detailed route shorts every such stack against the instance (measured: HEAD unit u201, 1,904 of 2,800 markers).
This module computes one type-frame window per placed cell (cell body + margin, snapped outward to the site / row grid,
united over every instance of the type, so one abstract per type stays valid) and removes those windows from the OBS
rectangles of the LEF text.  Windows that touch a planned hard core are not opened (island_windows reports in_core).

Library:  cut_lef_text(lef_text, windows, layers=...) -> (text, stats)
          tree_sites(tree_json_path) -> [((x, y), source)]
CLI (patch an existing kit in place, idempotent per source file copy kept as .precut):
  abstract_cutout.py PLAN.json KIT_DIR [--margin-um 0.25] [--dry-run]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CUT_LAYERS = tuple(f"M{i}" for i in range(1, 8)) + ("RVTN", "RVTP", "LVTN", "LVTP", "SLVTN", "SLVTP")
PG_CUT_LAYER = "M7"


def rect_sub(rect, holes):
    """[(x0, y0, x1, y1)] of rect minus the union of holes"""
    out = [tuple(rect)]
    for h in holes:
        nxt = []
        for r in out:
            if h[0] >= r[2] or h[2] <= r[0] or h[1] >= r[3] or h[3] <= r[1]:
                nxt.append(r)
                continue
            if h[0] > r[0]:
                nxt.append((r[0], r[1], h[0], r[3]))
            if h[2] < r[2]:
                nxt.append((h[2], r[1], r[2], r[3]))
            lo, hi = max(r[0], h[0]), min(r[2], h[2])
            if h[1] > r[1]:
                nxt.append((lo, r[1], hi, h[1]))
            if h[3] < r[3]:
                nxt.append((lo, h[3], hi, r[3]))
        out = nxt
    return out


def _holes_near(rect, holes):
    return [h for h in holes if not (h[0] >= rect[2] or h[2] <= rect[0] or h[1] >= rect[3] or h[3] <= rect[1])]


def cut_lef_text(txt, windows, layers=CUT_LAYERS, pg_layer=PG_CUT_LAYER):
    """cut `windows` (type-frame rects, um) out of every OBS RECT on `layers` and out of POWER/GROUND pin RECTs on
    pg_layer.  Pin shapes of signals and clock are never touched.  -> (new text, stats)"""
    st = dict(obs_rects_in=0, obs_rects_out=0, pg_rects_in=0, pg_rects_out=0)
    if not windows:
        return txt, st
    lines, out = txt.split("\n"), []
    ctx, layer, use = None, None, None      # ctx: 'obs' | 'pin' | None
    rect_re = re.compile(r"^(\s*)RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*;\s*$")
    for ln in lines:
        s = ln.strip()
        if re.match(r"^OBS\b", s):
            ctx, layer = "obs", None
        elif re.match(r"^PIN\b", s):
            ctx, layer, use = "pin", None, None
        elif ctx == "pin" and re.match(r"^USE\s+", s):
            use = s.split()[1]
        elif re.match(r"^END\s+\S+", s) and ctx == "pin":
            ctx = None
        elif s == "END" and ctx == "obs":
            ctx = None
        elif re.match(r"^LAYER\s+\S+", s):
            layer = s.split()[1]
        m = rect_re.match(ln)
        if m and ctx == "obs" and layer in layers:
            r = tuple(float(m.group(i)) for i in range(2, 6))
            pieces = rect_sub(r, _holes_near(r, windows))
            st["obs_rects_in"] += 1
            st["obs_rects_out"] += len(pieces)
            out += [f"{m.group(1)}RECT {a:.4f} {b:.4f} {c:.4f} {d:.4f} ;" for a, b, c, d in pieces if c > a and d > b]
            continue
        if m and ctx == "pin" and use in ("POWER", "GROUND") and layer == pg_layer:
            r = tuple(float(m.group(i)) for i in range(2, 6))
            pieces = rect_sub(r, _holes_near(r, windows))
            st["pg_rects_in"] += 1
            st["pg_rects_out"] += len(pieces)
            out += [f"{m.group(1)}RECT {a:.4f} {b:.4f} {c:.4f} {d:.4f} ;" for a, b, c, d in pieces if c > a and d > b]
            continue
        out.append(ln)
    return "\n".join(out), st


def tree_sites(path, cell_um=None):
    """die-frame clock cell sites of a kit clock/tree.json ('sites': name -> [x, y])"""
    d = json.loads(Path(path).read_text())
    tag = Path(path).name
    return [(tuple(xy), f"{tag}:{n}") for n, xy in d["sites"].items()]


def apply_to_kit(P, kit_dir, windows_by_type, smod, dry_run=False):
    """patch kit_dir/abstracts/<module>.lef of every type with windows; keep the original as .precut"""
    res = {}
    for tn, win in windows_by_type.items():
        f = Path(kit_dir) / "abstracts" / f"{smod[tn]}.lef"
        if not f.is_file():
            continue
        pre = f.with_suffix(".lef.precut")
        src = pre.read_text() if pre.is_file() else f.read_text()
        new, st = cut_lef_text(src, win)
        st["windows"] = len(win)
        res[tn] = st
        if not dry_run:
            if not pre.is_file():
                pre.write_text(src)
            f.write_text(new)
    return res


def run(plan, kit_dir, margin_um=0.25, dry_run=False):
    import die_trial as D
    import schema as S
    P = S.Plan(S.load(plan), Path(plan))
    smod = D.standin_module_names(P)
    sites = tree_sites(Path(kit_dir) / "clock" / "tree.json")
    # sites are PLACED cells: no plan-site snap slack, only the margin
    win, recs = D.island_windows(P, sites, snap=0.0, margin=margin_um)
    res = apply_to_kit(P, kit_dir, win, smod, dry_run)
    rep = dict(schema="ot_abstract_cutout/1", sites=len(sites), margin_um=margin_um, types_with_windows=len(win),
               windows=sum(len(v) for v in win.values()),
               sites_under_partition=sum(1 for r in recs if r["parts"]),
               sites_outside_partitions=sum(1 for r in recs if not r["parts"]),
               in_core=sum(1 for r in recs for h in r["parts"] if h["in_core"]), per_type=res)
    if not dry_run:
        (Path(kit_dir) / "abstract_cutout.json").write_text(json.dumps(rep, indent=1) + "\n")
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan")
    ap.add_argument("kit_dir")
    ap.add_argument("--margin-um", type=float, default=0.25)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rep = run(a.plan, a.kit_dir, a.margin_um, a.dry_run)
    print(json.dumps({k: v for k, v in rep.items() if k != "per_type"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
