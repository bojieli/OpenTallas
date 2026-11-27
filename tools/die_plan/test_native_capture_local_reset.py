"""Native capture banks may opt into an exact depth-preserving local reset copy."""
import pytest

from clock_landings import LandingError, Landings


RAW = """    ot_dp_rrelay u_rrl_378 (.clk(clk), .d(rst_rl_377), .q(rst_rl_378));  // raw wire depth 7 @ (10, 20)
    ot_dp_rrelay u_rrl_362 (.clk(clk), .d(rst_rl_361), .q(rst_n_t47));  // boot tap depth 8 @ (50, 80)
    wire rst_n = rst_n_t47;
"""
CAPTURE = """    ot_dp_st #(.W(1)) u_bin_i_hp_fault_N_q_d1 (.clk(clk), .rst_n(rst_n), .d(d), .ea(e), .q(q), .eq(eq));
"""
PEER = CAPTURE.replace("u_bin_i_hp_fault_N_q_d1", "u_bin_peer")


def emit(body):
    landing = object.__new__(Landings)
    landing.types = {"ei": {"clock": {"landing_local_resets": [
        dict(name="hp_fault_t70", raw="rst_rl_378", xy_um=[28.62, 54.0],
             consumers=["u_bin_i_hp_fault_N_q_d1"])
    ]}}}
    landing.collect = False
    landing.reset_placements = {}
    new_body, logic = landing._local_resets_with_body("ei", "ei", body, [])
    return new_body, logic, landing.reset_placements["ei"]["local_resets"][0]


def test_native_capture_local_reset_keeps_peers_and_exact_depth():
    body, logic, copy = emit(RAW + CAPTURE + PEER)
    assert body == RAW + CAPTURE.replace(".rst_n(rst_n)", ".rst_n(cland_lrst_hp_fault_t70)") + PEER
    assert any(".d(rst_rl_378)" in line for line in logic)
    assert (copy["raw"], copy["depth"], copy["added_flops"], copy["added_cycles"]) == ("rst_rl_378", 8, 1, 0)


@pytest.mark.parametrize(("body", "message"), [
    (RAW + CAPTURE.replace("ot_dp_st ", "different_flop "), "not an emitted native EQ input bank"),
    (RAW.replace("= rst_n_t47;", "= missing_reset;") + CAPTURE, "no registered wavefront depth"),
    (RAW + CAPTURE + CAPTURE, "not one emitted landing instance"),
])
def test_unproved_native_capture_local_reset_is_rejected(body, message):
    with pytest.raises(LandingError, match=message):
        emit(body)
