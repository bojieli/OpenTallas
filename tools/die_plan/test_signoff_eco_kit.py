"""KW-FIX-17 11-05: sign-off library config of post-route ECO iteration dirs (AUTO-RESIGN ECO-dir class)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import signoff as S  # noqa: E402


class EcoKit(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.kit = Path(self.td.name) / "kit"
        self.eco = self.kit / "eco_20261105_015748_1651180" / "i3"
        self.eco.mkdir(parents=True)
        (self.kit / "macros").mkdir()
        (self.kit / "macros" / "m_tt.lib").write_text("library(m) {}\n")
        (self.kit / "config.mk").write_text("export ADDITIONAL_LIBS = /work/macros/m_tt.lib\n")

    def tearDown(self):
        self.td.cleanup()

    def test_normal_kit_unchanged(self):
        self.assertEqual(S.kit_config(self.kit), (self.kit / "config.mk", self.kit))

    def test_eco_dir_uses_config_eco_on_parent_root(self):
        (self.eco / "config_eco.mk").write_text("export ADDITIONAL_LIBS = /work/macros/m_tt.lib\noverride export CORNERS = bc\n")
        self.assertEqual(S.kit_config(self.eco), (self.eco / "config_eco.mk", self.kit))
        libs, miss = S.macro_libs(str(self.eco), "tt")
        self.assertEqual([str(x) for x in libs], [str(self.kit / "macros" / "m_tt.lib")])
        self.assertEqual(miss, [])

    def test_eco_dir_without_config_eco_falls_back_to_parent(self):
        self.assertEqual(S.kit_config(self.eco), (self.kit / "config.mk", self.kit))

    def test_unrelated_dir_without_config(self):
        d = Path(self.td.name) / "other"
        d.mkdir()
        self.assertEqual(S.kit_config(d), (None, d))
        self.assertEqual(S.macro_libs(str(d), "tt"), ([], []))

    def test_no_kit(self):
        self.assertEqual(S.kit_config(None), (None, None))

    # DS66-STA 11-05: kit context of a pruned ECO pass dir comes from the parent kit (t48 ff_ref_missing artefact)
    def _routed(self, d):
        b = d / "run" / "results" / "asap7" / "dp_x" / "base"
        b.mkdir(parents=True)
        for n in ("6_final.odb", "6_final.sdc", "6_final.spef", "6_final.v"):
            (b / n).write_text("x\n")
        return b

    def test_pruned_eco_dir_reads_parent_kit_context(self):
        for n in ("constraint.sdc", "sdc_lint.json", "pins.json"):
            (self.kit / n).write_text("{}\n")
        (self.eco / "config_eco.mk").write_text("export X = 1\n")
        d = S.discover(self._routed(self.eco), kit=self.eco)
        self.assertEqual(d["sdc"], str((self.kit / "constraint.sdc").resolve()))
        self.assertEqual(d["sdc_source"], "kit")
        self.assertEqual(d["sdc_lint_ctx"], str((self.kit / "sdc_lint.json").resolve()))
        self.assertEqual(d["pins"], str((self.kit / "pins.json").resolve()))
        self.assertEqual(d["kit_ctx_parent"], str(self.kit.resolve()))

    def test_eco_dir_own_context_wins(self):
        for n in ("constraint.sdc", "sdc_lint.json", "pins.json"):
            (self.kit / n).write_text("{}\n")
            (self.eco / n).write_text("{}\n")
        (self.eco / "config_eco.mk").write_text("export X = 1\n")
        d = S.discover(self._routed(self.eco), kit=self.eco)
        self.assertEqual(d["sdc"], str((self.eco / "constraint.sdc").resolve()))
        self.assertEqual(d["sdc_lint_ctx"], str((self.eco / "sdc_lint.json").resolve()))
        self.assertNotIn("kit_ctx_parent", d)

    def test_unrelated_dir_keeps_6_final_sdc(self):
        o = Path(self.td.name) / "other"
        o.mkdir()
        d = S.discover(self._routed(o), kit=o)
        self.assertEqual(d["sdc_source"], "6_final.sdc")
        self.assertIsNone(d["sdc_lint_ctx"])
        self.assertNotIn("kit_ctx_parent", d)


if __name__ == "__main__":
    unittest.main()
