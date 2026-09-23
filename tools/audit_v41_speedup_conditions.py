#!/usr/bin/env python3
"""Target-free Amdahl and cache sensitivity; byte service is not total time."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def expert_only_speedup(dense_bytes, routed_bytes, expert_acceleration):
    if expert_acceleration < 1:
        raise ValueError('Acceleration must be at least one')
    return (dense_bytes + routed_bytes) / (dense_bytes + routed_bytes / expert_acceleration)


def common_budget_ratio(weight_acceleration, target=3):
    """Maximum unchanged C/H for (H+C)/(H/r+C)>=target; H is weight time."""
    if target <= 1 or weight_acceleration <= 0:
        raise ValueError('Invalid target or acceleration')
    return (1 - target / weight_acceleration) / (target - 1)


def main():
    names = ['configs/models/candidates/deepseek-v4.1-flash.json',
             'configs/architecture/rom_hbm_review_v3.json',
             'results/architecture/v41_architecture_feasibility.json',
             'tools/audit_v41_speedup_conditions.py']
    m,c,a = [json.loads((ROOT/p).read_text()) for p in names[:3]]
    routed = m['routed_weight_bytes'] * m['experts_per_token'] // m['num_experts']
    dense = m['dense_weight_bytes']
    assert dense+routed == a['contexts'][1]['weight_bytes']
    cache = []
    for fraction in (0, .5, 1):
        remaining = dense * (1-fraction)
        cache.append({'dense_cache_fraction': fraction,
                      'dense_cache_bytes': dense*fraction,
                      'ideal_dense_cache_sram_mm2': dense*fraction/c['sram_bytes_per_mm2_assumed'],
                      'remaining_external_weight_bytes': remaining+routed,
                      'expert_share_of_external_bytes': routed/(remaining+routed),
                      'expert_only_10x_external_service_speedup': expert_only_speedup(remaining,routed,10),
                      'external_weight_floor_us_at_4_5TB_s_per_die': {str(n): (remaining+routed)/(n*4.5e6) for n in (8,16,32,84)}})
    out = {
        'schema':'opentallas.v41-speedup-conditions.v1',
        'status':'conditional_service_analysis_not_achieved_system_speedup',
        'active_weight_bytes':dense+routed,'non_routed_weight_bytes':dense,'routed_weight_bytes':routed,
        'routed_fraction_of_active_weight_bytes':routed/(dense+routed),
        'expert_only_infinite_speedup_equal_byte_service':(dense+routed)/dense,
        'expert_only_10x_speedup_equal_byte_service':expert_only_speedup(dense,routed,10),
        'cache_scenarios':cache,
        'maximum_common_time_over_hbm_weight_time_for_3x':{str(r):common_budget_ratio(r) for r in (2,3,4,5,10,100)},
        'limits':[
            'Byte fractions equal time fractions only under equal byte-service rates, no overlap and no other work; these are conditional examples, not measured Amdahl fractions.',
            'Cache removes external reads on hits, not local reads or arithmetic. Full dense cache uses profile active dense inventory; executable placement/alignment and actual lookup semantics remain to be audited.',
            'No arbitrary routed expert cache hit is assumed. Caching one token selected experts does not cache every possible route.',
            'HBM aggregate bandwidth assumes all listed dies can serve the token concurrently; floors exclude read latency, placement and non-weight work.',
            'Common C is non-overlapped unchanged critical-path time; overlapping memory/compute needs a dependency schedule instead of summing these terms.',
            'Negative common budget means weight acceleration alone is insufficient even with zero common time.',
            'SRAM area is an assumed raw-density screen without ports, ECC, alignment, wiring or physical qualification.'
        ],
        'input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}}
    (ROOT/'results/architecture/v41_speedup_conditions.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('input_sha256','limits')},indent=2))


if __name__ == '__main__':
    main()
