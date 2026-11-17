"""The physical mechanism is also exercised on a real t34 ODB (see result record)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("s81_vpw_bank", Path(__file__).with_name("s81_vpw_bank.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class InstallTest(unittest.TestCase):
    def test_install_and_refuse_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            k = Path(td)
            (k / "face_flops.tcl").write_text("face\n")
            (k / "clock_taps.tcl").write_text("clock\n")
            mod.install(k)
            self.assertTrue((k / "face_flops.tcl").read_text().startswith("face\n"))
            self.assertTrue((k / "clock_taps.tcl").read_text().endswith("clock\n"))
            self.assertEqual((k / "s81_vpw_bank.tcl").read_bytes(), Path(mod.__file__).with_suffix(".tcl").read_bytes())
            before = {p.name: p.read_bytes() for p in k.iterdir()}
            with self.assertRaises(ValueError):
                mod.install(k)
            self.assertEqual(before, {p.name: p.read_bytes() for p in k.iterdir()})

    def test_missing_hook_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            k = Path(td)
            (k / "face_flops.tcl").write_text("face\n")
            with self.assertRaises(ValueError):
                mod.install(k)
            self.assertEqual([p.name for p in k.iterdir()], ["face_flops.tcl"])


if __name__ == "__main__":
    unittest.main()
