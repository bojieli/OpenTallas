"""Real PG layer generation without importing the heavy kit generator."""
import ast
import tempfile
import unittest
from pathlib import Path
import re

SRC = Path(__file__).resolve().parents[2] / "physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py"
TREE = ast.parse(SRC.read_text())
NAMES = {"PDN", "PDN_MACRO", "macro_pdn", "pg_top_pdn"}
BODY = [n for n in TREE.body if (isinstance(n, ast.FunctionDef) and n.name in NAMES) or
        (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in NAMES for t in n.targets))]
G = dict(Path=Path, re=re)
exec(compile(ast.Module(body=BODY,type_ignores=[]),str(SRC),"exec"),G)

class PGInterface(unittest.TestCase):
    def test_default_bytes(self):
        for pg in (None,"M5"):
            self.assertEqual(G["pg_top_pdn"](G["PDN"],None,pg), (G["PDN"],None))

    def test_m6_has_actual_pins_stripes_and_vias(self):
        p,i = G["pg_top_pdn"](G["PDN"]+G["PDN_MACRO"],None,"M6","M6")
        self.assertIn("-pins {M6}",p)
        self.assertNotIn("-pins {M5}",p)
        self.assertIn("add_pdn_stripe -grid {top} -layer {M6}",p)
        self.assertIn("add_pdn_connect -grid {top} -layers {M5 M6}",p)
        self.assertEqual(i["parent_landing_layer"],"M7")

    def test_existing_native_child_bridge_reused(self):
        with tempfile.TemporaryDirectory() as t:
            Path(t,"leaf.lef").write_text("PIN VDD\n LAYER M5 ;\nEND VDD\nPIN VSS\n LAYER M5 ;\nEND VSS\n")
            p,i=G["macro_pdn"]({"leaf":{}},t,"M6")
            p,i=G["pg_top_pdn"](p,i,"M6","M6")
            self.assertEqual(p.count("add_pdn_stripe -grid {top} -layer {M6}"),1)
            self.assertEqual(p.count("add_pdn_connect -grid {top} -layers {M5 M6}"),1)
            self.assertEqual(i["masters_by_pg_pin_layer"],{"M5":["leaf"]})

    def test_missing_reservation_refused(self):
        with self.assertRaisesRegex(ValueError,"obs_max"):
            G["pg_top_pdn"](G["PDN"],None,"M6","M5")

if __name__ == "__main__":
    unittest.main()
