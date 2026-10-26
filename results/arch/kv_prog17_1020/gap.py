import sys, pickle
sys.path.insert(0, '/home/ubuntu/wt/kv-prog17-1020')
from tools.qwen_static_schedule import mu_calendar as MC
from tools.qwen_static_schedule import mu_opcal as O
M = MC
rows = pickle.load(open(sys.argv[2],'rb')); MC.KV_ATT_END = int(sys.argv[1])
fp = MC.kv_frame_params(rows); P = fp['layer_period']
p = M._need(dict(M.SOURCED, users=O.NU, occupancy="measured", head_chunks=8, **fp)); p.setdefault("head_tok_ofs", p.get("emb_t", O.EMB_T))
segs, grp = O.segments(p)
u0 = O.token_units(p, segs, grp, filler=False); uf = O.token_units(p, segs, grp, filler=True)
T = sum(b["length"] for _, b in u0); H = 2*T; kvr = p["kv_lp_rows"]
W = MC.kv_attention_window(rows[1])
res = {}
for a in range(0, P, int(sys.argv[3])):
    R = O.CyclicRes(H); t = 0
    for _ in range(2):
        for n, b in u0: R.add(b["windows"], t, 0); t += b["length"]
    t = R.earliest(uf[0][1]["windows"], a, 1); tt = t
    for n, b in uf:
        tt = R.earliest(b["windows"], tt, 1)
        while "kv_begin" in b and not M.kv_launch_legal(kvr[b["stage"] - 1], tt + b["kv_begin"]):
            tt += 1; tt = R.earliest(b["windows"], tt, 1)
        R.add(b["windows"], tt, 1); tt += b["length"]
    lo = t + T // 2
    iv = sorted((x, y) for x, y, o in R.r['kvs'] if y > lo and x < lo + 4 * P)
    gaps = [b2[0] - a2[1] for a2, b2 in zip(iv, iv[1:])]
    res[a] = (tt - t - T, max(gaps), min(gaps))
best = sorted(res.items(), key=lambda kv: -kv[1][2])[:8]
print('W', W, 'P', P, 'need gap >=', W, 'best (start: slip, maxgap, mingap)', best)
