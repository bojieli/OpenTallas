#!/usr/bin/env python3
"""Owner's 47-user/520-die target: necessary static-copy bound and structural opportunity.

This changes no source model, owner target or release record. The exploratory witness
shortens twelve model resource windows; it is NOT evidence of implemented RTL throughput.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import dv_mu_calendar as M


def report():
    model = M.load_model()
    stages = M.stage_windows(model)
    design = M.design(model)
    n, q = 47, M.PHASE_Q
    period = M.qup(__import__('math').ceil(design['T_ar']))
    nr = max(g['occ'] for g in stages if g['copies'] == 1)
    largest = max((g for g in stages if g['copies'] == 2), key=lambda g: g['occ'])
    gap_min = M.qup(nr)
    long_gap = M.qup(largest['occ'])
    bound = (n - 1) * gap_min + long_gap
    # An odd ring cannot alternate A/B at every elementary gap. At least one
    # gap must therefore be >= this group's whole window. All remaining gaps
    # must still fit the largest nonduplicated stage (a different constraint).
    short = ((period - long_gap) // (n - 1)) // q * q
    changes = [dict(stage=g['id'], label=g['label'], original=g['occ'],
                    exploratory=short, reduction=g['occ'] - short)
               for g in stages if g['copies'] == 1 and g['occ'] > short]
    candidate = copy.deepcopy(stages)
    for g in candidate:
        if g['copies'] == 1:
            g['occ'] = min(g['occ'], short)
    shifts = [k * short for k in range(n)]
    colours = {g['id']: M.assign_copies(shifts, period, g['occ'])
               for g in candidate if g['copies'] == 2}
    assert all(colours.values()), colours
    users = [dict(user=k, shift=shifts[k], kind='ar') for k in range(n)]
    collisions = M.collisions(candidate, users, period, colours)[0]
    assert not collisions, collisions
    assert bound > period and design['dies'] == 520
    return dict(schema='opentallas.s81_dv.mu_47_bound.v1', coordinator_decision=DECISION, owner_target_users=46, superseded_target_users=n,
                owner_target_dies=520, target_preserved=False,
                source_model=dict(path=str(M.BAL.relative_to(M.ROOT)),
                                  sha256=hashlib.sha256(M.BAL.read_bytes()).hexdigest()),
                phase_quantum=q, period=period,
                fixed_copy_existing_windows=dict(nonduplicated_max=nr,
                    minimum_short_gap=gap_min, duplicated_max_group=largest['id'],
                    duplicated_max_window=largest['occ'], minimum_long_gap=long_gap,
                    minimum_period=bound, deficit_cycles=bound-period,
                    max_available_long_gap=period-(n-1)*gap_min,
                    result='INFEASIBLE under these windows, fixed copy per user, and period'),
                structural_opportunity=dict(grade='hypothetical model only; RTL delta unmeasured',
                    short_gap=short, long_gap=period-shifts[-1], changed_stages=changes,
                    shifts=shifts, brute_force_collisions=len(collisions),
                    requirement='Implement and measure all listed occupancy reductions without changing single-user latency; preserve actual workload and mapped memories'),
                rejected_shortcuts=['46 users is diagnostic, not completion of owner target',
                    'Third copies require die budget change; not adopted',
                    'Changing user copy each token requires mutable-state migration/replication and user-0 fixed-copy proof'])

# Coordinator decision 2026-10-19 (MU-S81b): the target is the proven 46-user calendar; this bound is kept as the
# condition under which 47 would be recorded.
DECISION = {"date": "2026-10-19", "target_users": 46,
            "text": "S81 multi-user AR target = 46 users (the proven collision-free calendar), not 47. No third copy of the four full-scan groups (S002/S011/S020/S029, ~+40 dies) for one user. 47 is recorded only if the twelve non-duplicated FFN-pair stages measure >= 1.4% faster in RTL (occupancy 20,754 -> <= 20,468 cycles); until then 47 is a hypothetical opportunity, not a target.",
            "composition": "46 x 1,224.1 = 56,309 tok/s aggregate AR (results/arch/token_path_1018/index.json multi_user.ds_rom.ar)"}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    text = json.dumps(report(), indent=1) + '\n'
    if args.out:
        args.out.write_text(text)
    else:
        print(text, end='')
