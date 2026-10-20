#!/usr/bin/env python3
"""Generate native narrow dual-clock banks; never alter the wide masters.

These remain the project's calibrated analytical SRAM abstracts. They do not
provide internal transistor layout or macro-SPICE qualification.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/mem_compiler'))
import sram_gen as S
from build_aligned_v2 import patched, aligned_outline, aligned_write_lef


def main():
    out = ROOT / 'physical/asap7_memory_macros_v2'
    records = []
    # Depths8/16 would retain6.91/6.49 native contacts/um. Use a real
    # 32-row array, with client address zero-extension, rather than stretching
    # a LEF or pretending that unconnected mask contacts have disappeared.
    for words in (32, 128, 256):
        name = f'ot_sram_1r1w2c_{words}x64_m1'
        spec = S.SramSpec(name, words, 64, 1, 1, '1r1w2c')
        with patched(S, macro_outline=aligned_outline, write_lef=aligned_write_lef):
            sheet = S.compile_macro(spec, out)
        a = sheet['area']
        contacts = sum(p.width for p in S.pins_for(spec))
        counts = [math.ceil(contacts / 2), contacts // 2]
        densities = [n / a['macro_height_um'] for n in counts]
        assert max(densities) <= 6, (name, densities)
        record = {'master': name, 'words': words, 'bits': 64,
                  'width_um': a['macro_width_um'], 'height_um': a['macro_height_um'],
                  'area_um2': a['macro_area_um2'], 'contacts_we': counts,
                  'contacts_per_um_we': densities,
                  'clock_pins': ['rclk', 'wclk'], 'read_edges': 1,
                  'same_address_simultaneous_read_write': 'forbidden by client schedule',
                  'internal_layout_qualified': False, 'external_escape_qualified': False}
        records.append(record)
    price = []
    for words in (8, 16, 32, 128, 256):
        record = next(r for r in records if r['words'] == max(32, words))
        for width in (128, 256, 285, 512, 546):
            banks = math.ceil(width / 64)
            price.append({'logical_words': words, 'physical_words': record['words'], 'logical_bits': width, 'banks': banks,
                          'physical_bits_per_word': banks * 64,
                          'unused_bits_per_word': banks * 64 - width,
                          'raw_macro_area_um2': banks * record['area_um2'],
                          'clock_and_control_loads': banks, 'added_read_edges': 0,
                          'clock_reach_escape_and_floorplan_area': 'not yet qualified'})
    files = [Path(__file__), ROOT/'tools/mem_compiler/sram_gen.py',
             ROOT/'tools/mem_compiler/views.py', ROOT/'tools/mem_compiler/build_aligned_v2.py',
             ROOT/'tools/mem_compiler/asap7_calibration.json']
    result = {'schema': 'opentallas.sram-banked-2c.1019', 'masters': records,
              'logical_prices': price,
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files},
              'scope': 'native project-model contracts; external PG/via/DRC and client integration remain open'}
    dst = ROOT/'results/arch/sram_pin_access_1019/model.json'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(result, indent=2) + '\n')
    print('BANKED_2C_MODEL PASS masters=3 native_face_density<=6 no_extra_read_edge')


if __name__ == '__main__':
    main()
