import unittest
from meas_resta import tt_setup_text, with_pf_macro_libs

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


class HardChildMacroLibs(unittest.TestCase):
    """PF-HARDCHILD-VERDICT (ROOT-CORNER 2026-10-19): a pre-fix w18 Tcl replay names its /src macro libs before read_db."""
    PDK = 'read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib'
    OLD = [PDK, 'read_liberty /src/physical/ref_tile/a/views/ot_a/ot_a_ss.lib',
           'read_liberty /src/physical/ref_tile/b/views/ot_b/ot_b_ss.lib', 'read_db /work/x/6_final.odb',
           'read_sdc /work/x/6_final.sdc']

    def test_old_tcl_gets_the_corner_sta_line_before_read_db(self):
        out = with_pf_macro_libs(self.OLD)
        line = ('set ::env(OT_PF_MACRO_LIBS) [list /src/physical/ref_tile/a/views/ot_a/ot_a_ss.lib '
                '/src/physical/ref_tile/b/views/ot_b/ot_b_ss.lib]')
        self.assertEqual(out, self.OLD[:3] + [line] + self.OLD[3:])
        # the TT swap renames the env line's libs with the read_liberty lines
        self.assertIn('ot_a_tt.lib /src/physical/ref_tile/b/views/ot_b/ot_b_tt.lib]', tt_setup_text("\n".join(out)))

    def test_matches_corner_sta_and_is_idempotent(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'w18'))
        import corner_sta
        new = corner_sta.script('ss', '/work/x', ['physical/ref_tile/a/views/ot_a', 'physical/ref_tile/b/views/ot_b'])
        want = next(l for l in new.splitlines() if 'OT_PF_MACRO_LIBS' in l)
        self.assertIn(want, with_pf_macro_libs(self.OLD))
        lines = new.splitlines()
        self.assertEqual(with_pf_macro_libs(lines), lines)            # a fixed Tcl is replayed unchanged

    def test_no_macro_tcl_unchanged(self):
        lines = [self.PDK, 'read_db /work/x/6_final.odb']
        self.assertEqual(with_pf_macro_libs(lines), lines)


if __name__=='__main__':unittest.main()
