import importlib.util
from pathlib import Path
import unittest

s = importlib.util.spec_from_file_location("form", Path(__file__).with_name("serdes_form_params.py"))
form = importlib.util.module_from_spec(s)
s.loader.exec_module(form)


class CapturedForm(unittest.TestCase):
    source = "ot_pdie_serdes_col #(.HOLD_EDGES(64), .RST_TREE(0), .TXL(2)) u_core (.clk(clk));"

    def test_captured_zero_is_replaced_and_other_parameters_survive(self):
        out, actual = form.apply(self.source)
        self.assertIn(".RST_TREE(1)", out)
        self.assertIn(".HOLD_EDGES(64)", out)
        self.assertIn(".TXL(2)", out)
        self.assertEqual(actual["RST_TREE"], {"captured": 0, "actual": 1})
        self.assertEqual(form.apply(out)[0], out)

    def test_explicit_mutant_or_different_form_is_protected(self):
        with self.assertRaises(ValueError):
            form.apply(self.source.replace("RST_TREE(0)", "RST_TREE(2)"))

    def test_wrong_instance_or_missing_capture_fails(self):
        for text in (self.source.replace("u_core", "u_peer"), self.source.replace(".RST_TREE(0), ", ""), self.source*2):
            with self.assertRaises(ValueError):
                form.apply(text)


if __name__ == "__main__":
    unittest.main()
