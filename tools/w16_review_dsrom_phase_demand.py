#!/usr/bin/env python3
"""Frozen owner-input review; does not implement a schedule or qualify hardware."""
import argparse
from decimal import Decimal as D
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'phase': ('fea811df454fcc7aaa1609a42c3ee4eb58c9672a', 'results/uarch/w10_q_existing_icg_r1/phases.json'),
    'phase_tool': ('fea811df454fcc7aaa1609a42c3ee4eb58c9672a', 'tools/w10_q_phase_reservations.py'),
    'power_tool': ('e79394b1c', 'tools/w10_q_power_envelope.py'),
    'power': ('e79394b1c', 'results/uarch/w10_q_power_envelope_r1/power.json'),
    'geometry': ('e61a5a1ee', 'results/quality/w16_w17_geometry_search_20261001/search.json'),
    'OR': ('3f9b596c58528ef2338fe49fc5b6f7e1c00da1fd', 'results/quality/w10_q_mask_basis_audit_20261001/audit.json'),
    'whole': ('9345c1fc048b2e19255e5c27b2bfde6f64360f29', 'results/quality/w16_w17_whole_dsrom_candidate_20261001/candidate.json'),
    'CROM': ('dd3f54450', 'results/uarch/w11_crom_home_service_preflight_20261001/contract.json'),
    'demand_tool': ('7ed62357d77b534dbd8a177e84321f91f105b45b', 'tools/w11_dsrom_crom_demand.py'),
    'demand': ('f4bce8fa0a5162964262dd28c476aed549587dd0', 'results/uarch/w11_crom_demand_20261001/demand_v2.json.gz'),
    'summary': ('f4bce8fa0a5162964262dd28c476aed549587dd0', 'results/uarch/w11_crom_demand_20261001/summary.json'),
    'Engram': ('195fcdac57d10e9047863bf43dcacb247341d1e5', 'results/quality/w16_engram_home_service_demand_20261001/demand.json'),
}


def blob(commit, path):
    full = subprocess.check_output(['git', 'rev-parse', commit], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(['git', 'show', full + ':' + path], cwd=ROOT)
    return raw, dict(commit=full, path=path, sha256=hashlib.sha256(raw).hexdigest())


def require(ok, message):
    if not ok:
        raise ValueError(message)


def rank_review(rank):
    records, summary = rank['records'], rank['summary']
    cycles = sum(r['one_port_cycles_within_emit_dedup'] for r in records)
    words = sum(r['ideal_command_prefetch_cycles'] for r in records)
    uses = sum(r['logical_lane_uses'] for r in records)
    bound = sum(o['unique_words'] for r in records for o in r['operand_demands'] if o['kind'] == 'checkpoint_CROM')
    generated = sum(o['unique_words'] for r in records for o in r['operand_demands'] if o['kind'] == 'unbound_generated')
    require(cycles == words == uses == bound + generated == 549760, 'coefficient issue totals')
    require(bound == 508800 and generated == 40960, 'bound/generated split')
    require(len(records) == summary['commands'] == 491 and rank['bound_operands'] == 729, 'command/descriptor counts')
    require(summary['per_emit_dedup_service_cycles'] == cycles, 'summary service mismatch')
    require(summary['per_command_unique_prefetch_cycles'] == words, 'summary prefetch mismatch')
    peak = max(r['peak_unique_words_per_emit'] for r in records)
    bankpeak = max(r['peak_same_bank_unique_words_per_emit'] or 0 for r in records)
    require(peak == bankpeak == 1024, 'bank demand peak')
    witnesses = [dict(layer=r['layer'], instruction=r['instruction'], global_instruction=r['global_instruction'],
                      values=r['peak_unique_words_per_emit'], bank_values=r['peak_same_bank_unique_words_per_emit'],
                      containers=r['peak_containers_per_emit'], command_buffer_bits=r['command_prefetch_buffer_bits'])
                 for r in records if r['peak_same_bank_unique_words_per_emit'] == 1024]
    return dict(rank=rank['rank'], static_issue_cycles=cycles, bound_cycles=bound, generated_cycles=generated,
                static_issue_ns=str(D(cycles) / D('1.2')), commands=491, operand_descriptors=729,
                peak_same_bank_values=bankpeak, useful_peak_bits=peak * 32, response_peak_bits=peak * 64,
                continuous_serial_emit_required_values_per_fast_cycle=str(D(peak) * D(3) / D(4)),
                one_port_min_issue_cycles_for_peak=1024, peak_witnesses=witnesses)


def validate_service(crom, phase):
    require(crom['capacity']['logical_address_bits'] == 20, 'CROM address width')
    require(crom['ports']['scalar_logical_words_per_fast_cycle'] == 1, 'unbound CROM port change')
    require(not crom['ports']['unrelated_read_parallelism'], 'unbound bank parallelism')
    timing = crom['timing_preflight']
    require(timing['streaming_period_ps'] - timing['SS_macro_clk_to_q_ps'] - timing['capture_setup_ps'] - timing['setup_uncertainty_ps'] == 4,
            'capture margin')
    require(phase['root_stop_credit'] == 0, 'inactive root credit forbidden')
    require(phase['CROM_proposal']['macros'] == 512, 'historical CROM reservation scope')


def build():
    pins, data = {}, {}
    for name, (commit, path) in PINS.items():
        raw, pins[name] = blob(commit, path)
        if name.endswith('_tool'):
            continue
        data[name] = json.loads(gzip.decompress(raw) if name == 'demand' else raw)
    phase, crom = data['phase'], data['CROM']
    validate_service(crom, phase)
    dependencies = {}
    for name, item in phase['input_files'].items():
        path = item['path'].split('/OpenTallas/')[-1] if '/OpenTallas/' in item['path'] else item['path']
        commit = PINS[name][0] if name in ('geometry', 'power') else PINS['phase'][0]
        _, pin = blob(commit, path)
        require(pin['sha256'] == item['sha256'], 'unresolved phase prerequisite: ' + name)
        dependencies[name] = pin
    _, pin = blob(PINS['phase'][0], 'tools/w10_q_power_envelope.py')
    require(pin['sha256'] == pins['power_tool']['sha256'], 'phase power implementation mismatch')
    dependencies['phase_power_tool_binding'] = pin
    for path, expected in data['OR']['source_sha256'].items():
        _, pin = blob(PINS['OR'][0], path)
        require(pin['sha256'] == expected, 'OR audit source mismatch: ' + path)
        dependencies['OR:' + path] = pin
    require(pins['demand']['sha256'] == data['summary']['authoritative_demand_sha256'], 'authoritative v2 pin')
    for path, item in data['summary']['RTL_address_liveness_slot_sources'].items():
        _, pin = blob(item['commit'], path)
        require(pin['sha256'] == item['sha256'], 'demand RTL pin')
        dependencies[path] = pin
    item = data['summary']['source_program']
    _, pin = blob(item['commit'], item['path'])
    require(pin['sha256'] == item['sha256'], 'demand program pin')
    dependencies['demand_program'] = pin
    require([r['rank'] for r in data['demand']['ranks']] == [0, 1, 2, 3], 'rank coverage')
    ranks = [rank_review(r) for r in data['demand']['ranks']]
    engram = data['Engram']['HBM_candidate']
    require(engram['compact_whole_table_flat_sector_address_bits'] == 33 and engram['source_default_sector_address_bits'] == 24,
            'Engram aperture')
    return dict(schema='opentallas.w16.dsrom-phase-demand-review.v1', source_pins=pins,
        verified_dependencies=dependencies, frozen_git_source_integrity=True,
        main_replay_claim=False, owner_phase_numerical_replay=False,
        dependency_resolution='Exact e793 power code/receipt and e61 geometry hash resolved; external library/argv full replay NOT performed.',
        phase_scope='fea is conditional instantaneous power reservations, not a full-program feasible schedule.',
        demand_scope=data['summary']['scope'], rank_reviews=ranks,
        latency_scope='458133.333...ns is static one-port issue service including predicated commands, not additive token slowdown or measured token latency.',
        capacity=dict(required_words=549760, capacity_words=552960, spare_words=3200,
                      logical_address_bits=20, banks=45, capacity_is_bandwidth=False),
        CROM=dict(one_logical_response_per_fast_cycle=True, macro_capture_margin_ps=4,
                  margin_scope='Predictive macro plus assumed capture setup; excludes wire/skew, mux and contextual SS/FF closure.',
                  historical_phase_macros=512, candidate_rank_macros=45, automatic_power_transfer=False,
                  required_staging_contract=['Exact logical-to-striped-bank/lane mapping and golden coefficient order',
                      'Per-bank issue calendar with all constant consumers and generated operand producers',
                      'Finite command/burst buffers, write/read ports, capture/select stages, FF/mux/fanout area',
                      'Fast-to-serial CDC, destination lane capture, backpressure leases, reverse credit and progress deadline',
                      'Per-phase bank/clock/data/wire energy, routing tracks and physical slot budget',
                      'Issue-to-last-consumer absolute intervals composed with existing compute; no free prefetch overlap']),
        Q_OR_repricing=data['OR']['local_repricing_sensitivity'],
        Q_OR_scope='OR2 is not an established generic independent-input NAND construction; OR3 sensitivity requires separate complete area/power/phase repricing, not blind correction credit.',
        Q_inactive_root_credit=0,
        Engram=dict(flat_sector_address_bits=33, current_sector_address_bits=24,
                    sectors_per_token=engram['sectors_per_token'], transfer_bytes_per_token=engram['transferred32byte_sector_bytes_per_token'],
                    region_home_TP_replica_binding=None, shared_controller_service_and_deadline=None,
                    codec='All eight actual scale bytes; reassembly and decoded destination writes require service costs.'),
        full_HBM_scope='Original actual callback-closed software token evidence supplies no hardware clock, port, latency or admission credit.',
        full_program_cost_bound=False, whole_feasible_schedule=False, prefetch_overlap_credit=0,
        engine_RTL_build_ready=False, physical_admission=False, headline_rate=None, jobs_launched=0,
        verdict='BLOCKED_FULL_COST_CALENDAR_AND_COEFFICIENT_SERVICE')


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--out', type=Path)
    group.add_argument('--check', type=Path)
    args = parser.parse_args()
    text = json.dumps(build(), sort_keys=True, indent=2) + '\n'
    if args.check:
        require(args.check.read_text() == text, 'review receipt mismatch')
        print('PASS frozen review receipt; full cost/calendar BLOCKED; no main or owner phase replay claim')
    else:
        with args.out.open('x') as out:
            out.write(text)


if __name__ == '__main__':
    main()
