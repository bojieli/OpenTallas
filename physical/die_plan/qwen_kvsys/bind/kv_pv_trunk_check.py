#!/usr/bin/env python3
"""KV-P6-PV 10-23: PV wide-pair trunk timing invariants on a KV bind dir (bus_groups.json) + minimum-pad LP.

    kv_pv_trunk_check.py BIND_DIR OUT.json

pv_trunk_gen (rtl qkd_pvw_die_t: "column s: command AND data COL_D[s] after the pair; V chunk vc<k>_<g> must arrive
DELTA[g] edges after the header vh<k>") means, per pair side and for EVERY vport k and column s:
    V(k,s) - D(s) - H(k) = const          V = vport out_v_lo/hi -> slice pv2, D = ctl cmd -> column join/slices,
                                          H = vport out_t/valid/epoch -> ctl arrival check
and D(s) + R(s) = const (R = column y_valid/fault -> ctl, the col_valid all-equal check).  astk owner response_data
-> slice pe2 is checked like V with a free offset.  As built both hold exactly (V-D-H = -2/-1 by column parity on S).
The bound lanes forward 2 cycles a hop, so only sources at the hub end (vport_*_3, astk) still meet the cmd wave; the
mid-trunk vports are off by up to 24 edges -> pads on 1024-bit V chunks.  The LP gives the MINIMUM pad flops for any
lane routing (natural depth is a lower bound per member) that restores the as-built relative timing up to one shift
(absorbed by cfg_fia / TRUNK_D / FLAG_D regen).  Not modelled: the result trunk (T*Q*_r0 -> RH), R8 covers it.
"""
import json, re, sys, collections
import numpy as np
from scipy.optimize import linprog
B = sys.argv[1]
L = json.load(open(B + '/bus_groups.json'))['landing']
def mem():
    for x in L:
        for m in x['members']:
            yield x, m
def bits(m): return sum(b - a + 1 for a, b in m['sink_bits'])
out = {}
for side, pvw, pfx in (('S', 'pvw_0', 'pv_S_'), ('N', 'pvw_1', 'pv_N_')):
    D, R, V, H = {}, {}, collections.defaultdict(list), collections.defaultdict(list)
    for x, m in mem():
        src, snk = m['source'], x['sink']
        if src == pvw + '__u_ctl.cmd' and re.search(r'_s\d+_', snk):
            s = int(re.search(r'_s(\d+)_', snk).group(1))
            D.setdefault(s, set()).add((m['asbuilt_stages'], m['bound_stages'], x['sink_part']))
        mm = re.match(pvw + r'__u_s(\d+)_j\.(y_valid|fault)$', src)
        if mm and x['sink_part'] == 'hub_C':
            R.setdefault(int(mm.group(1)), set()).add((m['asbuilt_stages'], m['bound_stages']))
        mv = re.match(r'(vport_\w+)\.out_v_(lo|hi)$', src)
        if mv and x['sink_part'].startswith(pfx) and re.search(r'_s(\d+)_', snk):
            s = int(re.search(r'_s(\d+)_', snk).group(1))
            V[(mv.group(1), s)].append((m['asbuilt_stages'], m['bound_stages'], bits(m)))
        mp = re.match(r'(astk_\w+?)__u_strip_g_er_chain_u_er_g_owner_\d+__u_owner\.response_data$', src)
        if mp and x['sink_part'].startswith(pfx) and re.search(r'_s(\d+)_', snk):
            s = int(re.search(r'_s(\d+)_', snk).group(1))
            V[('PE:' + mp.group(1), s)].append((m['asbuilt_stages'], m['bound_stages'], bits(m)))
        mh = re.match(r'(vport_\w+)\.out_(t|valid|epoch)$', src)
        if mh and x['sink_part'] == 'hub_C' and re.search(pvw + '__u_ctl', snk):
            H[mh.group(1)].append((m['asbuilt_stages'], m['bound_stages'], bits(m)))
    for s in D: assert len({(a, b) for a, b, _ in D[s]}) == 1, (side, s, D[s])
    D = {s: next(iter(v)) for s, v in D.items()}
    R = {s: next(iter(v)) for s, v in R.items()}
    ks = sorted({k for k, _ in V})
    Hd = {k: (max(a for a, _, _ in H[k]), max(b for _, b, _ in H[k]), sum(c for _, _, c in H[k])) for k in H}
    for k in ks:
        if k.startswith('PE:'): Hd[k] = (0, -300, 0)   # astk pe2: free offset (its ahub age regenerates), no header lane
    # as-built invariant V - D - H
    inv_a = collections.Counter(); inv_b = collections.Counter()
    for (k, s), lst in V.items():
        for a, b, n in lst:
            inv_a[a - D[s][0] - Hd[k][0]] += n
            inv_b[(k, b - D[s][1] - Hd[k][1])] += n
    tot_a = collections.Counter(D[s][0] + R[s][0] for s in D)
    tot_b = collections.Counter(D[s][1] + R[s][1] for s in D)
    print(f'== {side}: cols {len(D)} vports {ks}')
    print('  as-built  V-D-H histogram (bits):', dict(inv_a), ' D+R:', dict(tot_a))
    vb = collections.defaultdict(set)
    for (k, v), n in inv_b.items(): vb[k].add(v)
    print('  bound     V-D-H per vport:', {k: sorted(v) for k, v in vb.items()}, ' D+R:', dict(tot_b))
    # LP (shift-preserving): bound(V-D-H)(k,s) - asb(V-D-H)(k,s) = c (one shift per side, absorbed by cfg_fia / ctl ages);
    # bound(D+R)_s - asb(D+R)_s = K (absorbed by TRUNK_D/FLAG_D).  Vars D_s >= nat, H_k >= nat, R_s >= nat, c, K free.
    S = sorted(D); nk = len(ks); nS = len(S)
    iD = {s: i for i, s in enumerate(S)}; iH = {k: nS + j for j, k in enumerate(ks)}; iR = {s: nS + nk + i for i, s in enumerate(S)}
    ic = 2 * nS + nk; iK = ic + 1; nv = iK + 1
    c = np.zeros(nv); A = []; b = []; const = 0.0
    def ge(coef, rhs):
        row = np.zeros(nv)
        for i, v in coef: row[i] -= v
        A.append(row); b.append(-rhs)
    for s in S:
        c[iD[s]] += 33; const -= 33 * D[s][1]; ge([(iD[s], 1)], D[s][1])
        c[iR[s]] += 2; const -= 2 * R[s][1]; ge([(iR[s], 1)], R[s][1])
    for k in ks:
        c[iH[k]] += Hd[k][2]; const -= Hd[k][2] * Hd[k][1]; ge([(iH[k], 1)], Hd[k][1])
    for (k, s), lst in V.items():
        for a, bb, n in lst:
            e = a - D[s][0] - Hd[k][0]                      # as-built V-D-H of this member
            # V = D + H + e + c  >= natural bb ; cost n*(V - bb)
            c[iD[s]] += n; c[iH[k]] += n; c[ic] += n; const += n * (e - bb)
            ge([(iD[s], 1), (iH[k], 1), (ic, 1)], bb - e)
    Aeq = []; beq = []
    for s in S:
        row = np.zeros(nv); row[iD[s]] = 1; row[iR[s]] = 1; row[iK] = -1; Aeq.append(row); beq.append(D[s][0] + R[s][0])
    bounds = [(0, None)] * nS + [((-300 if k.startswith('PE:') else 0), None) for k in ks] + [(0, None)] * nS + [(-300, 300), (-300, 300)]
    r = linprog(c, A_ub=np.array(A), b_ub=np.array(b), A_eq=np.array(Aeq), b_eq=np.array(beq), bounds=bounds, method='highs', integrality=np.ones(nv))
    x = np.round(r.x).astype(int)
    Dopt = {s: int(x[iD[s]]) for s in S}; Hopt = {k: int(x[iH[k]]) for k in ks}; cc = int(x[ic])
    vpad = sum(n * (Dopt[s] + Hopt[k] + (a - D[s][0] - Hd[k][0]) + cc - bb) for (k, s), lst in V.items() for a, bb, n in lst)
    cpad = sum(33 * (Dopt[s] - D[s][1]) for s in S)
    hpad = sum(Hd[k][2] * (Hopt[k] - Hd[k][1]) for k in ks)
    fpad = sum(2 * (int(x[iR[s]]) - R[s][1]) for s in S)
    print(f'  LP optimum (shift-preserving): pad flops {r.fun + const:.0f} = V {vpad} + cmd {cpad} + hdr {hpad} + flag {fpad}; shift c={cc}, K={x[iK]}')
    print('  D_s opt by part:', {D[s][2]: Dopt[s] for s in S}, ' natural', {D[s][2]: D[s][1] for s in S})
    print('  H_k opt:', Hopt, ' natural', {k: Hd[k][1] for k in ks})
    # flag-only loop scenario (cmd left at bound, no cmd pads): flags padded to max D+R (shift-preserving)
    sh = {s: D[s][1] + R[s][1] - (D[s][0] + R[s][0]) for s in S}
    print('  flag-only (cmd unpadded): flag pad flops', sum(2 * (max(sh.values()) - v) for v in sh.values()))
    # KV-P5 rule scenario: cmd padded to max Delta -> D_s = asb + dcmax ; V pads needed then
    dcm = max(D[s][1] - D[s][0] for s in S)
    Dp = {s: D[s][0] + dcm for s in S}
    Lp = {k: max(bb - Dp[s] - (a - D[s][0]) for (kk, s), lst in V.items() if kk == k for a, bb, _ in lst) for k in ks}
    vpad_p = sum(n * (Dp[s] + (a - D[s][0]) + Lp[k] - bb) for (k, s), lst in V.items() for a, bb, n in lst)
    print(f'  KV-P5 rule (cmd pads to max Delta {dcm}): cmd pads {sum(33*(Dp[s]-D[s][1]) for s in S)}, V pads STILL needed {vpad_p}')
    Vtot = sum(n for lst in V.values() for _, _, n in lst)
    print(f'  V bits {Vtot}; H bits', {k: v[2] for k, v in Hd.items()})
    out[side] = dict(Dopt=Dopt, Hopt=Hopt, shift=cc, K=int(x[iK]), lp_pad_flops=int(round(r.fun + const)), vpad=vpad, cpad=cpad, hpad=hpad, fpad=fpad, rule_cmd_pads=sum(33*(Dp[s]-D[s][1]) for s in S), rule_vpad_still=vpad_p)
json.dump({k: {kk: (str(vv) if not isinstance(vv, int) else vv) for kk, vv in v.items()} for k, v in out.items()}, open(sys.argv[2], 'w'), indent=1)
