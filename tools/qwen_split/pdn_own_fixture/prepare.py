#!/usr/bin/env python3
"""Generate a native closed reset-repeater PG fixture; no abstract pin edits.
Run: prepare.py REPO OUTPUT TECH_LEF
Candidate pdn_regroup.py must support --own-grid. Native driver uses real LEFs.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pdn_regroup
repo, out, tech = map(Path, sys.argv[1:])
out.mkdir(parents=True, exist_ok=True)
for name in ('driver.sh', 'readback.tcl', 'check_shorts.py'):
    shutil.copyfile(Path(__file__).parent / name, out / name)
inputs = {}
for master in ('qfd_rst_rep', 'qfd_rst_rep_p8'):
    p = repo / f'physical/ref_tile/{master}/views/{master}/{master}.lef'
    shutil.copyfile(p, out / f'{master}.lef')
    inputs[master] = {'source':str(p), 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
shutil.copyfile(tech, out / 'tech.lef')
inputs['tech'] = {'source':str(tech), 'sha256':hashlib.sha256(tech.read_bytes()).hexdigest()}
insts = []
for mi, master in enumerate(('qfd_rst_rep', 'qfd_rst_rep_p8')):
    for oi, orient in enumerate(('R0', 'MX', 'MY', 'R180')):
        for phase in range(4):
            insts.append(dict(n=f'r{mi}_{oi}_{phase}', m=master, o=orient,
                              x=21.6 + (oi*4+phase)*21.6, y=21.6+mi*43.2+phase*2.16))
(out/'die.v').write_text('module fixture();\n'+''.join(f'  {i["m"]} {i["n"]} ();\n' for i in insts)+'endmodule\n')
(out/'pos.json').write_text(json.dumps({'insts':insts}))
pdn = '''# Fixture original r5-like grid; regroup generates the tested candidate and mutant
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core -voltage_domains CORE -pins {M9} -starts_with GROUND
add_pdn_stripe -grid core -layer M8 -width .48 -pitch 9.091 -offset 0
add_pdn_stripe -grid core -layer M9 -width .48 -pitch 9.091 -offset 0
add_pdn_connect -grid core -layers {M8 M9}
'''
for i in insts:
    pdn += f'define_pdn_grid -macro -instances {{^{i["n"]}$}} -voltage_domains CORE -name pg_{i["n"]} -starts_with GROUND -grid_over_boundary\n'
    pdn += f'add_pdn_stripe -grid pg_{i["n"]} -layer M8 -width .48 -pitch 9.091 -offset 0\n'
(out/'pdn.tcl').write_text(pdn)
# tie_local without standard rows exits early but adds the production M5->M8 connection to normal grids.
for name, own in [('candidate', {'qfd_rst_rep':(2.16,3.36),'qfd_rst_rep_p8':(2.16,3.36)}), ('mutant', {})]:
    summary = pdn_regroup.regroup(out, 8.64, f'{name}.pdn.tcl', pos_json=out/'pos.json', tie_local_pg=True, own_grid=own)
    (out/f'{name}.json').write_text(json.dumps(summary, indent=2)+'\n')
    t = '''read_lef tech.lef
read_lef -library /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef -library qfd_rst_rep.lef
read_lef -library qfd_rst_rep_p8.lef
read_verilog die.v
link_design fixture
initialize_floorplan -die_area {0 0 400 120} -core_area {1 1 399 119} -site asap7sc7p5t
set block [ord::get_db_block]
'''
    for i in insts:
        t += f'set i [$block findInst {i["n"]}]; $i setOrient {i["o"]}; $i setLocation {round(i["x"]*1000)} {round(i["y"]*1000)}; $i setPlacementStatus FIRM\n'
    t += f'source {name}.pdn.tcl\npdngen -failed_via_report {name}.vias.rpt\ncheck_power_grid -net VDD\ncheck_power_grid -net VSS\nwrite_db {name}.odb\nputs OWN_GRID_FIXTURE_PASS\n'
    (out/f'{name}.tcl').write_text(t)
(out/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
