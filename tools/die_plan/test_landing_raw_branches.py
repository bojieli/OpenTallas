"""FE3 literal raw branches: stage originals resolve in the ORIGINAL body (FLOW-9 10-30 peer blocker)."""
import pytest

from landing_raw_branches import RawBranches, RawBranchError

BODY = """
    ot_dp_rrelay u_b (.clk(clk), .d(rst_in), .q(b));
    ot_dp_rrelay u_s0 (.clk(clk), .d(b), .q(s0));
    ot_dp_rrelay u_s1 (.clk(clk), .d(s0), .q(s1));
"""


def cfg(*originals):
    return [dict(name="br", base="b", stages=[dict(original=o, xy_um=[1.0, 2.0]) for o in originals],
                 consumers=["reader:x:0"])]


def emit(g, body=BODY):
    assert g.raw_for("reader:x:0", "s1") == "cland_raw_br_1"
    return g.validate(body + "\n" + "\n".join(g.rtl))


def test_literal_chain_from_original_body_validates():
    g = RawBranches("t", cfg("s0", "s1"), BODY)
    r = emit(g)
    assert r["flops"] == 2 and r["branches"] == 1
    assert [row["original_instance"] for row in g.rows] == ["u_s0", "u_s1"]


def test_generated_copy_cannot_masquerade_as_its_own_original():
    # Before the fix the final combined text resolved cland_raw_br_0 to the generated copy (D = base), so this passed.
    with pytest.raises(RawBranchError, match="generated raw copy"):
        RawBranches("t", cfg("cland_raw_br_0", "s1"), BODY)


def test_original_only_in_generated_text_is_rejected():
    with pytest.raises(RawBranchError, match="not unique in ORIGINAL body"):
        RawBranches("t", cfg("s0", "late_q"), BODY)
    dup = BODY + "    ot_dp_rrelay u_s0b (.clk(clk), .d(b), .q(s0));\n"
    with pytest.raises(RawBranchError, match="not unique in ORIGINAL body"):
        RawBranches("t", cfg("s0", "s1"), dup)


def test_original_predecessor_is_checked_in_original_body():
    with pytest.raises(RawBranchError, match="ORIGINAL s1 D=s0 != literal predecessor b"):
        RawBranches("t", cfg("s1", "s0"), BODY)


def test_final_text_must_keep_the_original_driver_instance():
    g = RawBranches("t", cfg("s0", "s1"), BODY)
    moved = BODY.replace("u_s1 (", "u_s1_new (")
    with pytest.raises(RawBranchError, match="driver u_s1_new != ORIGINAL instance u_s1"):
        emit(g, moved)


def test_generator_wavefront_copy_is_accepted_only_by_its_exact_instance():
    body = BODY + "    ot_dp_rgate u_g (.clk(clk), .d(s1), .q(rst_n_t3));\n"
    c = cfg("s0", "s1", "cland_reset_bx")
    g = RawBranches("t", c, body)
    gen = "    wire cland_reset_bx;\n    ot_dp_rrelay u_cland_rst_bx (.clk(clk), .d(s1), .q(cland_reset_bx));"
    assert g.raw_for("reader:x:0", "cland_reset_bx") == "cland_raw_br_2"
    r = g.validate(body + "\n" + gen + "\n" + "\n".join(g.rtl))
    assert r["flops"] == 3
    g2 = RawBranches("t", c, body)
    g2.raw_for("reader:x:0", "cland_reset_bx")
    fake = "    wire cland_reset_bx;\n    ot_dp_rrelay u_cland_lrst_bx (.clk(clk), .d(s1), .q(cland_reset_bx));"
    with pytest.raises(RawBranchError, match="driver u_cland_lrst_bx != ORIGINAL instance u_cland_rst_bx"):
        g2.validate(body + "\n" + fake + "\n" + "\n".join(g2.rtl))


def test_local_reset_copy_cannot_be_an_original():
    with pytest.raises(RawBranchError, match="not unique in ORIGINAL body"):
        RawBranches("t", cfg("cland_lrst_s0", "s1"), BODY)
