#!/usr/bin/env python3
"""Check HA7 immutable replay and cross-sweep accounting without model inference."""
import json
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
p = Path(sys.argv[1]) if len(sys.argv)>1 else root/'results/uarch/hbm_accel_speculation_20261003/tracejoin_r2.json'
r = json.loads(p.read_text())
assert r['replay']['mismatches'] == 0
assert r['replay']['ar_us'] == 442.14
assert r['replay']['draft_us'] == 51.88
assert r['replay']['verify_by_P']['6']['total_us'] == 700.85
assert abs(12-r['trace_statistics']['union_by_p']['2']['mean']-r['prefetch']['lag_one_recall']*6)<.002
assert r['prefetch']['optimistic_rate_gain_fraction'] < .01
assert r['prefetch']['conditional_incremental_saved_us'] == 0
assert r['trace_statistics']['traces'] == 30
pairs = r['trace_statistics']['previous_token']['pairs']
assert sum(r['trace_statistics']['previous_token']['hit_histogram']) == pairs
rows = r['sweep']
assert len(rows) == 120
key = lambda x: (x['stacks_per_die'],x['gamma'],x['replicas'],x['cohort'])
lookup = {key(x):x for x in rows}
for x in rows:
    assert not x['adopt']
    assert x['conditional_step_us'] > 0
    assert abs(x['conditional_tokens_s']*x['conditional_step_us']/1e6-x['tau'])<1e-9
    if x['replicas']==1:
        assert x['selector_saved_us']==0
    elif x['replicas']>1:
        prior=lookup[(x['stacks_per_die'],x['gamma'],x['replicas']-1,x['cohort'])]
        assert x['conditional_tokens_s'] >= prior['conditional_tokens_s']
    if x['stacks_per_die']==2:
        four=lookup[(4,x['gamma'],x['replicas'],x['cohort'])]
        assert x['conditional_tokens_s']<four['conditional_tokens_s']
        assert abs(x['conditional_step_us']-four['conditional_step_us']-
                   x['union_stream_penalty_us']-x['draft_stream_penalty_us'])<=.011  # pinned parts round to .01 us
assert abs(r['stream']['best_mixed_two_stack_rate_penalty']-.10829389625797403)<1e-10
cost=r['selector']['replica_costs'][-1]
assert cost['minimum_load_cycles_per_position'] == 6144
assert cost['incremental_DFF_area_lower_bound_mm2']>4.5
print('PASS: 7 pinned replay cases; 120 accounting rows; saved-trace reuse, 2-stack exposure, replica costs; no inference')
