import unittest
from view_export import export_corner_sequence, VerdictError

class CornerOwnership(unittest.TestCase):
    def test_all_actual_liberty_corners_keep_constraints(self):
        setup=['read_db /work/6_final.odb','set ::ot_ce_corner tt','read_sdc /work/6_final.sdc','read_spef /work/6_final.spef','set_propagated_clock [all_clocks]','read_sdc /work/w18_extra.sdc','read_sdc /meas/io_ref_routed.sdc']
        for c in ('tt','ss','ff'):
            with self.subTest(c=c):
                result=export_corner_sequence(setup,c)
                self.assertEqual(result[1],f'set ::ot_ce_corner {c}')
                self.assertEqual(result[:1]+result[2:],setup[:1]+setup[2:])

    def test_legacy_sequence_gets_explicit_selector_before_constraints(self):
        seq=['read_db /work/f.odb','read_sdc /work/f.sdc']
        self.assertEqual(export_corner_sequence(seq,'ff'),[seq[0],'set ::ot_ce_corner ff',seq[1]])

    def test_braced_selector(self):
        self.assertEqual(export_corner_sequence(['set ::ot_ce_corner {ss}'],'tt'),['set ::ot_ce_corner tt'])

    def test_unknown_selector_refused(self):
        with self.assertRaises(VerdictError):
            export_corner_sequence(['set ::ot_ce_corner $unverified'],'tt')

    def test_unknown_corner_refused(self):
        with self.assertRaises(VerdictError):
            export_corner_sequence(['read_db /work/f.odb'],'unknown')

if __name__=='__main__':unittest.main()
