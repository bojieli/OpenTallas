"""bind_verify HOLDFORM-1: the ot_dp_hd hold-pad Liberty buffer gets a wire model in the verify read (QC-FW-FORMS 11-12)."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import bind_verify as V
import gen_rtl


def test_model_written_when_bound_cells_use_hb4(tmp_path):
    cells = tmp_path / "bind_cells.sv"
    cells.write_text(gen_rtl.HOLD_CELLS)
    out = V.hold_pad_models([str(cells)], [], tmp_path)
    assert out == [str(tmp_path / "hold_pad_models.sv")]
    txt = Path(out[0]).read_text()
    assert "module HB4xp67_ASAP7_75t_R (input wire A, output wire Y);" in txt and "assign Y = A;" in txt


def test_no_model_without_hold_pads(tmp_path):
    f = tmp_path / "t.sv"
    f.write_text("module t(input a, output y); assign y = a; endmodule\n")
    assert V.hold_pad_models([str(f)], [], tmp_path) == []
    assert not (tmp_path / "hold_pad_models.sv").exists()


def test_no_model_when_a_lib_defines_the_cell(tmp_path):
    cells = tmp_path / "bind_cells.sv"
    cells.write_text(gen_rtl.HOLD_CELLS)
    lib = tmp_path / "cells_lib.v"
    lib.write_text("module HB4xp67_ASAP7_75t_R (input A, output Y); assign Y = A; endmodule\n")
    assert V.hold_pad_models([str(cells)], [str(lib)], tmp_path) == []
