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

    def test_fit_is_bound_to_its_lib_and_stale_files_go(self):
        with tempfile.TemporaryDirectory() as d:
            import hashlib
            m, k = load(d), self.kit(d)
            m.fit(k)
            h = (k / ".busfit" / "m_tt.lib").read_text().splitlines()[0]
            self.assertIn(hashlib.sha256(LIB.encode()).hexdigest(), h)
            (k / ".busfit" / "old_tt.lib").write_text("stale")
            (k / "macros" / "m.lef").write_text("MACRO other\nEND other\n")
            self.assertEqual(m.fit(k), {})
            self.assertFalse((k / ".busfit").exists())

    def test_readers_check_the_sha(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("sha256sum", load(d).PROC)
        self.assertIn("a stale one would read old timing arcs", (HERE / "signoff.py").read_text())

    def test_agreeing_lib_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            m = load(d)
            f, _ = m.fit_text(LIB, m.lef_macros(LEF)["m"])
            k = self.kit(d, lib=f)
            self.assertEqual(m.fit(k), {})
            self.assertFalse((k / ".busfit").exists())

    def test_patch_is_idempotent_and_guards_yosys(self):
        with tempfile.TemporaryDirectory() as d:
            m = load(d)
            p = Path(d) / "util.tcl"
            p.write_text("proc log_cmd { cmd args } {}\n")
            m.patch(p)
            once = p.read_text()
            m.patch(p)
            self.assertEqual(p.read_text(), once)
            self.assertIn("::sta::worst_slack_cmd", once)
            self.assertIn("*.odb", once)

    def test_eco_runners_carry_the_fit(self):
        self.assertIn("busfit_prep", (HERE / "post_route_drv" / "prd_run.sh").read_text())
        e = (HERE / "eco_loop.py").read_text()
        self.assertIn("OT_BUSFIT_PY", e)
        self.assertIn("kwrs_busfit.py patch", e)

    def test_runner_fingerprint_without_busfit_is_equal(self):
        import kit_resume as KR
        g = re.search(r'RUN_KIT = r"""(.*?)"""', SRC, re.S).group(1)
        n = KR.runner_norm(g)
        self.assertNotIn("kwrs_busfit", n)
        self.assertNotIn("KWRS_F", n)
        self.assertNotIn("KWRS_M", n)


if __name__ == "__main__":
    unittest.main()


def test_existing_timed_members_repair_narrow_eps_and_fd_ranges(tmp_path):
    m = load(tmp_path)
    # STA1294 class: the timed member text already exists, so missing-pin fitting
    # formerly did nothing even though the bus declaration hid those members.
    pins = {**{f'eps[{i}]': 'output' for i in range(32)},
            **{f'f_d[{i}]': 'output' for i in range(512)}}
    members = {name: f'pin("{name}") {{ direction : output; timing() {{ related_pin : "ck"; cell_rise (t) {{ values ("0.173"); }} }} }}' for name in pins}
    lib = 'library(l) {\n' + m.type_text('eps_t', 23, 0) + m.type_text('fd_t', 447, 0)
    lib += 'cell(m) { pin("ck") { direction : input; clock : true; }\n'
    for bus, typ in [('eps', 'eps_t'), ('f_d', 'fd_t')]:
        lib += f'bus({bus}) {{ bus_type : {typ}; direction : output;\n'
        lib += '\n'.join(text for name, text in members.items() if name.startswith(bus + '[')) + '\n}\n'
    lib += '}\n}\n'
    fixed, added = m.fit_text(lib, pins)
    assert added == [] and fixed != lib
    for bus, upper in [('eps', 31), ('f_d', 511)]:
        group = m.group(fixed, 'bus', bus)
        assert m.bus_range(fixed, group.end(), m.close_of(fixed, group.end() - 1))[1:] == (upper, 0)
    assert fixed.count('timing()') == lib.count('timing()')
    assert all(text in fixed for text in members.values())
    assert m.fit_text(fixed, pins) == (fixed, [])
    kit = tmp_path / 'kit'
    (kit / 'macros').mkdir(parents=True)
    (kit / 'macros/m.lef').write_text('MACRO m\n' + ''.join(f'PIN {n}\n DIRECTION OUTPUT ;\nEND {n}\n' for n in pins) + 'END m\n')
    (kit / 'macros/m_tt.lib').write_text(lib)
    report = m.fit(kit)
    assert report['m_tt.lib']['added'] == []
    assert (kit / '.busfit/m_tt.lib').is_file()
    # A valid library is byte-identical and produces no shadow lib.
    (kit / 'macros/m_tt.lib').write_text(fixed)
    assert m.fit(kit) == {} and not (kit / '.busfit').exists()
