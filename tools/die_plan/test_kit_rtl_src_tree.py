"""GENBUG (COORD r107): kit-rtl resolves against the kit's own source tree; kit_gen_lint rejects a kit_rtl.f path outside it.
Failing case before: B6gsl kit-rtl listed run/b/B6gsl/src/rtl/common/ot_dp_clk_landing.sv (3 LOCAL hits) while the kit's src_rel2 copy
had 7 -> GEN_LINT failed on the LOCAL defparam; S81-LEAF-T14 patched 35 kit_rtl.f entries by hand."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind as B  # noqa: E402
import kit_gen_lint as GL  # noqa: E402


def _kit(tmp, src, files, bind_out=None):
    kd = tmp / "gen"; kd.mkdir(exist_ok=True)
    fl = tmp / "rtl" / "kit_rtl.f"; fl.parent.mkdir(exist_ok=True); fl.write_text("\n".join(map(str, files)) + "\n")
    (fl.parent / "kit_rtl.json").write_text(json.dumps(dict(bind_out=str(bind_out or tmp / "out"))))
    (kd / "kit_rtl_paths.json").write_text(json.dumps(dict(src_tree=str(src), filelist=str(fl), files=[str(f) for f in files])))
    return kd


def test_filelist_outside_helper(tmp_path):
    a, b = tmp_path / "srcA", tmp_path / "srcB"
    for d in (a, b):
        (d / "rtl").mkdir(parents=True); (d / "rtl" / "x.sv").write_text("module x; endmodule\n")
    assert B.kit_filelist_outside([a / "rtl" / "x.sv"], [a]) == []
    assert B.kit_filelist_outside([a / "rtl" / "x.sv", b / "rtl" / "x.sv"], [a]) == [str((b / "rtl" / "x.sv").resolve())]


def test_lint_rejects_path_outside_kit_src(tmp_path):
    src, stale = tmp_path / "kit_src", tmp_path / "B6gsl_src"
    for d in (src, stale):
        (d / "rtl").mkdir(parents=True); (d / "rtl" / "ot_dp_clk_landing.sv").write_text("module ot_dp_clk_landing; endmodule\n")
    (tmp_path / "out").mkdir(); (tmp_path / "out" / "bind_cells.sv").write_text("module bc; endmodule\n")
    good = _kit(tmp_path, src, [tmp_path / "rtl" / "w.sv", src / "rtl" / "ot_dp_clk_landing.sv", tmp_path / "out" / "bind_cells.sv"])
    assert GL.kit_rtl_paths(good) == ([], True)
    bad = _kit(tmp_path, src, [tmp_path / "rtl" / "w.sv", stale / "rtl" / "ot_dp_clk_landing.sv"])
    errs, applies = GL.kit_rtl_paths(bad)
    assert applies and len(errs) == 1 and "B6gsl_src" in errs[0] and "outside the kit source tree" in errs[0]


def test_lint_na_without_record(tmp_path):
    assert GL.kit_rtl_paths(tmp_path) == ([], False)


def test_kit_rtl_cli_has_src_tree_and_wave_passes_it():
    t = Path(B.__file__).read_text()
    assert '"--src-tree"' in t and "OT_KIT_SRC_TREE" in t and "src_tree=str(base) if src_tree else None" in t
    w = (Path(B.__file__).resolve().parents[1] / "autopilot" / "kit_wave.py").read_text()
    assert re.search(r"kit-rtl \{q\(plan\)\}.{0,500}--src-tree \{q\(src\)\}", w, re.S)


def test_gen_phys_records_the_kit_source_tree():
    g = (Path(B.__file__).parent / "gen_phys.py").read_text()
    assert "kit_rtl_paths.json" in g and "opentallas.kit_rtl_paths.v1" in g


def test_rebase_maps_old_tree_paths_into_the_kit_tree(tmp_path):
    old, new = tmp_path / "B6gsl" / "src", tmp_path / "kit" / "src"
    assert B.kit_rebase_path(old / "rtl" / "lib" / "x.sv", old, new) == str(new / "rtl" / "lib" / "x.sv")
    assert B.kit_rebase_path(str(tmp_path / "other" / "y.sv"), old, new) == str(tmp_path / "other" / "y.sv")
    assert B.kit_rebase_path("rtl/z.sv", old, new) == "rtl/z.sv"


def _tree(root, rels, txt="module m; endmodule\n"):
    for r in rels:
        f = root / r; f.parent.mkdir(parents=True, exist_ok=True); f.write_text(txt)
    return root


def test_rebase_staged_copy_of_the_recorded_base(tmp_path):
    """KITRTL-PATHS 11-16: kit_store rewrites bind.f to kit-store/snaps/<id>/root/<abs> but keeps asbuilt base byte-identical;
    t61 listed snaps/b0a3../root/.../B6gF2s4tapfix1/src/rtl/common/ot_dp_clk_landing_ca.sv while base = .../B6gF2s4tapfix1/src."""
    old = tmp_path / "run" / "b" / "B6gF2s4tapfix1" / "src"
    new = _tree(tmp_path / "kw45" / "src_d4", ["rtl/common/ot_dp_clk_landing_ca.sv"])
    staged = tmp_path / "kit-store" / "snaps" / ("b0a3" * 10) / "root" / str(old).lstrip("/") / "rtl/common/ot_dp_clk_landing_ca.sv"
    _tree(staged.parent, [staged.name])
    assert B.kit_staged_original(staged) == old / "rtl/common/ot_dp_clk_landing_ca.sv"
    assert B.kit_rebase_path(str(staged), old, new) == str(new / "rtl/common/ot_dp_clk_landing_ca.sv")


def test_rebase_foreign_source_tree_into_the_kit_tree(tmp_path):
    """the bind of record (tapfix1) reused B6gF2s4's as-built netlist, so asbuilt_sources.json lib (-> bind.f) names
    run/b/B6gF2s4/src: those map by their repository-relative part when the kit tree has the file; a staged copy too."""
    old = tmp_path / "run" / "b" / "B6gF2s4tapfix1" / "src"
    other = _tree(tmp_path / "run" / "b" / "B6gF2s4" / "src", ["rtl/hdc/ot_hdc_delay.sv", "physical/die_plan/s81/bind/x.sv",
                                                               "rtl/only_there.sv"])
    new = _tree(tmp_path / "kw45" / "src_d4", ["rtl/hdc/ot_hdc_delay.sv", "physical/die_plan/s81/bind/x.sv"])
    moved = {}
    for rel in ("rtl/hdc/ot_hdc_delay.sv", "physical/die_plan/s81/bind/x.sv"):
        assert B.kit_rebase_path(str(other / rel), old, new, moved=moved) == str(new / rel)
    staged = tmp_path / "kit-store" / "snaps" / "abc123" / "root" / str(other).lstrip("/") / "rtl/hdc/ot_hdc_delay.sv"
    _tree(staged.parent, [staged.name])
    assert B.kit_rebase_path(str(staged), old, new, moved=moved) == str(new / "rtl/hdc/ot_hdc_delay.sv")
    assert moved[str(staged)] == str(new / "rtl/hdc/ot_hdc_delay.sv") and len(moved) == 3
    # a file the kit tree lacks stays where it is, so the outside-the-kit-tree check still fails it
    assert B.kit_rebase_path(str(other / "rtl/only_there.sv"), old, new) == str(other / "rtl/only_there.sv")
    assert B.kit_filelist_outside([other / "rtl/only_there.sv"], [new]) == [str((other / "rtl/only_there.sv").resolve())]
    # no repository top dir in the path: unchanged
    odd = _tree(tmp_path / "romq_rtl", ["a.sv"]) / "a.sv"
    assert B.kit_rebase_path(str(odd), old, new) == str(odd)


def test_rebase_never_moves_bind_out_or_kit_files(tmp_path):
    old = tmp_path / "B6gF2s4tapfix1" / "src"
    out = _tree(tmp_path / "B6gF2s4tapfix1" / "out", ["rtl/bind_cells.sv"])
    kd = _tree(tmp_path / "kit", ["rtl/w.sv"])
    new = _tree(tmp_path / "src_d4", ["rtl/bind_cells.sv", "rtl/w.sv"])
    staged_out = tmp_path / "kit-store" / "snaps" / "ff00" / "root" / str(out).lstrip("/")
    _tree(staged_out, ["rtl/bind_cells.sv"])
    for p in (out / "rtl/bind_cells.sv", kd / "rtl/w.sv", staged_out / "rtl/bind_cells.sv"):
        assert B.kit_rebase_path(str(p), old, new, keep=(out, kd)) == str(p)
    assert B.kit_rebase_path(str(staged_out / "rtl/bind_cells.sv"), old, new, keep=(staged_out, kd)) == \
        str(staged_out / "rtl/bind_cells.sv")


def test_moved_rows_record_bytes(tmp_path):
    other = _tree(tmp_path / "other" / "src", ["rtl/a.sv", "rtl/b.sv"])
    new = _tree(tmp_path / "new", ["rtl/a.sv"])
    _tree(new, ["rtl/b.sv"], "module changed; endmodule\n")
    moved = {str(other / "rtl/a.sv"): str(new / "rtl/a.sv"), str(other / "rtl/b.sv"): str(new / "rtl/b.sv"),
             str(other / "rtl/c.sv"): str(new / "rtl/c_unused.sv")}
    rows = B.kit_src_moved_rows(moved, [new / "rtl/a.sv", new / "rtl/b.sv"])
    assert [(Path(r["kit"]).name, r["same_bytes"]) for r in rows] == [("a.sv", True), ("b.sv", False)]


def test_kit_rtl_rebases_with_keep_and_records_foreign_moves():
    t = Path(B.__file__).read_text()
    assert "kit_rebase_path(p, old_base, st, keep=(out, kd), moved=src_moved)" in t
    assert '"src_rebased_foreign": src_moved' in t


def test_outside_error_carries_flow_class_marker():
    """S81-FAILS-1118: the bind's outside-the-kit-tree refusal names its class so the wave never files it UNCLASSIFIED"""
    src = Path(B.__file__).read_text()
    assert re.search(r'OT_CLASS: flow kit-rtl .*outside the kit source tree', src)
