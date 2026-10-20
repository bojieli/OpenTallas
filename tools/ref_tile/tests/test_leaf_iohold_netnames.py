"""Native output-hold export regression; run inside the pinned ORFS image.

No cell behavioral model is imported. The comparison uses exact native contact
identity and graph edges after OpenROAD writes and reads Verilog.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[3]
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
P='/OpenROAD-flow-scripts/flow/platforms/asap7'
LIBS=[f'{P}/lib/NLDM/asap7sc7p5t_{s}' for s in (
 'AO_RVT_TT_nldm_211120.lib.gz','INVBUF_RVT_TT_nldm_220122.lib.gz',
 'OA_RVT_TT_nldm_211120.lib.gz','SEQ_RVT_TT_nldm_220123.lib',
 'SIMPLE_RVT_TT_nldm_211120.lib.gz')]
RTL=r'''
module top(input clk, input d, input ot_outhold_src00000,
 input ot_outhold_p00000, input ot_outhold_n00000_0,
 output [1:0] y, output \escaped.pin[3] );
 wire internal_payload;
 DFFHQNx1_ASAP7_75t_R f0(.CLK(clk),.D(d),.QN(internal_payload));
 INVx1_ASAP7_75t_R i0(.A(internal_payload),.Y(y[0]));
 assign y[1]=y[0];
 DFFHQNx1_ASAP7_75t_R f1(.CLK(clk),.D(d),.QN(q1));
 INVx1_ASAP7_75t_R i1(.A(q1),.Y(\escaped.pin[3] ));
endmodule
'''
DUMP=r'''
import odb,json,sys
d=odb.dbDatabase.create();odb.read_db(d,sys.argv[1]);b=d.getChip().getBlock()
edges=[]
for n in b.getNets():
 t=sorted([('B',x.getName()) for x in n.getBTerms()]+[('I',x.getInst().getName(),x.getMTerm().getName()) for x in n.getITerms()])
 if t:edges.append(t)
r=dict(ports=sorted((x.getName(),str(x.getIoType())) for x in b.getBTerms()),cells=sorted((i.getName(),i.getMaster().getName()) for i in b.getInsts()),edges=sorted(edges),nets=sorted(n.getName() for n in b.getNets()))
open(sys.argv[2],'w').write(json.dumps(r,indent=2)+'\n')
'''


@unittest.skipUnless(Path(OR).exists(),'requires pinned OpenROAD image')
class HoldNetNames(unittest.TestCase):
 def test_hold_native_roundtrip(self):
  self.run_case(False)

 def test_pin_split_hold_native_roundtrip(self):
  self.run_case(True)

 def run_case(self,pin_split):
  base=Path(os.environ.get('TEST_WORK',tempfile.mkdtemp(prefix='hold-netnames-')))
  base=base/('pin_split' if pin_split else 'hold')
  base.mkdir(parents=True,exist_ok=True)
  (base/'coupon.v').write_text(RTL);(base/'dump.py').write_text(DUMP)
  setup='\n'.join('read_liberty '+p for p in LIBS)+'\n'+f'''
read_lef {P}/lef/asap7_tech_1x_201209.lef
read_lef {P}/lef/asap7sc7p5t_28_R_1x_220121a.lef
'''
  def run(args,log):
   r=subprocess.run([OR,*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
   (base/log).write_text(r.stdout);self.assertEqual(r.returncode,0,r.stdout[-3000:])
  # Force collisions with every generated naming family, plus real BTerms
  # using those names. Shared y bits exercise processing the same source twice.
  collisions=''
  for n in range(8):
   for stem in (f'ot_outhold_src{n:05d}',f'ot_outhold_p{n:05d}',f'ot_outhold_n{n:05d}_0',f'ot_outhold_n{n:05d}_1',f'ot_prs_{n:05d}_src',f'ot_prs_{n:05d}_q',f'ot_prs_{n:05d}_n0'):
    collisions+=f'if {{[$b findNet {stem}] eq "NULL"}} {{odb::dbNet_create $b {stem}}}\n'
  pg='add_global_connection -net VDD -inst_pattern .* -pin_pattern ^VDD$ -power\nadd_global_connection -net VSS -inst_pattern .* -pin_pattern ^VSS$ -ground\nglobal_connect\n'
  prs=f'source {ROOT}/physical/common_flow/pin_reg_split.tcl\nglobal_connect\n' if pin_split else ''
  flow=setup+f'''
read_verilog {base}/coupon.v
link_design top
initialize_floorplan -die_area {{0 0 43.2 43.2}} -core_area {{2.16 2.16 41.04 41.04}} -site asap7sc7p5t
source {P}/openRoad/make_tracks.tcl
set b [ord::get_db_block]
create_clock -name c -period 833.333 [get_ports clk]
set_input_delay 166.667 -clock c [all_inputs -no_clocks]
set_output_delay 166.667 -clock c [all_outputs]
set_dont_touch [get_nets internal_payload]
proc obj_names {{objects}} {{ set names {{}}; foreach o $objects {{ lappend names [get_full_name $o] }}; return [lsort $names] }}
set bindings [list [obj_names [all_inputs -no_clocks]] [obj_names [all_outputs]] [llength [all_clocks]]]
set k 0
foreach bt [$b getBTerms] {{
 set name [$bt getName]
 if {{[$bt getIoType] eq "OUTPUT"}} {{
  place_pin -pin_name $name -layer M5 -location [list [expr {{5.004+2.016*$k}}] 0] -force_to_die_boundary
 }} else {{
  place_pin -pin_name $name -layer M4 -location [list 0 [expr {{10.044+2.016*$k}}]] -force_to_die_boundary
 }}
 incr k
}}
{collisions}
{pg}
{prs}
set ::env(RESULTS_DIR) {base}
set ::env(OT_INHOLD_MASTER) HB2xp67_ASAP7_75t_R
set ::env(OT_INHOLD_DRV) BUFx4f_ASAP7_75t_R
source {ROOT}/physical/dsrom_window_source/leaf_iohold.tcl
global_connect
source {ROOT}/physical/common_flow/native_pg_binding.tcl
set native_pg_map [ot_pg_prepare $b]
ot_pg_assert_all_native $b $native_pg_map
if {{$bindings ne [list [obj_names [all_inputs -no_clocks]] [obj_names [all_outputs]] [llength [all_clocks]]]}} {{error {{port constraint binding changed}}}}
if {{[llength [get_nets internal_payload]] != 1}} {{error {{unrelated explicit net name changed}}}}
if {{![[$b findNet internal_payload] isDoNotTouch]}} {{error {{existing net dont_touch lost}}}}
write_sdc {base}/after.sdc
write_db {base}/actual.odb
write_verilog {base}/export.v
'''
  (base/'flow.tcl').write_text(flow);run(['-exit',str(base/'flow.tcl')],'flow.log')
  (base/'readback.tcl').write_text(setup+f'\nread_verilog {base}/export.v\nlink_design top\n{pg}\nsource {ROOT}/physical/common_flow/native_pg_binding.tcl\nset native_pg_map [ot_pg_prepare [ord::get_db_block]]\not_pg_assert_all_native [ord::get_db_block] $native_pg_map\nwrite_db {base}/readback.odb\n')
  run(['-exit',str(base/'readback.tcl')],'readback.log')
  for stem in ('actual','readback'):
   run(['-python',str(base/'dump.py'),str(base/f'{stem}.odb'),str(base/f'{stem}.json')],stem+'_dump.log')
  a=json.loads((base/'actual.json').read_text());b=json.loads((base/'readback.json').read_text())
  for key in ('ports','cells','edges'):self.assertEqual(a[key],b[key],key)
  self.assertIn('ot_outhold_src00000',a['nets'])
  self.assertTrue(any(x.startswith('ot_outhold_src') and x.endswith('_1') for x in a['nets']))
  self.assertTrue(any(x.startswith('ot_outhold_p') and x.endswith('_1') for x in a['nets']))
  self.assertTrue(any(x.startswith('ot_outhold_n') and x.endswith('_1') for x in a['nets']))
  (base/'receipt.json').write_text(json.dumps(dict(status='PASS',ports=len(a['ports']),cells=len(a['cells']),edges=len(a['edges']),cases=['shared_output_source','indexed_ports','escaped_identifier','existing_net_names','existing_BTerm_names','unrelated_explicit_get_nets','dont_touch','clock_and_delay_port_bindings','exact_native_Verilog_roundtrip','all_actual_PG_pins_bound',str(pin_split)+'_pin_reg_split']),indent=2)+'\n')


if __name__=='__main__':unittest.main()
