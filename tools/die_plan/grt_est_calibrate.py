#!/usr/bin/env python3
"""grt_est_calibrate.py -- per-family calibration of ADV-ROUTE-DEMAND against measured GRT overflow (class GRT-EST-OPTIMISTIC, QC-INT-R2-TOOLS 11-26).

Why: adv_route_demand is a plan-only RUDY estimate; its own calibration note says it ranks families but under-reads congestion inside them (est. peak
util stays under the 0.8 WARN line on types whose GRT then overflows 20k-85k).  This tool measures how optimistic it is per family and writes a
multiplier json that adv_route_demand reads in ADVISORY mode (it divides the usable supply by the multiplier; no multiplier file, or family 1.0, = old behaviour).

Family = fw | fe | st_a | coll (regex on the type name, FAMILIES below; other types have no family and are never scaled).
Multiplier of a family, from rows (type, measured GRT overflow):
    bad   = types with overflow >= OVERFLOW_BAD (default 2000 = a GRT that did not close, GRT-TRIAGE 'overflow_latest')
    q     = median estimated peak util of the bad types (est. = adv_route_demand.grid util of the plan's type, multiplier 1)
    m     = clamp(WARN_UTIL / q, 1, M_MAX) when len(bad) >= MIN_BAD, else 1.0 ("no-data": the family is listed, never scaled)
clean = rows with overflow < OVERFLOW_BAD whose calibrated peak (est x m) reaches WARN_UTIL: the price of the multiplier (false alarms) is reported.

    grt_est_calibrate.py build --plan PLAN.json --measured ROWS.tsv [--out grt_est_calibration.json]
    grt_est_calibrate.py triage GRT-TRIAGE.tsv > ROWS.tsv        (die, type, overflow_latest of the hub's GRT-TRIAGE table)
ROWS.tsv: type<TAB>overflow[<TAB>note]; a row whose type is not a plan type is matched by its base name (before "__cl") and skipped when none.
Feed more rows (signed / probe runs' congestion-N.rpt sums) and re-run; the json carries n per family so a reader sees how thin the evidence is.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
SCHEMA = "opentallas.grt_est_calibration.v1"
FAMILIES = (("fw", r"(^|_)fw(_|$)"), ("fe", r"(^|_)fe(_|$)"), ("st_a", r"(^|_)st_a(_|$)"), ("coll", r"^coll"))
OVERFLOW_BAD = 2000.0
MIN_BAD = 2
M_MAX = 4.0
WARN_UTIL = 0.8


def family_of(tn):
    for fam, rx in FAMILIES:
        if re.search(rx, str(tn)):
            return fam
    return None


def median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def est_peak(t):
    """peak estimated util of one plan type at multiplier 1 (None when the type has no legs / outline)"""
    import adv_route_demand as RD
    if not isinstance(t, dict) or not t.get("outline_um") or not (t.get("internal_stations") or t.get("ft_slots")):
        return None
    gr = RD.grid(t)
    return max((max(col) for col in gr["util"]), default=0.0)


def resolve(raw, name):
    P = raw.get("partition_types") or {}
    if name in P:
        return name
    base = name.split("__cl")[0]
    cands = sorted(n for n in P if n == base or n.split("__cl")[0] == base)
    return cands[0] if cands else None


def build(raw, rows, peak_fn=est_peak, bad=OVERFLOW_BAD, min_bad=MIN_BAD, m_max=M_MAX, warn=WARN_UTIL):
    """rows [(type, overflow)] -> calibration dict"""
    per = {}
    for name, ov in rows:
        tn = resolve(raw, name)
        fam = family_of(tn or name)
        if not tn or not fam:
            continue
        pk = peak_fn(raw["partition_types"][tn])
        if pk is None:
            continue
        per.setdefault(fam, []).append((tn, float(ov), pk))
    out = {}
    for fam, _rx in FAMILIES:
        rs = per.get(fam, [])
        badr = [r for r in rs if r[1] >= bad]
        if len(badr) >= min_bad and median([r[2] for r in badr]) > 0:
            q = median([r[2] for r in badr])
            m = round(min(m_max, max(1.0, warn / q)), 3)
            status = "calibrated"
        else:
            q, m, status = (median([r[2] for r in badr]) if badr else None), 1.0, "no-data"
        clean = [r for r in rs if r[1] < bad]
        out[fam] = dict(multiplier=m, status=status, n=len(rs), n_bad=len(badr), median_bad_est_peak=None if q is None else round(q, 3),
                        clean_false_alarms=sum(1 for r in clean if r[2] * m >= warn), n_clean=len(clean),
                        types=sorted({r[0] for r in rs})[:12])
    return dict(schema=SCHEMA, warn_util=warn, overflow_bad=bad, min_bad=min_bad, m_max=m_max, families=out)


def read_rows(path):
    rows = []
    for ln in Path(path).read_text().splitlines():
        p = ln.split("\t")
        if len(p) >= 2 and not ln.startswith("#"):
            try:
                rows.append((p[0].strip(), float(p[1])))
            except ValueError:
                continue
    return rows


def triage_rows(path):
    """die, type, ..., overflow_latest (column named overflow_latest) of a GRT-TRIAGE tsv -> [(type, overflow)]"""
    lines = [x for x in Path(path).read_text().splitlines() if x and not x.startswith("#")]
    hdr = lines[0].split("\t")
    it, io = hdr.index("type"), hdr.index("overflow_latest")
    out = []
    for ln in lines[1:]:
        p = ln.split("\t")
        if len(p) > io and p[io].strip().isdigit() and p[it] not in ("", "kit"):
            out.append((p[it], float(p[io])))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--plan", required=True)
    b.add_argument("--measured", required=True)
    b.add_argument("--out")
    t = sub.add_parser("triage")
    t.add_argument("tsv")
    a = ap.parse_args(argv)
    if a.cmd == "triage":
        for ty, ov in triage_rows(a.tsv):
            print(f"{ty}\t{ov:g}")
        return 0
    cal = build(json.loads(Path(a.plan).read_text()), read_rows(a.measured))
    txt = json.dumps(cal, indent=1) + "\n"
    if a.out:
        Path(a.out).write_text(txt)
    else:
        print(txt, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
