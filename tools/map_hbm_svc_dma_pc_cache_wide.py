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
MACRO = 'hbm_svc_dma_sram_bank_wide'
BASE = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2'

def blocks(lib):
    for m in re.finditer(r'\bcell\s*\(\s*(\S+?)\s*\)\s*\{', lib):
        level = 1
        end = m.end()
        while level:
            level += (lib[end] == '{') - (lib[end] == '}')
            end += 1
        yield m.group(1).strip('"'), lib[m.start():end]

def liberty_pin_directions(body):
    directions = {}
    for match in re.finditer(r'\bpin\s*\(\s*(\S+?)\s*\)\s*\{', body):
        level=1
        end=match.end()
        while level:
            level+=(body[end]=='{')-(body[end]=='}')
            end+=1
        direction=re.search(r'\bdirection\s*:\s*(input|output)',body[match.end():end])
        if direction:
            directions[match.group(1).strip('"')]=direction.group(1)
    return directions

def metadata_pair_inventory(mod, library_directions):
    drivers = {}
    for name, cell in mod['cells'].items():
        directions=cell.get('port_directions',library_directions.get(cell['type'],{}))
        for port, direction in directions.items():
            if direction == 'output':
                for bit in cell['connections'][port]:
                    drivers[bit] = (name, cell)
    def ff_driver(bit):
        visited = set()
        while bit not in visited:
            visited.add(bit)
            if bit not in drivers:
                return None
            name, cell = drivers[bit]
            if cell['type'].startswith('DFF'):
                return name
            if not cell['type'].startswith(('INV','BUF')):
                return None
            directions=cell.get('port_directions',library_directions.get(cell['type'],{}))
            inputs = [b for p, d in directions.items() if d == 'input'
                      for b in cell['connections'][p]]
            if len(inputs) != 1:
                return None
            bit = inputs[0]
        return None
    sets = {'meta': set(), 'meta_inv': set()}
    bits = {'meta': 0, 'meta_inv': 0}
    unresolved = []
    for name, wire in mod['netnames'].items():
        match = re.fullmatch(r'(meta|meta_inv)\[(\d+)\]', name)
        if not match:
            continue
        side = match.group(1)
        for bit in wire['bits']:
            bits[side] += 1
            driver = ff_driver(bit)
            if driver is None:
                unresolved.append([name, bit])
            else:
                sets[side].add(driver)
    shared = sets['meta'] & sets['meta_inv']
    return {'verdict': 'PASS_distinct_physical_pairs' if bits == {'meta':3072,'meta_inv':3072}
            and len(sets['meta'])==3072 and len(sets['meta_inv'])==3072 and not shared and not unresolved
            else 'FAIL_pair_inventory',
            'RTL_named_bits':bits,'primary_distinct_FF_cells':len(sets['meta']),
            'complement_distinct_FF_cells':len(sets['meta_inv']),
            'total_distinct_metadata_FF_cells':len(sets['meta']|sets['meta_inv']),
            'shared_FF_count':len(shared),'unresolved_bits':unresolved,
            'method':'trace every named meta[group]/meta_inv[group] bit through optional INV/BUF to physical mapped DFF output; require unique3072+3072 disjoint drivers',
            'mapped_driver_name_sha256':hashlib.sha256('\n'.join(sorted(sets['meta']|sets['meta_inv'])).encode()).hexdigest()}

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
    library_directions={name:liberty_pin_directions(body) for name,body in cells.items()}
    with tempfile.TemporaryDirectory(prefix='hbm-wide-map-') as scratch:
        merged = Path(scratch) / 'merged.lib'
        merged.write_text(header+'\n'.join(cells.values())+'\n}\n')
        netlist = Path(scratch) / 'mapped.json'
        bankstub = Path(scratch) / 'bank_stub.sv'
        banktext=(ROOT/'rtl/hbm/hbm_svc_dma_sram_bank_wide.sv').read_text()
        bankstub.write_text(banktext[:banktext.index('  reg [255:0] valid_map;')]+'endmodule\n')
        script = ('read_verilog -sv -Irtl/common rtl/common/ot_secded.sv '
                  'rtl/hbm/ot_hbm_svc_dma_pc_cache_wide.sv; '
                  f'read_verilog -sv -lib {bankstub}; '
                  'chparam -set ENABLE 1 ot_hbm_svc_dma_pc_cache_wide; '
                  'hierarchy -check -top ot_hbm_svc_dma_pc_cache_wide; '
                  'synth -top ot_hbm_svc_dma_pc_cache_wide -flatten; '
                  f'dfflibmap -liberty {merged}; abc -liberty {merged}; clean; '
                  f'stat -liberty {merged}; write_json {netlist}')
        proc = subprocess.run(['yosys','-Q','-T','-p',script], cwd=ROOT,
                              capture_output=True, text=True)
        if proc.returncode:
            raise RuntimeError(proc.stdout[-4000:]+proc.stderr)
        mod = json.loads(netlist.read_text())['modules']['ot_hbm_svc_dma_pc_cache_wide']
        count = Counter(c['type'] for c in mod['cells'].values())
        pairs = metadata_pair_inventory(mod,library_directions)
    unmapped = {k:v for k,v in count.items() if k not in areas and k != MACRO}
    area = sum(n*areas[k] for k,n in count.items() if k in areas)
    geo = json.loads((ROOT/(BASE+'.json')).read_text())['alignment_v2']['v2']
    evidence = {
        'verdict': 'PASS_mapped_shape' if not unmapped and count[MACRO] == 4 and pairs['verdict']=='PASS_distinct_physical_pairs' else 'FAIL_mapped_shape',
        'metadata_physical_pairs': pairs,
        'mapped_cell_counts': dict(count), 'unmapped_cells': unmapped,
        'mapped_controller_area_um2_per_PC': area,
        'hard_bank_logic_area_um2_per_PC': 4*1563.29676,
        'eight_real_macro_area_um2_per_PC': 8*geo['area_um2'],
        'controller_reservation_um2':2000,
        'reservation_verdict':'PASS' if area<=2000 else 'FAIL_budget_exceeded',
        'total_PC_area_um2': area+4*1563.29676+8*geo['area_um2'],
        'native_CAM_area':'not included; separately owned and must be added',
        'per_pc_slot_um': [265,480],
        'per_pc_slot_utilization': (area+4*1563.29676+8*geo['area_um2'])/(265*480),
        'macro_stack_height_um': 8*geo['height_um']+7*8.5,
        'scope': 'full PC controller mapped against4hardened bank abstracts; inherited8realmacro area; RVT SS; no timing/route claim',
        'liberty_source_sha256': {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in libs},
        'RTL_source_sha256': {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                             ['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh',
                              'rtl/hbm/hbm_svc_dma_sram_bank_wide.sv','rtl/hbm/ot_hbm_svc_dma_pc_cache_wide.sv',BASE+'_bb.v',BASE+'.json']},
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
