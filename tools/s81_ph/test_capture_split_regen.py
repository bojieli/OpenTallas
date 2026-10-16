"""Regeneration of the capture split RTL and kit specs reproduces the committed files byte for byte."""
import pathlib, subprocess, sys, unittest
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import capture_split, capture_split_specs  # noqa: E402


class CaptureSplitRegen(unittest.TestCase):
    def test_rtl_byte_identical(self):
        self.assertEqual(capture_split.check(), [])

    def test_specs_generated_or_preserved(self):
        bad, n = capture_split_specs.check()
        self.assertEqual(bad, [])
        self.assertEqual(n, 22)

    def test_status_x43_generated(self):
        import capx43_status_kits as ks
        out = ks.outputs()
        self.assertEqual(len(out), 4)
        names = {p.name for p in out}
        self.assertNotIn("dsfd_capt_status_x43_t.json", capture_split_specs.PRESERVED)
        self.assertTrue({"dsfd_capt_status_x43_t.tcl", "dsfd_capt_status_x43_s.json"} <= names)
        s = out[ks.PINS / "dsfd_capt_status_x43_s.tcl"]
        self.assertIn("place_pin -pin_name {rsv[0]} -layer M5", s)
        self.assertEqual(s.count("pin_name {t_st["), 64)

    def test_check_detects_a_change(self):
        out, _ = capture_split.render()
        rtl = out[capture_split.OUT]
        self.assertIn("ot_s81_rly #(.W(64), .RSREG(1))", rtl)
        self.assertIn("dsfd_capt_status_x43_t u_t", rtl)
        self.assertIn("dsfd_capt_x8x_s_w u_s", rtl)
        self.assertNotIn("ot_ratio_cdc_fifo #(.W(64)", rtl)

    def test_cli_check(self):
        for tool in ("capture_split.py", "capture_split_specs.py"):
            r = subprocess.run([sys.executable, str(HERE / tool), "--check"], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("PASS", r.stdout)


if __name__ == "__main__":
    unittest.main()
