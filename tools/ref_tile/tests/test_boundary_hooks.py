"""Execute the generated physical-stage hooks against a destructive IO reset.

The reset models io_plain/io_ref_skew assigning all ports to core_clk. Each
additional-domain hook must restore forwarded launch/capture clocks and retain
both max and min delays, including the CTS repair inside its wrapper.
"""
import pathlib
import subprocess
import sys
import unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import ref_tile as RT

class BoundaryHooks(unittest.TestCase):
    def test_every_physical_switch_restores_forwarded_domain(self):
        s={'kind':'tile', 'boundary_tcl':['boundary.tcl'], 'clock':'cts', 'recipe':1,
           'name':'test', 'pins':{}, 'route':{}, 'inhold':False, 'outhold':False}
        hooks=RT.gen_hooks(s,'physical/ref_tile/test')
        harness=r'''
proc clock_tree_synthesis {args} {}
proc reset_io {} {
  set ::launch core_clk; set ::capture core_clk
  set ::inmax 166.667; set ::inmin -50
  set ::outmax 166.667; set ::outmin -50
}
proc source {path} {
  switch -glob -- $path {
    */pre_cts_skew.tcl {
      rename clock_tree_synthesis ::qdm_cts_orig
      proc clock_tree_synthesis {args} { ::qdm_cts_orig {*}$args; reset_io }
    }
    */post_plain.tcl - */pre_ref_skew.tcl { reset_io }
    */boundary.tcl {
      set ::launch vw; set ::capture w_fi0
      set ::inmax 166.667; set ::inmin 0
      set ::outmax 316.667; set ::outmin 0
    }
    default {}
  }
}
reset_io
'''
        check=r'''
if {$launch ne "vw" || $capture ne "w_fi0" || $inmax != 166.667 || $inmin != 0 || $outmax != 316.667 || $outmin != 0} {
  error "forwarded boundary lost: $launch/$capture $inmax/$inmin $outmax/$outmin"
}
puts PASS
'''
        for name in ['pre_cts.tcl','post_cts.tcl','pre_grt.tcl','post_grt.tcl',
                     'pre_drt.tcl','post_drt.tcl','pre_fill.tcl','post_fill.tcl']:
            with self.subTest(stage=name):
                script=harness+hooks[name]+('\nclock_tree_synthesis\n' if name=='pre_cts.tcl' else '')+check
                run=subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
                self.assertEqual(run.stderr,'')
                self.assertIn('PASS',run.stdout)
    def test_legacy_without_extra_domains_has_no_cts_wrapper(self):
        s={'kind':'tile','clock':'cts','recipe':1,'name':'test','pins':{},'route':{},'inhold':False,'outhold':False}
        self.assertNotIn('ot_ref_cts_boundary_orig',RT.gen_hooks(s,'test')['pre_cts.tcl'])

if __name__=='__main__': unittest.main()
