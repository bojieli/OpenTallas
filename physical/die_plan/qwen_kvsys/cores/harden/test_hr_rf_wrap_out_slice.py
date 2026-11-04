"""DIE-KV-64/RF-E 11-03: hr_rf_wrap out_slice / reset_hold (registered write face of qkd_hr_ingest_eng)."""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hr_rf_wrap  # noqa: E402

CORE = """module eng(ck, rst_n, d_v, d_rdy, d_data, in_v, in_rdy, w_v, w_rdy, w_addr, w_data, done_v, done_tag, n_sectors, busy);
  input [0:0] ck;
  input [0:0] rst_n;
  input [0:0] d_v;
  output [0:0] d_rdy;
  input [7:0] d_data;
  input [0:0] in_v;
  output [0:0] in_rdy;
  output [0:0] w_v;
  input [0:0] w_rdy;
  output [3:0] w_addr;
  output [7:0] w_data;
  output [0:0] done_v;
  output [7:0] done_tag;
  output [31:0] n_sectors;
  output [0:0] busy;
endmodule
"""
SPEC = {"resets": ["rst_n"],
        "out_slice": {"v": "w_v", "rdy": "w_rdy", "data": ["w_addr", "w_data"],
                      "done": {"v": "done_v", "tag": "done_tag", "cnt": "n_sectors", "depth": 2,
                               "gate": {"v": "d_v", "rdy": "d_rdy", "fence_bit": "d_data[7]"}},
                      "busy": "busy", "rst": "rst_n"},
        "reset_hold": [{"v": "d_v", "rdy": "d_rdy", "rst": "rst_n"}, {"v": "in_v", "rdy": "in_rdy", "rst": "rst_n"}]}


def test_out_slice_private_port_banks_and_gates():
    text, rep = hr_rf_wrap.transform(CORE, "eng", SPEC)
    top = text[text.index("(* top = 1 *)"):]
    # each data port is driven by its private port flop bank only
    for b in ("w_addr", "w_data"):
        assert f"assign {b} = rf_od_{b};" in top
        assert len(re.findall(rf"\brf_od_{b}\b", top)) == 3          # decl, D, port
        assert f".{b}(rf_c_{b})" in top
    assert "assign w_v = {rf_pv};" in top and "rf_pv <=" in top
    # done released only when the slice is empty or transferring; registered port flops
    assert "wire rf_rel = (rf_qn != 0) && (!rf_ov || w_rdy[0]);" in top
    assert "rf_dv <= rf_rel" in top and "assign done_v = {rf_dv};" in top
    # busy covers the slice and pending dones
    assert "assign busy = {rf_cbusy || rf_ov || (rf_qn != 0) || rf_dvi};" in top
    # descriptor gate: done bound + reset relay; payload gate: reset relay
    assert "assign rf_hold_d_rdy = rf_dhold || !rf_rst_q__rst_n;" in top
    assert "assign rf_hold_in_rdy = !rf_rst_q__rst_n;" in top
    assert ".d_v({d_v[0] && !rf_hold_d_rdy})" in top and ".in_v({in_v[0] && !rf_hold_in_rdy})" in top
    # declared before use
    assert top.index("wire rf_crdy_d_rdy; wire rf_hold_d_rdy;") < top.index("wire rf_dacc")
    assert rep["out_slice"]["added_flops"] > 2 * (4 + 8)
    assert set(rep["input_gates"]) == {"d_v/d_rdy", "in_v/in_rdy"}


def test_out_slice_fail_closed():
    bad = dict(SPEC, out_slice=dict(SPEC["out_slice"], v="w_rdy"))
    with pytest.raises(SystemExit):
        hr_rf_wrap.transform(CORE, "eng", bad)
    bad = dict(SPEC, out_slice=dict(SPEC["out_slice"], done=dict(SPEC["out_slice"]["done"], depth=3)))
    with pytest.raises(SystemExit):
        hr_rf_wrap.transform(CORE, "eng", bad)
    bad = dict(SPEC, reset_hold=[{"v": "in_v", "rdy": "in_rdy", "rst": "d_v"}])
    with pytest.raises(SystemExit):
        hr_rf_wrap.transform(CORE, "eng", bad)
