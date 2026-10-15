"""Small real OpenROAD clock trees plus independently wired hard entries."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE
ROOT = Path(__file__).resolve().parents[3]
IMAGE = 'openroad/orfs:latest'
OR = '/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'


def available():
    return bool(shutil.which('docker')) and subprocess.run(
        ['docker', 'image', 'inspect', IMAGE], capture_output=True).returncode == 0


def view(root):
    v = root/'hard'; v.mkdir()
    lib = '''library(hard_tt) { time_unit : "1ps"; capacitive_load_unit(1,ff);
      nom_voltage : 0.7; nom_temperature : 25; nom_process : 1;
      cell(hard) { area : 100; ff(IQ,IQN) { clocked_on : "CLK"; next_state : "D"; } pin(CLK) { direction : input; clock : true; capacitance : 1; }
      pin(D) { direction : input; capacitance : 1; } pin(Q) { direction : output; function : "IQ"; timing() { related_pin : "CLK"; timing_type : rising_edge; cell_rise(scalar) { values("100"); } cell_fall(scalar) { values("100"); } } } } }'''
    for c in CE.CORNERS:
        (v/f'hard_{c}.lib').write_text(lib.replace('hard_tt', 'hard_'+c))
    (v/'insertion.json').write_text(json.dumps(dict(lib_clock_pin='CLK', **{
        c: dict(boundary=dict(n=4, min=90, mean=100, max=110)) for c in CE.CORNERS})))
    return v


class HybridSpec(unittest.TestCase):
    def test_explicit_accounting_and_no_exceptions(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);view(root)
            spec=dict(clock='hybrid_entries',clock_port='ck',clock_ports=['ck','child'],
                      clock_cts_roots=['ck'],children=[dict(view='hard')])
            text=CE.generate(spec,root)
            self.assertIn('set ::ot_ce_cts_roots {{ck}}',text)
            self.assertIn('CTS_MEASURE',text)
            self.assertNotIn('set_false_path',text)
            self.assertNotIn('set_clock_groups',text)
            spec['clock']='entries'
            with self.assertRaisesRegex(ValueError,'bound child clock pins'): CE.generate(spec,root)
            spec['clock']='hybrid_entries';spec['clock_cts_roots']=['ck','child']
            with self.assertRaisesRegex(ValueError,'proper subset'): CE.generate(spec,root)


@unittest.skipUnless(available(), 'real OpenROAD ORFS image required')
class HybridOpenroad(unittest.TestCase):
    def run_flow(self, mutant='', entries_only=False, second_root=False, mixed_internal=False, internal_root=False):
        with tempfile.TemporaryDirectory() as d:
            w=Path(d);view(w)
            # 16 actual flop clock sinks suffice to exercise TritonCTS, not a hardened child build.
            ports=['child'] if entries_only else (['ck','ck2','child'] if second_root else ['ck','child'])
            spec=dict(clock='entries' if entries_only else 'hybrid_entries', clock_port=ports[0],
                      clock_ports=ports,children=[dict(view='hard')])
            if not entries_only:spec['clock_cts_roots']=['ck','ck2'] if second_root else ['ck']
            cells='' if entries_only else '\n'.join(
                f'DFFHQNx1_ASAP7_75t_R r{i} (.CLK(ck),.D({"q0" if mixed_internal and i >= 4 else "d"}),.QN(q{i}));' for i in range(16))
            if second_root: cells+='\n'+'\n'.join(f'DFFHQNx1_ASAP7_75t_R s{i} (.CLK(ck2),.D({"q0" if internal_root else "d"}),.QN(z{i}));' for i in range(4))
            net='module top(input '+','.join(ports)+',input d,output y);\n'+cells+'\nhard h(.CLK(child),.D(d),.Q(y));\nendmodule\n'
            if mutant=='escaped_names':net=net.replace(' r0 (', ' \\c_q[0]$_DFF_P_ (')
            if mutant=='child_on_cts':net=net.replace('.CLK(child)', '.CLK(ck)')
            if mutant=='glue_on_entry':net=net.replace('.CLK(ck)', '.CLK(child)',1)
            (w/'t.v').write_text(net)
            (w/'hard.lef').write_text('''VERSION 5.8 ; BUSBITCHARS "[]" ; DIVIDERCHAR "/" ;
MACRO hard CLASS BLOCK ; ORIGIN 0 0 ; SIZE 10 BY 10 ; SYMMETRY X Y ;
PIN CLK DIRECTION INPUT ; USE CLOCK ; PORT LAYER M4 ; RECT 0.1 0.1 0.2 0.2 ; END END CLK
PIN D DIRECTION INPUT ; USE SIGNAL ; PORT LAYER M4 ; RECT 0.1 0.4 0.2 0.5 ; END END D
PIN Q DIRECTION OUTPUT ; USE SIGNAL ; PORT LAYER M4 ; RECT 9.8 0.4 9.9 0.5 ; END END Q
END hard END LIBRARY\n''')
            (w/'clocks.tcl').write_text(CE.clocks(spec,833.333))
            (w/'entries.tcl').write_text('set ::ot_ce_require_wire 1\n'+CE.generate(spec,w))
            old_hash=hashlib.sha256((w/'hard/hard_tt.lib').read_bytes()).hexdigest()
            roots='' if entries_only else ('set ::ot_ce_cts_roots {ck ck2}' if second_root else 'set ::ot_ce_cts_roots {ck}')
            flow=r'''
set_thread_count 2
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /w/hard.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] { read_liberty $l }
read_liberty /w/hard/hard_tt.lib
read_verilog /w/t.v
link_design top
initialize_floorplan -die_area {0 0 100 100} -core_area {5.4 5.4 94.6 94.6} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_pins -hor_layers M4 -ver_layers M5
source /w/clocks.tcl
set_input_delay 10 -clock core_clk [get_ports d]
set_output_delay 10 -clock core_clk [get_ports y]
source $P/setRC.tcl
set u [[ord::get_db_block] getDbUnitsPerMicron]
set k 0
foreach i [[ord::get_db_block] getInsts] {
  if {[$i getName] eq "h"} { $i setLocation [expr {70*$u}] [expr {70*$u}]; $i setPlacementStatus FIRM } else {
    $i setLocation [expr {int((15+12*($k%4))*$u)}] [expr {int((15+12*($k/4))*$u)}]
    $i setPlacementStatus PLACED; incr k
  }
}
detailed_placement
ROOTS
source /src/physical/common_flow/clock_entries.tcl
set_propagated_clock [get_clocks ot_entry_*]
clock_tree_synthesis -sink_clustering_enable -buf_list BUFx4_ASAP7_75t_R -root_buf BUFx4_ASAP7_75t_R
estimate_parasitics -placement
source /w/entries.tcl
set net [[[[ord::get_db_block] findBTerm child] getNet] getITerms]
if {[llength $net] != 1 || [[[lindex $net 0] getInst] getName] ne "h"} {error "hard entry altered by CTS"}
puts "HYBRID_RESULT PASS"
'''.replace('ROOTS',roots)
            if mutant=='missing_glue_clock':flow=flow.replace('source /w/entries.tcl','remove_clock [get_clocks ot_entry_0]\nsource /w/entries.tcl')
            (w/'run.tcl').write_text(flow)
            proc=subprocess.run(['docker','run','--rm','-v',f'{w}:/w','-v',f'{ROOT}:/src:ro',
                IMAGE,OR,'-no_init','-exit','/w/run.tcl'],capture_output=True,text=True,timeout=60)
            self.assertEqual(hashlib.sha256((w/'hard/hard_tt.lib').read_bytes()).hexdigest(),old_hash)
            return proc.returncode,proc.stdout+proc.stderr

    def test_real_hybrid_roots_and_compensation(self):
        rc,out=self.run_flow();self.assertEqual(rc,0,out[-6500:])
        self.assertIn('CTS_MEASURE tt ck sinks=16',out)
        self.assertIn('OT_ENTRIES COMP tt child',out)
        self.assertIn('OT_ENTRIES COMP tt ck',out)
        self.assertIn('HYBRID_RESULT PASS',out)
        self.assertRegex(out,r'OT_HYBRID CTS roots ck; hard-child entries excluded')
        rows=re.findall(r'COMP tt (\w+) -> \S+ wire=([\d.eE+-]+) R=([\d.eE+-]+) latency=([\d.eE+-]+) phi=([\d.eE+-]+)',out)
        self.assertEqual(len(rows),2)
        for _,wire,ins,lat,phi in rows:
            self.assertGreater(float(ins),0)
            self.assertAlmostEqual(float(wire)+float(ins)+float(lat),float(phi),places=6)
        self.assertNotEqual(float(rows[0][3]),float(rows[1][3]))

    def test_multiple_glue_roots_remain_independent(self):
        rc,out=self.run_flow(second_root=True);self.assertEqual(rc,0,out[-5000:])
        self.assertIn('CTS_MEASURE tt ck sinks=16',out)
        self.assertIn('CTS_MEASURE tt ck2 sinks=4',out)
        self.assertIn('CTS roots ck ck2;',out)

    def test_escaped_register_instance_maps_to_actual_db_object(self):
        rc,out=self.run_flow('escaped_names');self.assertEqual(rc,0,out[-5000:])
        self.assertIn('CTS_MEASURE tt ck sinks=16',out)
        self.assertIn('HYBRID_RESULT PASS',out)

    def test_internal_only_root_declares_its_reference_scope(self):
        rc,out=self.run_flow(second_root=True,internal_root=True);self.assertEqual(rc,0,out[-5000:])
        self.assertIn('ck2 sinks=4 reference_scope=all_internal_only boundary_sinks=4',out)

    def test_boundary_mean_excludes_internal_registers(self):
        rc,out=self.run_flow(mixed_internal=True);self.assertEqual(rc,0,out[-5000:])
        self.assertIn('sinks=16 reference_scope=boundary boundary_sinks=4',out)
        m=re.search(r'CTS_MEASURE tt ck .*?mean=([\d.eE+-]+) .*?all_mean=([\d.eE+-]+)',out)
        self.assertIsNotNone(m,out[-3000:])
        self.assertNotAlmostEqual(float(m[1]),float(m[2]),places=3)

    def test_old_entries_still_wires_only(self):
        rc,out=self.run_flow(entries_only=True);self.assertEqual(rc,0,out[-4000:])
        self.assertNotIn('CTS_MEASURE',out);self.assertIn('HYBRID_RESULT PASS',out)

    def test_accounting_mutants_rejected(self):
        for mutant in ['child_on_cts','glue_on_entry','missing_glue_clock']:
            with self.subTest(mutant=mutant):
                rc,out=self.run_flow(mutant);self.assertNotEqual(rc,0,out[-4000:])
                self.assertRegex(out,r'OT_HYBRID|OT_ENTRIES')
