#!/usr/bin/env python3
"""DIE-S81-7 (die-local driver, no shared-tool edit): rebuild ONLY the clock tree of kit F with the kit_detour.py patches
(DIE-S81-5) and main/QC-4 die_trial clock_kit, same arguments as kit_F.sh.  With --cal-region R --cal JSON the
region-DME delay model (die_trial.STAGE_1X_TT, d = n d0 + k1 L + k2 L^2/n) is replaced by the ROUTED fit of kit F's
15,856 region-DME legs (fit_stage.py) while region R's tree is built; every other region keeps the shipped model.
    clk_g.py OUT_CLOCK_DIR [--cal-region R --cal stage_fit.json]"""
import json, os, sys, argparse
from pathlib import Path
ap = argparse.ArgumentParser(); ap.add_argument("out"); ap.add_argument("--cal-region"); ap.add_argument("--cal")
a = ap.parse_args()
WT = Path(os.environ["OT_KIT_WT"]); O = "/srv/opentallas-scratch2/claude/die-s81-5"
sys.path.insert(0, str(WT / "tools" / "die_plan"))
import die_trial as DT
import schema as S
# kit_detour.py 1.6 patches (identical to kit F)
DT.DETOUR_SPAN_X = 1.6
DT.leg_blocked_run = lambda site, a_, b, step=1.08: float("inf")
_ld = DT.legal_detour
def _ld_retry(site, a_, b, step=5.4, margin=600.0, turn_um=20.0):
    for st, m in ((step, margin), (step, 1500.0), (2.16, margin), (2.16, 1500.0)):
        poly = _ld(site, a_, b, step=st, margin=m, turn_um=turn_um)
        if poly is not None:
            return poly
    return None
DT.legal_detour = _ld_retry
regions = json.loads(Path(f"{O}/feed/map_part.json").read_text())["part_region"]
if a.cal_region:
    fit = tuple(json.load(open(a.cal))["fit"]); ship = DT.STAGE_1X_TT; _dme = DT.dme_region_tree; hits = []
    def dme_cal(site, taps, *k, **kw):
        rs = {regions[t[0]] for t in taps}
        if rs == {a.cal_region}:
            DT.STAGE_1X_TT = fit; hits.append(len(taps))
            try:
                return _dme(site, taps, *k, **kw)
            finally:
                DT.STAGE_1X_TT = ship
        return _dme(site, taps, *k, **kw)
    DT.dme_region_tree = dme_cal
P = S.Plan(S.load(f"{O}/plan_s5.json"))
nodes, segs, leaf_legs, cm = DT.clock_kit(P, Path(a.out), 200.0, 250.0, False, False, True, regions, tree_form="link_htree",
                                          tree_opts={"feed": f"{O}/feed/feed_part_spine.json"}, clock_rc="1x",
                                          region_dme="delay")
print("CLK_DONE", json.dumps(cm)[:1500])
if a.cal_region:
    print("CAL_HITS", hits, "fit", fit)
