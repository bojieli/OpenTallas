"""leaf_affinity.tcl LOCAL SPLIT pass (DIE-S81-85 11-09): a zero-logic chain that spans the core is skip_far as one group,
so the split pass re-hangs its LOCAL sub-groups (flop bbox half-perimeter <= OT_LEAF_AFF_SPLIT_UM) onto one leaf each.

Fixture: one register chain a -> b -> c -> d (Q -> D, zero logic).  a, b sit at x = 0 / 2 um and c, d at x = 100 / 102 um,
so no single leaf lies within 30 um of every member (the whole group is skip_far, as for the S81 TX pin_q -> d0 .. d6
bit chains).  Leaves: L1 (driver at 0) holds a, L3 (driver at 3) holds b, L2 (driver at 100) holds c, L4 (driver at 101)
holds d; all four driven by buffers from one root net (same gating identity).
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).with_name('leaf_affinity.tcl')

FIXTURE = r'''
namespace eval ord {}
namespace eval sta {}
proc ord::get_db_block {} {return block}
proc ord::get_db_tech {} {return tech}
proc sta::sta_to_db_pin {p} {return $p}
proc all_registers {kind} {
 switch -- $kind {
  -clock_pins {return {aCK bCK cCK dCK}}
  -data_pins {return {aD bD cD dD}}
  -async_pins {return {}}
  default {error "unexpected register API: $kind"}
 }
}
proc get_property {p property} {if {$property ne "clocks"} {error "unexpected property"}; return clk}
proc get_full_name {p} {return $p}
proc estimate_parasitics {args} {incr ::estimated}
set estimated 0
set db [dict create]
proc obj {name args} { dict set ::db $name [dict create {*}$args] }
obj ff name DFFHQNx1 block 0
obj buf name BUFx24 block 0
foreach m {CK D Q A Y} { obj $m name $m }
# registers: name x  (DBU = 1 per um)
foreach {r x leaf data_in data_out} {a 0 L1 NULL nab b 2 L3 nab nbc c 100 L2 nbc ncd d 102 L4 ncd nout} {
 obj $r name $r master ff xy [list $x 0] terms [list ${r}CK ${r}D ${r}Q]
 obj ${r}CK inst $r net $leaf input 1 output 0 mterm CK
 obj ${r}D inst $r net $data_in input 1 output 0 mterm D
 obj ${r}Q inst $r net $data_out input 0 output 1 mterm Q
}
obj nab name nab type SIGNAL terms {aQ bD}
obj nbc name nbc type SIGNAL terms {bQ cD}
obj ncd name ncd type SIGNAL terms {cQ dD}
obj nout name nout type SIGNAL terms {dQ}
# leaves: driver x, sinks
foreach {l x sink} {L1 0 aCK L3 3 bCK L2 100 cCK L4 101 dCK} {
 obj drv$l name drv$l master buf xy [list $x 0] terms [list drv${l}A drv${l}Y]
 obj drv${l}A inst drv$l net root input 1 output 0 mterm A
 obj drv${l}Y inst drv$l net $l input 0 output 1 mterm Y
 obj $l name $l type CLOCK terms [list drv${l}Y $sink]
}
obj root name root type CLOCK terms {drvL1A drvL2A drvL3A drvL4A}
proc dispatch {self method args} {
 global db
 switch -- $method {
  getDbUnitsPerMicron {return 1}
  findNet {return [lindex $args 0]}
  getInst {return [dict get $db $self inst]}
  getMaster {return [dict get $db $self master]}
  getName {return [dict get $db $self name]}
  isBlock {return [dict get $db $self block]}
  getLocation {return [dict get $db $self xy]}
  getITerms {return [dict get $db $self terms]}
  getNet {return [dict get $db $self net]}
  getMTerm {return [dict get $db $self mterm]}
  getSigType {return [dict get $db $self type]}
  isInputSignal {return [dict get $db $self input]}
  isOutputSignal {return [dict get $db $self output]}
  disconnect {dict set db $self net NULL}
  connect {dict set db $self net [lindex $args 0]}
  default {error "unexpected DB method $self $method"}
 }
}
foreach o [concat [dict keys $db] {block tech NULL}] {interp alias {} $o {} dispatch $o}
proc run_hook {path} { source $path }
run_hook [lindex $argv 0]
puts "LEAVES a=[dict get $db aCK net] b=[dict get $db bCK net] c=[dict get $db cCK net] d=[dict get $db dCK net] estimated=$estimated"
'''


@unittest.skipUnless(shutil.which('tclsh'), 'tclsh unavailable')
class LocalSplit(unittest.TestCase):
    def run_fixture(self, source, env=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'hook.tcl').write_text(source)
            pre = ''.join(f'set ::env({k}) {v}\n' for k, v in (env or {}).items())
            (path / 'fixture.tcl').write_text(pre + FIXTURE)
            r = subprocess.run(['tclsh', str(path / 'fixture.tcl'), str(path / 'hook.tcl')], text=True, capture_output=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            return r.stdout

    @staticmethod
    def leaves(out):
        line = next(l for l in out.splitlines() if l.startswith('LEAVES'))
        return dict(kv.split('=') for kv in line.split()[1:5])

    def test_whole_chain_is_skip_far(self):
        out = self.run_fixture(SOURCE.read_text())
        self.assertIn('pairs 3 groups 1 cross_leaf_before 3 cross_leaf_after 3 groups_moved 0', out)
        self.assertIn('skip_far 1', out)

    def test_default_split_rehangs_local_subgroups(self):
        out = self.run_fixture(SOURCE.read_text())
        lv = self.leaves(out)
        self.assertEqual(lv['a'], lv['b'])          # left pair on one leaf
        self.assertEqual(lv['c'], lv['d'])          # right pair on one leaf
        self.assertNotEqual(lv['b'], lv['c'])       # the 98 um cut stays as CTS built it
        self.assertIn('OT_LEAF_AFF_SPLIT span_um 30 groups 1 subgroups 2 moved 2', out)
        self.assertIn('cross_leaf_after 1 ', out.split('OT_LEAF_AFF_SPLIT', 1)[1])
        self.assertIn('estimated=1', out)

    def test_split_off_keeps_cts_leaves(self):
        out = self.run_fixture(SOURCE.read_text(), {'OT_LEAF_AFF_SPLIT_UM': 0})
        self.assertEqual(self.leaves(out), {'a': 'L1', 'b': 'L3', 'c': 'L2', 'd': 'L4'})
        self.assertNotIn('OT_LEAF_AFF_SPLIT', out)

    def test_report_only_counts_without_moving(self):
        out = self.run_fixture(SOURCE.read_text(), {'OT_LEAF_AFF_REPORT_ONLY': 1})
        self.assertEqual(self.leaves(out), {'a': 'L1', 'b': 'L3', 'c': 'L2', 'd': 'L4'})
        self.assertIn('moved 2', out)

    def test_span_limit_is_respected(self):
        # 1 um span: no two chain flops (2 um apart) may merge, so no sub-group of two exists and nothing moves
        out = self.run_fixture(SOURCE.read_text(), {'OT_LEAF_AFF_SPLIT_UM': 1})
        self.assertEqual(self.leaves(out), {'a': 'L1', 'b': 'L3', 'c': 'L2', 'd': 'L4'})
        self.assertIn('subgroups 0 moved 0', out)

    def test_leaf_cap_still_applies_to_subgroups(self):
        # cap = largest CTS leaf fanout (1) + slack 0 = 1: a second sink may not join any leaf
        out = self.run_fixture(SOURCE.read_text(), {'OT_LEAF_AFF_SLACK': 0})
        self.assertEqual(self.leaves(out), {'a': 'L1', 'b': 'L3', 'c': 'L2', 'd': 'L4'})
        self.assertIn('cap 2', out)

    def test_missing_split_mutant_moves_nothing(self):
        src = SOURCE.read_text()
        guard = 'if {$la_split_um > 0 && [dict size $la_redo]} {'
        self.assertEqual(src.count(guard), 1)
        out = self.run_fixture(src.replace(guard, 'if {0} {'))
        self.assertEqual(self.leaves(out), {'a': 'L1', 'b': 'L3', 'c': 'L2', 'd': 'L4'})

    def test_missing_span_check_mutant_merges_across_the_core(self):
        src = SOURCE.read_text()
        check = '      if {($m2 - $m0) + ($m3 - $m1) > $la_s_lim} continue\n'
        self.assertEqual(src.count(check), 1)
        out = self.run_fixture(src.replace(check, ''))
        # one 4-member sub-group again fails the 30 um radius: the far skip comes back and nothing moves
        self.assertEqual(self.leaves(out), {'a': 'L1', 'b': 'L3', 'c': 'L2', 'd': 'L4'})
        self.assertIn('subgroups 1 moved 0', out)


if __name__ == '__main__':
    unittest.main()
