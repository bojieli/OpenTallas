import sys,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root/'tools/hier_contract'));import child_lint as C
out=Path(sys.argv[1]);out.mkdir(exist_ok=True)
view=root/'physical/ref_tile/vm_lg_bank_hc_static_1015/views/ot_hbm_vm_lg_static_bank';text=(view/'ot_hbm_vm_lg_static_bank.lef').read_text();m=C.parse_lef(text)
src=(root/'rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv').read_text();hdr=src.split(')(\n',1)[1].split(');',1)[0].replace('output reg','output wire')
# Literal existing native port header, same directions and bus shapes.
names=['clk','rst_n','local_rq','far_rq','local_wq','far_wq','local_read','local_write','near_rq','near_wq','near_rr','near_w_done','local_rr','far_rr','local_w_done','far_w_done','fault']
(out/'parent.v').write_text('module lg_parent_escape(\n'+hdr+');\n ot_hbm_vm_lg_static_bank u_leaf('+','.join('.'+n+'('+n+')'for n in names)+');\nendmodule\n')
import shutil
shutil.copy2(view/'ot_hbm_vm_lg_static_bank_tt.lib',out/'child.lib')
(out/'child.lef').write_text(text)
# Bad abstract blocks both adjacent layers over a real W-face terminal.
mut=text.replace('  OBS\n','  OBS\n    LAYER M3 ;\n      RECT 0 8.064 0.144 8.184 ;\n    LAYER M4 ;\n      RECT 0 8.064 0.144 8.184 ;\n    LAYER M5 ;\n      RECT 0 8.064 0.144 8.184 ;\n',1)
assert mut!=text;(out/'blocked.lef').write_text(mut)
ports=[];lines=[]
for name,pin in m['pins'].items():
 if C.is_pg(name,pin):continue
 rs=[r for r in pin['rects']if C.face_of(r,m['W'],m['H'])]
 assert len(rs)==1,(name,rs)
 r=rs[0];face=C.face_of(r,m['W'],m['H']);x=(r[1]+r[3])/2+48.384;y=(r[2]+r[4])/2+49.68
 if face=='W':x=0
 if face=='E':x=247.104
 if face=='S':y=0
 if face=='N':y=250.56
 lines.append(f'place_pin -pin_name {{{name}}} -layer {r[0]} -location {{{x:.6f} {y:.6f}}} -pin_size {{0.024 0.024}} -force_to_die_boundary')
 ports.append(dict(name=name,face=face,parent_xy=[x,y],layer=r[0]))
(out/'pins.tcl').write_text('\n'.join(lines)+'\n')
(out/'manifest.json').write_text(json.dumps(dict(child_lef_sha256=hashlib.sha256(text.encode()).hexdigest(),parent_shape_um=[247.104,250.56],leaf_origin_um=[48.384,49.68],orientation='R0',nets=1673,scope='Parent escape test only; not whole-die placement/timing/PG delivery',ports=ports),indent=2)+'\n')
tcl='''set root /work
set mode $::env(MODE)
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
if {$mode eq "blocked"} {read_lef /work/blocked.lef} else {read_lef /work/child.lef}
read_liberty /work/child.lib
read_verilog /work/parent.v
link_design lg_parent_escape
initialize_floorplan -die_area {0 0 247.104 250.56} -core_area {0 0 247.104 250.56} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set blk [ord::get_db_block]
set inst [$blk findInst u_leaf]
$inst setOrient R0
$inst setLocation 48384 49680
$inst setPlacementStatus FIRM
source /work/pins.tcl
set_routing_layers -signal M4-M6
create_clock -name core_clk -period 833.333 [get_ports clk]
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set missing 0
foreach p [$inst getITerms] {if {[$p getSigType] in {POWER GROUND}} continue; if {[$p getNet] eq "NULL"} {incr missing}}
if {$missing} {error "LG_PARENT missing signal nets $missing"}
puts "LG_PARENT connectedSignalPorts=1673 missing=$missing"
write_db /work/$mode-initial.odb
pin_access -verbose 1
puts "LG_PARENT pin_access complete mode=$mode"
if {$mode eq "blocked"} {error "LG_PARENT negative unexpectedly passed pin_access"}
global_route -guide_file /work/positive.guide
write_db /work/positive-grt.odb
detailed_route -output_drc /work/positive-drc.rpt
write_db /work/positive-final.odb
write_def /work/positive-final.def
puts "LG_PARENT detailed_route complete"
'''
(out/'run.tcl').write_text(tcl)
print(out)
