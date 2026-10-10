#!/usr/bin/env python3
"""Attribute campaign14's first divergent barrier to the exact compressor store."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

root = Path(sys.argv[1])
output = Path(sys.argv[2])
actual_path = root / 'snapshots/rtl_n0_j1_pc37.hex'
expected_path = root / 'golden_snapshots/gold_n0_j1_pc37.bin'
previous_path = root / 'golden_snapshots/gold_n0_j1_pc0.bin'
actual = np.asarray([int(x, 16) for x in actual_path.read_text().splitlines()
                     if x and not x.startswith('//')], dtype=np.uint32)
expected = np.fromfile(expected_path, dtype='<u4')
previous = np.fromfile(previous_path, dtype='<u4')
manifest = json.loads((root / 'golden_diagnostic_manifest.json').read_text())
instruction = manifest['programs'][1][36]
assert instruction['unit'] == 1 and instruction['me_nout'] == 64 and instruction['me_d_obase'] == 25
base = instruction['me_obase'] * 16
record = dict(
    source_commit='cefb5aa18', repair_commit='aff63db74',
    scope='original reduced campaign14 address-fault diagnosis; no native full-target claim',
    node=0, job=1, position=1, producer_pc=36, first_divergent_barrier_pc=37,
    producer_instruction=instruction,
    expected_dyn25=4, actual_dyn25_from_destination_address=0,
    actual_destination_element=base, expected_destination_element=base + 64,
    all_64_computed_values_bit_match_golden=bool(np.array_equal(actual[base:base + 64], expected[base + 64:base + 128])),
    golden_previous_record_preserved=bool(np.array_equal(expected[base:base + 64], previous[base:base + 64])),
    actual_next_record_still_zero=bool(np.all(actual[base + 64:base + 128] == 0)),
    different_vector_words=int(np.count_nonzero(actual != expected)),
    evidence_files={str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                    for path in (actual_path, expected_path, previous_path,
                                 root / 'src/rtl/hdc/v41x/ot_hdc_core_v41x.sv',
                                 root / 'wf2/obj_stage2_wfc_w1_deep/tb_dsrom_wavefront_array_stage2.sv')},
    root_cause='NSLOT=1 clears DYN25/26 to zero; ring8 programs still consume those entries',
)
record['address_fault_proved'] = bool(record['all_64_computed_values_bit_match_golden']
    and record['golden_previous_record_preserved'] and record['actual_next_record_still_zero']
    and record['different_vector_words'] == 128)
output.write_text(json.dumps(record, indent=2) + '\n')
print(json.dumps(record, indent=2))
raise SystemExit(0 if record['address_fault_proved'] else 1)
