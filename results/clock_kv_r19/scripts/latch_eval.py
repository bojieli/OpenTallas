"""CLOCK-KV-R19 seam form (b) evaluation: negative-level lockup latch per zero-logic seam bit (DIAGNOSTIC, own model).
Runs die_sta_related main with the per-endpoint records captured, then per seam endpoint path:
  latch transparent while its clock is low; it releases the launched bit at the falling edge (+T/2) ->
  hold_after = hold + T/2 - lat_hold_pen ; setup_after = setup - T/2 - (latch ck->q max - 0) .
Latch arcs: DLLx1_ASAP7_75t_R estimate passed on the command line (UNCHECKED until OpenSTA regchar)."""
import sys, json, pickle
sys.argv = [sys.argv[0]] + sys.argv[1:]
import die_sta_related as R
cap = {}
orig = R.hold_buffer_model
def wrap(tt, ff, bits=None, hb=R.HB4):
    cap.setdefault("n", 0); cap["n"] += 1
    cap[len(cap)] = (tt, ff)
    return orig(tt, ff, bits=bits, hb=hb)
R.hold_buffer_model = wrap
i = sys.argv.index("--latch-ckq"); ckq = float(sys.argv[i + 1]); del sys.argv[i:i + 2]
o = sys.argv.index("--dump"); dump = sys.argv[o + 1]; del sys.argv[o:o + 2]
R.main(sys.argv[1:])
T = R.PERIOD_PS
res = {}
for name, idx in (("intra", 1), ("seam", 2)):
    tt, ff = cap[idx]
    keys = [k for k in ff if k in tt]
    s2 = [(tt[k][0] - T / 2 - ckq, k) for k in keys]
    h2 = [(ff[k][1] + T / 2, k) for k in keys]
    ws, wh = min(s2), min(h2)
    res[name] = dict(paths=len(keys), tt_setup_after_ps=round(ws[0], 2), setup_neg_after=sum(1 for v, _ in s2 if v < 0),
                     worst_setup=list(ws[1]), ff_hold_after_ps=round(wh[0], 2), hold_neg_after=sum(1 for v, _ in h2 if v < 0),
                     real_setup_neg_after=sum(1 for v, k in s2 if v < 0 and tt[k][2]),
                     setup_before_min_ps=round(min(tt[k][0] for k in keys), 2))
json.dump(dict(model=dict(period_ps=T, latch_ckq_ps=ckq, form="neg-level lockup latch, release at falling edge"), **res),
          open(dump, "w"), indent=1)
print("LATCH", json.dumps(res))
