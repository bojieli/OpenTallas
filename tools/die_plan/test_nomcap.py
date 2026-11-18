"""NOMCAP-1118 (OWNER r708): nominal input-pin load on clock buffer/inverter cells + sequential CLK pins."""
import gzip
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import nomcap

HERE = Path(__file__).resolve().parent

LIB = """library (x) {
  cell (BUFx24_ASAP7_75t_R) {
    pin (A) {
      capacitance : 1.0;
      rise_capacitance_range (0.9, 1.2);
      fall_capacitance_range (0.9, 1.2);
      direction : input;
    }
    pin (Y) {
      direction : output;
      rise_capacitance_range (0.1, 0.2);
    }
  }
  cell (INVx1_ASAP7_75t_R) {
    pin (A) {
      direction : input;
      rise_capacitance_range (0.4, 0.5);
    }
  }
}
"""
SEQ = """library (s) {
  cell (DFFHQNx1_ASAP7_75t_R) {
    pin (CLK) {
      direction : input;
      rise_capacitance_range (0.4, 0.5);
      fall_capacitance_range (0.4, 0.5);
    }
    pin (D) {
      direction : input;
      rise_capacitance_range (0.6, 0.7);
    }
  }
}
"""


class NomCap(unittest.TestCase):
    def test_repo_copies_match_manifest(self):
        self.assertEqual(nomcap.check(), [])
        man = nomcap.manifest()
        self.assertEqual(man["ruling"], "r708")
        self.assertEqual(len(man["libraries"]), 6)
        for r in man["libraries"]:
            for pin in r["pins"]:
                cell, p = pin.split("/")
                if r["kind"] == "SEQ":
                    self.assertEqual(p, "CLK")
                else:
                    self.assertIn(cell.rsplit("_ASAP7", 1)[0], nomcap.CLOCK_CELLS)

    def test_strip_scope(self):
        t, s = nomcap.strip_lib(LIB, "INVBUF")
        self.assertEqual(s, [("BUFx24_ASAP7_75t_R", "A", 2)])
        self.assertIn("rise_capacitance_range (0.4, 0.5)", t)        # data inverter keeps the range
        self.assertIn("rise_capacitance_range (0.1, 0.2)", t)        # output pin untouched
        self.assertIn("capacitance : 1.0", t)
        t, s = nomcap.strip_lib(SEQ, "SEQ")
        self.assertEqual(s, [("DFFHQNx1_ASAP7_75t_R", "CLK", 2)])
        self.assertIn("rise_capacitance_range (0.6, 0.7)", t)        # D pin keeps the range

    def test_copies_are_the_source_minus_ranges(self):
        for r in nomcap.manifest()["libraries"]:
            with gzip.open(nomcap.LIB_DIR / r["file"], "rt") as f:
                text = f.read()
            self.assertGreater(text.count("cell ("), 30)
            self.assertEqual(text.count("_capacitance_range") + r["removed_lines"] > r["removed_lines"], True)

    def test_map_paths_and_switch(self):
        stock = ["/x/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz", "/x/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz",
                 "/x/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib"]
        old = os.environ.get("OT_NOMCAP")
        try:
            os.environ["OT_NOMCAP"] = "1"
            m = nomcap.map_paths(stock)
            self.assertEqual(m[0], stock[0])
            self.assertEqual(m[1], str(nomcap.LIB_DIR / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz"))
            self.assertEqual(m[2], str(nomcap.LIB_DIR / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz"))
            os.environ["OT_NOMCAP"] = "0"
            self.assertEqual(nomcap.map_paths(stock), stock)
        finally:
            if old is None:
                os.environ.pop("OT_NOMCAP", None)
            else:
                os.environ["OT_NOMCAP"] = old

    def test_config_mk_lines(self):
        L = nomcap.config_mk_lines("/work/nomcap")
        for k in ("TC", "BC", "WC"):
            row = [x for x in L if x.startswith(f"export {k}_NLDM_LIB_FILES = ")]
            self.assertEqual(len(row), 1)
            self.assertIn("/work/nomcap/asap7sc7p5t_SEQ_RVT_", row[0])
            self.assertIn("/work/nomcap/asap7sc7p5t_INVBUF_RVT_", row[0])
            self.assertEqual(row[0].count("$(PLATFORM_DIR)/lib/NLDM/"), 3)

    @unittest.skipUnless(shutil.which("tclsh"), "tclsh")
    def test_tcl_selector_swaps_stock_files(self):
        sel = (HERE / "timing_libs.tcl").read_text()
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            (d / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz").write_text("x")
            (d / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz").write_text("x")
            files = ["/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib",
                     "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz",
                     "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz",
                     "/work/macros/m_tt.lib"]
            p = d / "t.tcl"
            p.write_text(sel + "\nputs [join [ot_lib_nomcap {" + " ".join(files) + "}] \\n]\n")
            env = dict(os.environ, OT_NOMCAP_DIR=str(d))
            out = subprocess.run(["tclsh", str(p)], text=True, capture_output=True, env=env).stdout.split()
            self.assertIn(str(d / "asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz"), out)
            self.assertIn(str(d / "asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz"), out)
            self.assertIn(files[2], out)
            self.assertIn(files[3], out)
            env["OT_NOMCAP"] = "0"
            out = subprocess.run(["tclsh", str(p)], text=True, capture_output=True, env=env).stdout.split()
            self.assertIn(files[0], out)
            env.pop("OT_NOMCAP"); env.pop("OT_NOMCAP_DIR")
            out = subprocess.run(["tclsh", str(p)], text=True, capture_output=True, env=env).stdout.split()
            self.assertIn(files[0], out)

    def test_signoff_mounts_copies(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("so_nomcap_t", HERE / "signoff.py")
        so = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(so)
        self.assertEqual(so.nomcap_dir(), nomcap.LIB_DIR.resolve())
        with tempfile.TemporaryDirectory() as td:
            r = Path(td) / "libraries.json"
            r.write_text(json.dumps({"libraries": [{"path": "/nomcap/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib.gz"}]}))
            self.assertEqual(so.nomcap_label(r), "nominal-r708")
            r.write_text(json.dumps({"libraries": [{"path": "/OpenROAD-flow-scripts/x.lib"}]}))
            self.assertEqual(so.nomcap_label(r), "range")


if __name__ == "__main__":
    unittest.main()
