"""Clock insertion keeps genuine late paths and subtracts the tagged source edge."""
import pathlib
import subprocess
import unittest

HELPER = pathlib.Path(__file__).resolve().parents[2] / 'physical/common_flow/clock_family.tcl'

class ClockWireEdges(unittest.TestCase):
    def test_tagged_edges_and_late_insertion(self):
        script = r'''
namespace eval sta {proc time_sta_ui {v} {return $v}}
proc get_full_name {x} {return $x}
proc clock {method} {return {0 416.5}}
proc pin {method} {return vertex}
proc vertex {method transition mode} {set ::remaining 1; return paths}
proc paths {method} {
  switch $method {
    has_next {return $::remaining}
    next {set ::remaining 0; return path}
    finish {return}
  }
}
proc path {method} {
  if {$method eq "tag"} {return [list path tc $::marker clock $::source {(clock prop)}]}
  return $::arrival
}
proc check {transition marker source arrival expected} {
  set ::marker $marker; set ::source $source; set ::arrival $arrival
  set got [ot_cf_wire_transition pin clock $transition tc]
  if {abs($got-$expected)>0.00001} {error "got $got expected $expected"}
}
check rise ^max ^ 604.36 604.36
check rise ^max v 1020.86 604.36
check fall vmax v 648.67 232.17
check fall vmax ^ 232.17 232.17
puts PASS
'''
        proc = subprocess.run(['tclsh'], input=f'source {{{HELPER}}}\n'+script,
                              text=True, capture_output=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), 'PASS', proc.stderr)
        self.assertFalse(proc.stderr, proc.stderr)

if __name__ == '__main__':
    unittest.main()
