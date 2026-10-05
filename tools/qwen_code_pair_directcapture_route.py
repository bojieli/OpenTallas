#!/usr/bin/env python3
"""Physical-only ORFS launcher; reuse exact mapped objects, no ABC or RTL edits.

Interface: --source-dir frozen_source --mapped-dir retained_mapping --slot-dir
frozen_Kant_slot --work fresh_output --nickname unique_variant. Slot substitution
is the reverse-placement variant; mapped substitution is Erdos's source variant.
"""
import argparse
from collections import defaultdict
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for flag in ('source-dir', 'mapped-dir', 'slot-dir', 'work'):
        ap.add_argument('--' + flag, type=Path, required=True)
    ap.add_argument('--nickname', required=True)
    ap.add_argument('--image', default='openroad/orfs:asap7lock')
    a = ap.parse_args()
    src, mapped, slot, work = [p.resolve() for p in (a.source_dir, a.mapped_dir, a.slot_dir, a.work)]
    work.mkdir(parents=True, exist_ok=False)
    for f in ('mapped.v', 'mapped.json'):
        shutil.copy2(mapped / f, work / f)
    shutil.copytree(slot, work / 'slot')
    # Yosys JSON does not contain mapped-library port directions, and its
    # anonymous names differ from write_verilog. Use the actual physical names
    # and scalar/concatenation wiring in the retained Verilog itself.
    v = (mapped / 'mapped.v').read_text()
    def signal(s):
        return s.strip().lstrip('\\')
    cells = {}
    for match in re.finditer(r'^\s{2}(\w+)\s+(\S+)\s*\((.*?)^\s{2}\);', v, re.M | re.S):
        kind, name, body = match.groups()
        connections = {}
        for pin, expr in re.findall(r'\.(\w+)\((.*?)\)', body, re.S):
            expr = expr.strip()
            connections[pin] = ([signal(x) for x in expr[1:-1].split(',')][::-1]
                                if expr.startswith('{') else [signal(expr)])
        outputs = {'rd_out'} if kind.startswith('ot_sram_') else {'QN'} if kind.startswith('DFF') else {'Y'}
        cells[name.lstrip('\\')] = dict(type=kind, connections=connections,
            port_directions={p: 'output' if p in outputs else 'input' for p in connections})
    for i, (dest, origin) in enumerate(re.findall(r'^\s*assign\s+(\S+)\s*=\s*(.*?);', v, re.M)):
        cells[f'alias{i}'] = dict(type='alias', connections={'Y': [signal(dest)], 'A': [signal(origin)]},
                                 port_directions={'Y': 'output', 'A': 'input'})
    drivers = {}
    for name, cell in cells.items():
        for pin, bits in cell['connections'].items():
            if cell['port_directions'][pin] == 'output':
                for i, bit in enumerate(bits):
                    drivers[bit] = (name, pin, i)

    @lru_cache(None)
    def leaves(bit):
        if bit not in drivers:
            return frozenset()
        name, pin, index = drivers[bit]
        cell = cells[name]
        if cell['type'].startswith('ot_sram_'):
            return frozenset([(name, index)]) if pin == 'rd_out' else frozenset()
        if cell['type'].startswith('DFF'):
            return frozenset()
        return frozenset(x for p, bits in cell['connections'].items()
                         if cell['port_directions'][p] == 'input' for b in bits for x in leaves(b))

    groups = defaultdict(list)
    bindings = []
    # Direct-capture source: bind all 256 data plus all 256 sidecar-word
    # bits by actual mapped D fanin, never generated cell name/order.
    placements = {}
    macro_tcl = (slot / 'macros.tcl').read_text()
    for macro, master, x, y, orient in re.findall(
        r'place_macro -macro_name \[ot_code_pair_instance \{([^}]+)\} (\w+)\] -location \{([\d.]+) ([\d.]+)\} -orientation (\w+)', macro_tcl):
        placements[macro] = (master, float(x), float(y), orient)
    @lru_cache(None)
    def pin_xy(macro, bit):
        master, x, y, orient = placements[macro]
        lef = (src / 'physical/asap7_memory_macros' / master / (master+'.lef')).read_text()
        width, height = map(float, re.search(r'SIZE ([\d.]+) BY ([\d.]+)', lef).groups())
        pin = 'rd_out['+str(bit)+']'
        block = re.search(r'\bPIN '+re.escape(pin)+r'\s+(.*?)\bEND '+re.escape(pin)+r'(?=\s)', lef, re.S)
        if not block:
            raise RuntimeError('missing actual LEF output pin '+pin)
        rect = list(map(float,re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',block[1]).groups()))
        px,py=(rect[0]+rect[2])/2,(rect[1]+rect[3])/2
        if orient=='MY': px=width-px
        elif orient!='R0': raise RuntimeError('unbound macro orientation '+orient)
        return [x+px,y+py]
    for name, cell in cells.items():
        if not cell['type'].startswith('DFF'):
            continue
        macro_bits = leaves(cell['connections']['D'][0])
        if not macro_bits:
            continue  # protected controller/metadata FF, not macro capture
        macros = {n for n, i in macro_bits}
        if len(macros)!=1 or len(macro_bits)!=1:
            raise RuntimeError('direct capture D is not one physical macro bit: '+name)
        macro,index=next(iter(macro_bits))
        match=re.search(r'column\[(\d+)\].bank\[(\d+)\]',macro)
        if not match or not 0<=index<256:
            raise RuntimeError('unbound capture source '+macro)
        column,bank=map(int,match.groups())
        kind='data' if macro.endswith('data_store') else 'fullcheck' if macro.endswith('check_store') else None
        if kind is None: raise RuntimeError('unexpected macro capture '+macro)
        key=f'{column},{bank}'
        groups[key].append(name)
        xy=pin_xy(macro,index)
        # Target is an explicit model preference within the unchanged fence,
        # not a claim that the router has already placed this D pin there.
        x0,y0=185.544+column*473.472,8.64+bank*96.66
        target=[min(max(xy[0],x0+.54),x0+17.28-.54),min(max(xy[1],y0+.54),y0+51.84-.54)]
        bindings.append(dict(column=column,bank=bank,word_kind=kind,macro_bit=index,
            synthesized_cell=name,macro=macro,source_pin=f'rd_out[{index}]',
            source_pin_xy_um=xy,preferred_capture_D_xy_um=target,
            placement_measured=False))
    if len(bindings)!=5120 or any(len(groups[f'{p},{b}'])!=512 for p in range(2) for b in range(5)):
        raise RuntimeError('actual direct capture differs from ten512 FF groups')
    if len({(r['column'],r['bank'],r['word_kind'],r['macro_bit']) for r in bindings})!=5120:
        raise RuntimeError('direct capture binding is not one-to-one')
    (work / 'capture_bindings.json').write_text(json.dumps(bindings, indent=2) + '\n')
    # Same supported OpenDB API correction as Pauli d61f0f796. Preserve
    # supplier slot history; only the working hook's API spelling changes.
    hook = (slot / 'local_capture_regions.tcl').read_text()
    hook = hook.replace('$group setRegion $region', '$region addGroup $group')
    (work / 'local_capture_regions.tcl').write_text(hook)
    region = ['source /work/local_capture_regions.tcl', 'set members [dict create]']
    for key, members in sorted(groups.items()):
        region.append('dict set members {' + key + '} {' + ' '.join(members) + '}')
    region += ['ot_code_pair_capture_regions $members']
    (work / 'regions.tcl').write_text('\n'.join(region) + '\n')
    (work / 'constraint.sdc').write_text('''# Native ASAP7 ps/fF; exact Kant isolated boundary, no relaxation.
create_clock -name core -period 833.333333 [get_ports clk]
set_clock_uncertainty -setup 60 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
set code_inputs {}
foreach p [all_inputs] {if {[get_full_name $p] ni {clk por_n}} {lappend code_inputs $p}}
set_input_delay -clock core -max 120 $code_inputs
set_input_delay -clock core -min 0 $code_inputs
set_driving_cell -lib_cell BUFx2_ASAP7_75t_R -pin Y $code_inputs
set_output_delay -clock core -max 120 [all_outputs]
set_output_delay -clock core -min 0 [all_outputs]
set_load 0.558822 [all_outputs]
set_false_path -from [get_ports por_n]
''')
    macros = ['ot_sram_1r1w_1024x256_m2_r2c2', 'ot_sram_1r1w_128x256_m1_r2c2']
    bases = [f'/src/physical/asap7_memory_macros/{m}/{m}' for m in macros]
    config = ['export DESIGN_NAME = ot_qwen_hbm_code_pair_context',
              f'export DESIGN_NICKNAME = {a.nickname}', 'export PLATFORM = asap7',
              'export SYNTH_NETLIST_FILES = /work/mapped.v', 'export VERILOG_FILES = /work/mapped.v',
              'export SDC_FILE = /work/constraint.sdc', 'export CORNER = WC', 'export CORNERS = WC BC',
              'export WC_LIB_FILES = $(WC_NLDM_LIB_FILES) ' + ' '.join(b + '_ss.lib' for b in bases),
              'export BC_LIB_FILES = $(BC_NLDM_LIB_FILES) ' + ' '.join(b + '_ff.lib' for b in bases),
              'export ADDITIONAL_LIBS = ' + ' '.join(b + '_ss.lib' for b in bases),
              'export ADDITIONAL_LEFS = ' + ' '.join(b + '.lef' for b in bases),
              'export GDS_ALLOW_EMPTY = ' + ' '.join(macros),
              'export DIE_AREA = 0 0 864 673.92', 'export CORE_AREA = 8.64 8.64 855.36 665.28',
              'export PLACE_DENSITY = 0.55', 'export MACRO_PLACE_HALO = 2.16 2.16',
              'export MACRO_ROWS_HALO_X = 2.16', 'export MACRO_ROWS_HALO_Y = 2.16',
              'export MACRO_PLACEMENT_TCL = /work/slot/macros.tcl',
              'export FOOTPRINT_TCL = /work/slot/pins.tcl',
              'export POST_FLOORPLAN_TCL = /work/regions.tcl',
              'export MIN_ROUTING_LAYER = M2', 'export MAX_ROUTING_LAYER = M9',
              'export MIN_CLK_ROUTING_LAYER = M4', 'export MAX_CLK_ROUTING_LAYER = M9',
              'export HOLD_SLACK_MARGIN = 0', 'export SETUP_SLACK_MARGIN = 0',
              'export TNS_END_PERCENT = 100', 'export LEC_CHECK = 0',
              'export NUM_CORES = 16', 'export SKIP_REPORT_METRICS = 0']
    (work / 'config.mk').write_text('\n'.join(config) + '\n')
    # Require the SDC actually emitted by its ODB producer; do not invent
    # a checkpoint or constraint file when this pinned Makefile misses it.
    (work / 'side_effects.mk').write_text('$(RESULTS_DIR)/%.sdc: $(RESULTS_DIR)/%.odb\n\t@test -f $@\n')
    manifest = dict(engine_source_main='1a89e001adf794f6e3674230b6c189114913e79e',
                    scope='Owner-authorized diagnostic route despite retained predicted timing miss',
                    mapped_netlist_sha256=hashlib.sha256(v.encode()).hexdigest(),
                    image=a.image, source=str(src), slot=str(slot), cores=16,
                    route_variant=a.nickname, constraints='833.333333ps SS60 FF25, isolatedIO120ps/min0/.558822fF',
                    source_files={str(p.relative_to(src)): hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in src.rglob('*') if p.is_file() and '.git' not in p.parts},
                    abc_repeated=False, rtl_changes=False)
    (work / 'route_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    make = 'make -f Makefile -f /work/side_effects.mk DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base NUM_CORES=16 '
    result = f'/work/results/asap7/{a.nickname}/base/'
    cmd = ['docker', 'run', '--rm', '-v', f'{src}:/src:ro', '-v', f'{work}:/work',
           '-w', '/OpenROAD-flow-scripts/flow', a.image, 'bash', '-lc',
           'source /OpenROAD-flow-scripts/env.sh; ' +
           make + '-j1 ' + result + '1_2_yosys.v && ' +
           make + '-j1 ' + result + '2_1_floorplan.odb && ' + make + '-j16 finish']
    with (work / 'route.log').open('w') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    (work / 'route.exit').write_text(str(result.returncode) + '\n')
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
