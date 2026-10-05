"""Timeout policy propagation only: subprocesses are mocked, no tool launch."""
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import run_abi3_physical as flow


ARGS = ["--view", "asap7", "--block", "reduction_s8_g2",
        "--clock-period-ns", "1", "--output", "unused.json"]


@pytest.fixture(autouse=True)
def clean_policy(monkeypatch):
    monkeypatch.delenv("OT_SYNTH_TIMEOUT_SECONDS", raising=False)
    monkeypatch.delenv("OT_FLOW_TIMEOUT_SECONDS", raising=False)


def test_defaults_and_explicit_subprocess_none(monkeypatch):
    assert flow.synth_timeout_seconds() == 7200
    assert flow.flow_timeout_seconds() == 21600
    seen = []
    def fake_run(cmd, **kwargs):
        seen.append(kwargs["timeout"])
        return subprocess.CompletedProcess(cmd, 0)
    monkeypatch.setattr(flow.subprocess, "run", fake_run)
    flow.run(["never-launched"])
    flow.run(["never-launched"], timeout=None)
    assert seen == [7200, None]


@pytest.mark.parametrize("raw", ["unlimited", "none", " NONE ", "UNLIMITED"])
def test_environment_unlimited(monkeypatch, raw):
    monkeypatch.setenv("OT_SYNTH_TIMEOUT_SECONDS", raw)
    monkeypatch.setenv("OT_FLOW_TIMEOUT_SECONDS", raw)
    assert flow.synth_timeout_seconds() is None
    assert flow.flow_timeout_seconds() is None


@pytest.mark.parametrize("cli,kwargs,expected", [
    ([], {}, (7200, 21600)),
    ([], {"synth_timeout": None, "flow_timeout": None}, (None, None)),
    (["--synth-timeout-seconds", "unlimited", "--flow-timeout-seconds", "none"], {}, (None, None)),
    (["--synth-timeout-seconds", "9000", "--flow-timeout-seconds", "30000"], {}, (9000, 30000)),
    (["--synth-timeout-seconds", "9000"], {"synth_timeout": None, "flow_timeout": None}, (9000, None)),
])
def test_cli_and_python_overrides_reach_subprocess(monkeypatch, cli, kwargs, expected):
    seen = []
    def fake_run(cmd, **options):
        seen.append(options["timeout"])
        return subprocess.CompletedProcess(cmd, 0)
    def fake_main(args, **kwargs):
        # Exercise the same no-argument callbacks used by Yosys and ORFS.
        flow.run(["synth"], timeout=flow.synth_timeout_seconds())
        flow.run(["route"], timeout=flow.flow_timeout_seconds())
        return 7
    monkeypatch.setattr(flow.subprocess, "run", fake_run)
    monkeypatch.setattr(flow, "_main", fake_main)
    assert flow.main(ARGS + cli, **kwargs) == 7
    assert tuple(seen) == expected
    assert flow.synth_timeout_seconds() == 7200
    assert flow.flow_timeout_seconds() == 21600


def test_environment_restored_on_driver_exception(monkeypatch):
    monkeypatch.setenv("OT_SYNTH_TIMEOUT_SECONDS", "8100")
    monkeypatch.setenv("OT_FLOW_TIMEOUT_SECONDS", "27000")
    def fail(args, **kwargs):
        assert flow.synth_timeout_seconds() is None
        assert flow.flow_timeout_seconds() is None
        raise RuntimeError("preserved failure")
    monkeypatch.setattr(flow, "_main", fail)
    with pytest.raises(RuntimeError, match="preserved failure"):
        flow.main(ARGS, synth_timeout=None, flow_timeout=None)
    assert flow.synth_timeout_seconds() == 8100
    assert flow.flow_timeout_seconds() == 27000


@pytest.mark.parametrize("flag,value,error", [
    ("--synth-timeout-seconds", "0", SystemExit),
    ("--flow-timeout-seconds", "599", flow.FlowError),
    ("--flow-timeout-seconds", "invalid", flow.FlowError),
])
def test_invalid_numeric_policy_preserved_before_tools(monkeypatch, flag, value, error):
    monkeypatch.setattr(flow, "_main", lambda args, **kwargs: pytest.fail("must validate before tools"))
    with pytest.raises(error):
        flow.main(ARGS + ["--synth-timeout-seconds", "unlimited", flag, value])
    assert flow.synth_timeout_seconds() == 7200
    assert flow.flow_timeout_seconds() == 21600


@pytest.mark.parametrize("stage", ["synthesis", "sta"])
def test_actual_stage_callback_forwards_none(monkeypatch, tmp_path, stage):
    monkeypatch.setenv("OT_SYNTH_TIMEOUT_SECONDS", "unlimited")
    class ReachedTool(Exception):
        pass
    def fake_run(cmd, **kwargs):
        assert kwargs["timeout"] is None
        assert cmd[0] == str(flow.YOSYS if stage == "synthesis" else flow.STA)
        raise ReachedTool
    monkeypatch.setattr(flow.subprocess, "run", fake_run)
    liberty = tmp_path / "test.lib"
    liberty.write_text("test")
    source = tmp_path / "test.v"
    source.write_text("module test; endmodule")
    view = {"time_unit_ns": 1, "dff_liberty_corner_relative": "test.lib"}
    corner = {"liberty": [liberty]}
    block = {"top": "test", "sources": [str(source)], "parameters": {}}
    with pytest.raises(ReachedTool):
        if stage == "synthesis":
            flow.run_synthesis(view, corner, block, tmp_path, 1, [])
        else:
            monkeypatch.setattr(flow, "sdc_text", lambda *args: "# mocked SDC\n")
            flow.run_sta(view, corner, block, tmp_path, tmp_path / "mapped.v", 1)


@pytest.mark.parametrize("use_sys_argv", [False, True])
def test_actual_initial_record_preserves_invocation_argv(monkeypatch, tmp_path, use_sys_argv):
    import json
    source = tmp_path / "test.v"
    source.write_text("module test; endmodule\n")
    output = tmp_path / "record.json"
    argv = ["--view", "asap7", "--top", "test", "--source", str(source),
            "--clock-period-ns", "1", "--stages", "", "--output", str(output),
            "--synth-timeout-seconds", "unlimited"]
    view = dict(flow.VIEWS["asap7"])
    view["corners"] = {name: dict(corner, liberty=[]) for name, corner in view["corners"].items()}
    monkeypatch.setitem(flow.VIEWS, "asap7", view)
    monkeypatch.setattr(flow, "git_identity", lambda: {})
    monkeypatch.setattr(flow, "driver_identity", lambda: {})
    monkeypatch.setattr(flow, "resolve_signal_integrity_constraints", lambda *args, **kwargs: None)
    monkeypatch.setattr(flow, "run", lambda *args, **kwargs: pytest.fail("no subprocess required"))
    monkeypatch.setattr(sys, "argv", ["invoked-driver", *argv])
    flow.main(None if use_sys_argv else argv)
    record = json.loads(output.read_text())
    assert record["runner"]["argv"] == ["tools/run_abi3_physical.py", *argv]
    assert record["stages_requested"] == []
