"""DH58-RFCLK: launch-side negative-level lockup latch form on HEAD (estimate). Same model as
tools/die_plan/s81_pd9/latch_eval_s81.py (PATH-S81-PD9), adapted to the current die_sta_related signatures
(endpoint_slacks dd=, hold_buffer_model part_bits=). Runs die_sta_related.main unchanged.
  setup_after = setup - (T/2 + latch_ckq - launch_clkq_max)      (TT)
  hold_after  = hold + T/2 + latch_ckq_min - launch_clkq_min     (FF)"""
import sys, json
sys.path.insert(0, sys.argv.pop(1))
import die_sta_related as R
cap = []
orig = R.hold_buffer_model
def wrap(tt, ff, *a, **kw):
    cap.append((tt, ff)); return orig(tt, ff, *a, **kw)
R.hold_buffer_model = wrap
ckq_by, ckqmin_by = {}, {}
oes = R.endpoint_slacks
def es(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, models_a, models_b, *a, **kw):
    for m in models_a:
        ckq_by[m["name"]] = max(ckq_by.get(m["name"], -1e9), m["clkq_max"])
        ckqmin_by[m["name"]] = min(ckqmin_by.get(m["name"], 1e9), m["clkq_min"])
    return oes(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, models_a, models_b, *a, **kw)
R.endpoint_slacks = es
argv = sys.argv[1:]
def take(flag):
    i = argv.index(flag); v = argv[i + 1]; del argv[i:i + 2]; return v
ckq = float(take("--latch-ckq")); ckqmin = float(take("--latch-ckq-min")); dump = take("--dump")
R.main(argv)
T = R.PERIOD_PS
res = {}
for name, idx in (("intra", 0), ("seam", 1)):
    if idx >= len(cap): continue
    tt, ff = cap[idx]
    keys = [k for k in ff if k in tt]
    if not keys: res[name] = dict(paths=0); continue
    s2 = [(tt[k][0] - (T / 2 + ckq - ckq_by.get(k[3], 0.0)), k) for k in keys]
    h2 = [(ff[k][1] + T / 2 + ckqmin - ckqmin_by.get(k[3], 0.0), k) for k in keys]
    s0 = [(tt[k][0], k) for k in keys]; h0 = [(ff[k][1], k) for k in keys]
    ws, wh = min(s2), min(h2)
    res[name] = dict(paths=len(keys), tt_setup_before_ps=round(min(s0)[0], 2), ff_hold_before_ps=round(min(h0)[0], 2),
                     hold_neg_before=sum(1 for v, _ in h0 if v < 0),
                     tt_setup_after_ps=round(ws[0], 2), setup_neg_after=sum(1 for v, _ in s2 if v < 0),
                     worst_setup=[str(x) for x in ws[1]], ff_hold_after_ps=round(wh[0], 2), worst_hold=[str(x) for x in wh[1]],
                     hold_neg_after=sum(1 for v, _ in h2 if v < 0),
                     worst_hold_before=[str(x) for x in min(h0)[1]])
    # selective form: latch only where the pair keeps TT setup >= 0 with it (zero/short-logic face hops), plain elsewhere
    sel = [(h2[i][0] if s2[i][0] >= 0 else h0[i][0], s2[i][0] if s2[i][0] >= 0 else s0[i][0], s2[i][0] >= 0, keys[i]) for i in range(len(keys))]
    res[name].update(sel_latched=sum(1 for x in sel if x[2]), sel_ff_hold_ps=round(min(x[0] for x in sel), 2),
                     sel_hold_neg=sum(1 for x in sel if x[0] < 0), sel_tt_setup_ps=round(min(x[1] for x in sel), 2),
                     sel_worst_hold=[str(v) for v in min(sel)[3]],
                     sel_hold_neg_by_where_top=sorted(__import__("collections").Counter(str(x[3][2]).split("->")[0] for x in sel if x[0] < 0).items(), key=lambda kv: -kv[1])[:12])
json.dump(dict(model=dict(period_ps=T, latch_ckq_ps=ckq, latch_ckq_min_ps=ckqmin, launch_clkq_credit=ckq_by,
                          launch_clkq_min_credit=ckqmin_by, form="launch-side neg-level lockup latch on every non-landed pair"), **res),
          open(dump, "w"), indent=1)
print("LATCH", json.dumps(res))
