"""New native CTS intake requires executable current SDCs, not a policy marker."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pre_route_gate as G
import ref_tile as RT
from test_multiple_cts_roots import spec as multiple_spec
from test_tile_hybrid_raw_entries import spec as hybrid_spec


class NativeCtsSdc(unittest.TestCase):
    def kit(self, kd, spec):
        texts = {
            "clock.sdc": RT.gen_sdc(spec, 770.0),
            "clock_entry.sdc": "set ::ot_ce_require_wire 1\n" + RT.clock_entry_constraints.generate(spec, RT.ROOT),
            "signoff.sdc": RT.gen_signoff(spec, "*", "none_*"),
        }
        for name, text in texts.items():
            (kd / name).write_text(text)
        return texts

    def test_current_multiple_and_hybrid_are_admitted(self):
        for spec in (multiple_spec(), hybrid_spec()):
            with self.subTest(mode=spec["clock"]), tempfile.TemporaryDirectory() as d:
                self.kit(Path(d), spec)
                self.assertEqual(G.stale_native_cts_sdcs(Path(d), spec), [])

    def test_each_old_baked_sdc_is_refused(self):
        spec = multiple_spec()
        for name in ("clock.sdc", "clock_entry.sdc", "signoff.sdc"):
            with self.subTest(sdc=name), tempfile.TemporaryDirectory() as d:
                kd = Path(d); texts = self.kit(kd, spec)
                text = texts[name]
                start = text.index("  # Before CTS, a standard-cell root")
                end = text.index("  set sources {}; set names {}", start)
                (kd / name).write_text(text[:start] + text[end:])
                self.assertEqual(G.stale_native_cts_sdcs(kd, spec), [name])

    def test_markers_and_tampered_executable_policy_do_not_pass(self):
        mutations = {
            "commented_operation": lambda t: t.replace("      unset_propagated_clock $clock", "      # unset_propagated_clock $clock"),
            "no_op": lambda t: t.replace("      unset_propagated_clock $clock", "      set ignored $clock"),
            "wrong_stage": lambda t: t.replace("&& $::ot_ref_pre_cts &&", "&& !$::ot_ref_pre_cts &&"),
            "raw_roots_ideal": lambda t: t.replace("foreach name $::ot_ce_cts_roots", "foreach name $::ot_ce_ports"),
            "later_repropagation": lambda t: t + "\nset_propagated_clock [get_clocks ot_entry_*]\n",
            "disabled_call": lambda t: t.replace("ot_ce_apply\n", "# ot_ce_apply\n"),
            "stage_flag": lambda t: t.replace("set ::ot_ref_pre_cts 1", "set ::ot_ref_pre_cts 0"),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name), tempfile.TemporaryDirectory() as d:
                kd=Path(d); texts=self.kit(kd, multiple_spec())
                altered=mutate(texts["clock.sdc"])
                self.assertNotEqual(altered, texts["clock.sdc"])
                self.assertIn("PRE_CTS_IDEAL_CTS_ROOT", altered)
                (kd / "clock.sdc").write_text(altered)
                self.assertEqual(G.stale_native_cts_sdcs(kd, multiple_spec()), ["clock.sdc"])

    def test_missing_stage_sdc_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(set(G.stale_native_cts_sdcs(Path(d), multiple_spec())),
                             {"clock.sdc", "clock_entry.sdc", "signoff.sdc"})

    def test_ordinary_single_root_and_legacy_parent_are_exempt(self):
        # VM landingr4/seqr3/x34r8/x43cb2 use ordinary single-root SDCs;
        # exact 4af regeneration was byte-identical (receipt d437a9c0a).
        for spec in ({"kind":"tile", "clock":"cts"},
                     {"kind":"cluster", "clock":"hybrid_entries"},
                     {"kind":"cluster", "clock":"entries"}):
            with self.subTest(spec=spec), tempfile.TemporaryDirectory() as d:
                (Path(d)/"clock.sdc").write_text("create_clock -name core_clk -period 770 [get_ports ck]\n")
                self.assertEqual(G.stale_native_cts_sdcs(Path(d), spec), [])

    def test_local_gate_surfaces_actionable_failure(self):
        spec = multiple_spec()
        with tempfile.TemporaryDirectory() as d:
            kd=Path(d); self.kit(kd, spec)
            (kd/"clock.sdc").write_text("# OT_ENTRIES PRE_CTS_IDEAL_CTS_ROOT\n")
            gate=G.Gate()
            with patch.object(RT, "load_spec", return_value=spec), patch.object(RT, "gen", return_value={"findings":[]}):
                with self.assertRaises(FileNotFoundError):
                    G.check_kit(gate, kd, None)
            finding=next(i for i in gate.items if i["check"]=="native_cts_sdc")
            self.assertEqual(finding["severity"], "FAIL")
            self.assertIn("source-bound --cts", finding["fix"])


if __name__ == "__main__":
    unittest.main()
