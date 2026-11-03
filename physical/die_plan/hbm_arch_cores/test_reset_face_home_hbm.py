"""KW-FIX-2 11-02 (GEOM-111 class R): the HBM core kit homes reset inputs at their pin face.

The kit's face_flops.tcl skip set holds clocks + straps only (resets were skipped for a reset_tree.tcl that this
generator never writes, so rst_n entry flops floated 212-647 um from the pin).  Probe on ot_hgi_qw_dec attempt_3
2_floorplan.odb with this skip set: 1669 pin registers (was 1668), u_fcore.u_rst.sync_q[1] FIRM at (252.72, 4.32)
for rst_n at (255.0, 0.1).  --no-reset-face-home restores the old skip set."""
import importlib.util
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
spec = importlib.util.spec_from_file_location("coregen_rfh", HERE / "gen_core_kit_hbm.py")
coregen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coregen)
TOOL_FF = (REPO / "tools/die_plan/face_flops.tcl").read_text()


def _skip(ff):
    return re.findall(r"^set ff_skip_re \{(.*)\}$", ff, re.M)


def test_resets_homed_by_default():
    ff = coregen.face_flops_text(TOOL_FF, ["clk"], ["rst_n", "rst_col"], ["strap_id"])
    assert _skip(ff) == ["^(clk|strap_id)$"]
    sk = re.compile(_skip(ff)[0])
    assert not sk.match("rst_n") and not sk.match("rst_col") and sk.match("clk") and sk.match("strap_id")


def test_opt_out_restores_old_skip():
    ff = coregen.face_flops_text(TOOL_FF, ["clk"], ["rst_n"], [], home_resets=False)
    assert _skip(ff) == ["^(clk|rst_n)$"]


def test_only_generator_patches_applied():
    ff = coregen.face_flops_text(TOOL_FF, ["clk"], ["rst_n"], [])
    back = ff.replace("set ff_skip_re {^(clk)$}", re.findall(r"^set ff_skip_re \{.*$", TOOL_FF, re.M)[0])
    back = back.replace("\nset ff_unreg [open $::env(RESULTS_DIR)/ot_unreg_pins.txt w]", "")
    back = back.replace('incr ff_miss; puts $ff_unreg "$pass\\t$nm"; continue', "incr ff_miss; continue")
    assert back == TOOL_FF
    assert "ot_unreg_pins.txt" in ff


def test_cli_flag_declared():
    src = (HERE / "gen_core_kit_hbm.py").read_text()
    assert '"--no-reset-face-home"' in src and "home_resets=not a.no_reset_face_home" in src
