"""Contract-confusion negatives for the default-OFF partition tolerance resolver."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from partition_clock_binding import resolve


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.k = Path(self.tmp.name)
        (self.k / "plan_pins.json").write_text('{"pins":[]}\n')
        self.freeze = dict(schema="opentallas.partition_freeze.v1", die="s81_head", type="hd_test",
                           outline_um=[100, 200], pins_file="plan_pins.json",
                           pins_sha256=hashlib.sha256((self.k / "plan_pins.json").read_bytes()).hexdigest(),
                           reset_contract=dict(module="ot_hd_test", edges=64))
        self.budget = dict(schema="opentallas.die_plan.partition_budget.v1", die="s81_head", type="hd_test",
                           module="ot_hd_test", outline_um=[100, 200],
                           clock=dict(insertion_ps=450, insertion_ff_ps=342, insertion_tol_ps=40))
        self.binding = dict(type="hd_test", insertion_ps=dict(tt=450, ff=342), insertion_tol_ps=40)
        (self.k / "config.mk").write_text("export DESIGN_NICKNAME = dp_hd_test\nexport DESIGN_NAME = ot_hd_test\n")
        self.write()

    def write(self):
        for name, d in (("freeze.json", self.freeze), ("budget.json", self.budget), ("clock_binding.json", self.binding)):
            (self.k / name).write_text(json.dumps(d))
        self.sha = hashlib.sha256((self.k / "freeze.json").read_bytes()).hexdigest()
        self.budget_sha = hashlib.sha256((self.k / "budget.json").read_bytes()).hexdigest()
        self.binding_sha = hashlib.sha256((self.k / "clock_binding.json").read_bytes()).hexdigest()

    def call(self, **kw):
        a = dict(kit=self.k, corner="TT", expected_type="hd_test", expected_freeze_sha256=self.sha, observed_bound=450,
                 expected_budget_sha256=self.budget_sha, expected_binding_sha256=self.binding_sha)
        a.update(kw)
        return resolve(**a)

    def test_declared_both_corners_and_stricter_environment(self):
        self.assertEqual(self.call()["effective_tol_ps"], 40)
        self.assertEqual(self.call(corner="FF", observed_bound=342)["effective_tol_ps"], 40)
        self.assertEqual(self.call(tolerance_env=15)["effective_tol_ps"], 15)
        self.assertFalse(self.call()["authorizes_resume"])

    def test_wrong_caller_or_binding_type_refused(self):
        with self.assertRaises(ValueError): self.call(expected_type="hd_other")
        self.binding["type"] = "hd_other"; self.write()
        with self.assertRaises(ValueError): self.call()

    def test_wrong_corner_bound_or_conflicting_budget_refused(self):
        with self.assertRaises(ValueError): self.call(observed_bound=342)
        self.budget["clock"]["insertion_ff_ps"] = 350; self.write()
        with self.assertRaises(ValueError): self.call()  # other corner must also match

    def test_nonfinite_bool_and_nonpositive_refused(self):
        for bad in (float("nan"), float("inf"), True, 0, -1):
            with self.subTest(bad=bad):
                self.binding["insertion_tol_ps"] = bad; self.write()
                with self.assertRaises(ValueError): self.call()

    def test_environment_cannot_loosen_contract(self):
        for bad in (40.1, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError): self.call(tolerance_env=bad)

    def test_frozen_identity_and_pin_drift_refused(self):
        with self.assertRaises(ValueError): self.call(expected_freeze_sha256="0" * 64)
        (self.k / "plan_pins.json").write_text('{"different":true}')
        with self.assertRaises(ValueError): self.call()

    def test_core_context_or_ss_refused(self):
        with self.assertRaises(ValueError): self.call(corner="SS")
        (self.k / "master_slice.json").write_text('{}')
        with self.assertRaises(ValueError): self.call()

    def test_config_die_outline_module_or_tolerance_conflicts_refused(self):
        for section, key, bad in ((self.budget, "die", "other"), (self.budget, "outline_um", [101, 200]),
                                  (self.budget, "module", "ot_other"),
                                  (self.budget["clock"], "insertion_tol_ps", 41)):
            old = section[key];section[key] = bad;self.write()
            with self.assertRaises(ValueError): self.call()
            section[key] = old;self.write()
        (self.k / "config.mk").write_text("export DESIGN_NICKNAME = dp_other\nexport DESIGN_NAME = ot_hd_test\n")
        with self.assertRaises(ValueError): self.call()

    def test_consistent_wider_budget_and_binding_cannot_replace_pinned_context(self):
        old_budget, old_binding = self.budget_sha, self.binding_sha
        self.budget["clock"]["insertion_tol_ps"] = 100
        self.binding["insertion_tol_ps"] = 100
        self.write()  # freeze/pins/type still identical and both metadata files agree
        with self.assertRaises(ValueError):
            self.call(expected_budget_sha256=old_budget, expected_binding_sha256=old_binding)
        with self.assertRaises(ValueError): self.call(expected_budget_sha256=old_budget)
        with self.assertRaises(ValueError): self.call(expected_binding_sha256=old_binding)

    def test_consumer_default_off_preserves_legacy_tolerance(self):
        import tkinter
        t = tkinter.Tcl()
        source = Path(__file__).with_name("postcts_gate.tcl").read_text()
        a = source.index("# SOURCE-ONLY opt-in proposal:")
        b = source.index("set bound $ot_pg_bound", a)
        t.eval("set ::env(OT_POSTCTS_BINDING_TOL) 0; set ot_pg_tol 20")
        t.eval(source[a:b])  # no exec/context/native OpenROAD command is reached
        self.assertEqual(t.getvar("ot_pg_tol"), "20")
        t.eval("set ::env(OT_POSTCTS_BINDING_TOL) invalid")
        with self.assertRaises(tkinter.TclError): t.eval(source[a:b])

    def test_native_residual_reclassification_is_only_proposed(self):
        tol = self.call()["effective_tol_ps"]
        self.assertLess(28.03, tol)  # turn would fit declared40
        self.assertGreater(48.15, tol)  # shim still fails; no blanket PASS
        self.assertEqual(self.call()["policy"], "unchanged; resolve tolerance only")


if __name__ == "__main__":
    unittest.main()
