#!/usr/bin/env python3
"""STA-0171 signed-child parameter serialization class (native_bb.py).  Runs under pytest or `python3 -I` directly."""
from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import native_bb  # noqa: E402

VMR = """// Signed MIF0 metadata only.
(* blackbox *) module qfd_dv_s8x_vmr #(parameter integer MUT = 0, parameter integer MIF = 0) (
    input wire ck, output wire [255:0] q, input wire ft_ck_i, output wire ft_ck_o);
endmodule
"""
CRH = "(* blackbox *) module qfd_dv_s8_crh_rp1 #(parameter integer MIF = 0) (input wire ck, output wire fault);\nendmodule\n"
ROM = 'module ot_rom_64x32_m2 (clk, q);\n  parameter VIAMAP = "", INSTANCE = "";\n  input clk; output q;\nendmodule\n'
PLAIN = "module ot_sram_1r1w_bb (input clk, output q);\nendmodule\n"
Z32 = "0" * 32


def bits(v, w=32):
    return format(v % (1 << w), f"0{w}b")


class SignedParamSerialize(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        d = Path(self.td.name)
        self.hdr = []
        for name, text in (("qfd_dv_s8x_vmr_bb.v", VMR), ("qfd_dv_s8_crh_rp1_bb.v", CRH),
                           ("ot_rom_64x32_m2_bb.v", ROM), ("ot_sram_1r1w_bb.v", PLAIN)):
            (d / name).write_text(text)
            self.hdr.append(d / name)
        self.hp = native_bb.headers_params(self.hdr)

    def tearDown(self):
        self.td.cleanup()

    def test_header_defaults_parsed(self):
        self.assertEqual(self.hp["qfd_dv_s8x_vmr"], {"MUT": ("int", 0), "MIF": ("int", 0)})
        self.assertEqual(self.hp["ot_rom_64x32_m2"], {"VIAMAP": ("str", ""), "INSTANCE": ("str", "")})
        self.assertEqual(self.hp["ot_sram_1r1w_bb"], {})
        # only numeric-default masters are scanned; ROM content labels stay with the existing ROM rule
        self.assertEqual(native_bb.numeric_types(self.hdr), "qfd_dv_s8_crh_rp1 {MIF} qfd_dv_s8x_vmr {MIF MUT}")
        self.assertEqual(native_bb.parse_value("32'sd0"), ("int", 0))
        self.assertEqual(native_bb.parse_value("4'sb1111"), ("int", -1))
        self.assertEqual(native_bb.parse_value("1'bx")[0], "unknown")

    def test_header_survey_never_raises(self):
        d = Path(self.td.name)
        (d / "bad_bb.v").write_text("module broken #(parameter A = 0 (input a);\nendmodule\n")
        (d / "dup_bb.v").write_text("(* blackbox *) module qfd_dv_s8_crh_rp1 #(parameter integer MIF = 1) (input ck);\nendmodule\n")
        hp = native_bb.headers_params(self.hdr + [d / "bad_bb.v", d / "dup_bb.v", d / "missing_bb.v"])
        self.assertEqual(hp["qfd_dv_s8_crh_rp1"]["MIF"][0], "unknown")
        _, _, err = native_bb.plan([("qfd_dv_s8_crh_rp1", "top", "u_cl", "MIF", "1", Z32)], hp)
        self.assertEqual(len(err), 1)

    def test_strip_on_default(self):
        rows = [("qfd_dv_s8x_vmr", "top", "u_suvm.u_va", "MIF", "1", Z32),
                ("qfd_dv_s8x_vmr", "top", "u_suvm.u_va", "MUT", "1", "0"),       # 1-bit literal 1'b0 == 0
                ("qfd_dv_s8_crh_rp1", "top", "u_cl", "MIF", "1", Z32)]
        ys, rep, err = native_bb.plan(rows, self.hp)
        self.assertEqual(err, [])
        self.assertEqual(ys, ["setparam -unset MIF t:qfd_dv_s8_crh_rp1", "setparam -unset MIF t:qfd_dv_s8x_vmr",
                              "setparam -unset MUT t:qfd_dv_s8x_vmr"])
        self.assertEqual(rep["stripped"][0]["cells"], ["top/u_cl"])

    def test_error_on_non_default(self):
        for v in (bits(1), bits(-1), "x" * 32, "1" + Z32):
            rows = [("qfd_dv_s8x_vmr", "top", "u_va", "MIF", "1", Z32),
                    ("qfd_dv_s8x_vmr", "top", "u_vb", "MIF", "1", v)]
            ys, rep, err = native_bb.plan(rows, self.hp)
            self.assertEqual(len(err), 1, v)
            self.assertIn("top/u_vb", err[0])
        # a parameter whose header default is not a verifiable number is never dropped
        hp = native_bb.headers_params(self.hdr)
        hp["qfd_dv_s8_crh_rp1"]["MIF"] = ("unknown", "W*2")
        _, _, err = native_bb.plan([("qfd_dv_s8_crh_rp1", "top", "u_cl", "MIF", "1", Z32)], hp)
        self.assertEqual(len(err), 1)

    def test_main_plan_hard_error_writes_no_script(self):
        d = Path(self.td.name)
        (d / "c.tsv").write_text("qfd_dv_s8x_vmr\ttop\tu_va\tMIF\t1\t" + bits(1) + "\n")
        rc = native_bb.main_plan(d / "c.tsv", d / "s.ys", d / "s.json", self.hdr)
        self.assertEqual(rc, 2)
        self.assertFalse((d / "s.ys").exists())
        self.assertEqual(len(json.loads((d / "s.json").read_text())["errors"]), 1)

    def test_no_change_for_unparameterised(self):
        rows = [("qfd_dv_s8x_vmr", "top", "u_va", "MIF", "0", ""), ("qfd_dv_s8x_vmr", "top", "u_va", "MUT", "0", "")]
        ys, rep, err = native_bb.plan(rows, self.hp)
        self.assertEqual((ys, rep["stripped"], err), ([], [], []))
        d = Path(self.td.name)
        (d / "c.tsv").write_text("")
        self.assertEqual(native_bb.main_plan(d / "c.tsv", d / "s.ys", d / "s.json", self.hdr), 0)
        self.assertEqual((d / "s.ys").read_text(), "")

    def test_physical_patch_after_metadata_json_and_idempotent(self):
        d = Path(self.td.name)
        t = d / "synth.tcl"
        t.write_text("check -assert\n" + native_bb.PHYS_OLD + "\n")
        native_bb.patch_physical(t, self_path="/work/native_bb.py")
        txt = t.read_text()
        self.assertLess(txt.index("write_json"), txt.index(native_bb.SIGNED_PARAM_MARK))
        self.assertLess(txt.index(native_bb.SIGNED_PARAM_MARK), txt.index(native_bb.PHYS_OLD))
        self.assertIn("python3 -I /work/native_bb.py plan", txt)
        native_bb.patch_physical(t, self_path="/work/native_bb.py")
        self.assertEqual(t.read_text(), txt)
        t.write_text("unknown\n")
        with self.assertRaises(ValueError):
            native_bb.patch_physical(t)


if __name__ == "__main__":
    unittest.main(verbosity=2)
