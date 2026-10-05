#!/usr/bin/env python3
"""Conditional energy ledger, not a measured-power or total-power claim.

Prices enumerable shared-ROM work; unresolved terms remain symbolic and prevent
qualification. All sensitivities retain the identical token work and inventory.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f'invalid {name}')
    return value


def evaluate(candidate, inputs, technology, scenarios, kv):
    if 'tpot_us' not in candidate or 'service' not in candidate:
        raise ValueError('candidate lacks a schedulable token: ' + '; '.join(candidate.get('rejection', [])))
    tp = candidate['candidate']['tp']
    seconds = nonnegative(candidate['tpot_us'], 'tpot_us') * 1e-6
    if seconds == 0:
        raise ValueError('zero token time')
    service = candidate['service']
    geom = candidate['geometry']
    weight_bytes = 0
    activation_access_bytes = 0
    macs = {}
    selected_read_envelope = 0
    missing_read_envelopes = []
    for node in inputs['dag']:
        if node['kind'] != 'weight':
            continue
        rep = tp if node.get('replicated') else 1
        weight_bytes += nonnegative(node['weight_bytes'], 'weight_bytes') * rep
        fmt = node['format']
        macs[fmt] = macs.get(fmt, 0) + nonnegative(node['macs'], 'macs') * rep
        # Every tile stages its input activation; result written once by owner.
        measured = service[node['id']]
        activation_access_bytes += (2 * node['activation_bytes'] * measured['active_tiles'] * tp
                                    + 2 * node['result_bytes'] * rep)
        if 'source_request_cycles_upper' in measured:
            selected_read_envelope += (measured['source_request_cycles_upper']
                                      * measured['weight_bytes_per_cycle_active'] * tp)
        else:
            missing_read_envelopes.append(node['id'])
    energy = technology['energy']
    coeff = scenarios['mac_lane']['scenario_B']['per_mac']
    compute = sum(count * coeff[fmt]['value'] * 1e-12 for fmt, count in macs.items())
    traffic = kv['traffic']
    hbm_bytes = (traffic['fullscan_index_B_per_token']
                 + traffic['selected_CKV_HBM_B_if_fetch_every_compressed_layer']
                 + traffic['window_cold_B_all_layers'])
    # Cold per-layer row staging is deliberately retained; resident state is a
    # separate scenario requiring the corresponding ownership/exactness gate.
    hbm_pj_bit = scenarios['memory']['hbm_path_total']['value']
    hbm_dynamic = hbm_bytes * 8 * hbm_pj_bit * 1e-12
    stacks = candidate['topology']['memory_inventory']['hbm_stacks']
    if stacks is None:
        raise ValueError('missing HBM stack inventory')
    idle = stacks * scenarios['memory']['idle_w_per_stack']['value'] * seconds
    rows = []
    read_cases = [('useful_payload_floor', weight_bytes)]
    if not missing_read_envelopes:
        read_cases.append(('selected_request_calendar_envelope', max(weight_bytes, selected_read_envelope)))
    for read_case, read_bytes in read_cases:
        for distance in (0.35, 1, 5):
            for wire in (0.1, 0.4):
                for extra_source_fifo in (False, True):
                    terms = {
                        'ROM_reads': read_bytes * energy['rom_read_j_per_byte']['value'],
                        'weight_network_repeated_wire': read_bytes * 8 * distance * wire * 1e-12,
                        'mandatory_G0_weight_ring_write_read': 2 * read_bytes * energy['sram_read_j_per_byte']['value'],
                        'optional_extra_source_FIFO_write_read': 2 * read_bytes * energy['sram_read_j_per_byte']['value'] if extra_source_fifo else 0,
                        'activation_result_SRAM_proxy': activation_access_bytes * energy['sram_read_j_per_byte']['value'],
                        'weight_arithmetic_only': compute,
                        'HBM_index_KV_read_proxy': hbm_dynamic,
                        'HBM_standby_assumption': idle,
                    }
                    subtotal = sum(terms.values())
                    rows.append(dict(read_case=read_case, assumed_mean_weight_path_mm=distance,
                                     wire_pj_bit_mm=wire, mandatory_G0_weight_ring=True,
                                     optional_extra_source_FIFO=extra_source_fifo,
                                     applicability=('lower_bound_not_actual_candidate_read_traffic' if read_case == 'useful_payload_floor' else 'conditional_request_calendar_envelope_not_measured_activity'),
                                     terms_j=terms, priced_subtotal_j_per_token=subtotal,
                                     priced_subtotal_average_w=subtotal / seconds,
                                     total_j_per_token=None, total_average_w=None))
    dies = candidate['topology']['logic_dies']
    active_dies = len(candidate['topology']['stages']) * tp
    rom_area = geom['rom_mm2_per_die'] * active_dies
    auxiliary = candidate['topology'].get('auxiliary', {})
    # Auxiliary ROM macro area is inferable from allocated physical pair count.
    aux_rom_area = (auxiliary.get('dies', 0) * auxiliary.get('pairs_per_die', 0)
                    * 2 * inputs['macro']['area_mm2'])
    rom_area += aux_rom_area
    leak = technology['power']['static_leakage_w_per_mm2']['rom_array']
    return dict(schema='opentallas.hbrom.power-projection.v1', qualified=False,
                status='conditional_partial_projection_unknown_terms_not_zero',
                candidate=candidate['candidate'], tpot_us=candidate['tpot_us'],
                workload=dict(useful_weight_bytes=weight_bytes, macs_by_format=macs,
                              selected_read_calendar_bytes=selected_read_envelope if not missing_read_envelopes else None,
                              activation_result_SRAM_access_proxy_bytes=activation_access_bytes,
                              HBM_read_proxy_bytes=hbm_bytes, HBM_stacks=stacks,
                              logic_dies=dies, ROM_macro_mm2=rom_area),
                sensitivities=rows,
                idle_sensitivity=dict(HBM_standby_W=stacks * scenarios['memory']['idle_w_per_stack']['value'],
                                      HBM_standby_evidence='ASSUMED W/stack; dominant term may depend on trained/standby policy',
                                      HBM_standby_j_per_token={k:stacks * technology['power']['memory_interface_idle_w_per_stack'][k] * seconds for k in ('range_low','value','range_high')},
                                      each_additional_W_per_logic_die_j_per_token=dies * seconds,
                                      each_additional_system_W_j_per_token=seconds,
                                      ROM_leakage_only_j_per_token={k:rom_area * leak[k] * seconds for k in ('range_low','value','range_high')}),
                unknown_addends=['actual captured macro padding/toggling beyond request-calendar envelope',
                                  'clock network and clock-pin energy for new cluster and service regions',
                                  'logic/SRAM leakage with actual power-gating residency',
                                  'mux select and descriptor/control switching (wire proxy is not these)',
                                  'retained KV SRAM read/write, nonweight attention/index/SFU arithmetic',
                                  'HBM writes, transfer padding, protection and refresh policy delta',
                                  'link data bit-hops, PHY trained idle, replay/credit reverse traffic',
                                  'mutable SRAM/link/control protection energy and wake energy'],
                assumptions=['All coefficients are sizing assumptions or transfers; no shared-ROM measured power.',
                             'Wire distance is swept, not extracted physical routing.',
                             'Arithmetic coefficient excludes clocks; MAC includes one FP32 accumulation, no double count.',
                             'SRAM read coefficient used for writes is assumed; activation access counts assume one staged write and one read per tile, additional reuse reads unpriced.',
                             'HBM proxy retains full index scans and one selected-row read per layer; exact service trace may read more.',
                             'Selected G0 has a mandatory 1024-line weight ring: every sensitivity charges a write and read; there is no reachable no-staging candidate.',
                             'Optional extra source FIFO is a distinct extra buffering sensitivity, not permission to bypass the G0 ring.',
                             'Useful payload read case is only a lower bound; request-calendar envelope includes issued padding but is not a measured macro activity count.',
                             'HBM standby is an assumed 2.8 W per populated stack, not measured accelerator standby; it is charged across the full token.',
                             'ROM leakage excludes all clocked periphery and other logic; it is not total die idle.',
                             'No sum of independent die maxima is presented as simultaneous peak.'],
                peak_w=None, peak_reason='Needs phase-aligned power activities, clock enables, PHY and service traces')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--inputs', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    files = dict(candidate=Path(args.candidate), inputs=Path(args.inputs),
                 technology=ROOT/'configs/hardware/technology.json',
                 scenarios=ROOT/'configs/hardware/power_scenarios.json',
                 kv=ROOT/'results/uarch/hbrom/inputs/hbrom-kv.json')
    values = {k:json.loads(p.read_text()) for k,p in files.items()}
    result = evaluate(**values)
    result['source_pins'] = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files.values()}
    result['source_pins'][str(Path(__file__).resolve())] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    Path(args.out).write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
