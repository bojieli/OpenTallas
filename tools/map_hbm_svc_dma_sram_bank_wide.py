#!/usr/bin/env python3
"""Map the complete two-macro bank to source-pinned ASAP7 RVT SS cells.

This is mapped cell area, not a placement/timing closure claim. Memory area
comes from its actual aligned LEF; all synchronous/asynchronous control and
data flops remain in the full-shape mapped netlist.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
MACRO = 'ot_sram_1r1w_256x256_m2_r2c2'
BASE = 'physical/asap7_memory_macros_v2/' + MACRO + '/' + MACRO

def blocks(lib):
    for m in re.finditer(r'\bcell\s*\(\s*(\S+?)\s*\)\s*\{', lib):
        level = 1
        end = m.end()
        while level:
            level += (lib[end] == '{') - (lib[end] == '}')
            end += 1
        yield m.group(1).strip('"'), lib[m.start():end]

def run(libdir):
    libs = sorted(libdir.glob('*asap7*RVT_SS*.lib'))
    assert len(libs) == 5, 'require all five ASAP7 RVT SS cell categories'
    cells = {}
    text0 = libs[0].read_text()
    header = text0[:re.search(r'\bcell\s*\(', text0).start()]
    for p in libs:
        cells.update(blocks(p.read_text()))
    areas = {name: float(re.search(r'\barea\s*:\s*([\d.]+)', body).group(1))
             for name, body in cells.items()}
    with tempfile.TemporaryDirectory(prefix='hbm-wide-map-') as scratch:
        merged = Path(scratch) / 'merged.lib'
        merged.write_text(header+'\n'.join(cells.values())+'\n}\n')
        netlist = Path(scratch) / 'mapped.json'
        script = ('read_verilog -sv -Irtl/common rtl/common/ot_secded.sv '
                  'rtl/hbm/hbm_svc_dma_sram_bank_wide.sv; '
                  f'read_verilog -lib {BASE}_bb.v; '
                  'hierarchy -check -top hbm_svc_dma_sram_bank_wide; '
                  'synth -top hbm_svc_dma_sram_bank_wide -flatten; '
                  f'dfflibmap -liberty {merged}; abc -liberty {merged}; clean; '
                  f'stat -liberty {merged}; write_json {netlist}')
        proc = subprocess.run(['yosys','-Q','-T','-p',script], cwd=ROOT,
                              capture_output=True, text=True)
        if proc.returncode:
            raise RuntimeError(proc.stdout[-4000:]+proc.stderr)
        mod = json.loads(netlist.read_text())['modules']['hbm_svc_dma_sram_bank_wide']
        count = Counter(c['type'] for c in mod['cells'].values())
    unmapped = {k:v for k,v in count.items() if k not in areas and k != MACRO}
    area = sum(n*areas[k] for k,n in count.items() if k in areas)
    geo = json.loads((ROOT/(BASE+'.json')).read_text())['alignment_v2']['v2']
    evidence = {
        'verdict': 'PASS_mapped_shape' if not unmapped and count[MACRO] == 2 else 'FAIL_unmapped_cells',
        'mapped_cell_counts': dict(count), 'unmapped_cells': unmapped,
        'mapped_logic_area_um2_per_bank': area,
        'actual_macro_area_um2_per_bank': 2*geo['area_um2'],
        'total_area_um2_per_bank': area+2*geo['area_um2'],
        'per_pc_total_area_um2': 4*(area+2*geo['area_um2']),
        'per_pc_slot_um': [265,480],
        'per_pc_slot_utilization': 4*(area+2*geo['area_um2'])/(265*480),
        'macro_stack_height_um': 8*geo['height_um']+7*8.5,
        'scope': 'full 256groups, actual2macro bank, RVT SS mapped area; no timing/route claim',
        'liberty_source_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in libs},
        'RTL_source_sha256': {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                             ['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh',
                              'rtl/hbm/hbm_svc_dma_sram_bank_wide.sv',BASE+'_bb.v',BASE+'.json']},
    }
    return evidence

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--lib-dir', required=True,type=Path)
    parser.add_argument('--output', required=True,type=Path)
    args=parser.parse_args()
    evidence=run(args.lib_dir)
    with args.output.open('x') as f:
        json.dump(evidence,f,indent=2); f.write('\n')
    print(json.dumps(evidence,indent=2))
    raise SystemExit(0 if evidence['verdict']=='PASS_mapped_shape' else 1)
