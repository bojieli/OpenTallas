"""Place-stage log gates (HEAD-INT-R2 11-26; classes C-GPL-TD-INFLATION, C-FIRM-RESIZE-OVERLAP).

Pure log readers, no OpenROAD: they work on the retained 3_3_place_gp.log / 3_5_place_dp.log of a kit, so a finished run can be judged (and a
fix proven on the retained fed00 / ffbe77 logs) without a placement.

  gpl_td_passes(text)   every non-virtual timing-driven repair of the GPL log: iteration, overflow the trigger read, buffers inserted,
                        nets, repair_design area delta %, HPWL at the trigger.
  gpl_td_verdict(text, ...)  FAIL when a pass inserts more buffers than max_buffer_frac of the cells present, when the repair area delta
                        exceeds max_area_pct, or when a pass fires on a trigger far below the top-level overflow (cluster_regions > 0 and
                        the first pass fires above trigger_overflow_cap).  Thresholds are arguments; the defaults are the HEAD fed00 /
                        ffbe77 evidence (0.35 of cells, +10 % area).
  gpl_td_relaxed(text)  relaxed rule (COORD 11-26): area limit 15 % instead of 10 % only if movable util < 10 %, HPWL ratio <= 1.02 and TD
                        pass-2 added buffers <= 10 % of pass-1; any unparsed value -> old 10 % rule, reported as UNEVALUATED.
  dpl_firm_released(text)    the integer N of 'OT_CLAND released N FIRM cland cells ...' (None when the line is absent) and the keep_firm
                        count of 'OT_FT_KEEP_FIRM released N'.
  dpl_verdict(text)     FAIL unless both are 0 ('FIRM released = 0').
CLI: place_log_gate.py gpl|dpl LOG [...]; exit 1 on FAIL, 2 on an unreadable / line-less log.
"""
import re
import sys

_TD = re.compile(r"GPL-0100\]\s+Timing-driven iteration (\d+)/(\d+), virtual: (true|false)")
_IT = re.compile(r"GPL-0101\]\s+Iter:\s*(\d+), overflow:\s*([0-9.]+), keep resizer changes at:\s*([0-9.]+), HPWL:\s*(\d+)")
_BUF = re.compile(r"RSZ-0038\]\s+Inserted (\d+) buffers in (\d+) nets")
_AREA = re.compile(r"GPL-0107\]\s+Timing-driven: repair_design delta area: ([0-9.]+) um\^2 \(\+([0-9.]+)%\)")
_ADD = re.compile(r"GPL-0108\]\s+Timing-driven: repair_design, gpl delta gcells: (-?\d+)")
_UTIL = re.compile(r"OT_GPL_SPARSE movable util ([0-9.]+) %")
_CLUSTER = re.compile(r"^OT_LOGIC_CLUSTER (\S+) cells=(\d+)", re.M)


def gpl_td_passes(text):
    out = []
    cur = None
    for line in text.splitlines():
        m = _TD.search(line)
        if m:
            cur = dict(index=int(m.group(1)), of=int(m.group(2)), virtual=m.group(3) == "true",
                       iteration=None, overflow=None, hpwl=None, buffers=0, nets=0, area_pct=None, added=None)
            out.append(cur)
            continue
        if cur is None:
            continue
        m = _IT.search(line)
        if m and cur["iteration"] is None:
            cur.update(iteration=int(m.group(1)), overflow=float(m.group(2)), hpwl=int(m.group(4)))
            continue
        m = _BUF.search(line)
        if m and cur["buffers"] == 0:
            cur.update(buffers=int(m.group(1)), nets=int(m.group(2)))
            continue
        m = _AREA.search(line)
        if m and cur["area_pct"] is None:
            cur["area_pct"] = float(m.group(2))
            continue
        m = _ADD.search(line)
        if m and cur["added"] is None:
            cur["added"] = int(m.group(1))
    return [p for p in out if not p["virtual"]]


def gpl_cluster_regions(text):
    return len(_CLUSTER.findall(text))


def gpl_td_relaxed(text, max_util_pct=10.0, max_hpwl_ratio=1.02, max_pass2_frac=0.10):
    """Relaxed 15 % TD area rule inputs (COORD 11-26 14:52).  -> dict(evaluated, ok, util, hpwl_ratio, pass2_frac, pass1_added, pass2_added, line).
    util = the 'OT_GPL_SPARSE movable util N %' line; hpwl_ratio = HPWL at the last non-virtual TD trigger / HPWL at the first;
    pass1/pass2 added = the net buffers each non-virtual pass kept (GPL-0108 'gpl delta gcells'), pass2_frac = pass2 / pass1.
    Any value not parseable -> evaluated False, ok False (the old 10 % rule applies and the line says so)."""
    passes = gpl_td_passes(text)
    m = _UTIL.search(text)
    util = float(m.group(1)) if m else None
    ratio = frac = a1 = a2 = None
    if len(passes) >= 2:
        h1, h2 = passes[0]["hpwl"], passes[-1]["hpwl"]
        if h1 and h2 is not None:
            ratio = h2 / h1
        a1, a2 = passes[0]["added"], passes[1]["added"]
        if a1 and a2 is not None:
            frac = a2 / a1
    miss = [n for n, v in (("movable util", util), ("HPWL ratio", ratio), ("pass-2/pass-1 added buffers", frac)) if v is None]
    vals = (f"movable util {util if util is None else format(util, 'g')} %, HPWL ratio {ratio if ratio is None else format(ratio, '.4f')} "
            f"(limit {max_hpwl_ratio:g}), pass-2/pass-1 added buffers {a2}/{a1} = {frac if frac is None else format(frac, '.4f')} (limit {max_pass2_frac:g})")
    if miss:
        return dict(evaluated=False, ok=False, util=util, hpwl_ratio=ratio, pass2_frac=frac, pass1_added=a1, pass2_added=a2,
                    line=f"TD area rule: relaxed 15 % rule UNEVALUATED (unparsed: {', '.join(miss)}); old 10 % rule used; {vals}")
    ok = util < max_util_pct and ratio <= max_hpwl_ratio and frac <= max_pass2_frac
    return dict(evaluated=True, ok=ok, util=util, hpwl_ratio=ratio, pass2_frac=frac, pass1_added=a1, pass2_added=a2,
                line=f"TD area rule: {'relaxed 15 %' if ok else 'old 10 % (relaxed conditions not all met)'}; {vals}")


def gpl_td_verdict(text, cells=None, max_buffer_frac=0.35, max_area_pct=10.0, trigger_overflow_cap=0.35,
                   relaxed_area_pct=15.0):
    """-> (ok, [reasons]).  cells = movable cell count before the repair (None: the buffer fraction rule is skipped).
    The area limit is relaxed_area_pct (15) instead of max_area_pct (10) only when gpl_td_relaxed holds (util < 10 %, HPWL ratio <= 1.02,
    pass-2 added <= 10 % of pass-1); otherwise the old 10 % rule applies, and an area failure says whether the relaxed rule was unevaluated."""
    passes = gpl_td_passes(text)
    rel = gpl_td_relaxed(text)
    if rel["ok"]:
        max_area_pct = relaxed_area_pct
    bad = []
    for p in passes:
        if cells and p["buffers"] > max_buffer_frac * cells:
            bad.append(f"pass {p['index']}/{p['of']} inserted {p['buffers']} buffers > {max_buffer_frac:.0%} of {cells} cells")
        if p["area_pct"] is not None and p["area_pct"] > max_area_pct:
            bad.append(f"pass {p['index']}/{p['of']} repair_design area +{p['area_pct']:g} % > {max_area_pct:g} % ({rel['line']})")
    regions = gpl_cluster_regions(text)
    if regions and passes and passes[0]["overflow"] is not None and passes[0]["overflow"] < 0.5 and passes[0]["iteration"] is not None \
            and passes[0]["iteration"] <= 5:
        bad.append(f"first timing-driven pass fired at iteration {passes[0]['iteration']} on overflow {passes[0]['overflow']} "
                   f"with {regions} OT_LOGIC_CLUSTER regions (mean-over-regions trigger)")
    return (not bad), bad


_CL = re.compile(r"OT_CLAND released (\d+) FIRM cland cells")
_FT = re.compile(r"OT_FT_KEEP_FIRM released (\d+) keep_firm")


def dpl_firm_released(text):
    m, f = _CL.search(text), _FT.search(text)
    return (int(m.group(1)) if m else None), (int(f.group(1)) if f else 0)


def dpl_verdict(text):
    cl, ft = dpl_firm_released(text)
    if cl is None:
        return False, ["no 'OT_CLAND released N FIRM cland cells' line: the release scan did not run"]
    bad = []
    if cl:
        bad.append(f"FIRM released = {cl} cland cells (must be 0: DPL moved FIRM seats)")
    if ft:
        bad.append(f"FIRM released = {ft} keep_firm station cells (must be 0)")
    return (not bad), bad


def main(argv):
    if len(argv) < 3 or argv[1] not in ("gpl", "dpl"):
        print(__doc__)
        return 2
    rc = 0
    for path in argv[2:]:
        try:
            text = open(path, errors="replace").read()
        except OSError as e:
            print(f"{path}: {e}")
            return 2
        ok, why = (gpl_td_verdict(text) if argv[1] == "gpl" else dpl_verdict(text))
        if argv[1] == "gpl":
            for p in gpl_td_passes(text):
                print(f"{path}: TD pass {p['index']}/{p['of']} iter {p['iteration']} overflow {p['overflow']} buffers {p['buffers']} area +{p['area_pct']}%")
        if argv[1] == "gpl":
            print(f"{path}: {gpl_td_relaxed(text)['line']}")
        print(f"{path}: {'PASS' if ok else 'FAIL'}" + "".join(f"\n  - {w}" for w in why))
        rc = rc or (0 if ok else 1)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
