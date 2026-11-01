"""A requested macro FF repair must consume its actual FF timing views only."""
from pathlib import Path
import subprocess
import pytest
import gen_phys as G


def kit(tmp_path):
    (tmp_path / "macros").mkdir()
    (tmp_path / "macros" / "leaf_ff.lib").write_text('library(leaf_fast) { cell(leaf) {} }')
    return [("u_leaf", "leaf", "leaf.lef", "leaf_tt.lib", 0, 0, "R0")], ["/work/macros/leaf_tt.lib"]


def test_separate_ff_config_selects_only_ff_macro_views(tmp_path):
    macros, libs = kit(tmp_path)
    assert G.macro_ff_repair_stage(tmp_path, macros, libs) == {"leaf": "leaf_fast/leaf"}
    # Expand the generated stage with a representative original TT config.
    (tmp_path / "config.mk").write_text(
        "export PRE_GLOBAL_ROUTE_TCL = /work/hold_repair_pre.tcl\n"
        "export CORNER = TC\nexport ADDITIONAL_LIBS = /work/macros/leaf_tt.lib\n"
        "export BC_LIB_FILES = /platform/ff.lib /work/macros/leaf_ff.lib\n")
    stage = (tmp_path / "macro_ff_repair.mk").read_text().replace("include /work/config.mk", f"include {tmp_path}/config.mk")
    (tmp_path / "stage.mk").write_text(stage + '\nprobe:\n\t@echo $(CORNER) $(CORNERS) $(LIB_FILES) $(ADDITIONAL_LIBS) $(OT_MACRO_FF_BASE_PRE_GRT)\n')
    p = subprocess.run(["make", "-s", "-f", str(tmp_path / "stage.mk"), "probe"], check=True, capture_output=True, text=True)
    assert p.stdout.strip() == "BC bc /platform/ff.lib /work/macros/leaf_ff.lib /work/macros/leaf_ff.lib /work/hold_repair_pre.tcl"
    assert "leaf_fast/leaf" in (tmp_path / "macro_ff_pre_grt.tcl").read_text()
    assert "leaf_tt.lib" in (tmp_path / "config.mk").read_text()


def test_missing_ff_view_refuses_stage(tmp_path):
    macros, libs = kit(tmp_path)
    (tmp_path / "macros" / "leaf_ff.lib").unlink()
    with pytest.raises(ValueError, match="no ff view"):
        G.macro_ff_repair_stage(tmp_path, macros, libs)


def test_wrong_ff_master_refuses_stage(tmp_path):
    macros, libs = kit(tmp_path)
    (tmp_path / "macros" / "leaf_ff.lib").write_text('library(fast) { cell(other) {} }')
    with pytest.raises(ValueError, match="missing actual FF macro cells"):
        G.macro_ff_repair_stage(tmp_path, macros, libs)


def test_runner_shell_remains_valid(tmp_path):
    path = tmp_path / "run.sh"
    path.write_text(G.RUN_KIT)
    subprocess.run(["bash", "-n", str(path)], check=True)
    assert "DESIGN_CONFIG=/work/macro_ff_repair.mk" in G.RUN_KIT
