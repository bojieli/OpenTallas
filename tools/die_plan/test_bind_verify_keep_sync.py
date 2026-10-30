"""DIE-S81-30 10-29 (COORD ruling S81 bind6 VERIFY FAIL): bind_verify keeps the as-built leaf synchronisers the bind
emitted (S81 frame u_f_*.u_r0.u_xrl0..3) as leaves, and its lint closure finds every module definition it needs."""
import sys
from pathlib import Path
from types import SimpleNamespace as N

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_elab as E  # noqa: E402
import bind_verify as V  # noqa: E402
from bind import Graph, Rules  # noqa: E402


def _frame(keep):
    """bound frame: the partition's own u_rst_sync (bind reset) -> as-built leaf synchroniser u_xrl0 -> station rs."""
    own = N(path="p.u_rst_sync", module="ot_reset_sync", kind="leaf", ports={"clk": [1], "async_rst_n": [2],
            "sync_rst_n": [10]}, dirs={"clk": "input", "async_rst_n": "input", "sync_rst_n": "output"}, params={})
    xrl = N(path="p.u_u_r0_u_xrl0", module="ot_reset_sync", kind="leaf", ports={"clk": [3], "async_rst_n": [10],
            "sync_rst_n": [11]}, dirs={"clk": "input", "async_rst_n": "input", "sync_rst_n": "output"}, params={})
    st = N(path="p.u_u_r0_u_y_xo0_0", module="dsfd_rly_x", kind="leaf", ports={"rs": [11]}, dirs={"rs": "input"},
           params={})
    flat = N(cells=[own, xrl, st], const_drivers={}, top_ports={})
    R = Rules(V.VERIFY_RULES)
    if keep:
        R.keep_source = set(keep)
    errs = []
    return Graph(flat, R, errs), errs


def test_kept_leaf_synchroniser_drives_station_as_a_pin():
    g, errs = _frame({"p.u_u_r0_u_xrl0", "p.u_u_r0_u_y_xo0_0"})
    assert not errs
    assert g.kind == ["source", "leaf", "leaf"]          # the bind's own u_rst_sync is still the partition reset
    assert g.source(11) == ("pin", 1, "sync_rst_n", 0, 0)  # rs[0] <- u_xrl0.sync_rst_n, as in the RTL
    assert g.source(10) == ("reset", "low", 0)              # u_xrl0 input <- the bind reset tree


def test_default_without_names_is_unchanged():
    # MUTANT (bind6 verify): every ot_reset_sync is a source -> the leaf vanishes and rs reads as the partition reset
    g, errs = _frame(None)
    assert g.kind == ["source", "source", "leaf"]
    assert g.source(11) == ("reset", "low", 0)


def test_keep_source_needs_a_leaf_cell():
    g, _ = _frame({"p.u_u_r0_u_xrl0"})
    g.F.cells[1].kind = "glue"
    g2 = Graph(g.F, g.R, [])
    assert g2.kind[1] == "source"


def _tree(tmp_path):
    rtl = tmp_path / "rtl"
    (rtl / "common").mkdir(parents=True)
    (rtl / "eng").mkdir()
    (rtl / "pkg").mkdir()
    (rtl / "dup1").mkdir()
    (rtl / "dup2").mkdir()
    mac = tmp_path / "physical/asap7_memory_macros_v2/ot_rom_x"
    mac.mkdir(parents=True)
    (mac / "ot_rom_x.lef").write_text("")
    (mac / "ot_rom_x_bb.v").write_text("(* blackbox *)\nmodule ot_rom_x (input wire clk);\nendmodule\n")
    (mac / "ot_rom_x.v").write_text("module ot_rom_x (input wire clk);\nendmodule\n")
    # manifest leaf: instantiates a multi-module-file child, a ring from the bind's extra lib, a macro via `define,
    # a package, and an ambiguous child
    (rtl / "leaf.sv").write_text(
        "`define MYROM ot_rom_x\n"
        "module leaf (input wire clk);\n  import my_pkg::*;\n  ot_ve_qmul u_m (.clk(clk));\n"
        "  ot_dp_clk_landing u_l (.clk(clk));\n  `MYROM u_r (.clk(clk));\nendmodule\n")
    (rtl / "eng/ot_ve_fp.sv").write_text("module ot_ve_qadd (input wire clk);\nendmodule\n"
                                         "module ot_ve_qmul (input wire clk);\n  ot_ve_qadd u_a (.clk(clk));\nendmodule\n")
    (rtl / "common/ot_meso_fifo.sv").write_text("module ot_meso_fifo (input wire clk);\nendmodule\n"
                                                "module ot_meso_ring (input wire clk);\nendmodule\n")
    (rtl / "common/ot_dp_clk_landing.sv").write_text("module ot_dp_clk_landing (input wire clk);\n"
                                                     "  ot_meso_ring u_r (.clk(clk));\nendmodule\n")
    (rtl / "pkg/my_pkg.sv").write_text("package my_pkg;\n  localparam int A = 1;\nendpackage\n")
    (rtl / "dup1/ot_amb.sv").write_text("module ot_amb (input wire clk);\nendmodule\n")
    (rtl / "dup2/ot_amb.sv").write_text("module ot_amb (input wire clk);\nendmodule\n")
    (rtl / "leaf2.sv").write_text("module leaf2 (input wire clk);\n  ot_amb u_a (.clk(clk));\n"
                                  "  ot_bind_native_abc u_n (.clk(clk));\nendmodule\n")
    out = tmp_path / "out/rtl/native_glue"
    out.mkdir(parents=True)
    (out / "ot_bind_native_abc.sv").write_text("module ot_bind_native_abc (input wire clk);\nendmodule\n")
    (tmp_path / "out/rtl/part.sv").write_text("module part (input wire clk);\n  leaf u_l (.clk(clk));\nendmodule\n")
    ab0 = dict(rtl_roots=[], files=["rtl/leaf.sv", "rtl/leaf2.sv"])
    rep = dict(extra_lib=[str(rtl / "common/ot_meso_fifo.sv"), str(rtl / "common/ot_dp_clk_landing.sv")],
               files=[str(tmp_path / "out/rtl/part.sv"), str(out / "ot_bind_native_abc.sv")])
    idx = E.module_index(ab0["rtl_roots"], ab0["files"], tmp_path)
    prefer = list(rep["extra_lib"])
    return ab0, rep, idx, prefer


def test_lint_closure_finds_every_needed_definition(tmp_path):
    ab0, rep, idx, prefer = _tree(tmp_path)
    old, old_missing = E.closure(["leaf"], idx, prefer)
    # MUTANT (bind6 lint): the manifest index alone drops the multi-module-file child, the landing ring, the macro
    assert old == [str(tmp_path / "rtl/leaf.sv")] and old_missing == []
    LS = V.LintSources(ab0, tmp_path, rep, idx, prefer)
    files, missing = LS.closure(["leaf"])
    names = [Path(f).relative_to(tmp_path).as_posix() for f in files]
    assert missing == []
    assert names[0] == "rtl/pkg/my_pkg.sv"                     # package before its user
    assert set(names) == {"rtl/pkg/my_pkg.sv", "rtl/leaf.sv", "rtl/eng/ot_ve_fp.sv", "rtl/common/ot_dp_clk_landing.sv",
                          "rtl/common/ot_meso_fifo.sv", "physical/asap7_memory_macros_v2/ot_rom_x/ot_rom_x_bb.v"}
    assert set(old) <= set(files)                               # the old picks are kept


def test_lint_closure_native_glue_and_ambiguity_fail_closed(tmp_path):
    ab0, rep, idx, prefer = _tree(tmp_path)
    LS = V.LintSources(ab0, tmp_path, rep, idx, prefer)
    files, missing = LS.closure(["leaf2"])
    assert str(tmp_path / "out/rtl/native_glue/ot_bind_native_abc.sv") in files
    assert str(tmp_path / "out/rtl/part.sv") not in files      # partition modules are not leaf sources
    assert missing == ["ot_amb"] and set(LS.ambiguous) == {"ot_amb"}   # two rtl/ definitions: never a silent pick
    prefer.append(str(tmp_path / "rtl/dup2/ot_amb.sv"))
    files, missing = V.LintSources(ab0, tmp_path, rep, idx, prefer).closure(["leaf2"])
    assert missing == [] and str(tmp_path / "rtl/dup2/ot_amb.sv") in files


def test_lint_closure_unchanged_when_manifest_complete(tmp_path):
    ab0, rep, idx, prefer = _tree(tmp_path)
    (tmp_path / "rtl/solo.sv").write_text("module solo (input wire clk);\n  solo_c u_c (.clk(clk));\nendmodule\n"
                                          "module solo_c (input wire clk);\nendmodule\n")
    ab0["files"].append("rtl/solo.sv")
    idx = E.module_index([], ab0["files"], tmp_path)
    old, _ = E.closure(["solo"], idx, prefer)
    new, missing = V.LintSources(ab0, tmp_path, rep, idx, prefer).closure(["solo"])
    assert new == old and missing == []


def test_split_leaves_take_native_glue_cells(tmp_path):
    ab0, rep, idx, prefer = _tree(tmp_path)
    LS = V.LintSources(ab0, tmp_path, rep, idx, prefer)
    part = ("module part (input wire clk);\n  leaf2 u_l (.clk(clk));\n  ot_bind_native_abc g_u_x_1 (.clk(clk));\n"
            "  ot_dp_st u_st (.clk(clk));\nendmodule\n")
    # MUTANT (bind6 lint): the u_-only pattern missed the g_ native glue cells (4750 MODMISSING)
    assert V.split_leaves(part, ["part"], idx) == ["leaf2"]
    assert V.split_leaves(part, ["part"], LS) == ["leaf2", "ot_bind_native_abc"]


def test_macro_provider_file_is_added_before_its_user(tmp_path):
    ab0, rep, idx, prefer = _tree(tmp_path)
    (tmp_path / "rtl/sel").mkdir()
    (tmp_path / "rtl/sel/sel_tile.sv").write_text("`define SELT_OB 354\nmodule sel_t (input wire clk);\n"
                                                  "  ot_ve_qadd u_q (.clk(clk));\nendmodule\n")
    (tmp_path / "rtl/sel/ctl.sv").write_text("module ctl (input wire [`SELT_OB-1:0] f, input wire clk);\n"
                                             "`ifdef OT_X\n`endif\nendmodule\n")
    (tmp_path / "rtl/leaf3.sv").write_text("module leaf3 (input wire clk);\n  ctl u_c (.clk(clk));\nendmodule\n")
    ab0["files"].append("rtl/leaf3.sv")
    ab0["defines"] = ["OT_X"]
    idx = E.module_index([], ab0["files"], tmp_path)
    files, missing = V.LintSources(ab0, tmp_path, rep, idx, prefer).closure(["leaf3"])
    names = [Path(f).relative_to(tmp_path).as_posix() for f in files]
    assert missing == []
    assert names.index("rtl/sel/sel_tile.sv") < names.index("rtl/sel/ctl.sv")
    assert "rtl/eng/ot_ve_fp.sv" in names                      # the provider's own children are closed too


def test_declared_literal_matches_only_its_own_value():
    # bind6/bind6chk: 125,994 proven-dead literals (want ['literal','0'], bound 1'b0 = ['tied','0']) failed as TIED
    assert V.declared_constant(["literal", "0"], ["tied", "0"])
    assert V.declared_constant(["strap", "1"], ["tied", "1"])
    assert not V.declared_constant(["literal", "0"], ["tied", "1"])      # MUTANT: wrong value stays TIED
    assert not V.declared_constant(["pin", "a.q[0]", 0, False], ["tied", "0"])
    assert not V.declared_constant(None, ["tied", "0"])
    assert not V.declared_constant(["literal", "0"], ["pin", "a.q[0]", 0, False])


def test_macro_definer_inside_the_closure_moves_before_its_user(tmp_path):
    ab0, rep, idx, prefer = _tree(tmp_path)
    (tmp_path / "rtl/a_user.sv").write_text("module zz_user (input wire [`W-1:0] x);\nendmodule\n")
    (tmp_path / "rtl/z_def.sv").write_text("`define W 4\nmodule aa_def (input wire clk);\nendmodule\n")
    (tmp_path / "rtl/top3.sv").write_text("module top3 (input wire clk);\n  aa_def u_z (.clk(clk));\n"
                                          "  zz_user u_a (.x(4'b0));\nendmodule\n")
    ab0["files"] += ["rtl/top3.sv", "rtl/a_user.sv", "rtl/z_def.sv"]
    idx = E.module_index([], ab0["files"], tmp_path)
    files, missing = V.LintSources(ab0, tmp_path, rep, idx, prefer).closure(["top3"])
    names = [Path(f).relative_to(tmp_path).as_posix() for f in files]
    # MUTANT (bind6chk bk_sel): sel_tile.sv was listed after hq_tile.sv -> `SELT_* undefined
    assert missing == [] and names.index("rtl/z_def.sv") < names.index("rtl/a_user.sv")


def test_lint_sources_declared_view_absent_fails_closed(tmp_path):
    """DIE-S81-32/BIND: S81 verify256 ran from a sparse worktree without physical/asap7_memory_macros*; the manifest
    declared the macro views but module_index skipped them silently -> 1,769 MODMISSING (ROMs, r2c2 p192/p192bs
    ambiguity).  A declared source that is absent stops the verify; the closure never falls back to rtl/."""
    ab0, rep, idx, prefer = _tree(tmp_path)
    assert V.declared_missing(ab0, tmp_path) == []
    V.LintSources(ab0, tmp_path, rep, idx, prefer)              # complete checkout: unchanged
    ab0["files"].append("physical/asap7_memory_macros_v2/ot_rom_y/ot_rom_y_bb.v")
    assert V.declared_missing(ab0, tmp_path) == ["physical/asap7_memory_macros_v2/ot_rom_y/ot_rom_y_bb.v"]
    try:
        V.LintSources(ab0, tmp_path, rep, idx, prefer)
    except ValueError as e:
        assert "ot_rom_y_bb.v" in str(e) and "absent" in str(e)
    else:
        raise AssertionError("absent declared macro view was skipped silently")
