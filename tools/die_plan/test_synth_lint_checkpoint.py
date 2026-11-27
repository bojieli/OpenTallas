import json

import pytest

import rtl_lint
import synth_lint_checkpoint as checkpoint


def test_capture_precedes_lowering_and_leaves_stock_script(tmp_path):
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = test\nexport VERILOG_FILES = /work/test.sv\n")
    stock = rtl_lint.script(tmp_path)
    trial = rtl_lint.script(tmp_path, checkpoint="/work/.trial")
    assert "write_rtlil" not in stock
    assert "-noautowire" in trial
    assert trial.index("write_rtlil") < trial.index("\nproc\n")
    assert trial.endswith("check -assert\n")


def test_reject_incompatible_named_and_positional_macro_contracts(tmp_path):
    lint, native, active = (tmp_path / p for p in ("lint", "native", "active"))
    lint.write_text("module \\rom\n  wire input 1 \\ena\n  wire width 8 output 2 \\data\nend\n")
    native.write_text("module \\rom\n  wire input 2 \\ena\n  wire width 8 output 1 \\data\nend\n")
    source = "module \\top\n  cell \\rom \\u_rom\n    connect \\ena \\en\n  end\nend\n"
    active.write_text(source)
    assert checkpoint.hard_interfaces(active, lint, native) == ["\\rom"]
    for bad in (source.replace("\\ena", "$1"), source.replace("    connect", "    parameter")):
        active.write_text(bad)
        with pytest.raises(ValueError, match="unknown pin"):
            checkpoint.hard_interfaces(active, lint, native)
    active.write_text(source)
    native.write_text(native.read_text().replace("width 8", "width 9"))
    with pytest.raises(ValueError, match="signature mismatch"):
        checkpoint.hard_interfaces(active, lint, native)


def test_authority_sensitive_profile_uses_standalone_lint(tmp_path, monkeypatch):
    trial = tmp_path / ".trial"
    trial.mkdir()
    (tmp_path / "config.mk").write_text("export OT_NATIVE_SRAM_PATHS = 1\n")
    calls = []

    def stock(kit, **kwargs):
        calls.append(kwargs)
        return 1

    monkeypatch.setattr(rtl_lint, "run", stock)
    assert checkpoint.run_lint(tmp_path, trial) == 1
    assert calls == [{}]
    assert json.loads((tmp_path / checkpoint.RECEIPT).read_text())["status"] == "STOCK"


@pytest.mark.parametrize("guard_rejected,expected_calls", [(True, 2), (False, 1)])
def test_synthesis_retries_only_before_consumption(tmp_path, monkeypatch, guard_rejected, expected_calls):
    trial = tmp_path / ".trial"
    trial.mkdir()
    canon = tmp_path / "synth_canonicalize.tcl"
    original = "source stock\n" + checkpoint.HEADER + "\n"
    canon.write_text(original)
    marker = "ineligible" if guard_rejected else "selected"
    checkpoint.write_receipt(tmp_path, status="READY", trial=trial.name, identity={})
    monkeypatch.setattr(checkpoint, "CANON", canon)
    monkeypatch.setattr(checkpoint, "check_receipt", lambda kit, identity: None)
    monkeypatch.setattr(checkpoint, "require_isolated_container", lambda: None)
    calls = []

    def make(command, env=None):
        calls.append(command)
        if env is not None:
            assert canon.read_text() != original
            (trial / marker).write_text("native test")
            return 2
        assert canon.read_text() == original
        return 7

    monkeypatch.setattr(checkpoint.subprocess, "call", make)
    assert checkpoint.run_synth(tmp_path, trial, ["make", "synth"]) == (7 if guard_rejected else 2)
    assert calls == [["make", "synth"]] * expected_calls
    assert canon.read_text() == original


def test_pin_only_nickname_and_description_do_not_change_compiler_recipe():
    config = "export VERILOG_DEFINES = -DSYNTHESIS\nexport DESIGN_NAME = ot_s81sl_xs4\n"
    original = "# core floorplan old\nexport DESIGN_NICKNAME = kl_old\n" + config
    successor = "# core floorplan new\nexport DESIGN_NICKNAME = kl_new\n" + config
    assert checkpoint.compiler_config(original) == checkpoint.compiler_config(successor)
    assert checkpoint.compiler_config(original) != checkpoint.compiler_config(
        successor.replace("-DSYNTHESIS", "-DOTHER"))
    assert checkpoint.compiler_config(original) != checkpoint.compiler_config(
        successor.replace("kl_new", "$(unknown)"))
    with pytest.raises(ValueError, match="multiline"):
        checkpoint.compiler_config(successor + "export VERILOG_FILES = \\" + "\n")


def test_immutable_source_receipt_change_stops_before_stock_or_trial_synth(tmp_path, monkeypatch):
    trial = tmp_path / ".trial"
    trial.mkdir()
    source = tmp_path / "design.v"
    source.write_text("module design; endmodule\n")
    identity = {"kit_files": checkpoint.inventory(tmp_path, ["design.v"])}
    checkpoint.write_receipt(tmp_path, status="READY", trial=trial.name, identity=identity)
    source.write_text("module changed; endmodule\n")

    def no_process(*args, **kwargs):
        pytest.fail("synthesis must not consume input different from the strict lint input")

    monkeypatch.setattr(checkpoint.subprocess, "call", no_process)
    assert checkpoint.run_synth(tmp_path, trial, ["make", "synth"]) == 8
    assert "compiler inputs changed" in (tmp_path / "FAIL_PREFLOOR").read_text()
