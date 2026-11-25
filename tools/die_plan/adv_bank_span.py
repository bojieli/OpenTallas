#!/usr/bin/env python3
"""adv_bank_span.py -- PRECHECK advisory BANK-SPAN (HEAD-ALLFIX 11-25, from FABLE-RC-HEAD bank_span_check draft).

SRAM banks of one memory (same parent, <parent>.g_bank[k].u_m in hard_cores) share one write-data register slice.  A bank
seated farther than the registered-hop reach from its siblings forces an unregistered write-data leg longer than reach
(HEAD W4b hd_lep0N_w: u_rg2 g_safe_write g_bank[3] 480 um leg, TT setup -151 ps; W6 bank groups split across macro columns).
Per type and bank group: centre-to-centre span; WARN FAIL-SPAN when span > REACH_UM (405, plan reach), WARN WIDE when
span > WARN_UM (250: 833 ps minus macro setup and one cross-tap step).  Report only: never changes the PRE verdict.

    python3 adv_bank_span.py PLAN [--types a,b] [--reach 405] [--warn 250]     (rc 1 when any group is over --reach)
"""
import argparse
import json
import math
import re
import sys

REACH_UM = 405.0
WARN_UM = 250.0
BANK_RE = re.compile(r"^(.*)\.g_bank\\?\[(\d+)\\?\]\.u_m$")


def _box(h):
    x, y = h["origin_um"]
    w, hh = h["outline_um"]
    if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
        w, hh = hh, w
    return x, y, w, hh


def groups(t):
    """{parent: [(k, cx, cy)]} of the bank groups of one partition type"""
    g = {}
    for h in t.get("hard_cores") or []:
        m = BANK_RE.match(str(h.get("inst", "")))
        if not m or "origin_um" not in h or "outline_um" not in h:
            continue
        x, y, w, hh = _box(h)
        g.setdefault(m.group(1), []).append((int(m.group(2)), x + w / 2.0, y + hh / 2.0))
    return {p: v for p, v in g.items() if len(v) >= 2}


def judge(v, reach=REACH_UM, warn=WARN_UM):
    span = max(math.hypot(a[1] - b[1], a[2] - b[2]) for a in v for b in v)
    cx = sorted(a[1] for a in v)[len(v) // 2]
    cy = sorted(a[2] for a in v)[len(v) // 2]
    far = max(v, key=lambda a: math.hypot(a[1] - cx, a[2] - cy))
    verdict = "FAIL-SPAN" if span > reach else ("WIDE" if span > warn else "ok")
    return verdict, span, far, (cx, cy)


def check(raw, types=None, reach=REACH_UM, warn=WARN_UM):
    out = []
    pt = raw.get("partition_types") or {}
    for tn in (types or sorted(pt)):
        t = pt.get(tn)
        if not isinstance(t, dict):
            continue
        for p, v in sorted(groups(t).items()):
            verdict, span, far, med = judge(v, reach, warn)
            if verdict != "ok":
                out.append((verdict, tn, p, len(v), span, far, med))
    return out


def findings(raw, plan_path, tree=None, **_kw):
    try:
        rows = check(raw)
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [f"WARN ADV-BANK-SPAN not checked: {type(e).__name__}: {str(e)[:200]}"]
    return [f"WARN ADV-BANK-SPAN {v} {tn} {p}: {n} banks span {s:.0f} um (reach {REACH_UM:g}, warn {WARN_UM:g}); "
            f"outlier g_bank[{f[0]}] at ({f[1]:.0f},{f[2]:.0f}), median ({m[0]:.0f},{m[1]:.0f})" for v, tn, p, n, s, f, m in rows]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="adv_bank_span", description=__doc__.split("\n\n")[0])
    ap.add_argument("plan")
    ap.add_argument("--types", default="")
    ap.add_argument("--reach", type=float, default=REACH_UM)
    ap.add_argument("--warn", type=float, default=WARN_UM)
    a = ap.parse_args(argv)
    raw = json.load(open(a.plan))
    rows = check(raw, [t for t in a.types.split(",") if t] or None, a.reach, a.warn)
    for v, tn, p, n, s, f, m in rows:
        print(f"{v} {tn} {p}: {n} banks span {s:.0f} um; outlier g_bank[{f[0]}] at ({f[1]:.0f},{f[2]:.0f}), median ({m[0]:.0f},{m[1]:.0f})")
    print(f"bank groups over reach: {sum(1 for r in rows if r[0] == 'FAIL-SPAN')}, over warn: {sum(1 for r in rows if r[0] == 'WIDE')}")
    return 1 if any(r[0] == "FAIL-SPAN" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
