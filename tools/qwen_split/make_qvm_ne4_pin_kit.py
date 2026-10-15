#!/usr/bin/env python3
"""Prepare a truthful parent-only QVM boundary repair; CLOSED children stand.

Exact ne3 readonly TT STA: the parent adds output BUFx6f 21.99069ps;
input re adds BUFx2 66.46056ps and 27.53534ps of following wire delay.
Use actual child pin coordinates and omit redundant parent port buffering.
No RTL, child view, SRAM, data edge, IO budget or signoff clock is changed.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
P = ROOT / 'physical/qvm_ne4_boundary_1015'
BASE = '4ad880d2b'
RECORD = '310aff7e859f0771e64ac79e3e598699336ab850'


def blob(commit, path):
    return subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)


def pins(text):
    result = {}
    for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1\n', text, re.M | re.S):
        r = re.search(r'LAYER (\S+) ;\s*RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', m[2])
        if r:
            layer, x0, y0, x1, y1 = r.groups()
            result[m[1]] = dict(layer=layer, x=(float(x0)+float(x1))/2, y=(float(y0)+float(y1))/2)
    return result


def main():
    P.mkdir(parents=True, exist_ok=True)
    spec = json.loads(blob(BASE, 'physical/ref_tile/qvm_bank_entries_my_native/spec.json'))
    floorplan = json.loads(blob(BASE, 'physical/ref_tile/qvm_bank_entries_my_native/floorplan.json'))
    assert floorplan['die'] == [0, 0, 371.52, 224.64]
    data_path = 'physical/ref_tile/qvm_data256_native/views/qvm_data256_native/qvm_data256_native.lef'
    ctrl_path = 'physical/ref_tile/qvm_bank_ctrl_native/views/qvm_bank_ctrl_native/qvm_bank_ctrl_native.lef'
    dp, cp = pins(blob(BASE, data_path).decode()), pins(blob(BASE, ctrl_path).decode())
    parent_path = 'physical/ref_tile/qvm_bank_entries_my_native/views/qvm_bank_banked_native/qvm_bank_banked_native.lef'
    parent = pins(blob(RECORD, parent_path).decode())
    blocks = {b['inst']: b for b in floorplan['blocks']}
    plan = {}

    def from_child(port, inst, local, side):
        b = blocks[inst]
        q = (cp if inst == 'u_ctrl' else dp)[local]
        assert q['layer'] == 'M4' and b['orient'] == 'R0'
        plan[port] = dict(face=side, layer='M4', xy=[.096 if side == 'W' else 371.424, b['y']+q['y']],
                          child=inst, child_pin=local, child_xy=[b['x']+q['x'], b['y']+q['y']])

    for n in ['re', 'we', 'rst_n', 'clk']:
        from_child('ck_ctrl' if n == 'clk' else n, 'u_ctrl', n, 'W')
    for name, width in [('ra', 8), ('wl', 8), ('wm', 16)]:
        for i in range(width):
            from_child(f'{name}[{i}]', 'u_ctrl', f'{name}[{i}]', 'W')
    for half, suffix in enumerate(['lo', 'hi']):
        for i in range(256):
            from_child(f'wd[{256*half+i}]', 'u_in_'+suffix, f'd[{i}]', 'W')
            from_child(f'q[{256*half+i}]', 'u_out_'+suffix, f'q[{i}]', 'E')
        from_child('ck_in_'+suffix, 'u_in_'+suffix, 'clk', 'W')
    for n in ['ck_mem_lo', 'ck_mem_hi', 'ck_cap_lo', 'ck_cap_hi', 'ck_out_lo', 'ck_out_hi']:
        q = parent[n]
        plan[n] = dict(face='S', layer='M5', xy=[q['x'], .096], retained_ne3_clock_x=q['x'])
    coords = [(q['layer'], *q['xy']) for q in plan.values()]
    assert len(coords) == len(set(coords)), 'coincident pins'
    assert len(plan) == 1068, len(plan)
    text = '# Candidate: actual CLOSED child pin numeric identities, same global y.\n'
    for name, q in plan.items():
        text += f"place_pin -pin_name {{{name}}} -layer {q['layer']} -location {{{q['xy'][0]:.6f} {q['xy'][1]:.6f}}}\n"
    (P/'pins.tcl').write_text(text)
    receipt = dict(schema='opentallas.qvm_parent_boundary_candidate.v1', base_source=BASE,
      base_record=RECORD, outline_outer=floorplan['die'], data_cycles_added=0,
      status='candidate: no closure/native claim; final shared exporter reference correction must land before gate',
      parent_buffer_change='DONT_BUFFER_PORTS=1: existing CLOSED registered child ports already form the hardware boundary',
      layout_rule='all actual control/write-data pins share y with their declared CLOSED child pin; q same y as its actual source child pin',
      source_views_sha256={n:hashlib.sha256(blob(BASE, n)).hexdigest() for n in [data_path, ctrl_path]}, pins=plan)
    (P/'pin_plan.json').write_text(json.dumps(receipt, indent=2)+'\n')
    spec['name'] = 'qvm_bank_entries_my_native_ne4'
    spec['io_tcl'] = str(P.relative_to(ROOT)/'pins.tcl')
    spec.pop('pin_ranges', None)
    spec['orfs_vars'] = dict(spec.get('orfs_vars') or {}, DONT_BUFFER_PORTS='1')
    spec['route']['pin_h'] = 'M4'
    spec['job'].update(owner='Codex:Q-COMPUTE-ELEM1417', branch='codex/qwen-compute-elements-1417', tag='ne4', hold_merge=True,
      purpose='Actual parent boundary repair after ne3 native failure; exact closed child views stand',
      views_to='physical/ref_tile/qvm_bank_entries_my_native_ne4/views',
      record_to='results/rtl/ref_tile/qvm_bank_entries_my_native_ne4')
    spec['job']['extra_paths'] += [str(P.relative_to(ROOT)), 'results/arch/qwen_split_1014/tt_functional_partition_1417/qvm_ne3_native_audit.json']
    spec['reroute_reason'] = dict(kind='pin_register',
      source='results/arch/qwen_split_1014/tt_functional_partition_1417/qvm_ne3_native_audit.json',
      cell='qvm_bank_banked_native', launch_ps=298.09891, capture_ps=143.81141,
      fix='Actual existing registered child pins now align with parent face pins; remove redundant parent input/output port buffers measured at66.46/21.99ps in exactreadonlyTTSTA. Existing CLOSED child RTL/views and actual SRAMs stand; no phase/IO-budget waiver.')
    spec['slot_change_request'] = 'Standalone candidate within unchanged outer371.52x224.64 frame; all W/E pins use actual CLOSED child M4 y coordinates, no current die adoption. physical/qvm_ne4_boundary_1015/pin_plan.json'
    spec['structural_change'] = spec['job']['structural_change'] = (
      'ne4 actual parent boundary structural fix: ne3 CLOSED TT138.43/FF23.35/DRC0 but rawpublished nativeL298.099/C143.811; '
      'verified same nested children compose toL228.799/C198.611 and stillFAIL. ExactTTSTA shows redundantouteroutputBUFx6f21.99069ps and reinputBUFx266.46056ps+wire27.53534ps. '
      'DONT_BUFFER_PORTS1 removes redundant parent buffering at already registered CLOSED child interfaces; exact Wre/we/ra/wl/wm/wd and E q bit y positions derive from those child LEFs. '
      'All7closed digital children+2realSRAMs, outline, clockentry names, static schedule and data edges unchanged. '
      'FreshTT/FF/DRC/native220/190/80 and correct nestedclockR/spread delivery required; no automatic publication.')
    (P/'spec.json').write_text(json.dumps(spec, indent=2)+'\n')
    subprocess.run(['python3', 'tools/ref_tile/ref_tile.py', 'gen', str(P/'spec.json')], cwd=ROOT, check=True)
    print('Prepared parent-only QVM native boundary candidate; no route launched')


if __name__ == '__main__':
    main()
