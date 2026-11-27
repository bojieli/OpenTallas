"""C-LPAD-LEAFDN-SEAT-MISS-C085: seat_match resolves plan relay_sites keys through the KIT-RD-1 rename (k<row>_<stage>), strictly."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_istations as KI  # noqa: E402
import seat_match as SM  # noqa: E402

PKT = ("module m(input clk);\n"
       "  ot_dp_dly #(.W(1), .D(1)) u_y_xd_lpad_a_d_k0_0 (.clk(clk), .d(x), .q(s0));\n"
       "  ot_dp_dly #(.W(1), .D(1)) u_y_xd_lpad_a_d_k0_1 (.clk(clk), .d(s0), .q(s1));\n"
       "  ot_dp_lk #(.W(1)) u_lk_xd_lpad_a_d_k0_1 (.clk(clk), .d(s1), .q(s1q));\n"
       "  ot_dp_dly #(.W(1), .D(1)) u_y_xd_lpad_a_d_k1_0 (.clk(clk), .d(y), .q(t0));\n"
       "endmodule\n")


def judge(keys):
    return SM.judge({k: [1.0, 2.0] for k in keys}, PKT)


def test_plan_key_without_k_resolves_to_the_renamed_stage_of_the_same_row():
    v = judge(["u_y_xd_lpad_a_d_0_0.q", "u_y_xd_lpad_a_d_0_1.q", "u_y_xd_lpad_a_d_0_1.q__rs1", "u_y_xd_lpad_a_d_1_0.q"])
    assert set(v.values()) <= {"OK", "UNKNOWN"}, v


def test_wrong_stage_wrong_row_or_other_chain_stays_dead():
    v = judge(["u_y_xd_lpad_a_d_0_2.q", "u_y_xd_lpad_a_d_2_0.q", "u_y_xd_lpad_b_d_0_0.q", "u_y_xd_lpad_a_d_0_1.r[3]"])
    assert v["u_y_xd_lpad_a_d_0_2.q"] == "DEAD-INST" and v["u_y_xd_lpad_a_d_2_0.q"] == "DEAD-INST" and v["u_y_xd_lpad_b_d_0_0.q"] == "DEAD-INST"


def test_krd_alias_is_exact_only():
    ident = {"u_y_xd_x_p_k0_3"}
    assert SM.krd_alias("u_y_xd_x_p_0_3", ident) == "u_y_xd_x_p_k0_3"
    assert SM.krd_alias("u_y_xd_x_p_0_4", ident) is None and SM.krd_alias("u_y_xd_x_p_1_3", ident) is None
    assert SM.krd_alias("u_y_other_0_3", ident) is None


def test_place_time_seating_tcl_normalises_the_same_rename():
    assert r"regsub {^(u_(?:y|lk)_xd_.*)_k([0-9]+)_([0-9]+)([.]|$)} $n" in KI.RELAY_TCL


def test_relay_split_flop_keys_normalise_the_same_rename():
    """the 16 __rs clones of t27 were never made: rs_key (flop names of rs_split_all) must read u_y_xd_..._k0_3.q as the plan's ..._0_3.q"""
    assert r"regsub {^(u_(?:y|lk)_xd_.*)_k([0-9]+)_([0-9]+)([.]|$)} $k {\1_\2_\3\4} k" in KI.RELAY_SPLIT_TCL


def test_relay_split_clone_keys_seat_when_their_flop_does_and_the_row_names_them():
    keys = ["u_y_xd_lpad_a_d_0_1.q", "u_y_xd_lpad_a_d_0_1.q__rs1", "u_y_xd_lpad_a_d_0_1.q__rs2", "u_y_xd_lpad_a_d_0_2.q__rs1", "u_y_xd_lpad_a_d_0_2.q"]
    rs = {k: [1.0, 2.0] for k in keys}
    clones = {"u_y_xd_lpad_a_d_0_1.q__rs1", "u_y_xd_lpad_a_d_0_2.q__rs1"}
    v = SM.judge(rs, PKT, clones=clones)
    assert v["u_y_xd_lpad_a_d_0_1.q__rs1"] == "OK-CLONE"                 # its flop stage 1 exists, the row names this clone
    assert v["u_y_xd_lpad_a_d_0_1.q__rs2"] == "UNKNOWN"                  # no relay_split row makes rs2: still not judged (fails the lint)
    assert v["u_y_xd_lpad_a_d_0_2.q__rs1"] == "DEAD-INST" and v["u_y_xd_lpad_a_d_0_2.q"] == "DEAD-INST"   # flop of the clone is past the chain
    assert SM.plan_clones({"relay_split": [{"flop": "f", "clones": [{"name": "f__rs1", "sinks": ["s"]}]}]}) == {"f__rs1"}
