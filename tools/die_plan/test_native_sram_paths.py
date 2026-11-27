import json

import pytest

import native_sram_paths as NSP
import rtl_lint


MASTER = "ot_sram_test"
OLD = "u_bound.g_bank[0].g_fit.u_mem"
ACTUAL = "u_bound.g_bank[0].genblk2.g_fit.u_mem"


def _design(extra=None):
    return {"modules": {
        "top": {"cells": {"u_bound": {"type": "bound"}}},
        "bound": {"cells": {
            ACTUAL.removeprefix("u_bound."): {"type": MASTER},
            "u_core": {"type": "$paramod$core"},
            **(extra or {}),
        }},
        "$paramod$core": {"attributes": {"hdlname": "my_core"}},
    }}


DECLARED = [{"inst": OLD, "master": MASTER}, {"inst": "u_bound.u_core", "master": "my_core"}]


def _scripts():
    macro = (f"place_macro -macro_name {{{NSP._odb(OLD)}}} -location {{17.0 24.0}} -orientation MY -exact\n"
             "place_macro -macro_name {u_bound.u_core} -location {55.0 24.0} -orientation R0 -exact\n")
    pdn = f"define_pdn_grid -macro -instances {{{NSP._pg_pattern(OLD)}}} -halo {{0}}\n"
    return macro, pdn


def test_authoritative_paths_keep_placement_and_rewrite_pdn():
    selected = NSP.resolve(_design(), "top", DECLARED)
    assert selected == {OLD: ACTUAL, "u_bound.u_core": "u_bound.u_core"}
    old_macro, old_pdn = _scripts()
    macro, pdn = NSP.project(old_macro, old_pdn, selected)
    assert macro == old_macro.replace(NSP._odb(OLD), NSP._odb(ACTUAL))
    assert pdn == old_pdn.replace(NSP._pg_pattern(OLD), NSP._pg_pattern(ACTUAL))
    assert NSP.project(old_macro, old_pdn, {p: p for p in selected}) == (old_macro, old_pdn)


def test_refuse_ambiguous_or_wrong_master_paths():
    extra = {ACTUAL.removeprefix("u_bound.").replace("genblk2", "genblk3"): {"type": MASTER}}
    with pytest.raises(ValueError, match="found 2"):
        NSP.resolve(_design(extra), "top", DECLARED)
    extra = {OLD.removeprefix("u_bound."): {"type": "another_macro"}}
    with pytest.raises(ValueError, match="has native master another_macro"):
        NSP.resolve(_design(extra), "top", DECLARED)
    with pytest.raises(ValueError, match="no exact native path"):
        NSP.resolve(_design(), "top", [{"inst": OLD, "master": "another_core"}])


def test_stage_pair_and_refuse_unknown_consumers(tmp_path):
    (tmp_path / NSP.EXPECTED).write_text(json.dumps(DECLARED))
    for name, body in zip(NSP.SCRIPTS, _scripts()):
        (tmp_path / name).write_text(NSP.wrapper(name, body))
    (tmp_path / "other.tcl").write_text(f"read_macro {{{NSP._odb(OLD)}}}")
    with pytest.raises(ValueError, match="unsupported native macro consumer"):
        NSP.apply(tmp_path, _design(), "top")
    assert not (tmp_path / NSP.RECEIPT).is_file()
    (tmp_path / "other.tcl").write_text("# no physical instance names\n")
    info = NSP.apply(tmp_path, _design(), "top")
    assert info["expected"] == info["matched"] == 2
    assert NSP._odb(ACTUAL) in (tmp_path / "macro_place_native.tcl").read_text()
    assert NSP._pg_pattern(ACTUAL) in (tmp_path / "pdn_native.tcl").read_text()
    assert json.loads((tmp_path / NSP.RECEIPT).read_text()) == info


def test_rtl_lint_reuses_native_yosys_json_hook(tmp_path):
    p = tmp_path / "config.mk"
    p.write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/top.v\n")
    assert "write_json" not in rtl_lint.script(tmp_path)
    p.write_text(p.read_text() + "export OT_NATIVE_SRAM_PATHS = 1\n")
    assert "write_json /work/kit_assembly_elaborated.json" in rtl_lint.script(tmp_path)


def test_native_lint_projects_both_scripts_before_synth(tmp_path, monkeypatch):
    import shutil
    from types import SimpleNamespace

    (tmp_path / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/top.v\n"
                                      "export OT_NATIVE_SRAM_PATHS = 1\n")
    (tmp_path / "top.v").write_text("module top; endmodule\n")
    (tmp_path / NSP.EXPECTED).write_text(json.dumps(DECLARED))
    shutil.copyfile(NSP.__file__, tmp_path / "native_sram_paths.py")
    for name, body in zip(NSP.SCRIPTS, _scripts()):
        (tmp_path / name).write_text(NSP.wrapper(name, body))

    def fake_yosys(*args, **kwargs):
        (tmp_path / "kit_assembly_elaborated.json").write_text(json.dumps(_design()))
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(rtl_lint.subprocess, "run", fake_yosys)
    assert rtl_lint.run(tmp_path) == 0
    record = json.loads((tmp_path / "rtl_lint.json").read_text())
    assert record["native_sram_paths"]["aliases"] == {OLD: ACTUAL}
    assert (tmp_path / NSP.RECEIPT).is_file()
    assert (tmp_path / "macro_place_native.tcl").is_file()
    assert (tmp_path / "pdn_native.tcl").is_file()
