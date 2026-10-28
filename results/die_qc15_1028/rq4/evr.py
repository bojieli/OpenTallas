# DIE-QC-15: routed (clock GRT) recheck of A0 trunk q4: spread (regs + child pins + 250/202.5), duty (spice-scaled),
# MPW (DFFHQNx1 lib table, conservative TT table at FF), max clock slew; placement-RC q4 alongside. usage: evr.py
import json, statistics as st
T = 833.0; HALF = T / 2; K = {"TT": 1.0485, "FF": 1.0552}
IDX = [5, 10, 20, 40, 80, 160, 320]; MPWT = [39.99, 42.25, 42.25, 45.32, 80.57, 161.13, 321.05]
def mpw(s):
    if s <= IDX[0]: return MPWT[0]
    for i in range(len(IDX) - 1):
        if s <= IDX[i + 1]: return MPWT[i] + (s - IDX[i]) / (IDX[i + 1] - IDX[i]) * (MPWT[i + 1] - MPWT[i])
    return MPWT[-1]
tr = json.load(open("trunk_q4.json")); CI = {k: tuple(v) for k, v in tr["summary"]["child_ins"].items()}
out = {}
for C, ci in (("TT", 0), ("FF", 1)):
    regs = []; tot = []; duty = []; mpwf = []; slews = []; T_ = {}
    src = None
    for l in open(f"arr_rq4_{C}.txt"):
        p = l.split()
        if p[0] == "S":
            rise, fall, slew = float(p[4]), float(p[5]), float(p[7])
            if p[2].startswith("ICG"): src = (rise, fall); continue
            if p[2] in CI: tot.append(rise + CI[p[2]][ci]); continue
            regs.append(rise); slews.append(slew)
            hi = HALF + K[C] * ((fall - rise) - HALF); lo = T - hi
            duty.append(hi / T)
            if min(hi, lo) < mpw(slew): mpwf.append(p[1])
        elif p[0] == "T":
            T_[p[1]] = float(p[5]); slews.append(float(p[5]))
    allv = regs + tot
    out[C] = dict(regs=dict(n=len(regs), mean=round(st.mean(regs), 1), min=round(min(regs), 1), max=round(max(regs), 1)),
                  child_total=dict(n=len(tot), min=round(min(tot), 1), max=round(max(tot), 1)),
                  all=dict(min=round(min(allv), 1), max=round(max(allv), 1), spread=round(max(allv) - min(allv), 1)),
                  duty=dict(min=round(min(duty), 4), max=round(max(duty), 4), outside_45_55=sum(1 for d in duty if not 0.45 <= d <= 0.55)),
                  mpw_fail=len(mpwf), max_clock_slew_ps=round(max(slews), 1), slew_gt_320=sum(1 for s in slews if s > 320),
                  icg_clk=src)
    pl = json.load(open("../../die-qc14-1028/a0trunk/evtr_q4.json"))[C]
    out[C]["placement_rc_q4"] = dict(all=pl["all"], regs_mean=pl["regs"]["mean"])
print(json.dumps(out, indent=1)); json.dump(out, open("evr_q4.json", "w"), indent=1)
