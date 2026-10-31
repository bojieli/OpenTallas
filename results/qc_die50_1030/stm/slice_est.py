"""DIE-QC-50/stm: analytic per-type estimate for every plan_qc49 slice type (fe fw hc sc st stm su ctl).
aspect from the outline; fill from QC-KITS-AB est_qc49.txt (synth um2 / free area) where present;
die-clock sinks = planned sinks (taps.sink_sites: face + ft registers; core contents NOT included -> lower bound)
or, for stm, the measured placed sink bins; R4 grid max sinks (nearest); density taps at 1200/960/200 with ring-band
keep-outs; ft slots whose registers cannot meet pin_reg<=30 on both faces AND hop<=405 (stations < ceil(span/405)+1).
usage: slice_est.py PLAN EST_TXT OUT.json"""
import json, math, re, sys, copy
from collections import defaultdict
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S, taps as TP
plan, est, outp = sys.argv[1:4]
raw = json.load(open(plan))
fill = {}
for ln in open(est):
    a = ln.split()
    if len(a) > 6 and a[0] != "type" and a[6] not in ("-",):
        try: fill[a[0]] = float(a[6])
        except ValueError: pass
cls = lambda tn: (re.match(r"sl[ew]_([a-z]+)", tn).group(1) if re.match(r"sl[ew]_([a-z]+)", tn) else None)
types = [tn for tn in raw["partition_types"] if cls(tn)]
P0 = S.Plan(raw, plan)
r2 = copy.deepcopy(raw)
BIN = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"
for tn in types:
    ck = r2["partition_types"][tn].setdefault("clock", {})
    if ck.get("tap_mode"): continue
    ck.update(tap_mode="density", tap_max_sinks=1200, tap_target_sinks=960, tap_radius_um=200.0)
    if (ROOT / BIN / f"{tn}.json").exists(): ck["sink_bins_file"] = f"{BIN}/{tn}.json"
    bands = (ck.get("landing_contract") or {}).get("bands") or {}
    if bands and not ck.get("keepouts_um"): ck["keepouts_um"] = [list(b["rect_um"]) for b in bands.values()]
P1 = S.Plan(r2, plan)
rows = {}
for tn in types:
    t = raw["partition_types"][tn]; w, h = t["outline_um"]
    n_inst = sum(1 for q in raw["partitions"] if q["type"] == tn)
    try:
        sk = TP.sink_sites(P1, tn)
        nsink = sum(p[2] for p in sk)
        g = [(x, y) for _, x, y in S.tap_grid(P0, tn)]
        ld = defaultdict(float)
        for x, y, wt in sk:
            ld[min(range(len(g)), key=lambda j: abs(x - g[j][0]) + abs(y - g[j][1]))] += wt
        r4max = max(ld.values()) if ld else 0
        nd = len(S.tap_grid(P1, tn))
    except Exception as e:
        nsink, r4max, nd = None, None, "ERR " + str(e)[:80]
    bad = []
    for f in t.get("ft_slots", []):
        a, b = f["in_face"], f["out_face"]
        span = (w if {a, b} == {"E", "W"} else h if {a, b} == {"N", "S"} else (w + h) / 2)
        need = math.ceil(span / 405.0) + 1
        if f["stations"] < need: bad.append((f["name"], f["width"], f["stations"], need, round(span)))
    rows[tn] = dict(cls=cls(tn), n=n_inst, outline=[w, h], aspect=round(max(w, h) / min(w, h), 3), fill=fill.get(tn),
                    sinks=nsink, sinks_measured=(ROOT / BIN / f"{tn}.json").exists(), r4_taps=len(S.tap_grid(P0, tn)),
                    r4_max_sinks=r4max, density_taps=nd, ft_short=bad, ft_short_bits=sum(x[1] for x in bad))
json.dump(rows, open(outp, "w"), indent=1)
agg = defaultdict(list)
for tn, r in rows.items(): agg[r["cls"]].append(r)
for c, rs in sorted(agg.items()):
    f = [r["fill"] for r in rs if r["fill"] is not None]
    print(f"{c:4s} types {len(rs):2d} inst {sum(r['n'] for r in rs):3d} aspect {min(r['aspect'] for r in rs)}-{max(r['aspect'] for r in rs)}"
          f" fill {min(f) if f else '-'}-{max(f) if f else '-'}"
          f" sinks {min((r['sinks'] or 0) for r in rs):.0f}-{max((r['sinks'] or 0) for r in rs):.0f}"
          f" R4 max {min((r['r4_max_sinks'] or 0) for r in rs):.0f}-{max((r['r4_max_sinks'] or 0) for r in rs):.0f}"
          f" dens taps {[r['density_taps'] for r in rs][:4]} ft_short slots/bits max {max(len(r['ft_short']) for r in rs)}/{max(r['ft_short_bits'] for r in rs)}")
