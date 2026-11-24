"""pytest: ADV-RAW-RESET-TO-PORT on the QC C1b positive (COORD FABLE FLOW REVIEW: C1b strict died at EMIT sle_su_c.x_ctl_o,
'writer START raw reset rr_t85 drives an output port')."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adv_raw_reset_port as A  # noqa: E402

BODY = """module qfd_qc_sle_su_c(input clk, output [3:0] x_o, output rst_o);
  wire rr_t84, rr_t85, rr_t1;
  ot_dp_rrelay u0 (.clk(clk), .q(rr_t85));
  ot_dp_rrelay u1 (.clk(clk), .q(rr_t1));
  assign rst_o = rr_t85;
endmodule
"""


def ty(raws):
    return {"clock": {"landing_writer_start": {"branches": {"x_ctl_o": {"stages": [{"xy_um": [0, 0], "raw_reset": r} for r in raws]}}},
                      "landing_reader_start": {"branches": {"rd": {"stages": [{"xy_um": [0, 0], "raw_reset": "rr_t1"}]}}}}}


def test_port_driven_detects_assign_and_output():
    assert A.port_driven(BODY) >= {"rst_o", "rr_t85"}
    assert "rr_t1" not in A.port_driven(BODY)


def test_c1b_writer_stage_on_port_relay_flagged():
    st = A.start_stages(ty(["rr_t31", "rr_t85"]))
    bad = A.judge(st, A.port_driven(BODY))
    assert bad == [("writer", "x_ctl_o", 1, "rr_t85")]


def test_clean_plan_passes():
    assert A.judge(A.start_stages(ty(["rr_t31", "rr_t1"])), A.port_driven(BODY)) == []


def test_never_raises():
    assert A.findings(None, "p")[0].startswith("WARN ADV-RAW-RESET-TO-PORT not checked")
