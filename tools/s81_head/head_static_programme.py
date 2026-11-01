#!/usr/bin/env python3
"""Compose native HEAD entry frames with its selected plan and reset transport.

The caller supplies the actual peer timing, activation source and START producer.
This emits a plan candidate for its die owner, never installs a frozen-plan delta
or promotes a provider-pin fixture to a production transport measurement.
"""
import argparse
import json
from pathlib import Path

from head_boot_recipe import compile_recipe, defaults, provider
from head_bootstrap_delta import apply as bootstrap_transport
from head_entry_schedule import compile_entry, uint


def compile_programme(plan, offsets, inventory, job, timing, source_defaults):
    for key in ('start_producer', 'activation_source'):
        name = timing.get(key)
        if not isinstance(name, str) or not name or name.upper().startswith('TEST'):
            raise ValueError(f'explicit actual {key} required')
    if 'job_active' in timing['start_producer'].lower():
        raise ValueError('CTL job_active is downstream of START, not its producer')
    # Unlike the component compiler, an installed boot binding uses the actual
    # clock/reset profile supplied by the selected source assembly.
    clock_id = uint(timing['clock_reset_id'], 64, 'actual clock/reset identity')
    phase_bound = uint(timing['phase_bound'], 32, 'actual HBC phase bound')
    if not clock_id or not phase_bound:
        raise ValueError('actual clock/reset identity and phase bound must be nonzero')
    entry = compile_entry(inventory, job, timing)
    if entry['authority']['start_global_edge'] is None:
        raise ValueError('actual 80-beat activation source and residence dates required')
    # Re-encode with the externally selected clock identity, including both
    # header copies. The HBC body/CRC and native programme identity stay intact.
    entry['host_params'].update(CLOCK_RESET_ID=clock_id, PHASE_BOUND=phase_bound)
    mask = ((1 << 64) - 1) << (114 + 16)
    for row in entry['frames']:
        if row['kind'] in ('HBC_LOAD', 'HBC_COMMIT'):
            row['frame'] = (row['frame'] & ~mask) | (clock_id << (114 + 16))
    candidate = bootstrap_transport(plan)
    hp, ht, content = provider(candidate, 'ot_s81hd_host_ep_core')
    cp, _, _ = provider(candidate, 'ot_s81hd_ctl_core')
    content.setdefault('params', {}).update(entry['host_params'])
    if timing['host_counter_zero_edge'] < offsets['parts'][hp['name']]['release']:
        raise ValueError('selected HOST counter origin precedes its plan reset release')
    if timing['ctl_start_offset'] != offsets['parts'][cp['name']]['release']:
        raise ValueError('CTL START offset differs from the selected plan wavefront')
    hbc = [r for r in entry['frames'] if r['kind'].startswith('HBC_')]
    zero = timing['host_counter_zero_edge']
    programme = dict(
        start=dict(producer=timing['start_producer'],
                   die_edge=entry['authority']['start_global_edge']),
        activation_source=timing['activation_source'],
        host_boot_counter_zero_global_edge=zero,
        transport=dict(peer_to_hbc_input=timing['peer_to_hbc_input'],
                       peer_to_host_frame=uint(timing['peer_to_host_frame'], 48, 'peer-to-HOST frame age'),
                       peer_to_ctl_csr_apply=timing['peer_to_ctl_settled'],
                       hbc_commit_to_context_valid=timing['commit_to_context_valid'],
                       peer_frame_period=timing['peer_frame_period']),
        hbc_records=[dict(receive_edge=r['edge'] + timing['peer_to_hbc_input'] - zero,
                          payload=(r['frame'] >> 16) & ((1 << 512) - 1)) for r in hbc],
        config={k: job[k] for k in ('plen', 'glen', 'group', 'rbase', 'issue_offset',
                                    'issue_period', 'merge_deadline')},
        csr_apply_edges={str(r['address']): r['settled_edge'] for r in entry['frames']
                         if r['kind'] == 'CSR'})
    if job.get('mode', 'ar') == 'mtp':
        programme['config'].update(mode='mtp', mtp_result_mtag=job['mtp_result_mtag'])
    recipe = compile_recipe(candidate, offsets, source_defaults, programme)
    if recipe['status'] == 'BLOCKED':
        raise ValueError('composed native programme rejected: ' + '; '.join(recipe['blockers']))
    # Independent producer/consumer compilers must emit the same exact frames.
    expected = [(r['edge'], r['lane'], r['frame']) for r in entry['frames']]
    actual = [(r['launch_global_edge'], r['lane'], int(r['frame553'], 16))
              for r in recipe['frames']]
    if expected != actual:
        raise ValueError('native entry and selected-plan recipe disagree on emitted frames')
    recipe.update(activation_source=timing['activation_source'],
                  activation_records=entry['xb_records'],
                  activation_resident_global_edge=entry['activation_resident_edge'],
                  production_transport_qualified=entry['production_transport_qualified'],
                  adoption='PLAN CANDIDATE ONLY: die-owner plan event, reset/RTL, geometry and physical gates required')
    return candidate, programme, recipe


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'offsets', 'inventory', 'job', 'timing', 'out'):
        ap.add_argument('--' + name, type=Path, required=True)
    ap.add_argument('--host-source', type=Path,
                    default=Path(__file__).resolve().parents[2] / 'rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv')
    ap.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2],
                    help='source repository root containing referenced physical pin assets')
    args = ap.parse_args()
    if args.out.exists():
        ap.error('fresh output directory required; preserve prior verdicts')
    read = lambda p: json.loads(p.read_text())
    candidate, programme, recipe = compile_programme(
        *(read(getattr(args, name)) for name in ('plan', 'offsets', 'inventory', 'job', 'timing')),
        defaults(args.host_source.read_text()))
    from head_source_delta import rebase_pin_assets
    rebase_pin_assets(candidate, args.plan, args.out / 'plan_candidate.json', args.root)
    args.out.mkdir(parents=True)
    for name, data in (('plan_candidate.json', candidate), ('programme.json', programme), ('recipe.json', recipe)):
        (args.out / name).write_text(json.dumps(data, indent=2) + '\n')
    print(recipe['status'], 'frames', len(recipe['frames']), 'activation', len(recipe['activation_records']))


if __name__ == '__main__':
    main()
