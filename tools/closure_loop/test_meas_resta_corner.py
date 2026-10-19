import unittest
from meas_resta import tt_setup_text

class ExplicitCornerOwnership(unittest.TestCase):
    def test_raw_macro_metadata_tracks_actual_tt_libraries(self):
        old = 'read_liberty /x/ot_sram_ss.lib\nread_liberty /x/std_RVT_SS_nldm.lib\nset ::ot_ce_corner ss\nread_sdc /work/w18_extra.sdc\nputs "OT_CORNER ss"\n'
        new = tt_setup_text(old)
        self.assertIn('ot_sram_tt.lib',new)
        self.assertIn('std_RVT_TT_nldm.lib',new)
        self.assertLess(new.index('set ::ot_ce_corner tt'),new.index('read_sdc /work/w18_extra.sdc'))
        self.assertNotIn('set ::ot_ce_corner ss',new)
        self.assertIn('puts "OT_CORNER tt"',new)
        self.assertEqual(tt_setup_text(new),new)

    def test_braced_generated_setter(self):
        self.assertEqual(tt_setup_text('set ::ot_ce_corner {ss}\n'),'set ::ot_ce_corner tt\n')

    def test_hold_and_real_checks_unchanged(self):
        ff='set ::ot_ce_corner ff\nread_liberty /x/m_ff.lib\nset_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\nsource /src/strict_actual_scene_guard.tcl\n'
        self.assertEqual(tt_setup_text(ff),ff)

    def test_does_not_rewrite_unrecognized_corner_expression(self):
        text='set ::ot_ce_corner ss_suffix\nset ::ot_ce_corner $requested\n# set ::ot_ce_corner ss\n'
        self.assertEqual(tt_setup_text(text),text)

if __name__=='__main__':unittest.main()
