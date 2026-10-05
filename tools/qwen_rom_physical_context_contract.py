#!/usr/bin/env python3
"""Additive read-only Qwen sink/load and parent release contract.

Uses existing mapped evidence only. Does not run elaboration, synthesis or STA.
A passing release preflight is not hardware admission: full source-qualified
clock/reset distribution, slot and contextual SS/FF receipts remain mandatory.
"""
import argparse
import collections
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = Path('results/uarch/qwen_rom_physical_context_current_20261002')
RESET = Path('results/uarch/qwen_rom_reset_producer_g0_20261002')
CONE = Path('results/uarch/qwen_rom_hold_capture_loaded_map_20261002/terminal_r4')
ADAPTER = Path('results/uarch/h4_c0_r33_source_adapter_20261002/r1/model/source_adapter.json')
MOVEMENT = Path('results/uarch/h4_c0_ordered_movement_20261002/provider_mapping_checkpoint.json')


def read(path):
    raw = (ROOT / path).read_bytes()
    return gzip.decompress(raw).decode() if str(path).endswith('.gz') else raw.decode()


def object_at(path):
    return json.loads(read(path))


def block(raw, start):
    begin = raw.index('{', start)
    depth, end = 1, begin + 1
    while depth:
        depth += (raw[end] == '{') - (raw[end] == '}')
        end += 1
    return raw[start:end]


def pin_caps(raw):
    if not re.search(r'capacitive_load_unit\s*\(\s*1\s*,\s*ff\s*\)', raw):
        raise ValueError('Liberty capacitance units must be fF')
    result = {}
    for c in re.finditer(r'\bcell\s*\(\s*([^\s)]+)\s*\)', raw):
        cell = block(raw, c.start())
        for p in re.finditer(r'\bpin\s*\(\s*([^\s)]+)\s*\)', cell):
            pin = block(cell, p.start())
            cap = re.search(r'\bcapacitance\s*:\s*([\d.eE+-]+)', pin)
            if cap:
                result[(c[1].strip('"'), p[1].strip('"'))] = {
                    'cap_fF': float(cap[1]), 'clock': bool(re.search(r'\bclock\s*:\s*true', pin))}
    return result


def sinks_from_json(net):
    result = []
    for name, cell in sorted(net['cells'].items()):
        for pin, wires in cell['connections'].items():
            if pin in ('CLK', 'RESETN') or (cell['type'].startswith('ot_rom_') and pin == 'clk'):
                if len(wires) != 1:
                    raise ValueError('scalar clock/reset pin required')
                result.append(dict(instance=name, cell=cell['type'], pin=pin, net=str(wires[0])))
    return result


def sinks_from_verilog(raw):
    result = []
    # Exact existing flattened Yosys netlist spelling; reject unmatched DFFs.
    cells = list(re.finditer(r'(?m)^\s*(\w+_ASAP7_75t_R)\s+(\\[^\s]+|[^\s(]+)\s*\((.*?)\);', raw, re.S))
    for c in cells:
        for p in re.finditer(r'\.(CLK|RESETN)\s*\(\s*([^\s)]+)\s*\)', c[3]):
            result.append(dict(instance=c[2], cell=c[1], pin=p[1], net=p[2]))
    expected = sum(c[1].startswith('DFF') for c in cells)
    if expected != sum(s['pin'] == 'CLK' for s in result):
        raise ValueError('mapped sequential clock inventory incomplete')
    return result


def summarize(sinks, libraries):
    classes = collections.Counter((s['cell'], s['pin'], s['net']) for s in sinks)
    records = []
    for (cell, pin, net), count in sorted(classes.items()):
        caps = {}
        for corner, lib in libraries.items():
            item = lib[(cell, pin)]  # no guessed pin type/capacitance
            if pin.lower() == 'clk' and not item['clock']:
                raise ValueError('clock pin must be declared clock in Liberty')
            caps[corner] = dict(pin_cap_fF=item['cap_fF'], total_cap_fF=count * item['cap_fF'])
        records.append(dict(cell=cell, pin=pin, net=net, count=count, corners=caps))
    return dict(clock_sinks=sum(s['pin'].lower() == 'clk' for s in sinks),
                reset_sinks=sum(s['pin'] == 'RESETN' for s in sinks), classes=records,
                pin_only=True, wire_cap_fF=None, clock_tree_area_um2=None,
                reset_distribution_area_um2=None, contextual_closure=False,
                total_pin_cap_fF={corner:{pin:sum(r['corners'][corner]['total_cap_fF']
                    for r in records if r['pin'].lower() == pin.lower()) for pin in ('CLK', 'RESETN')}
                    for corner in libraries})


def release_preflight(receipt, model, expected_instantiated_source_sha256):
    """Check actual provider pin intervals; never substitute bench NBA phase.

    Receipt interval endpoints already include measured wire/clock skew at BOTH
    root RESETN pins. Source hash binding is checked before phase arithmetic.
    This checks external root prerequisites, not downstream timing closure.
    """
    if receipt.get('schema') != 'QWEN_ROOT_PROVIDER_PIN_INTERVALS_V1':
        raise ValueError('actual root provider receipt schema required')
    if receipt.get('scope') != 'physical_external_root_pins' or receipt.get('bench_schedule') is not False:
        raise ValueError('bench NBA schedule is not a physical root provider')
    for field in ('provider_source_sha256', 'instantiated_source_sha256'):
        if not re.fullmatch('[0-9a-f]{64}', receipt.get(field, '')):
            raise ValueError('actual provider and instantiated source hashes required')
    if receipt['instantiated_source_sha256'] != expected_instantiated_source_sha256:
        raise ValueError('provider bound to different instantiated source')
    window = model['conditional_external_release_window']
    pins = receipt.get('pins', [])
    if len(pins) != 2 or len({p['instance_pin'] for p in pins}) != 2:
        raise ValueError('both distinct external root RESETN endpoints required')
    margins = []
    for p in pins:
        for k in ('deassert_min_ps_after_previous_root_posedge', 'deassert_max_ps_after_previous_root_posedge',
                  'reset_low_pulse_min_ps', 'reset_slew_min_ps', 'reset_slew_max_ps',
                  'clock_slew_min_ps', 'clock_slew_max_ps'):
            if not isinstance(p.get(k), (int, float)) or not math.isfinite(p[k]):
                raise ValueError('unknown arrival/slew cannot be zero-filled')
        lo = p['deassert_min_ps_after_previous_root_posedge']
        hi = p['deassert_max_ps_after_previous_root_posedge']
        if lo > hi:
            raise ValueError('inverted arrival interval')
        for kind in ('reset', 'clock'):
            if not 5 <= p[kind+'_slew_min_ps'] <= p[kind+'_slew_max_ps'] <= 320:
                raise ValueError('slew outside characterized grid')
        removal = lo - window['deassert_min_ps_after_previous_root_posedge']
        recovery = window['deassert_max_ps_after_previous_root_posedge'] - hi
        pulse = p['reset_low_pulse_min_ps'] - window['reset_low_pulse_min_ps']
        if min(removal, recovery, pulse) < 0:
            raise ValueError('external provider contract fails; not an internal zero-delay path verdict')
        margins.append(dict(instance_pin=p['instance_pin'], removal_margin_ps=removal,
                            recovery_margin_ps=recovery, pulse_margin_ps=pulse))
    return dict(status='EXTERNAL_PROVIDER_PREFLIGHT_ONLY', margins=margins, hardware_admission=False)


def macro_inventory(name, replicas):
    base = Path('physical/asap7_memory_macros') / name
    lef = read(base / (name+'.lef'))
    size = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lef)
    caps = {c: pin_caps(read(base / (name+'_'+c+'.lib')))[(name, 'clk')]['cap_fF'] for c in ('ss', 'ff')}
    return dict(name=name, replicas=replicas, width_um=float(size[1]), height_um=float(size[2]),
                total_area_um2=replicas*float(size[1])*float(size[2]), clock_cap_fF=caps,
                clock_total_cap_fF={c: replicas*v for c, v in caps.items()}, reset_pins=0,
                signal_pin_layers=sorted(set(layer for pin in re.finditer(
                    r'\bPIN\s+(\S+)(.*?)\bEND\s+\1\b', lef, re.S)
                    if pin[1] not in ('VDD', 'VSS')
                    for layer in re.findall(r'\bLAYER\s+(M\d+)\s*;', pin[2]))),
                obstruction_layers=sorted(set(re.findall(r'\bLAYER\s+(M\d+)\s*;', lef.split('OBS', 1)[1]))),
                abstract_includes_PG_and_OBS=True, current_slot_PG_OBS_join=None)


def build():
    model = object_at(RESET / 'model-r5.json')
    libs = {}
    for corner in ('ss', 'ff'):
        libs[corner] = pin_caps(read(RESET / ('inputs/seq_'+corner+'.lib.gz')))
        rom = Path('physical/asap7_memory_macros/ot_rom_4096x266_m8')
        libs[corner].update(pin_caps(read(rom / ('ot_rom_4096x266_m8_'+corner+'.lib'))))
    historic = sinks_from_verilog(read(OUT / 'inputs/historical_logic_mapped.v.gz'))
    cone = sinks_from_json(object_at(CONE / 'mapped.json.gz')['modules']['qwen_loaded_capture'])
    hist_summary, cone_summary = summarize(historic, libs), summarize(cone, libs)
    resources = model['persistent_KV']['resources']
    # Bind actual floorplan policy rather than import its build entry points.
    floor = read(Path('tools/qwen_o4_floorplan.py'))
    pitch = json.loads(re.search(r'UPPER_PITCH_NM = (\{[^\n]+\})', floor)[1].replace("'", '"'))
    share = float(re.search(r'SIGNAL_SHARE = ([\d.]+)', floor)[1])
    corridor = float(re.search(r'CORRIDOR_UM = ([\d.]+)', floor)[1])
    tracks_per_um = sum(1000/pitch[layer] for layer in ('M6', 'M8')) * share
    adapter, movement = object_at(ADAPTER), object_at(MOVEMENT)
    euclid = object_at(OUT / 'inputs/euclid_fulltile_context_preflight_r1.json')
    russell = object_at(OUT / 'inputs/russell_contract_r3.json')
    origins = object_at(OUT / 'inputs/peer-source-origins-r1.json')
    # The wrapper source explicitly selects SMIN6, although its JSON target
    # omits SMIN. The preserved census was elaborated with SMIN7.
    wrapper = read(OUT / 'inputs/euclid_ot_qwen_rom_fulltile_tp4_context_top.sv')
    wrapper_smin = int(re.search(r'\.SMIN\((\d+)\)', wrapper)[1])
    root_ff = 'DFFASRHQNx1_ASAP7_75t_R'
    added_caps = {c: {pin:6*libs[c][(root_ff,pin)]['cap_fF'] for pin in ('CLK', 'RESETN')} for c in libs}
    packet = dict(schema='QWEN_PHYSICAL_CONTEXT_CURRENT_V1', base='ce132ffea40cf31f1af9d8c7af696d5e57125213',
        status='PARENT_PHYSICAL_DEPENDENCIES_OPEN', default_on=False, RTL_map_PR_allowed=False,
        re_elaboration=False, constraints=model['constraints'], protocol=model['protocol'],
        root_provider=dict(actual_receipt=None, bench_is_physical_receipt=False,
            required_schema='QWEN_ROOT_PROVIDER_PIN_INTERVALS_V1',
            conditional_pin_window=model['conditional_external_release_window'],
            source='die CXX bench rt_rst_n NBA cyc5; stages cyc6/7; downstream start cyc8',
            owner='Euclid/root physical provider; upstream die/core and serial release join remains parent-owned'),
        mapped_sinks=dict(historical_complete_logic=dict(**hist_summary, current_source_qualified=False,
            reason='old ot_qwen_rom_tile_logic namespace/default arithmetic; no source-qualified current W12 mapping',
            clock_domain='historical single clk; not physical 0.9GHz serial readiness'),
            current_loaded_capture=dict(**cone_summary, complete_tile=False,
                producer_ports_external=['wrom_addr', 'wrom_re'], physical_producer_CLKQ_observed=False),
            planned_cone_with_four_bank5_FFs_and_two_root_FFs=dict(clock_sinks=cone_summary['clock_sinks']+6,
                reset_sinks=cone_summary['reset_sinks']+6, measured=False,
                incremental_pin_cap_fF=added_caps,
                total_pin_cap_fF={c:{p:cone_summary['total_pin_cap_fF'][c][p]+added_caps[c][p]
                    for p in ('CLK', 'RESETN')} for c in libs}),
            complete_current_tile=dict(clock_bits_preopt=None, reset_bits_preopt=None,
                preserved_source_clock_bits_preopt=model['price']['source_logic_tile_clock_bits']+1032,
                preserved_source_reset_bits_preopt=58919, mapped_sinks=None, preopt_widths_are_not_pin_counts=True,
                preserved_census_SMIN=7, current_wrapper_SMIN=wrapper_smin,
                census_transfer_to_current_wrapper_allowed=False)),
        macros=[macro_inventory('ot_rom_4096x266_m8', 10), macro_inventory('ot_sram_1r1w_128x256_m1_r2c2', 2)],
        root_cost=dict(nominal_cell_area_um2=model['price']['root_cell_area_um2_per_tile'],
            complete_clock_reset_distribution_slot_cost_um2=None, tiles_per_die=1536,
            upstream_root_RESETN_sinks_per_die=3072, excludes_die_core_and_other_domains=True,
            proposed_external_root_RESETN_pin_cap_fF_per_die={c:3072*libs[c][(root_ff,'RESETN')]['cap_fF'] for c in libs}),
        producer_arrival_contract=dict(actual_SS_CLKQ_max_ps=None, actual_FF_CLKQ_min_ps=None,
            registered_source=model['source_ports']['producer'],
            required_address_hold_equation=model['release_equations']['address_hold'],
            required_reset_equations={k:v for k,v in model['release_equations'].items() if 'tile_' in k},
            source_qualified_complete_sink_map_required=True, external_zero_delay_is_internal_failure=False),
        routing=dict(policy_layers=['M6', 'M8'], policy_signal_share=share, corridor_um=corridor,
            policy_capacity_tracks=corridor*tracks_per_um,
            actual_KV_fill_tracks=resources['required_parallel_signal_tracks_at_fill_boundary'],
            minimum_policy_width_um=resources['required_parallel_signal_tracks_at_fill_boundary']/tracks_per_um,
            policy_fit=resources['required_parallel_signal_tracks_at_fill_boundary'] <= corridor*tracks_per_um,
            current_routed_capacity=None, clock_reset_tracks_additional=None,
            note='Conditional lower bound for this boundary/layer policy; not a production channel receipt'),
        peer_source_joins=dict(origins=origins, Euclid_fulltile=euclid,
            Russell_production=dict(source_sha256=russell['source_sha256'],
                policy_selected=russell['production_policy_selected'],
                actual_tail_physical_context=russell['physical_context'],
                boundary=russell['boundary'], receipt_schema=russell['receipt_schema'],
                pricing=russell['pricing'], remaining=russell['remaining']),
            actual_KV_capture=object_at(OUT / 'inputs/russell_actual_capture_inventory_r1.json'),
            current_wrapper_census_join='SMIN6 vs preservedSMIN7; KV_NH2/KV_VB131072 vs census defaults4/262144. No new elaboration; totals held at original scope.'),
        persistent_KV=dict(source_commit=model['persistent_KV']['source_commit'],
            actual_service_macros_per_stack=resources['actual_service_macro_count_per_stack'],
            macro_area_mm2_per_stack=resources['actual_service_macro_area_mm2_per_stack'],
            assembly_slots_per_stack=resources['assembly_entries_per_stack'],
            inherited_slot_is_current_fit=False, current_slot_fit=None,
            domains_Hz={k:resources[k+'_target_Hz'] for k in ('stream', 'serial', 'service')},
            cold_calendar_role='reference only, not selected production',
            latency=model['persistent_KV']['latency'], physical_contract_blockers=model['persistent_KV']['blockers']),
        ordered_movement=dict(checkpoint=movement, Qwen_source=adapter['Qwen'],
            lowered_r33_scope='DeepSeek40PC source join; Qwen1737PC source unchanged',
            actual_address_and_reverse_credit_receipts=None, full_program_qualified=False),
        current_once_calendar=dict(required_schema=adapter['Dewey_once_reprice_schema'],
            required_receipt_fields=adapter['required_reprice_fields'], actual_receipt=None,
            admitted=False, owner='Dewey', no_new_numerical_run=True,
            RF_highword_RMW_recharged=False, C0_control_recharged=False),
        ranked_dependencies=[
            '1 Actual upstream root provider phase/pulse/slew at both root RESETN pins, hashed instantiated source; hold ib_go/input through first downstream accept',
            '2 Bind explicit Euclid SMIN6/KV_NH2/KV_VB131072 source before transferring SMIN7/defaultKV census; current complete tile/die/core/serial/service sink map and SS/FF producer CLKQ plus reset/address distribution min/max/skew',
            '3 Complete root/CTS/reset distribution/CDC/control area plus current slot/PGOBS and real corridor capacity',
            '4 Russell finite KV assembly/retirement/reverse credit and domain readiness; cold calendar stays reference',
            '5 Kepler actual addressed owner/version/generation/payload and consumer/reverse grant; Dewey once-only r33 calendar receipt'])
    return packet, dict(historical_complete_logic=historic, current_loaded_capture=cone)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / OUT)
    args = parser.parse_args()
    packet, sinks = build()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'parent-IO-next-receipt-r1.json').write_text(json.dumps(dict(
        schema='QWEN_PARENT_IO_NEXT_RECEIPT_REQUEST_V1', status='REQUIRED_NOT_OBSERVED',
        target_source_sha256=packet['peer_source_joins']['Euclid_fulltile']['source_sha256'],
        child_source_sha256=packet['peer_source_joins']['Euclid_fulltile']['child_source_sha256'],
        target_parameters=packet['peer_source_joins']['Euclid_fulltile']['explicit_current_target'],
        target_SMIN=packet['mapped_sinks']['complete_current_tile']['current_wrapper_SMIN'],
        external_ports=['clk_stream','reset_stream_n','ib_go','ib[378:0]','xl[127:0]',
                        'kvw_ce','kvw_addr[6:0]','kvw_data[511:0]','kvw_mask[511:0]'],
        root_receipt_schema=packet['root_provider']['required_schema'],
        required_root_fields=['provider_source_sha256','instantiated_source_sha256',
            'scope=physical_external_root_pins','bench_schedule=false','pins[2].instance_pin',
            'pins[2].deassert_min_ps_after_previous_root_posedge',
            'pins[2].deassert_max_ps_after_previous_root_posedge',
            'pins[2].reset_low_pulse_min_ps','pins[2].reset_slew_min_ps',
            'pins[2].reset_slew_max_ps','pins[2].clock_slew_min_ps','pins[2].clock_slew_max_ps'],
        root_bounds=packet['root_provider']['conditional_pin_window'],
        launch_contract=packet['protocol']['queue'],
        ordered_acceptance=packet['protocol']['acceptance'],
        current_mapped_receipt_required=['full source bundle hash and explicit parameters',
            'each surviving cell clock/reset sink and domain; 10ROM2KV clocks included once',
            'SS/FF registered wrom_addr/re CLKQ min/max and loaded buffer/wire min/max',
            'root-to-all-reset recovery/removal/pulse/slew with clock skew and 60ps/25ps uncertainties',
            'complete CTS/reset/distribution/CDC area and current slot LEF/PGOBS/corridor join'],
        source_census_transfer_allowed=False, hardware_admission=False,
        next_owner='Euclid root/provider and mapping context; Russell actual production receipt/calendar; Maxwell composition'),
        indent=2, sort_keys=True)+'\n')
    (args.out / 'model-r1.json').write_text(json.dumps(packet, indent=2, sort_keys=True)+'\n')
    (args.out / 'mapped-sink-census-r1.json.gz').write_bytes(gzip.compress(
        json.dumps(sinks, sort_keys=True, separators=(',', ':')).encode(), mtime=0))
    paths = [Path(__file__).relative_to(ROOT), Path('tests/test_qwen_rom_physical_context_contract.py'),
             RESET/'model-r5.json', RESET/'tile_registers_r1.json.gz', CONE/'mapped.json.gz', ADAPTER, MOVEMENT, Path('tools/qwen_o4_floorplan.py')]
    paths += [Path(p) for p in ('rtl/hdc/ot_qwen_rom_tile_context_candidate_r2.sv',
        'rtl/hdc/ot_qwen_rom_tile_w12.sv', 'rtl/hdc/ot_qwen_w12_matvec.sv',
        'rtl/physical/ot_qwen_rom_bank5_control_distribution.sv',
        'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv',
        'rtl/test/qwen_rom_runtime/qwen_rom_rt_w12.cpp',
        'tools/uarch_model.py', 'tools/uarch_model_qwen_reset.py')]
    paths += sorted((ROOT / OUT / 'inputs').glob('*'))
    paths += sorted((ROOT / RESET / 'inputs').glob('seq_*.lib.gz'))
    for name in ('ot_rom_4096x266_m8', 'ot_sram_1r1w_128x256_m1_r2c2'):
        base = Path('physical/asap7_memory_macros') / name
        paths += [base/(name+suffix) for suffix in ('.lef', '_ss.lib', '_ff.lib')]
    pins = {str(p.relative_to(ROOT) if p.is_absolute() else p):
            hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    (args.out / 'sourcepins-r1.json').write_text(json.dumps(dict(base=packet['base'], sha256=pins), indent=2, sort_keys=True)+'\n')
    artifacts = {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in args.out.iterdir()
                 if p.is_file() and p.name != 'artifact-sha256-r1.json'}
    (args.out / 'artifact-sha256-r1.json').write_text(json.dumps(artifacts, indent=2, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
