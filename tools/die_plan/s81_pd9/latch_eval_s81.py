"""PATH-S81-PD9 seam hold form (b): LAUNCH-side negative-level lockup latch per zero-logic seam endpoint (DIAGNOSTIC,
own model on top of the shared main die_sta_related.py; COORD 02:54 correction: launch side, setup-checked first).
The latch sits at the launch partition's pin-register output, transparent while its clock is low; it releases the
launched bit at the falling edge T/2 + latch ck->q, so the launch path's own clk->q (budget register or core ETM
out_max) is replaced by T/2 + latch ck->q (credited):
  setup_after = setup - (T/2 + latch_ckq - launch_clkq_max)
  hold_after  = hold + T/2 + latch_ckq_min - launch_clkq_min   (FF; the launch path's own min clk->q is replaced too)
Latch arcs: DLLx1_ASAP7_75t_R ck->q ~73 ps (command line, UNCHECKED until OpenSTA regchar).
Runs die_sta_related.main unchanged; endpoint records captured through hold_buffer_model (needs --hold-buffers HB4)
and launch clk->q per endpoint model name through endpoint_slacks (first corner seen = TT)."""
import sys, json
import die_sta_related as R
cap = []
orig = R.hold_buffer_model
def wrap(tt, ff, bits=None, hb=R.HB4):
    cap.append((tt, ff))
    return orig(tt, ff, bits=bits, hb=hb)
R.hold_buffer_model = wrap
ckq_by_name, ckqmin_by_name = {}, {}
oes = R.endpoint_slacks
def es(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, models_a, models_b):
    for m in models_a:   # TT runs first and is slower: max clkq_max = TT launch arc, min clkq_min = FF launch arc
        ckq_by_name[m["name"]] = max(ckq_by_name.get(m["name"], -1e9), m["clkq_max"])
        ckqmin_by_name[m["name"]] = min(ckqmin_by_name.get(m["name"], 1e9), m["clkq_min"])
    return oes(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, models_a, models_b)
R.endpoint_slacks = es
argv = sys.argv[1:]
i = argv.index("--latch-ckq"); ckq = float(argv[i + 1]); del argv[i:i + 2]
j = argv.index("--latch-ckq-min"); ckqmin = float(argv[j + 1]); del argv[j:j + 2]
o = argv.index("--dump"); dump = argv[o + 1]; del argv[o:o + 2]
R.main(argv)
T = R.PERIOD_PS
res = {}
for name, idx in (("intra", 0), ("seam", 1)):
    tt, ff = cap[idx]
    keys = [k for k in ff if k in tt]
    s2 = [(tt[k][0] - (T / 2 + ckq - ckq_by_name.get(k[3], 0.0)), k) for k in keys]
    h2 = [(ff[k][1] + T / 2 + ckqmin - ckqmin_by_name.get(k[3], 0.0), k) for k in keys]
    ws, wh = min(s2), min(h2)
    res[name] = dict(paths=len(keys), tt_setup_after_ps=round(ws[0], 2), setup_neg_after=sum(1 for v, _ in s2 if v < 0),
                     worst_setup=[str(x) for x in ws[1]], ff_hold_after_ps=round(wh[0], 2),
                     hold_neg_after=sum(1 for v, _ in h2 if v < 0),
                     real_setup_neg_after=sum(1 for v, k in s2 if v < 0 and tt[k][2]),
                     setup_before_min_ps=round(min(tt[k][0] for k in keys), 2),
                     hold_before_min_ps=round(min(ff[k][1] for k in keys), 2),
                     hold_neg_before=sum(1 for k in keys if ff[k][1] < 0))
json.dump(dict(model=dict(period_ps=T, latch_ckq_ps=ckq, latch_ckq_min_ps=ckqmin, launch_clkq_credit=ckq_by_name,
                          launch_clkq_min_credit=ckqmin_by_name,
                          form="launch-side neg-level lockup latch, release at falling edge, launch clkq credited"), **res),
          open(dump, "w"), indent=1)
print("LATCH", json.dumps(res))
