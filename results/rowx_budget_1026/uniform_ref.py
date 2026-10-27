#!/usr/bin/env python3
"""LABELLED REFERENCE ONLY (not evidence): per-owner held-row counts if the 512 selected compressed rows were
independent and uniform over the 16 (die, stack) owners (owner = g[7:4]).  Exact binomial tails per owner +
Monte-Carlo max over the 16 owners of one layer."""
import json, math, sys
import numpy as np
N, K = 512, 16
p = 1.0 / K
def tail_gt(b):            # P(Binomial(N, p) > b), exact in log space
    s = 0.0
    for k in range(b + 1, N + 1):
        s += math.exp(math.lgamma(N + 1) - math.lgamma(k + 1) - math.lgamma(N - k + 1) + k * math.log(p) + (N - k) * math.log1p(-p))
    return s
rng = np.random.default_rng(20261026)
S = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000
mx = np.concatenate([rng.multinomial(N, [p] * K, size=min(500_000, S - i)).max(axis=1) for i in range(0, S, 500_000)])
out = dict(model='uniform iid multinomial(512, 16 owners) -- REFERENCE ONLY', samples_layers=S,
           per_owner=dict(mean=N * p, sd=math.sqrt(N * p * (1 - p)), p_gt_40=tail_gt(40), p_gt_80=tail_gt(80), p_gt_128=tail_gt(128)),
           layer_max=dict(mean=float(mx.mean()), p50=float(np.percentile(mx, 50)), p99=float(np.percentile(mx, 99)),
                          p99_9=float(np.percentile(mx, 99.9)), p99_99=float(np.percentile(mx, 99.99)), max=int(mx.max()),
                          p_gt_40_mc=float((mx > 40).mean()), p_gt_80_mc=float((mx > 80).mean())),
           # union bound across the 16 owners (tight here) and across the 8 index layers of a token
           layer_p_gt_80_union=16 * tail_gt(80), layer_p_gt_128_union=16 * tail_gt(128))
out['token_8layers'] = dict(p_any_gt_40=1 - (1 - out['layer_max']['p_gt_40_mc']) ** 8,
                            p_any_gt_80_union=8 * out['layer_p_gt_80_union'], p_any_gt_128_union=8 * out['layer_p_gt_128_union'])
print(json.dumps(out, indent=1))
