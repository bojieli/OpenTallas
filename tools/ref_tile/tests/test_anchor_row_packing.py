"""Actual legal-row packing of owned anchors; no timing or netlist edits."""
from pathlib import Path
import shutil, subprocess, sys, tempfile, unittest
ROOT=Path(__file__).resolve().parents[3]
IMAGE='openroad/orfs:latest'
OR='/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad'
def available():
    return bool(shutil.which('docker')) and subprocess.run(['docker','image','inspect',IMAGE],capture_output=True).returncode==0

class SourceClosure(unittest.TestCase):
    def test_row_packer_is_consumed_with_the_anchoring_hook(self):
        sys.path.insert(0,str(ROOT/'tools/ref_tile'))
        import pre_route_gate as G
        import source_binding as SB
        hook='physical/qwen_die_masters/io_flop_at_pins.tcl'
        helper='physical/common_flow/anchor_row_packing.tcl'
        files={p:(ROOT/p).read_bytes() for p in (hook,helper)}
        self.assertIn(helper,SB.consumed_closure(files,[hook],[],G.PATH_RE))

@unittest.skipUnless(available(),'real ORFS image required')
class Packing(unittest.TestCase):
    def run_fixture(self,kind):
        with tempfile.TemporaryDirectory() as tmp:
            w=Path(tmp)
            (w/'top.v').write_text('module top(input ck,d,output [5:0] q);\n'+''.join(f'DFFHQNx1_ASAP7_75t_R r{i}(.CLK(ck),.D(d),.QN(q[{i}]));\n' for i in range(6))+'endmodule\n')
            script=r'''
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach l [glob $P/lib/NLDM/*RVT_TT*] {read_liberty $l}
read_verilog /w/top.v
link_design top
initialize_floorplan -die_area {0 0 40 40} -core_area {2 2 38 38} -site asap7sc7p5t
set b [ord::get_db_block];set row [lindex [$b getRows] 0];set box [$row getBBox]
set x [$box xMin];set y [$box yMin]
set obstacle [odb::dbInst_create $b [[ord::get_db] findMaster TAPCELL_ASAP7_75t_R] untouched_obstacle]
$obstacle setLocation 15000 15000;$obstacle setPlacementStatus FIRM
set names {};set before {};set k 0
foreach i [$b getInsts] {
 if {[$i getName] eq "untouched_obstacle"} continue
 $i setLocation 15000 15000
 if {"KIND" eq "unchanged"} {$i setLocation [expr {$x+int(($k*2500+1000)/[$row getSpacing])*[$row getSpacing]}] $y}
 $i setOrient [$row getOrient];$i setPlacementStatus FIRM
 lappend names [$i getName];dict set before [$i getName] [list [$i getLocation] [$i getOrient] [$i getPlacementStatus]]
 incr k
}
proc signature {b} {
 set result {}
 foreach i [$b getInsts] {
  set pins {}
  foreach it [$i getITerms] {set n [$it getNet];lappend pins [list [[$it getMTerm] getName] [expr {$n eq "NULL"?"NULL":[$n getName]}]]}
  lappend result [list [$i getName] [[$i getMaster] getName] [lsort $pins]]
 }
 return [lsort $result]
}
set original [signature $b]
set obstacle_before [list [$obstacle getLocation] [$obstacle getOrient] [$obstacle getPlacementStatus]]
if {"KIND" eq "infeasible"} {set c [$b getCoreArea];odb::dbBlockage_create $b [$c xMin] [$c yMin] [$c xMax] [$c yMax]}
if {"KIND" eq "unknown"} {lappend names unowned_missing}
source /src/physical/common_flow/anchor_row_packing.tcl
ot_anchor_pack::repair $b $names
if {$original ne [signature $b]} {error "netlist changed"}
if {$obstacle_before ne [list [$obstacle getLocation] [$obstacle getOrient] [$obstacle getPlacementStatus]]} {error "unowned obstacle moved"}
foreach name $names {
 set i [$b findInst $name];set ib [$i getBBox];set legal 0
 foreach r [$b getRows] {
  set rb [$r getBBox];lassign [$i getLocation] ix iy
  if {$iy==[$rb yMin] && $ix>=[$rb xMin] && [$ib xMax]<=[$rb xMax] && ($ix-[$rb xMin])%[$r getSpacing]==0 && [$i getOrient] eq [$r getOrient]} {set legal 1;break}
 }
 if {!$legal || [$i getPlacementStatus] ne "FIRM"} {error "illegal owned site/status $name"}
 if {"KIND" eq "unchanged" && [dict get $before $name] ne [list [$i getLocation] [$i getOrient] [$i getPlacementStatus]]} {error "already legal anchor moved"}
 foreach other [$b getInsts] {
  if {$other eq $i} continue
  set ob [$other getBBox]
  if {[$ib xMin]<[$ob xMax] && [$ib xMax]>[$ob xMin] && [$ib yMin]<[$ob yMax] && [$ib yMax]>[$ob yMin]} {error "positive overlap $name/[$other getName]"}
 }
}
puts ANCHOR_PACK_FIXTURE_PASS
'''.replace('KIND',kind)
            (w/'run.tcl').write_text(script)
            p=subprocess.run(['docker','run','--rm','-v',f'{ROOT}:/src:ro','-v',f'{w}:/w',IMAGE,OR,'-no_init','-exit','/w/run.tcl'],capture_output=True,text=True,timeout=90)
            return p.returncode,p.stdout+p.stderr
    def test_legal_pack_preserves_circuit_and_obstacles(self):
        rc,out=self.run_fixture('overlap');self.assertEqual(rc,0,out[-4000:]);self.assertIn('legally packed 6',out)
    def test_already_legal_anchors_unchanged(self):
        rc,out=self.run_fixture('unchanged');self.assertEqual(rc,0,out[-4000:]);self.assertIn('already nonoverlapping; unchanged',out)
    def test_infeasible_site_and_unknown_record_refused(self):
        for kind,why in [('infeasible','no legal free row site'),('unknown','not one actual FIRM standard cell')]:
            rc,out=self.run_fixture(kind);self.assertNotEqual(rc,0,out[-4000:]);self.assertIn(why,out)
if __name__=='__main__':unittest.main()
