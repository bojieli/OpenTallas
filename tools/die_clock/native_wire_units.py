#!/usr/bin/env python3
"""OpenROAD counterexample: W must be a full local/far pair, including count one.
Run with openroad -python -no_init -exit in the ASAP7 ORFS container.
This measures placed cells and native TT/FF STA, not die qualification.
"""
import json
from pathlib import Path
from openroad import Tech, Design
import odb

plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
tech = Tech()
for leaf in ('asap7_tech_1x_201209.lef', 'asap7sc7p5t_28_R_1x_220121a.lef'):
    tech.readLef(f'{plat}/lef/{leaf}')
d = Design(tech)
tcl = d.evalTclString
tcl('define_corners tt ff')
for corner in ('tt', 'ff'):
    tcl(f'read_liberty -corner {corner} {plat}/lib/NLDM/asap7sc7p5t_INVBUF_RVT_{corner.upper()}_nldm_220122.lib.gz')
cell = 'BUFx24_ASAP7_75t_R'
v = ['module top(input ck);', f'wire root; {cell} rootbuf(.A(ck),.Y(root));']
positions = {'rootbuf': (100, 200)}
paths = []
for mode in ('old', 'pair'):
    for count in range(5):
        name = f'{mode}{count}'
        prev = 'root'
        y = 50 + 30 * len(paths)
        for stage in range(count * (2 if mode == 'pair' else 1)):
            inst = f'{name}_p{stage}'
            net = f'n_{inst}'
            v += [f'wire {net}; {cell} {inst}(.A({prev}),.Y({net}));']
            positions[inst] = (100 + (180 if stage % 2 else 0), y)
            prev = net
        v += [f'wire {name}_out; {cell} {name}(.A({prev}),.Y({name}_out));']
        positions[name] = (100, y)
        paths.append((mode, count, name))
v += ['endmodule']
Path('/out/wire_units.v').write_text('\n'.join(v))
d.readVerilog('/out/wire_units.v')
d.link('top')
blk = d.getBlock()
u = blk.getDbUnitsPerMicron()
blk.setDieArea(odb.Rect(0, 0, int(1000*u), int(1000*u)))
for inst in blk.getInsts():
    x, y = positions[inst.getName()]
    inst.setLocation(int(x*u), int(y*u))
    inst.setPlacementStatus('PLACED')
tcl(f'source {plat}/setRC.tcl')
tcl('set_wire_rc -clock -layer M8')
tcl('create_clock -name ck -period 833.333 [get_pins rootbuf/Y]')
tcl('set_propagated_clock [all_clocks]')
tcl('estimate_parasitics -placement')
tcl('sta::find_timing_paths -path_delay max -group_path_count 1')
result = {}
for mode, count, name in paths:
    result[name] = [float(tcl(f'get_property [get_pins {name}/Y] {p}')) for p in ('arrival_max_rise','arrival_min_rise')]
# Baselines are at different y: remove the root->first-stage wire by measuring first input too.
for mode, count, name in paths:
    first = f'{name}_p0' if count else name
    a = [float(tcl(f'get_property [get_pins {first}/A] {p}')) for p in ('arrival_max_rise','arrival_min_rise')]
    result[name] = [v-b for v,b in zip(result[name],a)]
for mode in ('old','pair'):
    base = result[f'{mode}0']
    for count in range(1,5):
        result[f'{mode}{count}_per_unit'] = [(v-b)/count for v,b in zip(result[f'{mode}{count}'],base)]
print('NATIVE_WIRE_UNITS', json.dumps(result, sort_keys=True), flush=True)
old_gap = result['old2_per_unit'][0] - result['old1_per_unit'][0]
pair_gap = max(result[f'pair{k}_per_unit'][0] for k in range(1,5)) - min(result[f'pair{k}_per_unit'][0] for k in range(1,5))
assert old_gap > 10, ('old counterexample not reproduced',old_gap)
assert pair_gap < old_gap, ('pair did not improve count dependence',pair_gap,old_gap)
print('NATIVE_WIRE_UNITS_PASS', json.dumps(dict(old_gap_tt_ps=old_gap,pair_gap_tt_ps=pair_gap)),flush=True)
