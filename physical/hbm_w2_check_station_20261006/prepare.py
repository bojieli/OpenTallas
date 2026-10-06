"""Enroll the released CHECK cut; no controller edits or functional replay."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
BASE = ROOT/'physical/hbm_die_abstracts_20261006/links'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    gate = ROOT/'results/rtl/w2_transaction_pipeline_20261005/check_station_r2/terminal.json'
    accepted = json.loads(gate.read_text())
    assert accepted['passed'] and accepted['checker_checks'] == 36 and accepted['parent_checks'] == 19
    bank = ROOT/'rtl/hbm_accel/integrated_20261005/w2_parent/ot_hbm_w2_protected_bank_check_pipeline.sv'
    assert sha(bank) == '75b147f18c0cb93980c9436469c548118fce889cab551957ec7a7d8613efda82'
    assert accepted['source_pins'][str(bank.relative_to(ROOT))] == sha(bank)
    static = HERE/'bank_legacy_static.sv'
    assert sha(static) == '95daa28084bd1a644939d083f00f47758c14a25faf70445ce15d99b98475db0e'
    functions = []
    for name in ('encode64', 'raw64', 'check72'):
        matches = re.findall(r'function automatic[^;]*\b'+name+r'\([^;]*;.*?endfunction', static.read_text(), re.S)
        assert len(matches) == 1
        functions.append(matches[0])
    imports = ' import ot_gpu_w6_secded_pkg::*;\n import ot_hbm_w2_boundary_pkg::*;'
    original = bank.read_text()
    assert original.count(imports) == 1
    expanded = original.replace(imports, '\n'.join(functions))
    assert expanded.replace('\n'.join(functions), imports) == original
    (HERE/'bank_check_static.sv').write_text(expanded)
    pins = {str(bank.relative_to(ROOT)): sha(bank), str(gate.relative_to(ROOT)): sha(gate)}
    for filename, directory in [('ot_hbm_native_station.sv','parents'),
                                ('ot_hbm_native_frame_station.sv','native_quarter')]:
        src = BASE/directory/filename
        pins[str(src.relative_to(ROOT))] = sha(src)
        assert accepted['source_pins'][str(src.relative_to(ROOT))] == sha(src)
        s = src.read_text()
        if directory == 'parents':
            s = s.replace('parameter integer MODE=0,', 'parameter integer REGISTERED_CURRENT=0,REGISTERED_CHECK=0,MODE=0,', 1)
        else:
            s = s.replace('parameter integer ENABLE=0,NO=3', 'parameter integer REGISTERED_CURRENT=0,REGISTERED_CHECK=0,ENABLE=0,NO=3', 1)
            s = s.replace('ot_hbm_native_station #(', 'ot_hbm_native_station #(.REGISTERED_CURRENT(REGISTERED_CURRENT),.REGISTERED_CHECK(REGISTERED_CHECK),', 1)
        for name in ('bank','cut'):
            s = s.replace(f'ot_hbm_w2_protected_{name} #(',
                          f'ot_hbm_w2_protected_{name}_check_pipeline #(.REGISTERED_CURRENT(REGISTERED_CURRENT),.REGISTERED_CHECK(REGISTERED_CHECK),')
        enabled = s.replace('REGISTERED_CURRENT=0,REGISTERED_CHECK=0,','')
        enabled = enabled.replace('.REGISTERED_CURRENT(REGISTERED_CURRENT),.REGISTERED_CHECK(REGISTERED_CHECK),','')
        enabled = enabled.replace('_check_pipeline #(', '_check_on #(')
        gold = gate.parent/filename
        assert enabled == gold.read_text(), filename+' does not match released PASS19 source'
        assert accepted['generated_source_pins'][str(gold.relative_to(ROOT))] == sha(gold)
        pins[str(gold.relative_to(ROOT))] = sha(gold)
        (HERE/filename).write_text(s)
    binding_path = ROOT/'physical/hbm_w2_parent_context_20261005/binding.json'
    binding = json.loads(binding_path.read_text())['station_CHECK_registered_handoff']
    assert binding['NO2_source_FF_bits'] == 30396 and binding['NO3_source_FF_bits'] == 32774
    sources = ['bank_legacy_static.sv','bank_current_static.sv','bank_check_static.sv',
               'ot_hbm_native_station.sv','ot_hbm_native_frame_station.sv']
    model_path = ROOT/'tools/uarch_model.py'
    (HERE/'sources.json').write_text(json.dumps(dict(
        schema='w2-check-station-physical-v1', source_pins=pins,
        generated_pins={p:sha(HERE/p) for p in sources},
        enrolled_source='10ce / main19cf9da3c', top='ot_hbm_native_frame_station',
        parameters=dict(ENABLE=1,NO=2,REGISTERED_CURRENT=1,REGISTERED_CHECK=1),
        defaults=dict(REGISTERED_CURRENT=0,REGISTERED_CHECK=0),
        functional_gates_reused=['PASS36 checker','PASS19 native quarter'],
        source_declared_FF_bits=30396, NO3_source_FF_bits=32774, quarter_source_FF_bits=128718,
        full_payload_bits=2063,full_frame_bits=73,full_owner_bits=192,
        macro_count=0,macro_timing='No memory macros in station; no parent macro/clock credit borrowed',
        binding=binding, binding_sha256=sha(binding_path),
        unified_model_sha256=sha(model_path), model_term='station_CHECK_pipeline_successor',
        serial_incremental_edge_upper=68, incremental_latency_upper_ns=68/1.2,
        actual_mapped_clock_caps_required=True, actual_mapped_area_required=True,
        inherited_core_area_um2=36469.79964,
        core_bbox_um=[2.052,2.16,384.696,97.47],die_bbox_um=[0,0,386.709,99.677],
        target_buffered_utilization_percent=[55,60],
        fit_not_claimed_from_preoptimisation_FF_count=True,
        codec_scope='Exact existing static W6 equations; every non-import CHECK source byte unchanged; CURRENT and legacy dependencies unchanged',
        clocks='clk_sm833.333333ps and four kept real forwarding inversions',
        SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,
        memory_admission_GiB=16,
        admission_basis='R2 actual ORFS peak3.199GB and R1 Yosys peak517.63MB; 30396/15420 FF growth<2x; unchanged16GiB reservation covers measured growth with headroom, no process cap',
        physical_qualified=False,installed_parent_qualified=False),indent=2)+'\n')


if __name__ == '__main__':
    main()
