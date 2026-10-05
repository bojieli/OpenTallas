#!/usr/bin/env python3
"""Opt-in corrected element EDT route: real 32-chain restitch, mapped 4-channel codec.

The original scan route and codec ENABLE=0 defaults are untouched. This caller
selects Boole's qualified component, not an independent-PPI ATPG abstraction.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import tapeout_item8_scan_route as frame
from dft import liberty, macro_bound, netlist as nl
from dft.edt_pattern_encode import encode, response_check

driver = frame.driver
CODEC = 'rtl/dft/ot_scan_edt8to1.sv'
MODEL = 'results/uarch/scan_edt_codec_20261005/selected32_protocol_model.json'
ENCODER = 'tools/dft/edt_pattern_encode.py'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def splice_codec(text, codec):
    """Flatten already mapped codec cells without renaming original macro instances."""
    core = next(m for m in nl.parse_netlist(text) if m.name == 'ot_v41_rom_elem_q_qp_w10')
    for port in ('clk', 'rst_n'):
        if core.port_dirs.get(port) != 'input' or core.ranges.get(port) is not None:
            raise ValueError(f'actual scalar {port} binding missing')
    binding = {'clk': 'clk', 'rst_n': 'rst_n',
               'scan_en': 'scan_en', 'pattern_reset': 'scan_pattern_reset'}
    for p, target, width in (('edt_in', 'scan_in', 4), ('edt_out', 'scan_out', 4),
                             ('chain_in', 'edt_chain_in', 32), ('chain_out', 'edt_chain_out', 32)):
        for i in range(width):
            binding[f'{p}[{i}]'] = f'{target}[{i}]'
    if set(codec.port_bits('input') + codec.port_bits('output')) != set(binding):
        raise ValueError('mapped codec ABI differs from qualified 32/4 component')
    if any(name.startswith('edt_codec_') for name in core.ranges):
        raise ValueError('codec namespace collision')

    def bit(b):
        if nl.is_const_bit(b):
            return b
        if b in binding:
            return binding[b]
        # The mapping flow splits all nets and ports into scalar identifiers.
        if b not in codec.ranges or codec.ranges[b] is not None:
            raise ValueError(f'unsplit or undeclared codec bit {b}')
        return nl.verilog_name('edt_codec_' + b)

    wires = ['wire ' + bit(n) + ';' for n in codec.ranges if n not in binding]
    statements = []
    for inst in codec.instances:
        pins = []
        for pin, bits in inst.pins.items():
            expr = bit(bits[0]) if len(bits) == 1 else ('{' + ', '.join(bit(b) for b in bits) + '}' if bits else '')
            pins.append('.' + nl.verilog_name(pin) + '(' + expr + ')')
        statements.append(nl.verilog_name(inst.cell) + ' ' + nl.verilog_name('edt_codec_' + inst.name)
                          + ' (' + ', '.join(pins) + ');')
    for lhs, rhs, _ in codec.assigns:
        if len(lhs) != len(rhs):
            raise ValueError('codec assign width mismatch')
        statements.extend('assign ' + bit(a) + ' = ' + bit(b) + ';' for a, b in zip(lhs, rhs))
    ports = [p for p in core.ports if p not in ('edt_chain_in', 'edt_chain_out')]
    ports += ['scan_in', 'scan_out', 'scan_pattern_reset']
    header = 'module ' + nl.verilog_name(core.name) + '(' + ', '.join(nl.verilog_name(p) for p in ports) + ');'
    body = text[core.header_span[1]:core.end_span[0]]
    for direction, name in (('input', 'edt_chain_in'), ('output', 'edt_chain_out')):
        body, count = re.subn(r'\b' + direction + r'\s+\[31:0\]\s+' + name + r'\s*;', '', body)
        if count != 1:
            raise ValueError('expected exactly one internal chain port declaration')
    declarations = '\ninput [3:0] scan_in;\noutput [3:0] scan_out;\ninput scan_pattern_reset;\n'
    return header + declarations + body + '\n' + '\n'.join(wires + statements) + '\nendmodule\n'


def insert(mapped, case, block, view_name, corner, dft):
    if view_name != 'asap7' or not corner or not dft.get('bound_macros'):
        raise ValueError('EDT requires actual ASAP7 macro-bounded corrected element')
    cells = liberty.load_cells([Path(p) for p in corner['liberty']], case / 'dft_cache')
    pre = case / '1_2_yosys.prescan.v'
    shutil.copy2(mapped, pre)
    mod = nl.read_module(mapped, block['top'])
    bb = {n: macro_bound.read_bb_ports(Path(p)) for n, p in dft['bound_macros'].items()}
    text, report = macro_bound.insert_scan_bounded(
        mod, cells, bb, chains=32, max_length=1024,
        clock_mixing='no_mix', tech=view_name,
        scan_in='edt_chain_in', scan_out='edt_chain_out')
    if len(report['chains']) != 32 or report['flops'] != 31606:
        raise ValueError('corrected actual inventory did not restitch into 32 chains/31606 FF')
    work = case / 'edt_codec_map'
    work.mkdir(exist_ok=False)
    result = driver.run_synthesis(driver.VIEWS[view_name], corner,
        dict(top='ot_scan_edt8to1', sources=[CODEC],
             parameters=dict(ENABLE=1, CHAIN_COUNT=32, CHANNELS=4)), work, 0.833, [])
    if result['record']['unmapped_cell_types'] or result['record']['sequential_cell_count'] != 64:
        raise ValueError('codec must map exactly 64 real state FF and no unknown cells')
    codec = nl.read_module(result['netlist'], 'ot_scan_edt8to1')
    text = splice_codec(text, codec)
    mapped.write_text(text)
    shutil.copy2(mapped, case / '1_2_yosys.scan.v')
    length = max(c['length'] for c in report['chains'])
    report['edt'] = dict(chains=32, channels=4, ratio=8,
        source=CODEC, source_sha256=digest(ROOT / CODEC),
        model_sha256=digest(ROOT / MODEL), encoder_sha256=digest(ROOT / ENCODER),
        max_chain_length=length, shifts_per_pattern=length + 1,
        reset_shift_edges=1, response_window='reset shift and next L-1 shifts; final load edge excluded',
        pattern_reset='scan_pattern_reset', codec_mapping=result['record'],
        codec_mapped_sha256=digest(result['netlist']),
        external_scan_in='scan_in', external_scan_out='scan_out',
        control_contract='existing scan_en/test_mode/ICG capture constraints; no codec-only capture edge',
        functional_latency_delta=0, integrated_atpg='UNVALIDATED',
        legacy_independent_ppi_atpg_allowed=False,
        coverage_includes='element, codec state/logic and scan/reset controls; unknown/alias not detected')
    report['prescan_netlist_sha256'] = digest(pre)
    report['scan_netlist_sha256'] = digest(mapped)
    (case / 'scan_chains.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    summary = {k: v for k, v in report.items() if k not in ('chains', 'clock_roots')}
    summary['chain_lengths'] = [c['length'] for c in report['chains']]
    summary['inserted_by'] = 'tools/tapeout_item8_scan_edt.py real32 restitch + mapped codec'
    return summary


def prepare(output):
    argv = frame.prepare(output)
    for key, values in (('--die-area', ['0', '0', '510.84', '126.9']),
                        ('--core-area', ['0', '0.27', '510.84', '126.63']),
                        ('--nickname-tag', ['item8_q_scan_edt32x4_originalframe'])):
        i = argv.index(key)
        argv[i+1:i+1+len(values)] = values
    argv += ['--scan-chains', '32']
    path = Path(output) / 'recipe.json'
    record = json.loads(path.read_text())
    record.update(variant='scan_edt32x4_originalframe', source_change='corrected row-decode + opt-in mapped EDT',
                  route_argv=argv, integrated_atpg='UNVALIDATED',
                  component_pass_reused='main 0c69a8f31 selected r3 PASS32/4; no replay',
                  codec_model=MODEL, codec_model_sha256=digest(ROOT / MODEL),
                  additional_source_pins=[dict(path=p, sha256=digest(ROOT / p)) for p in (CODEC, ENCODER)])
    record['model'].update(new_height_um=126.9, replicated_abstract_area_delta_mm2=0,
                           codec_state_ff_per_element=64, codec_ff_body_floor_per_die_mm2=0.0354212352,
                           added_scan_control_port=1, external_scan_input_bits=4, external_scan_output_bits=4)
    path.write_text(json.dumps(record, indent=2) + '\n')
    return argv


def encode_actual(scanpath, cubepath, output):
    scan = json.loads(Path(scanpath).read_text())
    cube = json.loads(Path(cubepath).read_text())
    edt = scan['edt']
    length = edt['max_chain_length']
    if edt['channels'] != 4 or len(scan['chains']) != 32:
        raise ValueError('actual restitched32/4 scan record required')
    if len(cube['load']) != length or any(len(r) != 32 for r in cube['load']):
        raise ValueError('care cube must bind actual full L x 32 shift extent')
    # Fault streams must be generated after solving with these actual encoded
    # inputs. This hook does not substitute legacy filled-PPI responses.
    result = encode(cube['load'], 4)
    result.update(scan_sha256=digest(scanpath), cube_sha256=digest(cubepath),
                  coverage='UNVALIDATED', reset_shift_word=0,
                  response_protocol=edt['response_window'])
    failed = not result['encodable']
    responses = cube.get('fault_responses', {})
    if responses:
        if cube.get('protocol') != 'reset_shift_plus_L_encoded_capture' or cube.get('encoded_words') != result.get('words'):
            raise ValueError('fault streams require actual encoded-word and full edge-protocol binding')
        streams = [cube['good_response'], *responses.values()]
        if any(len(s) != length or any(len(row) != 32 for row in s) for s in streams):
            raise ValueError('response must include reset-shift and L-1 encoded old-response edges')
        checks = {f: response_check(cube['good_response'], s, 4) for f, s in responses.items()}
        result['fault_response_checks'] = checks
        failed |= any(c['lost_detection'] for c in checks.values())
    Path(output).write_text(json.dumps(result, indent=2) + '\n')
    return int(failed)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--scan', type=Path)
    parser.add_argument('--care-cube', type=Path)
    args = parser.parse_args()
    if args.care_cube:
        if not args.scan:
            parser.error('--care-cube requires --scan')
        return encode_actual(args.scan, args.care_cube, args.output)
    argv = prepare(args.output)
    if args.prepare_only:
        return 0
    os.environ['OT_ORFS_NUM_CORES'] = '16'
    os.environ['MAKEFLAGS'] = '-j16'
    # Scoped integration callback: the unchanged shared driver handles route,
    # constraints, failure preservation and explicit unlimited timeouts.
    previous = driver.apply_scan_insertion
    driver.apply_scan_insertion = insert
    try:
        return driver.main(argv, synth_timeout=None, flow_timeout=None)
    finally:
        driver.apply_scan_insertion = previous


if __name__ == '__main__':
    sys.exit(main())
