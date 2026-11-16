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
    assert re.search(r"kit-rtl \{q\(plan\)\}.{0,300}--src-tree \{q\(src\)\}", w, re.S)


def test_gen_phys_records_the_kit_source_tree():
    g = (Path(B.__file__).parent / "gen_phys.py").read_text()
    assert "kit_rtl_paths.json" in g and "opentallas.kit_rtl_paths.v1" in g


def test_rebase_maps_old_tree_paths_into_the_kit_tree(tmp_path):
    old, new = tmp_path / "B6gsl" / "src", tmp_path / "kit" / "src"
    assert B.kit_rebase_path(old / "rtl" / "lib" / "x.sv", old, new) == str(new / "rtl" / "lib" / "x.sv")
    assert B.kit_rebase_path(str(tmp_path / "other" / "y.sv"), old, new) == str(tmp_path / "other" / "y.sv")
    assert B.kit_rebase_path("rtl/z.sv", old, new) == "rtl/z.sv"
