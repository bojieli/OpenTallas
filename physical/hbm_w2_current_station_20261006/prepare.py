#!/usr/bin/env python3
"""Enroll Jason's passing registered CURRENT in a disjoint physical vehicle.

No functional replay or controller change. Inline the already basis-qualified
static W6 equations to avoid the measured procedural-codec frontend explosion.
Keep all state, repair, attributes, widths and finite ACK behavior unchanged.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT / 'physical/hbm_die_abstracts_20261006/links'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    bank = ROOT / 'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_current_pipeline.sv'
    assert sha(bank) == 'dccc3897b2afe75223b8d07fcac3ebeff2277a7ae9233aab7771a641a3025959'
    static = BASE / 'station_physical_20261006/ot_hbm_w2_protected_bank_static.sv'
    assert sha(static) == '95daa28084bd1a644939d083f00f47758c14a25faf70445ce15d99b98475db0e'
    functions = []
    for name in ('encode64', 'raw64', 'check72'):
        matches = re.findall(r'function automatic[^;]*\b' + name + r'\([^;]*;.*?endfunction', static.read_text(), re.S)
        assert len(matches) == 1
        functions.append(matches[0])
    original = bank.read_text()
    imports = ' import ot_gpu_w6_secded_pkg::*;\n import ot_hbm_w2_boundary_pkg::*;'
    assert original.count(imports) == 1
    current = original.replace(imports, '\n'.join(functions))
    assert current.replace('\n'.join(functions), imports) == original
    (HERE / 'bank_current_static.sv').write_text(current)
    # Default-OFF wrappers still need their legacy dependency at elaboration.
    (HERE / 'bank_legacy_static.sv').write_bytes(static.read_bytes())
    source_pins = {str(bank.relative_to(ROOT)): sha(bank), str(static.relative_to(ROOT)): sha(static)}
    for filename, directory in [('ot_hbm_native_station.sv', 'parents'),
                                ('ot_hbm_native_frame_station.sv', 'native_quarter')]:
        src = BASE / directory / filename
        source_pins[str(src.relative_to(ROOT))] = sha(src)
        s = src.read_text()
        if directory == 'parents':
            s = s.replace('parameter integer MODE=0,', 'parameter integer REGISTERED_CURRENT=0,MODE=0,', 1)
        else:
            s = s.replace('parameter integer ENABLE=0,NO=3', 'parameter integer REGISTERED_CURRENT=0,ENABLE=0,NO=3', 1)
            s = s.replace('ot_hbm_native_station #(', 'ot_hbm_native_station #(.REGISTERED_CURRENT(REGISTERED_CURRENT),', 1)
        for name in ('bank', 'cut'):
            s = s.replace(f'ot_hbm_w2_protected_{name} #(',
                          f'ot_hbm_w2_protected_{name}_current_pipeline #(.REGISTERED_CURRENT(REGISTERED_CURRENT),')
        # Enabling the wrappers reaches the exact on modules in PASS19.
        enabled = s.replace('REGISTERED_CURRENT=0,', '')
        enabled = enabled.replace('.REGISTERED_CURRENT(REGISTERED_CURRENT),', '')
        enabled = enabled.replace('_current_pipeline #(', '_current_on #(')
        accepted = ROOT / 'results/rtl/w2_transaction_pipeline_20261005/current_station_r1' / filename
        assert enabled == accepted.read_text(), f'changed enrolled station differs from PASS19: {filename}'
        source_pins[str(accepted.relative_to(ROOT))] = sha(accepted)
        (HERE / filename).write_text(s)
    sources = ['bank_legacy_static.sv', 'bank_current_static.sv', 'ot_hbm_native_station.sv', 'ot_hbm_native_frame_station.sv']
    (HERE / 'sources.json').write_text(json.dumps(dict(
        schema='w2-current-station-physical-v1', source_pins=source_pins,
        generated_pins={p:sha(HERE / p) for p in sources},
        enrolled_source='9a09d4a58 / main b0bd82528',
        top='ot_hbm_native_frame_station', parameters=dict(ENABLE=1,NO=2,REGISTERED_CURRENT=1),
        default_REGISTERED_CURRENT=0, functional_gates_reused=['PASS18 bank','PASS19 native quarter'],
        source_declared_FF_bits=15420, NO3_source_FF_bits=16646, quarter_source_FF_bits=65358,
        full_payload_bits=2063, full_frame_bits=73, full_owner_bits=192,
        macro_count=0, macro_timing='none in this station; no SRAM or macro clock credit borrowed',
        model_binding='physical/hbm_w2_parent_context_20261005/binding.json#station_CURRENT_registered_handoff',
        serial_added_edge_bound=68, nominal_added_ns_bound=56.6666666667,
        existing_changed_gate_parent_release_edge=90,
        source_scope='registered CURRENT equality/held repair/recheck/debt/POR/warm unchanged',
        codec_scope='existing exact static GF2 functions only; all non-import bytes of new bank unchanged',
        clocks='clk_sm833.333333ps plus four real kept forwarding inversions',
        SS_setup_uncertainty_ps=60, FF_hold_uncertainty_ps=25,
        target_buffered_utilization_percent=[55,60], initial_core_utilization_percent=38,
        sizing_basis='old NO2 postCTS13751um2 / mapped9393.35454um2 =1.46497 buffering multiplier; 38% initial targets55.63% actual; measured result decides fit',
        physical_qualified=False), indent=2)+'\n')


if __name__ == '__main__':
    main()
