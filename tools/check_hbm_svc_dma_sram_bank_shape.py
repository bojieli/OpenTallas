#!/usr/bin/env python3
"""Minimum full-shape synthesis and real macro pin geometry evidence.

Generic gates do not establish mapped area or physical closure. This gate
ensures one real memory, no inferred SRAM flop array, and finite LEF pin fit.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import argparse

ROOT = Path(__file__).resolve().parents[1]
MACRO = 'ot_sram_1r1w_128x256_m1_r2c2'
BASE = 'physical/asap7_memory_macros_v2/' + MACRO + '/' + MACRO
SOURCES = ['rtl/common/ot_secded.sv', 'rtl/common/ot_secded_cols.svh',
           'rtl/hbm/hbm_svc_dma_sram_bank.sv', BASE + '_bb.v', BASE + '.lef']


def check():
    with tempfile.TemporaryDirectory(prefix='hbm-bank-shape-') as scratch:
        netlist = Path(scratch) / 'bank.json'
        script = ('read_verilog -sv -Irtl/common rtl/common/ot_secded.sv '
                  'rtl/hbm/hbm_svc_dma_sram_bank.sv; '
                  f'read_verilog -lib {BASE}_bb.v; '
                  'hierarchy -check -top hbm_svc_dma_sram_bank; '
                  'synth -top hbm_svc_dma_sram_bank -flatten; stat; '
                  f'write_json {netlist}')
        result = subprocess.run(['yosys', '-Q', '-T', '-p', script],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        mod = json.loads(netlist.read_text())['modules']['hbm_svc_dma_sram_bank']
        cells = Counter(c['type'] for c in mod['cells'].values())
    lef = (ROOT / (BASE + '.lef')).read_text()
    width, height = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', lef).groups())
    pins = []
    for match in re.finditer(r'  PIN (\S+)\n(.*?)  END \1\n', lef, re.S):
        name, body = match.groups()
        if 'USE POWER' in body or 'USE GROUND' in body:
            continue
        for layer, x1, y1, x2, y2 in re.findall(
                r'LAYER (\S+) ;\s+RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)', body):
            rect = list(map(float, [x1,y1,x2,y2]))
            assert 0 <= rect[0] < rect[2] <= width
            assert 0 <= rect[1] < rect[3] <= height
            pins.append((name,layer,rect))
    overlaps = []
    for i, (name, layer, a) in enumerate(pins):
        for other, other_layer, b in pins[i+1:]:
            if layer == other_layer and max(a[0],b[0]) < min(a[2],b[2]) and max(a[1],b[1]) < min(a[3],b[3]):
                overlaps.append([name,other])
    assert cells[MACRO] == 1
    assert not any('latch' in kind.lower() or 'mem' in kind.lower() for kind in cells if kind != MACRO)
    assert not mod.get('memories')
    assert pins and not overlaps
    return {'verdict': 'PASS_shape_only', 'macro_count': cells[MACRO],
            'generic_cells': dict(cells), 'generic_total_cells': sum(cells.values()),
            'data_and_control_flipflops': sum(n for k,n in cells.items() if 'DFF' in k),
            'inferred_memories': 0, 'latches': 0,
            'yosys_check_zero_problems': 'found and reported 0 problems' in result.stdout,
            'macro_LEF': {'size_um': [width,height], 'signal_clock_repair_pin_rectangles': len(pins),
                          'all_rectangles_in_macro': True, 'same_layer_overlaps': overlaps},
            'area_scope': 'generic gate inventory; mapped area not established',
            'physical_scope': 'LEF rectangle fit only; routed pin accessibility/timing not established',
            'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    evidence = check()
    with args.output.open('x') as f:
        json.dump(evidence, f, indent=2)
        f.write('\n')
    print(json.dumps(evidence, indent=2))
