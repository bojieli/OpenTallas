#!/usr/bin/env python3
"""Propose one explicit head interface batch; do not mutate the frozen input.

Six station types receive row-legal Manhattan FT knees and sink-based taps.
All head soft types gain the already required START broadcast. The eight-kit
clock inventory includes physical reset+START relays at a joint fixed point;
spine SPO/SPR sink weights are retained. Publish data/boot cycle impacts before
any refreeze or P&R. No missing head RTL/codec or compiler schedule is invented.
"""
import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'tools/die_plan'))
import schema as S
import reset_tree as R
import ft_knee_sites as K
from gen_phys import type_pins

ST = ('hd_st_k5', 'hd_st_m', 'hd_st_n3', 'hd_st_n4', 'hd_st_str', 'hd_st_turn')
TYPES = ST + ('hd_spn', 'hd_spn_end')


def controls(tree):
    if not tree.get('start'):
        raise ValueError('START is absent')
    if tree['entry'] == 'sync':
        # The actual gen_rtl.CELLS ot_dp_rsync_s2/s3 has N p bits.
        ns = int(tree['sync_stages'])
        if ns not in (2, 3) or tree.get('lock'):
            raise ValueError('root lock/unknown sync needs an explicit weighted census')
        rows = [(f'u_rst_root.p[{i}]', tree['root'], 'reset_sync') for i in range(ns)]
        rows += [(f'u_run_root.p[{i}]', tree['start_in'], 'start_sync') for i in range(ns)]
    else:
        rows = [('u_rst_in', tree['root'], 'reset_entry'), ('u_run_in', tree['start_in'], 'start_entry')]
    rows += [(r['name'], r['xy'], r.get('role', 'reset')) for r in R.start_relays(tree)]
    if len({r[0] for r in rows}) != len(rows):
        raise ValueError('duplicate control alias')
    cnt = Counter((round(xy[0], 3), round(xy[1], 3)) for _, xy, _ in rows)
    return [[x, y, n] for (x, y), n in sorted(cnt.items())], dict(Counter(role for _, _, role in rows))


def propose(raw, checkpoint=None):
    base = copy.deepcopy(raw)
    before = S.Plan(base)
    reset_before = R.wf_plan(before)
    candidate = copy.deepcopy(raw)
    candidate['reset']['start'] = 'broadcast'
    knee = K.place(candidate, ST)
    fixed = {tn: copy.deepcopy(candidate['partition_types'][tn]['clock'].get('sink_sites_um', [])) for tn in TYPES}
    for tn in TYPES:
        ck = candidate['partition_types'][tn]['clock']
        ck.update(tap_mode='density', tap_target_sinks=600, tap_max_sinks=1500, tap_radius_um=150.)
    if checkpoint:
        checkpoint.mkdir(parents=True, exist_ok=True)
        (checkpoint / 'candidate_geometry.json').write_text(json.dumps(candidate, separators=(',', ':')) + '\n')
        (checkpoint / 'geometry_ledger.json').write_text(json.dumps(knee, indent=1) + '\n')
    print('HEAD8 geometry done; entering joint RESET/START clock census', flush=True)
    previous = None
    seen = set()
    control_report = {}
    for iteration in range(16):
        plan = S.Plan(candidate)
        trees = {tn: R.for_type(plan, tn) for tn in TYPES}
        rows = {tn: controls(trees[tn]) for tn in TYPES}
        print('HEAD8 control census round', iteration + 1, {tn: sum(r[2] for r in rows[tn][0]) for tn in TYPES}, flush=True)
        key = tuple((tn, tuple(tuple(x) for x in rows[tn][0])) for tn in TYPES)
        if key == previous:
            for tn, (sites, roles) in rows.items():
                control_report[tn] = dict(flops=sum(r[2] for r in sites), sites=len(sites), roles=roles,
                                         fixed_point_rounds=iteration + 1, preserved_extra_sink_rows=fixed[tn])
            break
        if key in seen:
            raise ValueError('joint control/tap inventory oscillates')
        seen.add(key)
        previous = key
        for tn, (sites, _) in rows.items():
            candidate['partition_types'][tn]['clock']['sink_sites_um'] = fixed[tn] + sites
    else:
        raise ValueError('joint control/tap inventory did not converge')
    after = S.Plan(candidate)
    reset_after = R.wf_plan(after)
    interface = {}
    for tn, ty in candidate['partition_types'].items():
        if ty.get('hard'):
            continue
        oldpins = {(b, i): (f, x, y, layer) for b, i, f, x, y, layer in type_pins(before, tn)}
        newpins = {(b, i): (f, x, y, layer) for b, i, f, x, y, layer in type_pins(after, tn)}
        interface[tn] = dict(outline_unchanged=ty['outline_um'] == base['partition_types'][tn]['outline_um'],
                             old_clock_taps=len(S.tap_grid(before, tn)), new_clock_taps=len(S.tap_grid(after, tn)),
                             old_clock_tap_coordinates=S.tap_grid(before, tn), new_clock_tap_coordinates=S.tap_grid(after, tn),
                             reset_in_before=R.reset_pin(before, tn), reset_in_after=R.reset_pin(after, tn),
                             reset_out_before=R.out_pins(before, tn), reset_out_after=R.out_pins(after, tn),
                             start_in_after=R.start_in_pin(after, tn), start_out_after=R.start_out_pins(after, tn),
                             logical_bus_pin_changes=[list(k) for k in sorted(set(oldpins) | set(newpins)) if oldpins.get(k) != newpins.get(k)],
                             reset_depth_before=reset_before['types'][tn]['depth_K'], reset_depth_after=reset_after['types'][tn]['depth_K'],
                             release_after_pin_before=reset_before['types'][tn]['release_after_pin'], release_after_pin_after=reset_after['types'][tn]['release_after_pin'],
                             start_pins_added=1 + len(reset_after['start']['types'][tn]['outs']))
    report = dict(scope='PROPOSED HEAD BATCH ONLY; no frozen plan mutation, P&R or adoption', station_types=ST,
                  START_scope=sorted(interface), geometry=knee, control_clock_fixed_point=control_report,
                  interface=interface, cold_boot=dict(old_reset_max=reset_before['max_release'], new_reset_max=reset_after['max_release'],
                     reset_max_delta=reset_after['max_release'] - reset_before['max_release'],
                     START_mode='broadcast', start_offsets_are_published_reset_offsets=True,
                     admission='External START edge S; mission release=max(R[p],S+R[p]); no timer/tie-high substitution.',
                     compiler_coherence='NOT RUN: TOK-SCHED must consume emitted offsets and supply the real head boot/START edge before adoption.'),
                  data_cycles_added=sum(r['added_cycles'] for r in knee),
                  data_latency_pricing='Per-slot ledger; gen latency/compiler reprice required before batch adoption.',
                  missing_head_RTL='Unchanged: ctl/host/mesh and host codec/calendar contracts remain separate known blockers.')
    return candidate, report, reset_after


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan'); ap.add_argument('--out', required=True); ap.add_argument('--ledger', required=True)
    args = ap.parse_args()
    candidate, report, offsets = propose(json.loads(Path(args.plan).read_text()), Path(args.out))
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    (out / 'die_plan.json').write_text(json.dumps(candidate, separators=(',', ':')) + '\n')
    (out / 'reset_start_offsets.json').write_text(json.dumps(offsets, indent=1) + '\n')
    Path(args.ledger).write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(dict(types=list(TYPES), data_cycles_added=report['data_cycles_added'], cold_boot=report['cold_boot'],
                          taps={t: [r['old_clock_taps'], r['new_clock_taps']] for t, r in report['interface'].items()})))
