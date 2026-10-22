"""PF-HARDCHILD-EXPORT (S81-CAPC2 2026-10-19): the view-export session must carry the verdict's OT_PF_MACRO_LIBS line
(hard-child ETM clock insertion for the sign-off PINFLOP reference), or a wires-only parent can never reproduce its
verdict (s81sl_capc d8836674d: export FF -158.19 / TT -27.41 vs verdict +18.21 / +198.74)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import view_export as ve  # noqa: E402

RT = "/src/physical/ref_tile/a_rt/views/ot_a_rt/ot_a_rt"
TR = "/src/physical/ref_tile/a_tr/views/ot_a_tr/ot_a_tr"
MEAS = f"""read_lef /p/tech.lef
read_liberty {RT}_tt.lib
set ::env(OT_PF_MACRO_LIBS) [list {RT}_tt.lib {TR}_tt.lib]
read_db /work/base/6_final.odb
set ::ot_ce_corner tt
read_sdc /work/base/6_final.sdc
read_spef /work/base/6_final.spef
set_propagated_clock [all_clocks]
read_sdc /meas/app0_io_ref_routed.sdc
puts "OT_REGS [llength [all_registers]]"
puts "OT_CORNER tt"
"""


class PfHardChildExport(unittest.TestCase):
    def test_verdict_section_keeps_env_before_read_db(self):
        sec = ve.verdict_section(MEAS)
        self.assertTrue(ve.PF_ENV_RE.match(sec[0]))
        self.assertTrue(sec[1].startswith("read_db "))
        self.assertNotIn("read_liberty", " ".join(sec))

    def test_section_files_checks_the_etms(self):
        files = ve.section_files(ve.verdict_section(MEAS))
        self.assertIn(("pf_macro_lib", f"{RT}_tt.lib"), files)
        self.assertIn(("pf_macro_lib", f"{TR}_tt.lib"), files)

    def test_corner_retag(self):
        sec = ve.verdict_section(MEAS)
        self.assertEqual(ve.export_corner_sequence(sec, "tt")[0], sec[0])          # TT: the verdict line verbatim
        ff = ve.export_corner_sequence(sec, "ff")[0]
        self.assertEqual(ff, ve.pf_env_line([f"{RT}_ff.lib", f"{TR}_ff.lib"]))
        self.assertTrue(ve.PF_ENV_RE.match(ff))
        self.assertEqual(ve.export_corner_sequence(sec, "ff")[2], "set ::ot_ce_corner ff")

    def test_no_env_without_line(self):
        self.assertEqual(ve.section_files(["read_db /work/x.odb"]), [("read_db", "/work/x.odb")])

    def test_main_inserts_mv_line_when_missing(self):
        src = (Path(ve.__file__).read_text())
        self.assertIn('pf_env_line([f"/mv{i}/{n}_{c}.lib" for i, n in mv])', src)


if __name__ == "__main__":
    unittest.main()
