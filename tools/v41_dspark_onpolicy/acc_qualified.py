"""Qualified V4.1-Flash DSpark acceptance statistics (protocol: results/speculative/v41_mtp_acceptance_qualified_20261003/
PROTOCOL.md).  Greedy: exact replay (analyze.walk).  T=1: speculative sampling replayed through the maximal coupling on the
sampled target trajectory (accept depth k with prob min(1, q_k(x_k)/p_k(x_k))), Monte Carlo over R replays per prompt.
Usage: python3 acc_qualified.py DRAFTS.json OUT.json"""
import sys, os, json, random, statistics, collections
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A

G = 5
R = 2000
HEADLINE = ('agentic_swe_agent', 'agentic_tau_bench', 'agentic_mind2web')
SEPARATE = ('agentic_bfcl', 'agentic_json_mode')
# repo rate formula (tools/uarch_model.py at the record's base): MTP gamma 5 is linear in tau
V41_TAU = 3.649
ROM = dict(ar=2786.8, mtp_at_3649=4588.9, src='results/uarch/consolidation.json headline_table v41[0] (per_user_ar, per_user_mtp)')
HBM = dict(ar_us=442.14, mtp_pass_us=715.82, drafter_us=49.9, src='tools/uarch_model.py HBM_W19 (fused)')


def rom_rate(t): return ROM['mtp_at_3649'] * t / V41_TAU
def hbm_rate(t): return t * 1e6 / (HBM['mtp_pass_us'] + HBM['drafter_us'])


def greedy_prompt(tr, g=G):
    """g < 5: the same DSpark block truncated to its first g drafts (exact; the row set stays the full-depth one)."""
    cy = A.walk(tr, {p: min(a, g) for p, a in A.rows_of(tr).items()})
    return dict(cycles=len(cy), committed=sum(a + 1 for a in cy), hist=[cy.count(k) for k in range(G + 1)])


def t1_prompt(tr, seed, g=G):
    toks, L, pt, qt = tr['tokens'], tr['L'], tr['p_tok'], tr['q_tok']
    last = len(toks) - 1
    n = len(toks)
    r = np.full((n + G + 2, G), -1.0)                 # r[p, k-1]: accept prob at depth k for the cycle starting at row p
    for p, q in qt.items():
        p = int(p)
        if p + 1 + G > last:
            continue
        for k in range(1, G + 1):
            px = pt[p + 1 + k - L]
            r[p, k - 1] = min(1.0, q[k - 1] / px) if px > 0 else 1.0
    if g < G:
        r = np.where(r[:, :1] >= 0, r, -1.0)[:, :g]
    rng = np.random.default_rng(seed)
    pos = np.full(R, L); cyc = np.zeros(R); com = np.zeros(R); hist = np.zeros(G + 1)
    act = r[pos, 0] >= 0
    while act.any():
        rr = r[pos[act]]
        u = rng.random(rr.shape)
        a = np.cumprod(u < rr, axis=1).sum(1)
        cyc[act] += 1; com[act] += a + 1; hist += np.bincount(a, minlength=G + 1)[:G + 1]
        pos[act] += a + 1
        act = np.zeros(R, bool); act[:] = r[np.minimum(pos, n + G), 0] >= 0
    return dict(cycles=float(cyc.mean()), committed=float(com.mean()), hist=(hist / R).tolist(),
                tau_replay_sd=float(np.std(com / np.maximum(cyc, 1))))


def alpha_of_tau(t):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if sum(m ** i for i in range(G + 1)) < t else (lo, m)
    return (lo + hi) / 2


def summ(pp, B=20000, seed=7):
    pp = [x for x in pp if x['cycles'] > 0]
    if not pp:
        return None
    by = collections.defaultdict(list)
    for x in pp:
        by[x['workload']].append(x)
    pooled = lambda s: sum(x['committed'] for x in s) / sum(x['cycles'] for x in s)
    med = lambda s: statistics.median(x['committed'] / x['cycles'] for x in s)
    rng = random.Random(seed); bp, bm = [], []
    for _ in range(B):
        s = []
        for w, v in by.items():
            s += [rng.choice(v) for _ in v]
        bp.append(pooled(s)); bm.append(med(s))
    bp.sort(); bm.sort()
    q = lambda v: [round(v[int(0.025 * B)], 3), round(v[int(0.975 * B) - 1], 3)]
    h = np.sum([x['hist'] for x in pp], 0)
    surv = [h[k:].sum() / h.sum() for k in range(1, G + 1)]
    cond = [surv[0]] + [surv[k] / surv[k - 1] for k in range(1, G)]
    tp, tm = pooled(pp), med(pp)
    return dict(prompts=len(pp), cycles=round(float(h.sum()), 1), generated_tokens=sum(x['n_generated'] for x in pp),
                tau_pooled=round(tp, 3), tau_pooled_ci95=q(bp), tau_median_of_prompts=round(tm, 3), tau_median_of_prompts_ci95=q(bm),
                per_prompt_tau_quartiles=[round(float(v), 3) for v in np.percentile([x['committed'] / x['cycles'] for x in pp], [25, 50, 75])],
                histogram_accepted_0_5=[round(float(v), 2) for v in h], conditional_acceptance_by_depth=[round(float(c), 4) for c in cond],
                alpha_equivalent_pooled=round(alpha_of_tau(tp), 4), alpha_equivalent_median=round(alpha_of_tau(tm), 4),
                rates=dict(rom_mtp_at_median=round(rom_rate(tm), 1), rom_mtp_at_median_ci95=[round(rom_rate(v), 1) for v in q(bm)],
                           rom_mtp_at_pooled=round(rom_rate(tp), 1),
                           hbm_w19_mtp_at_median=round(hbm_rate(tm), 1), hbm_w19_mtp_at_median_ci95=[round(hbm_rate(v), 1) for v in q(bm)],
                           hbm_w19_mtp_at_pooled=round(hbm_rate(tp), 1)),
                per_workload={w: dict(prompts=len(v), tau_pooled=round(pooled(v), 3), tau_median=round(med(v), 3),
                                      n_prompt_range=[min(x['n_prompt'] for x in v), max(x['n_prompt'] for x in v)])
                              for w, v in sorted(by.items())})


def main(path, out):
    trs = json.load(open(path))
    pp = collections.defaultdict(list)
    for i, tr in enumerate(trs):
        mode = tr.get('mode', 'greedy')
        st = greedy_prompt(tr) if mode == 'greedy' else t1_prompt(tr, 1000 + i)
        pp[mode].append(dict(workload=tr['item']['workload'], prompt_id=tr['item']['prompt_id'], n_prompt=tr['L'],
                             n_generated=len(tr['tokens']) - tr['L'], **st,
                             tau=round(st['committed'] / st['cycles'], 4) if st['cycles'] else None))
    # tau at gamma 1..5 by exact truncation of the same drafts (requested 2026-10-03 by the speculation study)
    by_gamma = {}
    for i, tr in enumerate(trs):
        mode = tr.get('mode', 'greedy')
        for g in range(1, G + 1):
            st = greedy_prompt(tr, g) if mode == 'greedy' else t1_prompt(tr, 1000 + i, g)
            by_gamma.setdefault(mode, {}).setdefault(g, []).append(dict(workload=tr['item']['workload'], cycles=st['cycles'],
                                                                        committed=st['committed']))
    gam = {}
    for mode, d in by_gamma.items():
        gam[mode] = {}
        for g, v in d.items():
            for name, sel in (('headline_multiturn', HEADLINE), ('separate_single_shot', SEPARATE)):
                x = [y for y in v if y['workload'] in sel and y['cycles'] > 0]
                if not x:
                    continue
                gam[mode].setdefault(name, {})[g] = dict(
                    tau_pooled=round(sum(y['committed'] for y in x) / sum(y['cycles'] for y in x), 3),
                    tau_median_of_prompts=round(statistics.median(y['committed'] / y['cycles'] for y in x), 3))
    res = dict(protocol='results/speculative/v41_mtp_acceptance_qualified_20261003/PROTOCOL.md', gamma=G, t1_replays_per_prompt=R,
               rate_basis=dict(rom=ROM, hbm_w19=HBM, v41_tau_current=V41_TAU,
                               draft_cost='V41_DRAFT_FRACTION = 3/40 of AR (ROM) / 49.9 us modelled (HBM): UNVALIDATED',
                               ar=dict(rom=ROM['ar'], hbm_w19=round(1e6 / HBM['ar_us'], 1)),
                               breakeven_tau=dict(rom=round(V41_TAU * ROM['ar'] / ROM['mtp_at_3649'], 3),
                                                  hbm_w19=round((HBM['mtp_pass_us'] + HBM['drafter_us']) / HBM['ar_us'], 3))),
               modes={}, tau_by_gamma_truncated=gam,
               tau_by_gamma_note='gamma g < 5 truncates the same native DSpark block (5 slots) to its first g drafts; the verify '
                                 'checks g+1 positions.  Exact for greedy; for T=1 the coupling at depth g+1 becomes the bonus token.')
    for mode, v in pp.items():
        res['modes'][mode] = dict(headline_multiturn=summ([x for x in v if x['workload'] in HEADLINE]),
                                  separate_single_shot=summ([x for x in v if x['workload'] in SEPARATE]),
                                  all_agentic=summ(v), per_prompt=v)
    json.dump(res, open(out, 'w'), indent=1)
    print('tau by gamma', json.dumps(gam))
    for mode, r in res['modes'].items():
        for k in ('headline_multiturn', 'separate_single_shot', 'all_agentic'):
            s = r[k]
            if s is None:
                continue
            print(mode, k, 'n', s['prompts'], 'median', s['tau_median_of_prompts'], s['tau_median_of_prompts_ci95'], 'pooled',
                  s['tau_pooled'], s['tau_pooled_ci95'], 'cond', s['conditional_acceptance_by_depth'], 'rates', s['rates'])
            print('   ', {w: (x['tau_median'], x['tau_pooled']) for w, x in s['per_workload'].items()})


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
