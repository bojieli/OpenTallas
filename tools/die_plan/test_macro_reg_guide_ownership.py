"""Bank128 regression: 512 FIRM pin captures must not invalidate a loose guide."""
import json
import subprocess
import unittest
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[2]/"physical/die_plan/hbm_arch_cores/macro_reg_guide.tcl"
if not SCRIPT.exists():SCRIPT=Path(__file__).with_name("macro_reg_guide.tcl")


def run(statuses,prefixes):
    pre=r'''
namespace eval ord {}
proc ord::get_db_block {} {return blk}
proc ord::get_db_tech {} {return tech}
proc tech {cmd args} {return 1000}
proc blk {cmd args} {return $::cells}
proc master {cmd args} {switch $cmd {isCore {return 1} getWidth {return 100} getHeight {return 270}}}
proc bbox {cmd args} {switch $cmd {xMin - yMin {return 0} xMax - yMax {return 1}}}
proc inst {id cmd args} {switch $cmd {getMaster {return master} getPlacementStatus {return [lindex $::statuses $id]} getName {return [lindex $::names $id]} getBBox {return bbox}}}
namespace eval odb {}
proc odb::dbRegion_create {args} {return region}
proc odb::dbBox_create {args} {}
proc odb::dbGroup_create {args} {return group}
proc region {args} {}
proc group {cmd args} {if {$cmd eq "addInst"} {lappend ::added [lindex $args 0]}}
set added {}
'''
    pre+='set statuses {'+' '.join(statuses)+'}\n'
    pre+='set names {'+' '.join('wface_data'+str(i) if i<2 else 'wface_we'+str(i) for i in range(len(statuses)))+'}\n'
    pre+='set cells {'+' '.join('i'+str(i) for i in range(len(statuses)))+'}\n'
    for i in range(len(statuses)):pre+=f'interp alias {{}} i{i} {{}} inst {i}\n'
    pre+='set ot_mrg_spec {north {'+' '.join(prefixes)+'} 0 0 100 100}\n'
    pre+='if {[catch {source {'+str(SCRIPT)+'}} msg]} {puts stderr $msg; exit 1}\nputs "ADDED=$added"\n'
    return subprocess.run(['tclsh'],input=pre,text=True,capture_output=True)


class Ownership(unittest.TestCase):
    def test_already_firm_group_is_retained_and_missing_pattern_still_fails(self):
        p=run(['FIRM','FIXED'],['wface_data'])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('2 matched cells already FIRM/FIXED',p.stdout)
        self.assertIn('ADDED=',p.stdout)
        p=run(['FIRM','FIXED'],['does_not_exist'])
        self.assertNotEqual(p.returncode,0)
        self.assertIn('no instance under',p.stderr)

    def test_mixed_group_guides_only_movable_controls(self):
        p=run(['FIRM','FIXED','PLACED'],['wface_data','wface_we'])
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('ADDED=i2',p.stdout)


if __name__=='__main__':unittest.main()
