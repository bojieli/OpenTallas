"""resign.lec_kit / run_cmds: a late-ECO pass dir without config.mk mounts its kit for LEC (S81-TYPES-5 11-07)."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import resign  # noqa: E402


def test_pass_dir_mounts_parent_kit(tmp_path):
    k = tmp_path / "kit"
    p = k / "eco_1" / "i1"
    v = p / "run" / "results" / "asap7" / "dp_x" / "base"
    v.mkdir(parents=True)
    (v / "6_final.v").write_text("module x; endmodule\n")
    (k / "config.mk").write_text("export DESIGN_NAME = x\n")
    assert resign.lec_kit(str(p)) == str(k)
    so, lec = resign.run_cmds(str(p), str(p / "run"), str(tmp_path), str(tmp_path / "o"), "img", "n")
    assert "%s:/work:ro" % k in lec
    assert any("/work/eco_1/i1/run/results/asap7/dp_x/base/6_final.v" in a for a in lec)
    assert so[so.index("--kit") + 1] == str(p)          # sign-off itself still reads the pass dir


def test_kit_with_config_unchanged(tmp_path):
    (tmp_path / "config.mk").write_text("")
    assert resign.lec_kit(str(tmp_path)) == str(tmp_path)
