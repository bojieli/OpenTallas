"""Wrong output subdirectories must not earn an all-NA generation-lint PASS."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_gen_lint as GL


def test_rtl_emission_directory_fails(tmp_path):
    rtl = tmp_path / "_rtl"
    rtl.mkdir()
    (rtl / "top.v").write_text("module top; endmodule\n")
    result = GL.lint(rtl, yosys=False)
    assert result["verdict"] == "FAIL"
    assert result["checks"]["kit_vehicle"]["verdict"] == "FAIL"
    assert "missing config.mk" in result["issues"][0]
    assert all(r["verdict"] == "NA" for n, r in result["checks"].items() if n != "kit_vehicle")


def test_valid_core_config_without_freeze_is_unchanged(tmp_path):
    (tmp_path / "config.mk").write_text("export DESIGN_NAME = top\nexport VERILOG_FILES = /work/top.v\n")
    (tmp_path / "top.v").write_text("module top; endmodule\n")
    result = GL.lint(tmp_path, yosys=False)
    assert result["verdict"] == "PASS"
    assert "kit_vehicle" not in result["checks"]
    assert result["checks"]["pins_vs_plan"]["verdict"] == "NA"
