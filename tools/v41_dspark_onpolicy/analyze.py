"""tau from DSpark drafts along the model's own greedy continuation.

row p (main position p, block = [tok[p+1], noise x4]) drafts d_1..d_5 for tok[p+2..p+6].
a(p) = leading matches.  Full-depth rows need p+6 <= last index.
tau_walk: a greedy speculative decode replayed exactly: start at p = L, commit a+1, p += a+1 (only full-depth cycles).
tau_rows: mean(a+1) over every full-depth row (position-averaged; not cycle-aligned).
"""
import json, sys, random, collections

GAMMA = 5
CLASS = lambda w: w.split('_')[0]


def rows_of(tr):
    toks, L = tr['tokens'], tr['L']
    last = len(toks) - 1
    acc = {}
    for p, d in tr['drafts'].items():
        p = int(p)
        if p + 1 + GAMMA > last:
            continue
        a = 0
        for k in range(GAMMA):
            if d[k] == toks[p + 2 + k]:
                a += 1
            else:
                break
        acc[p] = a
    return acc


def walk(tr, acc):
    p = tr['L']; cyc = []
    while p in acc:
        a = acc[p]; cyc.append(a); p += a + 1
    return cyc


def summarize(trs):
    cyc, rows = [], []
    for tr in trs:
        acc = rows_of(tr)
        rows += list(acc.values()); cyc += walk(tr, acc)
    def stats(v):
        if not v:
            return None
        hist = [v.count(k) for k in range(GAMMA + 1)]
        surv = [sum(1 for a in v if a >= k) / len(v) for k in range(1, GAMMA + 1)]
        cond = [surv[0]] + [surv[k] / surv[k - 1] if surv[k - 1] else None for k in range(1, GAMMA)]
        return dict(n=len(v), tau=sum(a + 1 for a in v) / len(v), histogram_accepted_0_5=hist,
                    survival_by_position=[round(s, 4) for s in surv],
                    conditional_acceptance_by_position=[round(c, 4) if c is not None else None for c in cond])
    return dict(walk=stats(cyc), rows=stats(rows))


def tau_walk_pooled(trs):
    c = t = 0
    for tr in trs:
        cy = walk(tr, rows_of(tr)); c += len(cy); t += sum(a + 1 for a in cy)
    return t / c if c else float('nan')


def macro(trs, key):
    by = collections.defaultdict(list)
    for tr in trs:
        by[key(tr)].append(tr)
    return sum(tau_walk_pooled(v) for v in by.values()) / len(by)


def harmonic(trs, key):
    """equal generated tokens per group: tau_mix = 1 / mean_g(1 / tau_g) (cycles per token averaged)."""
    by = collections.defaultdict(list)
    for tr in trs:
        by[key(tr)].append(tr)
    return len(by) / sum(1 / tau_walk_pooled(v) for v in by.values())


def boot(trs, fn, n=2000, seed=42):
    """stratified cluster bootstrap: resample prompts within each workload."""
    rng = random.Random(seed)
    by = collections.defaultdict(list)
    for tr in trs:
        by[tr['item']['workload']].append(tr)
    vals = []
    for _ in range(n):
        s = []
        for w, v in by.items():
            s += [rng.choice(v) for _ in v]
        vals.append(fn(s))
    vals.sort()
    return [round(vals[int(0.025 * n)], 4), round(vals[int(0.975 * n) - 1], 4)]


def main(path, out):
    trs = json.load(open(path))
    res = dict(per_workload={}, per_class={}, per_prompt=[])
    wl = sorted({t['item']['workload'] for t in trs})
    for w in wl:
        v = [t for t in trs if t['item']['workload'] == w]
        res['per_workload'][w] = dict(prompts=len(v), thinking_mode=v[0]['item']['thinking_mode'], **summarize(v))
    for c in sorted({CLASS(w) for w in wl}):
        v = [t for t in trs if CLASS(t['item']['workload']) == c]
        res['per_class'][c] = dict(prompts=len(v), **summarize(v), tau_walk_ci95=boot(v, tau_walk_pooled))
    for t in trs:
        acc = rows_of(t); cy = walk(t, acc)
        res['per_prompt'].append(dict(workload=t['item']['workload'], prompt_id=t['item']['prompt_id'],
                                      n_prompt=t['L'], n_generated=len(t['tokens']) - t['L'],
                                      cycles=len(cy), tau_walk=round(sum(a + 1 for a in cy) / len(cy), 4) if cy else None))
    res['overall'] = dict(prompts=len(trs), **summarize(trs),
                          tau_walk_pooled_ci95=boot(trs, tau_walk_pooled),
                          tau_walk_macro_over_workloads=macro(trs, lambda t: t['item']['workload']),
                          tau_walk_macro_over_workloads_ci95=boot(trs, lambda s: macro(s, lambda t: t['item']['workload'])),
                          tau_walk_equal_tokens_per_workload=harmonic(trs, lambda t: t['item']['workload']),
                          tau_walk_equal_tokens_per_workload_ci95=boot(trs, lambda s: harmonic(s, lambda t: t['item']['workload'])),
                          tau_walk_equal_tokens_per_class=harmonic(trs, lambda t: CLASS(t['item']['workload'])),
                          tau_walk_equal_tokens_per_class_ci95=boot(trs, lambda s: harmonic(s, lambda t: CLASS(t['item']['workload']))))
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res['overall'], indent=1))
    for w, r in res['per_workload'].items():
        print(w, r['thinking_mode'], 'walk', r['walk'] and (round(r['walk']['tau'], 3), r['walk']['n']), 'rows', r['rows'] and round(r['rows']['tau'], 3))
    for c, r in res['per_class'].items():
        print(c, round(r['walk']['tau'], 3), r['tau_walk_ci95'])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
