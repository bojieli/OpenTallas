#!/usr/bin/env python3
"""KW-FIX-5 kwrs_busfit (embedded in gen_phys RUN_KIT): fit and patch forms, and the stage-resume fingerprint stays equal."""
import importlib.util
import re
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
SRC = (HERE / "gen_phys.py").read_text()
BODY = re.search(r"<<'KWRS_BUSFIT'  # KWRS-BEGIN\n(.*?)KWRS_BUSFIT\n# KWRS-END", SRC, re.S).group(1)


def load(tmp):
    p = Path(tmp) / "kwrs_busfit.py"
    p.write_text(BODY)
    spec = importlib.util.spec_from_file_location("kwrs_busfit", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


LEF = """MACRO m
  PIN r0[0]
    DIRECTION INPUT ;
  END r0[0]
  PIN r0[1]
    DIRECTION INPUT ;
  END r0[1]
  PIN r0[2]
    DIRECTION INPUT ;
  END r0[2]
  PIN r0[3]
    DIRECTION INPUT ;
  END r0[3]
  PIN o[3]
    DIRECTION OUTPUT ;
  END o[3]
  PIN gone
    DIRECTION OUTPUT ;
  END gone
  PIN VDD
    DIRECTION INOUT ;
    USE POWER ;
  END VDD
  PIN ck
    DIRECTION INPUT ;
  END ck
END m
"""
LIB = """library (l) {
  type ("r0") {
    base_type : array;
    data_type : bit;
    bit_width : 2;
    bit_from : 3;
    bit_to : 2;
  }
  type ("o") {
    base_type : array;
    data_type : bit;
    bit_width : 3;
    bit_from : 2;
    bit_to : 0;
  }
  cell (m) {
    pin("ck") { direction : input; clock : true; }
    bus("r0") {
      bus_type : r0;
      direction : input;
      pin("r0[3]") { direction : input; }
      pin("r0[2]") { direction : input; }
    }
    bus("o") {
      bus_type : o;
      direction : output;
      pin("o[0]") { direction : output; timing() { related_pin : "ck"; } }
    }
  }
}
"""


class T(unittest.TestCase):
    def kit(self, tmp, lef=LEF, lib=LIB):
        k = Path(tmp) / "k"
        (k / "macros").mkdir(parents=True)
        (k / "macros" / "m.lef").write_text(lef)
        (k / "macros" / "m_tt.lib").write_text(lib)
        return k

    def test_fit_adds_only_missing_and_leaves_macros(self):
        with tempfile.TemporaryDirectory() as d:
            m, k = load(d), self.kit(d)
            r = m.fit(k)
            self.assertEqual(r["m_tt.lib"]["added"], ["gone", "o[3]", "r0[0]", "r0[1]"])
            self.assertEqual((k / "macros" / "m_tt.lib").read_text(), LIB)
            f = (k / ".busfit" / "m_tt.lib").read_text()
            self.assertEqual(f.count("{"), f.count("}"))
            self.assertEqual(m.present(f) >= {"r0[0]", "r0[1]", "r0[2]", "r0[3]", "o[3]", "gone", "ck"}, True)
            self.assertNotIn("VDD", f)
            for n in ("r0[0]", "o[3]", "gone"):
                g = re.search(r'pin\("%s"\) \{(.*?)\}' % re.escape(n), f, re.S).group(1)
                self.assertNotIn("timing", g)
            self.assertEqual(f.count("timing()"), LIB.count("timing()"))
            self.assertEqual(m.fit_text(f, m.lef_macros(LEF)["m"])[1], [])

    def test_agreeing_lib_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            m = load(d)
            f, _ = m.fit_text(LIB, m.lef_macros(LEF)["m"])
            k = self.kit(d, lib=f)
            self.assertEqual(m.fit(k), {})
            self.assertFalse((k / ".busfit").exists())

    def test_patch_is_idempotent_and_only_openroad_reader(self):
        with tempfile.TemporaryDirectory() as d:
            m = load(d)
            p = Path(d) / "read_liberty.tcl"
            p.write_text("log_cmd read_liberty -corner $corner $libFile\nlog_cmd read_liberty $libFile\n")
            m.patch(p)
            once = p.read_text()
            m.patch(p)
            self.assertEqual(p.read_text(), once)
            self.assertEqual(once.count("[ot_busfit $libFile]"), 2)
            self.assertIn("1_synth.odb", once)

    def test_runner_fingerprint_without_busfit_is_equal(self):
        import kit_resume as KR
        g = re.search(r'RUN_KIT = r"""(.*?)"""', SRC, re.S).group(1)
        n = KR.runner_norm(g)
        self.assertNotIn("kwrs_busfit", n)
        self.assertNotIn("KWRS_F", n)
        self.assertNotIn("KWRS_M", n)


if __name__ == "__main__":
    unittest.main()
