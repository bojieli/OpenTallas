"""QC-VERIFY-GAPS (QC s26 / baseline verify lint, 768 / 804 errors): the lint closure resolved a module with several
definitions without looking at its instantiators.  ot_qwen_rom_tile_nk (NK view, a0_core/nk_vr7n) sets
.IRCK/.NKP/.LQR on ot_qwen_rom_tile_w12 and the lint read the rtl/hdc copy, which declares none of them (64
PINNOTFOUND); the NL tile needs the a0_rc15 copy (IDLE_UCK), so one partition holding both (cbx_q10) cannot be one
Verilator run.  The lint closure now applies the bind kit closure's KITPARAM rule (a definition must declare every
parameter its instantiators set by name) and lint_split lints such a partition once per compatible leaf group."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E  # noqa: E402
import bind_verify as V  # noqa: E402


def _tree(tmp_path):
    rtl = tmp_path / "rtl"
    for d, body in (("aa_hdc", "module w (input wire clk);\nendmodule\n"),
                    ("nk", "module w #(parameter integer A = 0) (input wire clk);\nendmodule\n"),
                    ("nl", "module w #(parameter integer B = 0) (input wire clk);\nendmodule\n")):
        (rtl / d).mkdir(parents=True)
        (rtl / d / "w.sv").write_text(body)
    (rtl / "nk" / "leaf_a.sv").write_text("module leaf_a (input wire clk);\n  w #(.A(1)) u_w (.clk(clk));\nendmodule\n")
    (rtl / "nl" / "leaf_b.sv").write_text("module leaf_b (input wire clk);\n  w #(.B(1)) u_w (.clk(clk));\nendmodule\n")
    (rtl / "nl" / "leaf_c.sv").write_text("module leaf_c (input wire clk);\n  w u_w (.clk(clk));\nendmodule\n")
    ab0 = dict(rtl_roots=["rtl"], files=[])
    rep = dict(extra_lib=[], files=[])
    idx = E.module_index(ab0["rtl_roots"], ab0["files"], tmp_path)
    return ab0, rep, idx


def rel(tmp_path, files):
    return {Path(f).relative_to(tmp_path).as_posix() for f in files}


def test_lint_closure_picks_the_definition_its_instantiator_can_use(tmp_path):
    ab0, rep, idx = _tree(tmp_path)
    old, _ = E.closure(["leaf_a"], idx, [])
    assert "rtl/aa_hdc/w.sv" in rel(tmp_path, old)          # the old pick: no parameter A (Verilator PINNOTFOUND)
    LS = V.LintSources(ab0, tmp_path, rep, idx, [])
    files, missing = LS.closure(["leaf_a"])
    assert missing == [] and rel(tmp_path, files) == {"rtl/nk/leaf_a.sv", "rtl/nk/w.sv"} and not LS.conflicts
    files, _ = LS.closure(["leaf_b"])
    assert rel(tmp_path, files) == {"rtl/nl/leaf_b.sv", "rtl/nl/w.sv"}
    # no named parameter: the pick is unchanged
    files, _ = LS.closure(["leaf_c"])
    assert rel(tmp_path, files) == rel(tmp_path, E.closure(["leaf_c"], idx, [])[0])


def test_conflicting_leaves_are_grouped(tmp_path):
    ab0, rep, idx = _tree(tmp_path)
    LS = V.LintSources(ab0, tmp_path, rep, idx, [])
    LS.closure(["leaf_a", "leaf_b"])
    assert set(LS.conflicts) == {"w"}
    assert LS.leaf_groups(["leaf_a", "leaf_b"]) == [["leaf_a"], ["leaf_b"]]


def test_lint_split_runs_each_leaf_group_with_the_others_stubbed(tmp_path, monkeypatch):
    ab0, rep, idx = _tree(tmp_path)
    out = tmp_path / "out"
    (out / "rtl").mkdir(parents=True)
    part = out / "rtl" / "part.sv"
    part.write_text("module part (input wire clk);\n  leaf_a u_a (.clk(clk));\n  leaf_b u_b (.clk(clk));\nendmodule\n")
    top = out / "rtl" / "die_bound_top.sv"
    top.write_text("module die_bound_top (input wire clk);\n  part u_p (.clk(clk));\nendmodule\n")
    rep["files"] = [str(part), str(top)]
    LS = V.LintSources(ab0, tmp_path, rep, idx, [])
    seen = {}

    def fake_lint(d, name, files, defines=(), waive=(), incs=()):
        seen[Path(d).name] = (name, [Path(f).name if not str(f).startswith(str(tmp_path / "rtl")) else
                                     Path(f).relative_to(tmp_path).as_posix() for f in files])
        return dict(ran=True, errors=0, warnings=0, first_errors=[], waived=[])
    monkeypatch.setattr(V, "lint", fake_lint)
    lib = [str(tmp_path / "rtl/nk/leaf_a.sv"), str(tmp_path / "rtl/nl/leaf_b.sv")]
    res = V.lint_split(out, "die_bound_top", None, None, rep["files"], LS, [], tmp_path / "rs.sv", lib, ab0)
    assert res["runs"] == 3 and set(seen) == {"top", "part", "part__group1"}
    assert seen["part"][0] == seen["part__group1"][0] == "part"
    a, b = seen["part"][1], seen["part__group1"][1]
    assert "rtl/nk/w.sv" in a and "rtl/nl/w.sv" not in a and "other_leaf_stubs.sv" in a and "rtl/nl/leaf_b.sv" not in a
    assert "rtl/nl/w.sv" in b and "rtl/nk/w.sv" not in b and "rtl/nk/leaf_a.sv" not in b
    stub = (out / "lint" / "part" / "other_leaf_stubs.sv").read_text()
    assert "module leaf_b" in stub and "module leaf_a" not in stub
