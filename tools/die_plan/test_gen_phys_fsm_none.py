"""DIE-HEAD-85/HSPLIT 11-07: gen phys exports OT_FSM_NONE_WIRES=hunt for kits whose RTL defines an s81 link gearbox
(ot_s81ph_link_gbx*), so yosys fsm keeps the RX hunt FSM in its RTL encoding and the kit LEC pairs it by name."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_phys  # noqa: E402


def test_gearbox_kit_gets_hunt(tmp_path):
    (tmp_path / "a.sv").write_text("module ot_s81ph_link_gbx_safe3 #(parameter W = 1) (input wire clk);\nendmodule\n")
    assert gen_phys.fsm_none_wires(tmp_path) == ["hunt"]
    assert gen_phys.fsm_none_wires(tmp_path, "st,ek hunt") == ["hunt", "st", "ek"]


def test_other_kit_unchanged(tmp_path):
    (tmp_path / "a.sv").write_text("module top (input wire clk);\n  // ot_s81ph_link_gbx_safe3 u (.clk(clk));\nendmodule\n")
    assert gen_phys.fsm_none_wires(tmp_path) == []
    assert gen_phys.fsm_none_wires(tmp_path, "st") == ["st"]


def test_qc_glue_fsm_modules_get_st(tmp_path):
    (tmp_path / "a.sv").write_text("module ot_qwen_d2d_recovery #(parameter MASTER = 0) (input wire ck);\nendmodule\n")
    assert gen_phys.fsm_none_wires(tmp_path) == ["st"]
    (tmp_path / "a.sv").write_text("module qfd_sys_face_lctx3_core (input wire ck);\nendmodule\n")
    assert gen_phys.fsm_none_wires(tmp_path) == ["st"]
