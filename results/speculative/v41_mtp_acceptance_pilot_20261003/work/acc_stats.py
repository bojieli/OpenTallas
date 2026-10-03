"""Agentic acceptance statistics from DSpark draft records (committed run and/or pilot).
Uses the committed analyze.py definitions (rows_of / walk: exact greedy speculative replay, gamma 5)."""
import sys, json, gzip, random, statistics, collections
sys.path.insert(0, '/tmp/claude-mtp-wt/tools/v41_dspark_onpolicy')
import analyze as A
G = 5
def load(p):
    return json.load(gzip.open(p) if p.endswith('.gz') else open(p))
def per_prompt(trs):
    out = []
    for tr in trs:
        cy = A.walk(tr, A.rows_of(tr))
        out.append(dict(workload=tr['item']['workload'], prompt_id=tr['item']['prompt_id'], n_prompt=tr['L'],
                        n_generated=len(tr['tokens']) - tr['L'], cycles=len(cy), committed=sum(a + 1 for a in cy),
                        tau_walk=(sum(a + 1 for a in cy) / len(cy)) if cy else None, accepted=cy))
    return out
def alpha_of_tau(t):
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        if sum(m ** i for i in range(G + 1)) < t: lo = m
        else: hi = m
    return (lo + hi) / 2
def summ(pp, B=20000, seed=7):
    pp = [x for x in pp if x['cycles'] > 0]
    by = collections.defaultdict(list)
    for x in pp: by[x['workload']].append(x)
    def pooled(s): return sum(x['committed'] for x in s) / sum(x['cycles'] for x in s)
    def med(s): return statistics.median(x['tau_walk'] for x in s)
    def eqtok(s):  # equal tokens per workload: harmonic mean of per-workload pooled tau
        b = collections.defaultdict(list)
        for x in s: b[x['workload']].append(x)
        return len(b) / sum(1 / pooled(v) for v in b.values())
    rng = random.Random(seed); bp, bm, be = [], [], []
    for _ in range(B):
        s = []
        for w, v in by.items(): s += [rng.choice(v) for _ in v]
        bp.append(pooled(s)); bm.append(med(s)); be.append(eqtok(s))
    q = lambda v: [round(sorted(v)[int(0.025 * B)], 3), round(sorted(v)[int(0.975 * B)], 3)]
    allc = [a for x in pp for a in x['accepted']]
    surv = [sum(1 for a in allc if a >= k) / len(allc) for k in range(1, G + 1)]
    cond = [surv[0]] + [surv[k] / surv[k - 1] for k in range(1, G)]
    return dict(prompts=len(pp), cycles=len(allc), generated_tokens=sum(x['n_generated'] for x in pp),
                tau_pooled=round(pooled(pp), 3), tau_pooled_ci95=q(bp),
                tau_median_of_prompts=round(med(pp), 3), tau_median_of_prompts_ci95=q(bm),
                tau_equal_tokens_per_workload=round(eqtok(pp), 3), tau_equal_tokens_per_workload_ci95=q(be),
                per_cycle_committed_median=statistics.median(a + 1 for a in allc),
                conditional_acceptance_by_position=[round(c, 4) for c in cond],
                alpha_equivalent_geometric=round(alpha_of_tau(pooled(pp)), 4),
                alpha_equivalent_geometric_median=round(alpha_of_tau(med(pp)), 4),
                per_workload={w: dict(prompts=len(v), cycles=sum(x['cycles'] for x in v), tau_pooled=round(pooled(v), 3),
                                      tau_median=round(med(v), 3)) for w, v in sorted(by.items())})
if __name__ == '__main__':
    out = {}
    sets = {}
    for tag, path in [a.split('=', 1) for a in sys.argv[1:]]:
        trs = [t for t in load(path) if t['item']['workload'].startswith('agentic_')]
        sets[tag] = per_prompt(trs)
    if len(sets) > 1: sets['combined'] = [x for v in list(sets.values()) for x in v]
    for tag, pp in sets.items():
        out[tag] = summ(pp); out[tag]['per_prompt'] = [{k: v for k, v in x.items() if k != 'accepted'} for x in pp]
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != 'per_prompt'} for k, v in out.items()}, indent=1))
    json.dump(out, open('acc_stats.json', 'w'), indent=1)
