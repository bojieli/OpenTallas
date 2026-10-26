"""Actual implicit-power PA failure, physical tie mapping, and shell status propagation."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import unittest

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
spec=importlib.util.spec_from_file_location('case_status', HERE/'case_status.py')
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)
GOOD='OT_LEGAL instances=3 overlaps=0 outside=0\nOT_ASSERT PASS\nOT_PA DONE\n'
POWER='[ERROR DRT-0305] Net one_ of signal type POWER is not routable by TritonRoute. Move to special nets.\nOT_PA FAIL DRT-0305\n'


class CaseStatus(unittest.TestCase):
    def test_success_and_physical_failure_markers(self):
        self.assertEqual(S.check(GOOD,'run.tcl')['exit_code'],0)
        for bad in [GOOD+POWER,GOOD+'OT_ASSERT FAIL offtrack\n',GOOD.replace('overlaps=0','overlaps=1'),
                    GOOD.replace('OT_PA DONE',''),GOOD+'OT_PAFAIL DRT-0305\n',GOOD+'Error: script.tcl, 1 failure\n']:
            with self.subTest(bad=bad):self.assertNotEqual(S.check(bad,'run.tcl')['exit_code'],0)
        self.assertEqual(S.check(GOOD,'run.tcl',124)['exit_code'],124)
        self.assertNotEqual(S.check('OT_PA DONE\n','run.tcl',case_kind='a_pdn')['exit_code'],0)

    def test_pdn_requires_both_power_connectivity_checks(self):
        good='OT_PDN PASS special_shapes=12\nOT_PGCHECK VDD PASS\nOT_PGCHECK VSS PASS\n'
        self.assertEqual(S.check(good,'run_pdn.tcl')['exit_code'],0)
        for bad in [good.replace('OT_PGCHECK VSS PASS\n',''),good+'OT_PGCHECK VDD FAIL disconnected\n']:
            self.assertNotEqual(S.check(bad,'run_pdn.tcl')['exit_code'],0)
        self.assertEqual(S.check('OT_GRT DONE\n','run.tcl',case_kind='b')['exit_code'],0)

    def test_sta_requires_metrics_and_rejects_actual_missing_clock(self):
        good="tns -13.2\nwns -1.0\nworst slack -1.0\n"
        self.assertEqual(S.check(good,"grt_tt.tcl")["exit_code"],0)
        for bad in ["", "OT_TIME step=load s=8.8\n", good+"Error: grt_tt.tcl, 76 clock boundary pin missing or ambiguous: s_2_0/ck\n"]:
            self.assertNotEqual(S.check(bad,"grt_tt.tcl")["exit_code"],0)
        self.assertEqual(S.check(good,"grt_ff.tcl",1)["exit_code"],1)
        typed="tns max -125003880.00\nwns max -550466.56\nworst slack max -550466.56\n"
        self.assertEqual(S.check(typed,"grt_tt.tcl")["exit_code"],0)
        self.assertNotEqual(S.check(typed.replace("wns max -550466.56","wns max nan"),"grt_tt.tcl")["exit_code"],0)
        for value in ('---','e','nan','inf','-inf','1e999','-1.0 junk'):
            with self.subTest(value=value):
                self.assertNotEqual(S.check(good.replace('wns -1.0','wns '+value),"grt_tt.tcl")["exit_code"],0)

    def test_shell_preserves_effective_failure_even_after_final_date(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'run.log').write_text(GOOD+POWER)
            (p/'manifest.json').write_text('{"case":"a_pdn"}')
            (p/'docker').write_text('#!/bin/sh\nexit 0\n');(p/'docker').chmod(0o755)
            env=dict(os.environ,PATH=str(p)+os.pathsep+os.environ['PATH'])
            run=subprocess.run(['bash',str(HERE/'run_case.sh'),str(p),'run.tcl','run.log','1','1'],
                               env=env,text=True,capture_output=True)
            self.assertEqual(run.returncode,1,run.stdout+run.stderr)
            self.assertEqual((p/'run.log.process_exit').read_text().strip(),'0')
            self.assertEqual((p/'run.log.exit').read_text().strip(),'1')
            self.assertEqual(json.loads((p/'run.log.status.json').read_text())['status'],'FAIL')


def docker_available():
    return bool(shutil.which('docker')) and subprocess.run(
        ['docker','image','inspect','openroad/orfs:latest'],capture_output=True).returncode==0


FLOW='''set_thread_count 2
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /work/hard.lef
read_verilog /work/die.v
link_design top
initialize_floorplan -die_area {0 0 40 40} -core_area {5.4 5.4 34.6 34.6} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
set b [ord::get_db_block]
set i [$b findInst h]
$i setLocation 10800 10800
$i setPlacementStatus FIRM
MAPPING
set_routing_layers -signal M2-M9
if {[catch {pin_access -verbose 1} err]} {puts "OT_PA FAIL $err"RAISE} else {puts "OT_PA DONE"}
'''


@unittest.skipUnless(docker_available(),'actual OpenROAD ORFS image required')
class RealConstantMapping(unittest.TestCase):
    def run_case(self, mapped=False, strict=False, full=False, pg=None):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for name in ['die.v','hard.lef']:shutil.copyfile(HERE/'testdata/constants'/name,p/name)
            mapping=''
            if mapped:
                mapping='''source /src/physical/common_flow/die_constant_cells.tcl
set ties 0
foreach inst [$b getInsts] {
 if {[[$inst getMaster] getName] in {TIEHIx1_ASAP7_75t_R TIELOx1_ASAP7_75t_R}} {incr ties}
}
if {$ties != 2} {error "wrong physical tie count"}
set boxes {}
foreach inst [$b getInsts] {
 set bb [$inst getBBox]
 foreach other $boxes {
  lassign $other x0 y0 x1 y1
  if {[$bb xMin]<$x1 && [$bb xMax]>$x0 && [$bb yMin]<$y1 && [$bb yMax]>$y0} {error "constant placement overlap"}
 }
 lappend boxes [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]]
}
if {[$i getLocation] ne "10800 10800"} {error "hard macro moved"}
foreach net [$b getNets] {
 if {[$net getSigType] in {POWER GROUND} && ![$net isSpecial]} {error "unmapped constant net"}
}
'''
            if full:
                lef=p/'hard.lef';lef.write_text(lef.read_text().replace('SIZE 4 BY 4','SIZE 29.16 BY 29.16'))
            flow=FLOW.replace('MAPPING',mapping).replace('RAISE','; error $err' if strict else '')
            if full:flow=flow.replace('$i setLocation 10800 10800','$i setLocation 5400 5400')
            if pg == 'complete':
                flow += """
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name native -voltage_domains CORE -pins {M5}
add_pdn_stripe -grid native -layer M1 -width 0.018 -followpins
add_pdn_stripe -grid native -layer M2 -width 0.018 -followpins
add_pdn_stripe -grid native -layer M3 -width 0.09 -pitch 1.08 -spacing 0.45 -offset 0.27 -extend_to_boundary
add_pdn_stripe -grid native -layer M4 -width 0.12 -pitch 2.16 -spacing 0.96 -offset 0.54 -extend_to_boundary
add_pdn_stripe -grid native -layer M5 -width 0.12 -pitch 2.16 -spacing 0.96 -offset 0.54 -extend_to_boundary
foreach pair {{M1 M2} {M2 M3} {M3 M4} {M4 M5}} {add_pdn_connect -grid native -layers $pair}
pdngen
"""
            if pg == 'complete_r4':
                sys.path.insert(0,str(ROOT/'tools'))
                import qwen_rom_fulldie_b3r2 as B
                flow += '\nset_voltage_domain -name CORE -power VDD -ground VSS\n'
                flow += 'define_pdn_grid -name core -voltage_domains CORE -pins {M9}\n'
                flow += 'add_pdn_stripe -grid core -layer M8 -width .48 -pitch 4.32 -offset 0\n'
                flow += 'add_pdn_stripe -grid core -layer M9 -width .48 -pitch 4.32 -offset 0\n'
                flow += 'add_pdn_connect -grid core -layers {M8 M9}\n'
                flow += '\n'.join(B.native_stdcell_pg_lines('core'))+'\npdngen\n'
            if pg:
                flow += '\nsource /src/physical/common_flow/die_constant_pg_check.tcl\n'
            if pg in ('complete','complete_r4'):
                flow += 'foreach net {VDD VSS} {check_power_grid -net $net}\n'
            (p/'run.tcl').write_text(flow)
            run=subprocess.run(['docker','run','--rm','-v',f'{p}:/work','-v',f'{ROOT}:/src:ro',
                'openroad/orfs:latest','/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad',
                '-no_init','-exit','/work/run.tcl'],text=True,capture_output=True,timeout=30)
            return run.returncode,run.stdout+run.stderr

    def test_observed_bad_power_is_rejected_despite_process_zero(self):
        rc,log=self.run_case()
        self.assertEqual(rc,0,log[-3000:])
        self.assertIn('Net one_ of signal type POWER',log)
        self.assertIn('OT_PA FAIL DRT-0305',log)
        self.assertEqual(S.check(log,'run.tcl',rc)['exit_code'],1)

    def test_real_tie_cells_pass_pa_with_power_qualification_still_open(self):
        rc,log=self.run_case(mapped=True,strict=True)
        self.assertEqual(rc,0,log[-3000:])
        self.assertIn('OT_CONST MAPPED cells=2 hard_macros_unchanged=1',log)
        self.assertIn('OT_CONST PG_OPEN',log)
        self.assertIn('OT_PA DONE',log)
        self.assertNotIn('[ERROR',log)

    def test_no_legal_gap_cannot_emit_an_unplaced_constant(self):
        rc,log=self.run_case(mapped=True,strict=True,full=True)
        self.assertNotEqual(rc,0,log[-3000:])
        self.assertIn('OT_CONST: no legal row gap',log)

    def test_actual_pin_rail_contacts_and_connected_grid(self):
        rc,log=self.run_case(mapped=True,strict=True,pg='complete')
        self.assertEqual(rc,0,log[-3000:])
        self.assertIn('OT_CONST PG_CONTACT cells=2 pins=4',log)
        self.assertIn('All shapes on net VDD are connected',log)
        self.assertIn('All shapes on net VSS are connected',log)

    def test_actual_die_native_rail_ladder_reaches_core_M9(self):
        rc,log=self.run_case(mapped=True,strict=True,pg='complete_r4')
        self.assertEqual(rc,0,log[-5000:])
        self.assertIn('OT_CONST PG_CONTACT cells=2 pins=4',log)
        self.assertIn('All shapes on net VDD are connected',log)
        self.assertIn('All shapes on net VSS are connected',log)

    def test_logical_pg_binding_cannot_replace_literal_supply_rails(self):
        rc,log=self.run_case(mapped=True,strict=True,pg='missing')
        self.assertNotEqual(rc,0,log[-3000:])
        self.assertIn('missing literal M1 rail contact',log)
        self.assertIn('PG remains OPEN',log)

    def test_direct_openroad_error_is_fatal_in_generated_contract(self):
        rc,log=self.run_case(strict=True)
        self.assertNotEqual(rc,0,log[-3000:])
        self.assertIn('OT_PA FAIL DRT-0305',log)


if __name__=='__main__':unittest.main()
