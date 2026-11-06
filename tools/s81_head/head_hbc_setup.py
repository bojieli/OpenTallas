#!/usr/bin/env python3
"""Bind measured HBC setup before measuring the downstream CSR/START calendar.

This candidate contains only three HBC records and six HOST parameters. It does
not emit CSR, RUN, GO or START, and never supplies an identity or TEST timing.
"""
import argparse
import copy
import hashlib
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from head_boot_recipe import provider
from head_entry_schedule import ROOT, compile_hbc_setup, uint


def compile_candidate(plan, inventory, job, timing, clock_profile, *, plan_sha256, sidecar_sha256):
    profile = clock_profile['profile']
    digest = hashlib.sha256(json.dumps(profile, sort_keys=True, separators=(',', ':')).encode()).digest()
    if clock_profile['profile_sha256'] != digest.hex():
        raise ValueError('clock/reset profile digest differs from supplied facts')
    identity = uint(clock_profile['clock_reset_id'], 64, 'actual clock/reset identity')
    if not identity or identity != (int.from_bytes(digest[:8], 'little') or 1):
        raise ValueError('actual clock/reset identity does not bind the supplied profile')
    phase = uint(clock_profile['phase_bound'], 32, 'explicit profile admission')
    if not phase:
        raise ValueError('explicit nonzero profile admission required')
    for key in ('source_event', 'clock_profile', 'scope'):
        if not isinstance(profile.get(key), str) or not profile[key].strip() or profile[key].upper().startswith('TEST'):
            raise ValueError('explicit measured clock/reset ' + key + ' required')
    if profile['source_plan_sha256'] != plan_sha256 or profile['source_sidecar_sha256'] != sidecar_sha256:
        raise ValueError('clock/reset profile does not bind the exact selected plan/sidecar')
    setup = compile_hbc_setup(inventory, job, timing, clock_reset_id=identity)
    setup['host_params']['PHASE_BOUND'] = phase
    claimed = clock_profile['host_params_candidate']
    for key in ('LOCAL_STAGE', 'LOCAL_RANK', 'PHASE_BOUND', 'CLOCK_RESET_ID'):
        if claimed.get(key) != setup['host_params'][key]:
            raise ValueError('selected HBC binding differs from measured profile ' + key)
    if timing['reset_deassert_edge'] != profile['root_reset_deassert_global_edge']:
        raise ValueError('HBC reset origin differs from measured profile')
    if [r['edge'] for r in setup['frames']] != profile['qualified_host0_launch_edges']:
        raise ValueError('HBC records leave the measured three-record launch chain')
    if 'hbc_arrival_boot_edges' in timing:
        if timing['hbc_arrival_boot_edges'] != profile['qualified_host0_input_boot_edges']:
            raise ValueError('HBC native arrival boot ages differ from measured profile')
        if not profile.get('host_boot_counter_zero_time_ps') or not profile.get('qualified_host0_input_time_ps'):
            raise ValueError('native boot-age profile requires measured counter-zero and arrival timestamps')
        try:
            period = Decimal(str(profile['period_ps']))
            zero = Decimal(str(profile['host_boot_counter_zero_time_ps']))
            arrivals = [Decimal(str(v)) for v in profile['qualified_host0_input_time_ps']]
        except (KeyError, InvalidOperation, TypeError):
            raise ValueError('native boot-age profile has invalid measured timestamps')
        if not period.is_finite() or period <= 0 or not zero.is_finite() or len(arrivals) != 3 or any(
                not v.is_finite() or v != zero + age * period
                for v, age in zip(arrivals, timing['hbc_arrival_boot_edges'])):
            raise ValueError('native arrival timestamps do not prove the supplied boot ages')
    elif timing['host_counter_zero_edge'] != profile['host_boot_counter_zero_global_edge'] or \
            [r['edge'] + timing['peer_to_hbc_input'] for r in setup['frames']] != profile['qualified_host0_input_edges']:
        raise ValueError('HBC counter/arrival chain differs from measured profile')
    candidate = copy.deepcopy(plan)
    part, typ, content = provider(candidate, 'ot_s81hd_host_ep_core')
    content.setdefault('params', {}).update(setup['host_params'])
    setup.update(clock_profile_sha256=digest.hex(), selected_source_event=profile['source_event'],
                 source_plan_sha256=plan_sha256, source_sidecar_sha256=sidecar_sha256,
                 binding=dict(part=part['name'], type=part['type'], module=typ['module'],
                              provider='ot_s81hd_host_ep_core'),
                 adoption='HBC SOURCE CANDIDATE ONLY; runtime context admission and owner review remain required')
    return candidate, setup


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'sidecar', 'inventory', 'job', 'timing', 'clock-profile', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--asset-root', type=Path, default=ROOT,
                        help='allowed root containing selected physical pin assets')
    args = parser.parse_args(argv)
    if args.out.exists():
        parser.error('fresh output directory required; preserve prior verdicts')
    read = lambda p: json.loads(p.read_text())
    candidate, setup = compile_candidate(
        *(read(getattr(args, name)) for name in ('plan', 'inventory', 'job', 'timing', 'clock_profile')),
        plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
        sidecar_sha256=hashlib.sha256(args.sidecar.read_bytes()).hexdigest())
    from head_source_delta import rebase_pin_assets
    setup['plan_relative_pin_assets'] = rebase_pin_assets(
        candidate, args.plan.resolve(), args.out / 'plan_candidate.json', args.asset_root)
    args.out.mkdir(parents=True)
    for name, data in (('plan_candidate.json', candidate), ('hbc_setup.json', setup)):
        (args.out / name).write_text(json.dumps(data, indent=2) + '\n')
    (args.out / 'host_params.json').write_text(json.dumps(setup['host_params'], indent=2) + '\n')
    (args.out / 'frames.json').write_text(json.dumps(setup['frames'], indent=2) + '\n')
    # Exact ot_s81hd_mesh_lane tx_d[552:0], one record per qualified edge.
    (args.out / 'host0_peer_frames.hex').write_text(''.join(f"{r['frame']:0139x}\n" for r in setup['frames']))
    (args.out / 'peer_records.json').write_text(json.dumps([dict(lane=r['lane'], edge=r['edge'], kind=r['kind'],
        tx_d_width=553, tx_d_hex=f"{r['frame']:0139x}") for r in setup['frames']], indent=2) + '\n')
    (args.out / 'source_sidecar.json').write_bytes(args.sidecar.read_bytes())
    print('HBC_SETUP_CANDIDATE', 'records', len(setup['frames']), 'CSR/GO/START=NOT_EMITTED')


if __name__ == '__main__':
    main()
