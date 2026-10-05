#!/usr/bin/env python3
"""Review exact owner CROM cost joins. Does not design or admit a provider."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import subprocess
import types

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'finite': ('bc1ec8b8f73ce5594a2b65ac7856b88c3f6b027c', 'results/quality/w16_w17_crom_finite_prefetch_20261001/calendar.json'),
    'finite_tool': ('bc1ec8b8f73ce5594a2b65ac7856b88c3f6b027c', 'tools/w17_crom_finite_prefetch.py'),
    'landed_finite_tool': ('f8e435dd8c25749b5a8ce060e81c2e0b79f3ab30', 'tools/w17_crom_finite_prefetch.py'),
    'control': ('ebef36895739134e4d0eb5456ab40da4d4c4b8df', 'results/uarch/w10_crom_control_reservation_r1/budget.json'),
    'control_tool': ('ebef36895739134e4d0eb5456ab40da4d4c4b8df', 'tools/w10_crom_control_reservation.py'),
    'BF_scope': ('955c8da74d2a8e5129d2d95141b4bb04d404760d', 'results/quality/w16_w17_whole_calendar_20261001/calendar.json'),
}


def blob(commit, path):
    commit = subprocess.check_output(['git', 'rev-parse', commit], cwd=ROOT, text=True).strip()
    raw = subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)
    return raw, dict(commit=commit, path=path, sha256=hashlib.sha256(raw).hexdigest())


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_tool(raw, name):
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / 'tools' / (name + '.py'))
    exec(compile(raw, '<pinned ' + name + '>', 'exec'), module.__dict__)
    return module


def totals(finite, control, base):
    cc = finite['compiler_control_storage']
    require((cc['total4096x274_macros'], cc['mandatory_raw_capture_FF_bits'],
             cc['page_select_mux_bits'], cc['tag_valid_and_epoch_state_FF_bits']) == (16, 4384, 3288, 5372),
            'control inventory changed; requires new review')
    catalog = control['control_catalog_tag_reservation']
    require(catalog['FF_bits'] == 4384 + 5372 and catalog['macros'] == 16 and catalog['explicit_MUX2_bits'] == 3288,
            'catalog counts mismatch')
    require(base['total_storage_bits'] == 475402 and base['storage_bits_by_purpose']['two_operands_FP32_two_emit_slots'] == 131072,
            'two operand storage mismatch')
    scenarios = []
    require(sorted(s['credits'] for s in control['credit_scenarios']) == [2, 4, 128], 'credit coverage')
    for s in control['credit_scenarios']:
        credit = s['credit_route_reservation']
        require(credit['FF_bits'] == sum(s['state_bits_by_purpose'].values()), 'credit state count')
        require(s['state_bits_by_purpose']['route_pipeline_bits'] == 75 * 1024, 'forward route inventory')
        parts = [base, catalog, credit]
        ff = sum(p.get('total_storage_bits', p.get('FF_bits', 0)) for p in parts)
        area = sum(D(p['conditional_cell_plus_macro_area_mm2']) for p in parts)
        clock = sum(D(p['ungated_clock_W']) for p in parts)
        require(ff == s['buffer_plus_catalog_plus_credit_route_FF_bits'], 'combined FF count')
        require(area == D(s['conditional_combined_area_mm2']), 'combined area')
        require(clock == D(s['combined_ungated_clock_W']), 'combined clock')
        subtotal = D(base['priced_clock_leak_data_pin_subtotal_W']) + sum(D(p['clock_leak_data_pin_subtotal_W']) for p in (catalog, credit))
        wire = sum(D(p.get('unresolved_all_output_load_ceiling_W', p.get('unresolved_output_load_ceiling_W'))) for p in parts)
        ticks = sum(next(d['total_candidate_partial_ticks'] for d in cmd['deliveries'] if d['credits'] == s['credits']) for cmd in finite['commands'])
        require(D(ticks) / D(3600) == D(finite['candidate_delivery_partial_us_by_credit'][str(s['credits'])]), 'delivery sum')
        require(not s['whole_CROM_budget_ready'], 'unqualified complete budget claim')
        scenarios.append(dict(credits=s['credits'], FF_bits=ff, conditional_area_mm2=str(area),
            ungated_clock_W=str(clock), clock_leak_data_pin_allocation_W=str(subtotal),
            unresolved_output_wire_ceiling_W=str(wire), partial_delivery_ticks=ticks,
            partial_delivery_us=str(D(ticks)/D(3600)), qualified_receiver_deadline=False))
    return scenarios


def build():
    raws, pins, data = {}, {}, {}
    for name, (commit, path) in PINS.items():
        raws[name], pins[name] = blob(commit, path)
        if not name.endswith('_tool'):
            data[name] = json.loads(raws[name])
    require(raws['finite_tool'] == raws['landed_finite_tool'], 'landed owner tool mismatch')
    finite, control = data['finite'], data['control']
    source_checks = {}
    for group, record in (('finite', finite), ('control', control)):
        for name, pin in record['source_pins'].items():
            _, actual = blob(pin['commit'], pin['path'])
            require(actual['sha256'] == pin['sha256'], 'source pin mismatch: ' + group + ':' + name)
            source_checks[group + ':' + name] = actual
    replay = load_tool(raws['finite_tool'], 'w17_crom_finite_prefetch').build()
    require((json.dumps(replay, indent=2, sort_keys=True) + '\n').encode() == raws['finite'], 'owner finite replay differs')
    cp = control['source_pins']
    inputs = {k: json.loads(blob(cp[k]['commit'], cp[k]['path'])[0]) for k in ('operand_buffer', 'power', 'clock', 'area')}
    replay = load_tool(raws['control_tool'], 'w10_crom_control_reservation').build(finite, inputs['operand_buffer'], inputs['power'], inputs['clock'], inputs['area'])
    replay['source_pins'] = control['source_pins']
    require((json.dumps(replay, indent=2, sort_keys=True) + '\n').encode() == raws['control'], 'owner control replay differs')
    scenarios = totals(finite, control, inputs['operand_buffer'])
    family = next(x for x in data['BF_scope']['candidate_table'] if x['q_pairs'] == 1024)['schedules'][0]['families'][0]
    bf_pin = D(family['BF_root_pin_internal_only_upper_W'])
    bf_wire = D(family['BF_unresolved_output_wire_upper_W'])
    require(bf_pin + bf_wire == D(family['BF_incoming_CFG_STREAM_root_data_wire_upper_W']), 'BF decomposition')
    return dict(schema='opentallas.w16.crom-control-join-review.v1', source_pins=pins,
        verified_owner_source_pins=source_checks, owner_finite_exact_replay=True, owner_control_exact_replay=True,
        landed_tool_exact_to_bc1=True, main_full_join_replayed=False, cost_scenarios=scenarios,
        inventory=dict(coefficient_banks_per_home=45, additional_control_macros=16, catalog_capture_bits=4384,
                       page_mux_bits=3288, tag_valid_epoch_bits=5372, total_catalog_FF_bits=9756),
        scope='Per modeled home conditional reservations, not complete die/product totals or physical minima. Four equivalent rank calendars are not a proven home placement.',
        model_join=dict(Ram='Bind current finite coefficient/control costs to exact whole-program homes and absolute critical paths.',
                        Confucius='Join all new clocks, macro/pin/data activity and source intervals; preserve ungated Q roots and separate wire ceilings.',
                        direct_owner_acknowledgement=False),
        outstanding_whole_clocks=['Reverse ACK/control lane pipeline and CDC state beyond abstract return counter',
            'Destination clock crossing, lane cache acceptance and synchronizer/memory implementation',
            'Descriptor decoder, page selection, arbitration, tag/epoch comparator and fanout repair',
            'Actual home replication, 45+16 macro clock/load placement, complete CTS/PG/IR/SS/FF',
            'Full phase interval unions for BF enabled work, hub, Engram, coefficient refill and reset/glitch'],
        outstanding_critical_paths=['Repacked image and exact request/fill catalog producer plus generated Engram products',
            'Catalog read/capture/page-mux/select additional cycles before every bank wave and fill',
            'Measured or source-proved bounded sink, destination contention and held reverse credit completion',
            'All81 cold gamma refills preceding actual first emit; 491 command dependencies with no unpriced overlap',
            'All full-token operator/collective/CKV fence/Engram/vocabulary/home costs and source-order joins'],
        BF_separate_review=dict(incoming_pin_internal_allocation_W=str(bf_pin), unresolved_wire_ceiling_W=str(bf_wire),
            sum_W=str(bf_pin+bf_wire), source_interval=family['BF_root_data_activation_interval'],
            floor=False, always_on=False, physical_power=False),
        capacity_is_bandwidth=False, static_scalar_issue_us='458.1333333333333333333333333',
        scalar_scope='Includes predicated commands; not additive token slowdown. Scenario subtraction supplies no validated gain.',
        Q_OR_complete_repricing_pending=True, Q_inactive_root_credit=0, Engram_region_service_pending=True,
        hardware_clock_or_latency_from_HBM_software=False, complete_whole_clock_bound=False,
        full_operator_critical_path_ticks=None, complete_power_qualified=False, physical_admission=False,
        engine_RTL_build_ready=False, headline_rate=None, jobs_launched=0,
        verdict='EXACT_ADDITIVE_COST_REPLAY_WHOLE_JOIN_BLOCKED')


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--out', type=Path)
    group.add_argument('--check', type=Path)
    args = parser.parse_args()
    text = json.dumps(build(), sort_keys=True, indent=2) + '\n'
    if args.check:
        require(args.check.read_text() == text, 'review receipt mismatch')
        print('PASS exact pinned owner cost replays; whole clocks/critical paths remain BLOCKED')
    else:
        with args.out.open('x') as f:
            f.write(text)


if __name__ == '__main__':
    main()
