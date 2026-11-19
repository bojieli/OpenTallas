#!/usr/bin/env python3
"""skew_calib.py -- PRECHECK-1119: fit the in-tap skew estimate of kit_scan.py against measured CTS tap skew.

  skew_calib.py --roots /srv/opentallas-scratch2/claude/ot-jobs [--families a,b] --out DIR

Per kit with both 3_place.odb and a CTS log carrying `OT_TAP_INSERTION tap=<t> sinks=<n> ins_ps=<i> skew_ps=<s>`:
registers from 3_place.odb (placed_hops_or.py, cached in the kit_scan state), assigned to the kit taps as kit_scan does;
per tap (>= 100 measured sinks, FABLE-CLOSURE-STRATEGY's sink-weighted convention) features of the sink distance to the
tap (p98 - p2, p90 - p10, max, mean, n) against the measured skew_ps.  Writes taps.tsv, kits.tsv and fit.json (least
squares skew = a x feature + b per feature; kit-level agreement on the 60 / 100 ps bands).
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import kit_scan as KS  # noqa: E402

TAPLINE = re.compile(r"OT_TAP_INSERTION tap=(\S+) sinks=(\d+) ins_ps=([-\d.]+) skew_ps=([-\d.]+)")
MIN_SINKS = 100


def measured(kit):
    logs = sorted(Path(kit, "work/run/logs").glob("*/*/base/4_1_cts.log"))
    out = {}
    if logs:
        for m in TAPLINE.finditer(logs[0].read_text(errors="replace")):
            out[m.group(1)] = (int(m.group(2)), float(m.group(4)))    # the last line per tap wins (after balancing)
    return out


def feats(d):
    d = sorted(d)
    q = lambda f: d[int(f * (len(d) - 1))]  # noqa: E731
    return dict(p98_p2=q(0.98) - q(0.02), p90_p10=q(0.9) - q(0.1), dmax=d[-1], dmean=sum(d) / len(d), n=len(d))


def fit(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    a = sxy / sxx if sxx else 0.0
    b = my - a * mx
    ss = sum((y - (a * x + b)) ** 2 for x, y in zip(xs, ys))
    st = sum((y - my) ** 2 for y in ys)
    return a, b, (1 - ss / st) if st else 0.0


def band(v):
    return 0 if v < 60 else (1 if v < 100 else 2)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", required=True)
    ap.add_argument("--families", default="")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mem-gb", type=int, default=14)
    ap.add_argument("--cached-only", action="store_true", help="use only kits whose placed scan is already cached")
    a = ap.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fams = [f for f in a.families.split(",") if f]
    rows, kits = [], []
    for cfg in sorted(Path(a.roots).glob("*/work/config.mk")):
        kit = cfg.parent.parent
        tn = KS.kit_type(kit)
        if fams and not any(tn.startswith(f) for f in fams):
            continue
        meas = measured(kit)
        odb = KS.stage_file(kit, "3_place.odb")
        if not odb or not any(n >= MIN_SINKS for n, _ in meas.values()):
            continue
        raw = KS.STATE / f"{kit.name}.placed_raw.json"
        KS.STATE.mkdir(parents=True, exist_ok=True)
        if not raw.exists() and (a.cached_only or KS.run_placed(kit, odb, raw, a.mem_gb) != 0):
            continue
        ph = json.loads(raw.read_text())
        taps, cap = KS.taps_of(kit)
        if not taps or not ph.get("regs"):
            continue
        mem = KS.assign_taps(taps, [tuple(r) for r in ph["regs"]], int(min(cap or 1000, 1500)), KS.CBC.TAP_RADIUS_UM)
        kw = []
        for t, (n, s) in meas.items():
            if n < MIN_SINKS or len(mem.get(t, [])) < 8:
                continue
            f = feats(mem[t])
            rows.append(dict(kit=kit.name, type=tn, tap=t, sinks=n, skew_ps=s, **f))
            kw.append((s, f))
        if kw:
            ms, mf = max(kw, key=lambda r: r[0])
            kits.append(dict(kit=kit.name, type=tn, meas_worst=ms, est_feats_worst={k: max(f[k] for _, f in kw) for k in ("p98_p2", "p90_p10", "dmax")}))
        print(f"{tn}: {len(kw)} taps", flush=True)
    res = dict(taps=len(rows), kits=len(kits), fits={})
    for k in ("p98_p2", "p90_p10", "dmax", "dmean"):
        if len(rows) > 3:
            a_, b_, r2 = fit([r[k] for r in rows], [r["skew_ps"] for r in rows])
            ka = [(a_ * kk["est_feats_worst"].get(k, 0) + b_, kk["meas_worst"]) for kk in kits if k in kk["est_feats_worst"]]
            agree = sum(1 for e, m in ka if band(e) == band(m))
            res["fits"][k] = dict(a=round(a_, 4), b=round(b_, 1), r2=round(r2, 3), kit_band_agree=f"{agree}/{len(ka)}")
    with open(out / "taps.tsv", "w") as fh:
        cols = ["kit", "type", "tap", "sinks", "skew_ps", "p98_p2", "p90_p10", "dmax", "dmean", "n"]
        fh.write("\t".join(cols) + "\n")
        for r in rows:
            fh.write("\t".join(str(round(r[c], 1) if isinstance(r[c], float) else r[c]) for c in cols) + "\n")
    (out / "kits.json").write_text(json.dumps(kits, indent=1))
    (out / "fit.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
