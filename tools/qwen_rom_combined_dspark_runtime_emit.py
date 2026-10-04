#!/usr/bin/env python3
"""Enclosing one-layer host for the opt-in owner VPOS/KVmp/near successor.

Actual program sidecar supplies slot bases; native RTL owns math, row service,
ACK and drain. Compatible generated top/access headers are required. This does
not select a cached single-position model or credit standalone DSpark results.
"""
import argparse
from pathlib import Path
import qwen_rom_combined_nearbaseline_runtime_emit as predecessor

ROOT = Path(__file__).resolve().parents[1]
TOP = 'ot_qwen_rom_combined_dspark_die'


def emit(root=ROOT):
    src = predecessor.emit(root)
    def replace(old, new):
        nonlocal src
        if src.count(old) != 1:
            raise ValueError('DSpark enclosing host anchor: ' + old[:80])
        src = src.replace(old, new)
    replace('#include "combined_driver.hpp"',
            '#include "combined_driver.hpp"\n#include "dspark_slot_binding.hpp"')
    replace('struct DieMem {', 'struct DieMem {\n    std::vector<qwen_combined::NearPositionBases> near_slots;')
    replace('    m.prog = QwenHex::load(p + "/program.hex", 32);',
            '    m.near_slots=qwen_combined::load_near_position_bases(p+"/near_slot_bases.hex");\n    m.prog = QwenHex::load(p + "/program.hex", 32);')
    replace('        die[d]->rm_kv_ideal = 0;',
            '        die[d]->rm_kv_ideal = 0;\n        qwen_combined::initialize_dspark_inputs(*die[d]);')
    # Existing one-layer host has initial preload and an unreachable stage-switch
    # preload. Bind both so widening its stage scope cannot silently lose slots.
    old='preload_die_roms(*die[d], mem[d], pool);'
    if src.count(old)!=2:raise ValueError('actual ROM preload sites changed')
    src=src.replace(old, 'qwen_combined::bind_dspark_decoder_slots(*die[d],mem[d].near_slots,POS,VM_ELEMS);\n        '+old)
    replace('QWEN_ROM_NEARBASELINE PASS stages=%zu',
            'QWEN_DSPARK_NEAR_COMPONENT_DONE stages=%zu')
    return '// Actual opt-in '+TOP+' component host; no full-token/timing qualification.\n'+src


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    with a.out.open('x') as f:f.write(emit())
