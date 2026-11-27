"""ADV-GPL-TD-INFLATION (C-GPL-TD-INFLATION, CLASS-OWNERS-B 11-26; REPORT ONLY, never a gate).

Three checks on the one class "timing-driven GPL repair inflates the design":
  plan   PLAN.json [--types RE]   static: per type, the GPL regions the plan creates (logic_cluster_rects_um rows, place_regions rows) and
                                  whether the plan carries the gpl_td flag; types with regions are the ones exposed to the region-mean
                                  timing-driven trigger (OpenROAD tests the MEAN overflow of the top-level region and every region).
  log    3_3_place_gp.log ...     measured, one TSV row per log: regions / tiny regions (<= 20 cells), timing-driven passes, iteration of the
                                  first fire, trigger overflow vs top-level overflow (the region-mean gap), buffers kept, area growth, the
                                  place-resize repair_design buffers (3_4 log beside it), growth ratio G and the INFLATED verdict.
  calib  TSV ...                  TP / FP / FN / TN of the static predictor against the measured verdict.
Verdict INFLATED = growth ratio G = (kept timing-driven buffers + place-resize buffers) / movable cells >= 0.5, or the grown movable count
over the 400k OpenROAD cell cap.  Predictor RISK = timing-driven on and (a tiny region exists or the movable utilisation printed by the
OT_GPL_SPARSE line is under 2 %).  The predictor reads only what exists before the first timing-driven pass.
"""
import json
import os
import re
import sys
import time

TINY = 20
CAP = 400000
G_INFLATED = 0.5
UTIL_RISK_PCT = 2.0
COLS = ["path", "mtime", "regions", "region_cells_min", "region_cells_max", "tiny_regions", "td_on", "td_passes",
        "first_fire_iter", "first_fire_overflow", "first_fire_top_overflow", "buffers_td", "td_delta_area_pct",
        "td_delta_gcells_pct", "movable_top", "movable_after_td", "hpwl_first", "hpwl_min", "hpwl_final",
        "hpwl_ratio_min", "iters", "finished", "keep_overflow", "sparse_util_pct", "td_kept_buffers", "td_virtual_first", "mean_top_gap_max", "resize_buffers", "resize_nets", "resize_area_pct", "resize_long_wires", "census_nontap", "nets_top", "insts_top"]


def analyse(path):
    r = dict.fromkeys(COLS, "")
    r["path"] = path
    try:
        r["mtime"] = time.strftime("%m-%d %H:%M", time.localtime(os.path.getmtime(path)))
        txt = open(path, errors="replace").read()
    except OSError:
        return r
    lines = txt.splitlines()
    regions = []          # (name, movable instances)
    cur = None
    in_top = False
    td_fire = []          # (iter, overflow)
    virt = []
    bufs = []
    top_rows = {}         # iter -> top overflow
    hp = []
    gcell_pct = []
    area_pct = []
    movable_top = None
    nets_top = insts_top = None
    for ln in lines:
        m = re.search(r"GPL-0032\] ---- Initialize Region: (.*)", ln)
        if m:
            cur = m.group(1).strip()
            in_top = cur == "Top-level"
            continue
        if in_top:
            m = re.search(r"GPL-0010\] Number of nets:\s+(\d+)", ln)
            if m and nets_top is None:
                nets_top = int(m.group(1))
            m = re.search(r"GPL-0006\] Number of instances:\s+(\d+)", ln)
            if m and insts_top is None:
                insts_top = int(m.group(1))
        m = re.search(r"GPL-0007\] Movable instances:\s+(\d+)", ln)
        if m and cur is not None:
            if cur == "Top-level":
                if movable_top is None:
                    movable_top = int(m.group(1))
            else:
                regions.append((cur, int(m.group(1))))
            cur = None
            continue
        m = re.search(r"GPL-0100\].*virtual: (true|false)", ln)
        if m:
            virt.append(m.group(1) == "true")
            continue
        m = re.search(r"GPL-0101\]\s+Iter:\s*(\d+), overflow:\s*([\d.eE+-]+)", ln)
        if m:
            td_fire.append((int(m.group(1)), float(m.group(2))))
            continue
        m = re.search(r"RSZ-0038\] Inserted (\d+) buffers", ln)
        if m and td_fire and len(bufs) < len(td_fire):
            bufs.append(int(m.group(1)))
            continue
        m = re.search(r"GPL-0108\].*\(([+-][\d.]+)%\)", ln)
        if m:
            gcell_pct.append(float(m.group(1)))
        m = re.search(r"GPL-0107\].*\(([+-][\d.]+)%\)", ln)
        if m:
            area_pct.append(float(m.group(1)))
        m = re.match(r"\s*(\d+) \|\s+([\d.]+) \|\s+([\d.e+]+) \|[^|]*\|[^|]*\|\s*(\S*)\s*$", ln)
        if m:
            it, ov, h, grp = int(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4)
            if not grp:
                top_rows[it] = ov
                hp.append(h)
        m = re.search(r"GPL-1001\] Global placement finished at iteration (\d+)", ln)
        if m:
            r["iters"] = m.group(1)
            r["finished"] = 1
        m = re.search(r"GPL-1014\] Final placement area:.*\(([+-][\d.]+)%\)", ln)
        if m:
            r["td_delta_area_pct"] = m.group(1)
        m = re.search(r"OT_GPL_SPARSE movable util ([\d.]+) %", ln)
        if m:
            r["sparse_util_pct"] = m.group(1)
        m = re.search(r"global_placement .*-keep_resize_below_overflow ([\d.]+)", ln)
        if m:
            r["keep_overflow"] = m.group(1)
    gp = [ln for ln in lines if re.match(r"(OT_GPL_SPARSE )?global_placement ", ln)]
    r["td_on"] = int(any("-timing_driven" in g for g in gp)) if gp else ""
    r["regions"] = len(regions)
    if regions:
        sizes = [s for _, s in regions]
        r["region_cells_min"], r["region_cells_max"] = min(sizes), max(sizes)
        r["tiny_regions"] = sum(1 for s in sizes if s <= TINY)
    r["td_passes"] = len(td_fire)
    r["nets_top"] = nets_top if nets_top is not None else ""
    r["insts_top"] = insts_top if insts_top is not None else ""
    r["td_virtual_first"] = int(virt[0]) if virt else ""
    if bufs:
        r["td_kept_buffers"] = sum(b for b, v in zip(bufs, virt + [False] * len(bufs)) if not v)
    gaps = []
    for it, ov in td_fire:
        ks = [k for k in top_rows if k < it] or [k for k in top_rows if k <= it]
        if ks:
            gaps.append(top_rows[max(ks)] - ov)
    r["mean_top_gap_max"] = f"{max(gaps):.3f}" if gaps else ""
    m = re.findall(r"OT_CELL_CENSUS stage=\S+ nontap=(\d+)", txt)
    r["census_nontap", "nets_top", "insts_top"] = m[-1] if m else ""
    p4 = os.path.join(os.path.dirname(path), "3_4_place_resized.log")
    if os.path.exists(p4):
        t4 = open(p4, errors="replace").read()
        m = re.findall(r"RSZ-0038\] Inserted (\d+) buffers in (\d+) nets", t4)
        if m:
            r["resize_buffers"], r["resize_nets"] = sum(int(a) for a, _ in m), sum(int(b) for _, b in m)
        m = re.findall(r"final \|\s+([+-][\d.]+)%\s+\|", t4)
        if m:
            r["resize_area_pct"] = m[0]
        m = re.findall(r"RSZ-0037\] Found (\d+) long wires", t4)
        if m:
            r["resize_long_wires"] = m[0]
    if td_fire:
        it, ov = td_fire[0]
        r["first_fire_iter"], r["first_fire_overflow"] = it, ov
        ks = [k for k in top_rows if k < it] or [k for k in top_rows if k <= it]
        if ks:
            r["first_fire_top_overflow"] = top_rows[max(ks)]
        elif top_rows:
            r["first_fire_top_overflow"] = top_rows[min(top_rows)]
    r["buffers_td"] = sum(bufs) if bufs else (0 if r["td_on"] != "" else "")
    r["td_delta_gcells_pct"] = ";".join(f"{g:g}" for g in gcell_pct[::2]) if gcell_pct else ""
    r["movable_top"] = movable_top if movable_top is not None else ""
    if movable_top and bufs:
        r["movable_after_td"] = movable_top + int(round(movable_top * sum(g for g in gcell_pct[::2]) / 100.0)) if gcell_pct else ""
    if hp:
        r["hpwl_first"], r["hpwl_min"], r["hpwl_final"] = f"{hp[0]:.4g}", f"{min(hp):.4g}", f"{hp[-1]:.4g}"
        r["hpwl_ratio_min"] = f"{hp[-1] / min(hp):.3f}" if min(hp) else ""
    return r




def growth_ratio(r):
    m = _f(r.get("movable_top"))
    return (_f(r.get("td_kept_buffers")) + _f(r.get("resize_buffers"))) / m if m else 0.0


def final_cells(r):
    return _f(r.get("movable_top")) + _f(r.get("td_kept_buffers")) + _f(r.get("resize_buffers"))


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0


def inflated(r):
    """Measured verdict of a log row."""
    return growth_ratio(r) >= G_INFLATED or final_cells(r) > CAP


def risk(r):
    """Static predictor of a log row (pre-first-pass information only)."""
    if r.get("td_on") != 1 and r.get("td_on") != "1":
        return False
    util = r.get("sparse_util_pct")
    return _f(r.get("tiny_regions")) >= 1 or (util not in ("", None) and _f(util) < UTIL_RISK_PCT)


def region_mean_gap(r):
    """True when the first non-virtual pass fired on a mean far under the top-level overflow (the A3 signature)."""
    return _f(r.get("mean_top_gap_max")) >= 0.3 and _f(r.get("regions")) >= 1


def calibrate(rows):
    tp = fp = fn = tn = 0
    for r in rows:
        p, m = risk(r), inflated(r)
        tp += p and m
        fp += p and not m
        fn += (not p) and m
        tn += (not p) and not m
    return {"TP": tp, "FP": fp, "FN": fn, "TN": tn}


def plan_check(plan, types_re=None):
    """Static per-type count of the GPL regions a plan creates (report rows)."""
    out = []
    flag = (plan.get("gpl_td") or {})
    for tn, t in sorted((plan.get("partition_types") or plan.get("types") or {}).items()):
        if types_re and not re.search(types_re, tn):
            continue
        lc = t.get("logic_cluster_rects_um") or []
        pr = t.get("place_regions") or []
        if lc or pr:
            out.append({"type": tn, "logic_cluster_regions": len(lc), "place_regions": len(pr), "gpl_td": json.dumps(flag, sort_keys=True) if flag else "",
                        "exposed": "yes" if not flag.get("top_overflow_trigger") else "no (top_overflow_trigger)"})
    return out


def main(argv):
    if not argv or argv[0] not in ("plan", "log", "calib"):
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    if cmd == "plan":
        types = None
        if "--types" in rest:
            k = rest.index("--types")
            types = rest[k + 1]
            rest = rest[:k] + rest[k + 2:]
        for p in rest:
            rows = plan_check(json.load(open(p)), types)
            print(f"ADV-GPL-TD-INFLATION plan {p}: {len(rows)} types with GPL regions")
            for r in rows:
                print("  " + " ".join(f"{k}={v}" for k, v in r.items()))
        return 0
    if cmd == "log":
        print("\t".join(COLS + ["G", "inflated", "risk"]))
        for p in rest:
            r = analyse(p)
            print("\t".join(str(r[c]) for c in COLS) + f"\t{growth_ratio(r):.3f}\t{int(inflated(r))}\t{int(risk(r))}")
        return 0
    import csv
    rows = []
    for p in rest:
        rows += list(csv.DictReader(open(p), delimiter="\t"))
    print(json.dumps(calibrate(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
