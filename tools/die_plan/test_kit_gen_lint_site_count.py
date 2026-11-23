"""MACRO-SITES-GEN-1122 (COORD 20:1x): gen_lint fails closed when the KV static site file lists a different number of sites than
the elaborated design has instances of the master (2 sites for a 4-SRAM KV ectl q1/q2 core failed only at floorplan)."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "autopilot"))
import kit_gen_lint as GL  # noqa: E402

TCL = GL.KV_SITES_HEAD + """ from q1.json
set b [ord::get_db_block]
foreach {master sites} {sram_a {{15.552 13.26 MX} {15.552 127.404 R0}} sram_b {{1 2 R0}}} {
  set hit {}
}
"""


def kit(tmp, tcl):
    kd = tmp / "k"
    kd.mkdir()
    (kd / "config.mk").write_text("export DESIGN_NAME = top\nexport MACRO_PLACEMENT_TCL = /work/macro_place.tcl\n")
    (kd / "macro_place.tcl").write_text(tcl)
    return kd


def test_site_counts_parse(tmp_path):
    assert GL.kv_site_counts(kit(tmp_path, TCL)) == {"sram_a": 2, "sram_b": 1}


def test_count_mismatch_fails_closed(tmp_path):
    kd = kit(tmp_path, TCL)
    assert GL.macro_site_count(kd, {"sram_a": 2, "sram_b": 1}) == ([], True)
    errs, applies = GL.macro_site_count(kd, {"sram_a": 4, "sram_b": 1})
    assert applies and len(errs) == 1 and "sram_a: 2 static site(s)" in errs[0] and "4 instance(s)" in errs[0]
    errs, _ = GL.macro_site_count(kd, None)                       # not measured: fail closed
    assert errs and "not measured" in errs[0]


def test_other_placement_forms_are_na(tmp_path):
    kd = kit(tmp_path, "# hand placement\nplace_macro -macro_name u_s -location {1 2}\n")
    assert GL.kv_site_counts(kd) is None and GL.macro_site_count(kd, None) == ([], False)


def test_lint_tcl_counts_only_kv_site_masters():
    cfg = {"DESIGN_NAME": ["top"]}
    t = GL.lint_tcl(cfg, ["sram_a", "sram_b"])
    assert "flatten" in t and "foreach m {sram_a sram_b}" in t and "gen_lint_macros.tsv" in t and "@" not in t
    assert "gen_lint_macros.tsv" not in GL.lint_tcl(cfg) and "@MACRO_COUNT@" not in GL.lint_tcl(cfg)


def test_wave_classifies_site_count_as_plan():
    import kit_wave as KW
    cls, _ = KW.classify("gen_lint", "GEN_LINT FAIL issues 1\n  - GEN_LINT FAIL macro_site_count: sram_a: 2 static site(s) ...")
    assert cls == "PLAN"
