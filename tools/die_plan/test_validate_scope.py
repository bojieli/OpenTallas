"""KW-FIX-45 11-11: gen phys validates only the selected types' own errors (one invalid type elsewhere in the plan no
longer aborts every type's gen). QC 12:00 cut: slw_su_l1__clcc9d0155 'core chain ... enter hard macros' blocked ~15 types."""
import inspect
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402
import gen_rtl  # noqa: E402
import schema as S  # noqa: E402

ERRS = [
    "type slw_su_l1__clcc9d0155: core chain x_ctl_o u_lane4: 30 bit L routes enter hard macros ['u_lane5'] by > 0.5 um",
    "type sle_st_a_v2: clock edge y 5 outside outline",
    "port 'p1' defined twice",
    "type sle_hc1__cl22c1ff36: core chain geometry: boom",
]


class ScopeErrors(unittest.TestCase):
    def test_no_selection_is_whole_plan(self):
        self.assertEqual(S.scope_errors(ERRS, None), ERRS)
        self.assertEqual(S.scope_errors(ERRS, []), ERRS)

    def test_selected_type_does_not_see_other_types_errors(self):
        out = S.scope_errors(ERRS, ["sle_st_a_v2"])
        self.assertEqual(out, [ERRS[1], ERRS[2]])          # its own error + the die-level one; the bad su type is gone

    def test_clean_selected_type_still_sees_die_level_errors(self):
        self.assertEqual(S.scope_errors(ERRS, ["other_type"]), [ERRS[2]])

    def test_selected_bad_type_still_fails(self):
        out = S.scope_errors(ERRS, ["slw_su_l1__clcc9d0155", "sle_hc1__cl22c1ff36"])
        self.assertEqual(out, [ERRS[0], ERRS[2], ERRS[3]])

    def test_no_prefix_confusion(self):
        errs = ["type a: x", "type ab: y", "type a__b: z"]
        self.assertEqual(S.scope_errors(errs, ["a"]), ["type a: x"])
        self.assertEqual(S.scope_errors(errs, ["a__b"]), ["type a__b: z"])


class Wiring(unittest.TestCase):
    def test_write_rtl_scopes_validation(self):
        seen = []
        real_v, real_s = S.validate, S.scope_errors
        S.validate = lambda raw: ["die level boom"]            # the historic one-argument validate stays untouched
        S.scope_errors = lambda errs, types=None: (seen.append(types), errs)[1]
        try:
            for kw, want in (({"types": None, "validate_types": ["A"]}, ["A"]),
                             ({"types": ["B"], "validate_types": None}, ["B"]),
                             ({"types": None, "validate_types": None}, None)):
                with self.assertRaises(gen_rtl.GenError):
                    gen_rtl.write_rtl({}, "/nonexistent", **kw)
                self.assertEqual(seen[-1], want)
        finally:
            S.validate, S.scope_errors = real_v, real_s

    def test_gen_phys_passes_the_explicit_selection(self):
        src = inspect.getsource(gen_phys)
        self.assertIn("validate_types=types", src)
        self.assertIn("S.scope_errors(S.validate(raw), types)", src)
        self.assertIn("validate_types", inspect.signature(gen_rtl.write_rtl).parameters)


if __name__ == "__main__":
    unittest.main()
