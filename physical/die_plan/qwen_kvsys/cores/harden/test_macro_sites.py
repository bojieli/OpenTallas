import subprocess
import unittest
from macro_sites import static_placement_tcl


class LiteralMacroNames(unittest.TestCase):
    def run_case(self, names, expected='m', planned='tile[0].ram', master='RAM'):
        setup='''namespace eval ord {proc get_db_block {} {return blk}}
proc bb {method} {return 0}
proc master {method} {if {$method eq "getType"} {return BLOCK};return RAM}
'''
        for i, name in enumerate(names):
            setup += f'''proc m{i} {{method args}} {{
  if {{$method eq "getName"}} {{return {{{name}}}}}
  if {{$method eq "getMaster"}} {{return master}}
  if {{$method eq "getBBox"}} {{return bb}}
  if {{$method eq "setPlacementStatus"}} {{puts PLACED_m{i}}}
}}
'''
        setup += 'set names {' + ' '.join('{' + n + '}' for n in names) + '}\n'
        setup += 'proc blk {method args} {global names;if {$method eq "getDbUnitsPerMicron"} {return 1000};if {$method eq "getInsts"} {set r {};for {set j 0} {$j < [llength $names]} {incr j} {lappend r m$j};return $r};set j [lsearch -exact $names [lindex $args 0]];if {$j < 0} {return NULL};return m$j}\n'
        code=static_placement_tcl([dict(inst=planned,master=master,x=4.32,y=8.64,orient='R0')])
        # Tcl stdin does not set a failure rc for an uncaught command; catch explicitly.
        setup+='if {[catch {\n'+code+'\n} err]} {puts stderr $err;exit 1}\n'
        return subprocess.run(['tclsh'],input=setup,text=True,capture_output=True)
    def test_exact(self):
        r=self.run_case(['tile[0].ram']);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('PLACED_m0',r.stdout)
    def test_escaped_brackets(self):
        r=self.run_case([r'tile\[0\].ram']);self.assertEqual(r.returncode,0,r.stderr)
    def test_ambiguous_normalized(self):
        r=self.run_case([r'tile\[0\].ram',r'tile\[0\].ram']);self.assertEqual(r.returncode,1);self.assertIn('2 literal bracket matches',r.stderr)
    def test_exact_wins(self):
        r=self.run_case(['tile[0].ram',r'tile\[0\].ram']);self.assertEqual(r.returncode,0,r.stderr);self.assertIn('PLACED_m0',r.stdout)
    def test_wrong_master(self):
        r=self.run_case([r'tile\[0\].ram'],master='OTHER');self.assertEqual(r.returncode,1);self.assertIn('wrong planned macro master',r.stderr)
    def test_missing(self):
        r=self.run_case(['other']);self.assertEqual(r.returncode,1);self.assertIn('0 literal bracket matches',r.stderr)


if __name__=='__main__':unittest.main()
