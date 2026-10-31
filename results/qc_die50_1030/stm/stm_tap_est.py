"""DIE-QC-50/stm: density tap split estimate for the 11 plan_qc49 stm types.

Sinks = the MEASURED die-clock sinks of each type's plan_qc49 placed kit (QC-KITS-AA 3_place, AUTO-GEOM geom.tsv:
clock pins traced to clk|clk_t<i>; forwarded edge-clock ring flops excluded), binned with taps.bins_from_dump rules (10.8 um).  A type whose kit is not yet
placed uses the bins of its nearest placed variant (named PROXY, UNCHECKED until its own placement lands).
For each candidate (tap_max_sinks, tap_target_sinks, tap_radius_um) the plan taps are computed by the MAIN
tools (schema.tap_grid -> taps.density_taps) and judged with the AUTO-GEOM rule on the measured flops:
nearest tap, uncapped (geom_rules.clock_metrics 'nearest' mode) -> max sinks per tap (limit 1500) and the
farthest sink from its nearest tap (clock_reach limit 220).
usage: stm_tap_est.py PLAN GEOMDIR OUTDIR [--write-bins]"""
import argparse, json, math, sys, copy
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import schema as S, taps as TP
sys.path.insert(0, str(ROOT / "tools" / "autopilot"))
import geom_rules as GR

STM = ['slw_stm_v3', 'sle_stm_v3', 'slw_stm_v1__cle34a73c3', 'slw_stm_v1__cl05fc43f7__cl2086fa2c',
       'slw_stm_v1__cl05fc43f7__cl389df4e9', 'slw_stm_v2__cl1ca9c415', 'slw_stm_v2__cl9beb65e6',
       'sle_stm_v1__cl27746664', 'sle_stm_v1__clbe630b9c', 'sle_stm_v2__cl7b3062fa', 'sle_stm_v2__cl55be2264']
PROXY = {'sle_stm_v1__cl27746664': 'sle_stm_v1__clbe630b9c', 'slw_stm_v1__cle34a73c3': 'slw_stm_v1__cl05fc43f7__cl2086fa2c'}
BIN = 10.8
BINDIR = "physical/die_plan/qwen_compute/plan_of_record/sink_bins"


def flops(tsv):
    """die-clock sinks only: sequential / macro clock pins whose clock net traces (through buffers / inverters /
    clock cells, geom_rules.clock_metrics rule) to a grid tap port clk|clk_t<i>.  Ring flops on forwarded edge clocks
    (fclk_in_*) are not die-tap sinks and are left out."""
    D = GR.Design(str(tsv))
    memo = {}
    def root(n):
        path, cur, r = [], n, None
        while len(path) < 64:
            if cur in memo:
                r = memo[cur]; break
            path.append(cur)
            dr = D.nets[cur][1]
            if dr is None:
                break
            if dr[0] == "p":
                r = dr[1]; break
            ins = D.cell_in.get(dr[1], [])
            if D.kind(dr[1]) not in ("B", "K") or not ins:
                break
            ck = [x for x, c in ins if c]
            cur = ck[0] if ck else ins[0][0]
        for p in path:
            memo[p] = r
        return r
    out = []
    for cid, c in D.cells.items():
        if c[0] not in "SM":
            continue
        for n, is_clk in D.cell_in.get(cid, []):
            if is_clk:
                r = root(n)
                if r is not None and GR.GRID_TAP_RE.match(D.pin_by_k[r]["name"]):
                    out.append(GR.ctr(c))
    return out


def bins(pts):
    c = Counter((int(x // BIN), int(y // BIN)) for x, y in pts)
    return dict(bin_um=BIN, n=sum(c.values()), source="QC-KITS-AA plan_qc49 3_place geom.tsv: die-clock sinks rooted at clk|clk_t<i> (edge-clock ring flops excluded)",
                bins=[[round((i + 0.5) * BIN, 3), round((j + 0.5) * BIN, 3), n] for (i, j), n in sorted(c.items())])


def judge(taps_xy, pts):
    load = Counter(); far = 0.0
    for x, y in pts:
        d, j = min((abs(x - a) + abs(y - b), j) for j, (a, b) in enumerate(taps_xy))
        load[j] += 1; far = max(far, d)
    v = [load.get(j, 0) for j in range(len(taps_xy))]
    return max(v), min(v), round(far, 1)


ap = argparse.ArgumentParser()
ap.add_argument("plan"); ap.add_argument("geomdir"); ap.add_argument("out")
ap.add_argument("--write-bins", action="store_true")
ap.add_argument("--band-keepouts", action="store_true", help="clock.keepouts_um = the type's FIRM landing ring bands")
ap.add_argument("--cands", default="1500:1200:200,1200:960:200,1000:800:180")
a = ap.parse_args()
raw0 = json.load(open(a.plan))
out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
F = {}
for t in STM:
    src = PROXY.get(t, t) if not (Path(a.geomdir) / t / "geom.tsv").exists() else t
    F[t] = (src, flops(Path(a.geomdir) / src / "geom.tsv"))
    if a.write_bins:
        (ROOT / BINDIR).mkdir(parents=True, exist_ok=True)
        b = bins(F[t][1]); b["type"] = t; b["placed_kit"] = src
        (ROOT / BINDIR / f"{t}.json").write_text(json.dumps(b) + "\n")
rep = dict(types={}, cands=a.cands)
for t in STM:
    g = S.Plan(raw0, a.plan)
    base = [(x, y) for _, x, y in S.tap_grid(g, t)]
    rep["types"][t] = dict(placed_kit=F[t][0], proxy=F[t][0] != t, flops=len(F[t][1]),
                           r4_grid=dict(taps=len(base), judge=judge(base, F[t][1])))
for c in a.cands.split(","):
    cap, tgt, rad, *mn = c.split(":")
    raw = copy.deepcopy(raw0)
    for t in STM:
        ck = raw["partition_types"][t]["clock"]
        ck.update(tap_mode="density", tap_max_sinks=int(cap), tap_target_sinks=int(tgt), tap_radius_um=float(rad),
                  sink_bins_file=f"{BINDIR}/{t}.json")
        if mn:
            ck["tap_min_sinks"] = int(mn[0])
        if a.band_keepouts:
            ck["keepouts_um"] = [list(b["rect_um"]) for b in ck["landing_contract"]["bands"].values()]
    P = S.Plan(raw, a.plan)
    for t in STM:
        tg = S.tap_grid(P, t)
        xy = [(x, y) for _, x, y in tg]
        mx, mn, far = judge(xy, F[t][1])
        rep["types"][t][c] = dict(taps=len(tg), nearest_max=mx, nearest_min=mn, reach=far,
                                  tap_xy=[[n, round(x, 3), round(y, 3)] for n, x, y in tg])
        print(t, c, "taps", len(tg), "nearest max/min", mx, mn, "reach", far, "| R4", rep["types"][t]["r4_grid"]["judge"], flush=True)
(out / "tap_est.json").write_text(json.dumps(rep, indent=1) + "\n")
