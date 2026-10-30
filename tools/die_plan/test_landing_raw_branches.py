"""FE3 literal raw branches (landing_raw_branches.RawBranches): every copied stage must name an ORIGINAL relay.
FLOW 10-30 finding: validate() resolved stage.original against original+generated text, so a relay that exists only in
generated landing logic (or a generated raw-branch Q) could stand in for an original chain node."""
import os, sys
import pytest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from landing_raw_branches import RawBranches, RawBranchError

BODY = """
    wire r0, r1, r2;
    ot_dp_rrelay u_r0 (.clk(clk), .d(rst_raw_n), .q(r0));
    ot_dp_rrelay u_r1 (.clk(clk), .d(r0), .q(r1));
    ot_dp_rrelay u_r2 (.clk(clk), .d(r1), .q(r2));
"""


def graph(stages, body=BODY, base="r0"):
    cfg = [dict(name="b", base=base, stages=[dict(original=o, xy_um=[1.0, 2.0]) for o in stages], consumers=["origin"])]
    g = RawBranches("t", cfg, body, [10.0, 10.0])
    out = g.raw_for("origin", stages[-1])
    return g, out


def emitted(g, extra=""):
    return BODY + "\n" + "\n".join(g.rtl) + extra


def test_genuine_original_chain_passes():
    g, net = graph(["r1", "r2"])
    assert net == "cland_raw_b_1"
    r = g.validate(emitted(g))
    assert r["flops"] == 2 and r["branches"] == 1


def test_relay_only_in_generated_text_is_rejected():
    # u_fake exists only in generated logic with the right D: the old combined-text lookup accepted it
    g, _ = graph(["fake"])
    fake = "\n    ot_dp_rrelay u_fake (.clk(clk), .d(r0), .q(fake));"
    with pytest.raises(RawBranchError, match="exactly one same-clk plain relay"):
        g.validate(emitted(g, fake))


def test_generated_raw_branch_net_as_original_is_rejected():
    cfg = [dict(name="b", base="r0", stages=[dict(original="r1", xy_um=[1, 1]),
                                             dict(original="cland_raw_b_0", xy_um=[1, 1])], consumers=["origin"])]
    g = RawBranches("t", cfg, BODY, [10, 10])
    g.raw_for("origin", "cland_raw_b_0")
    with pytest.raises(RawBranchError, match="generated raw branch net"):
        g.validate(emitted(g))


def test_wrong_original_parent_is_rejected():
    g, _ = graph(["r2"])           # r2's original D is r1, not the base r0
    with pytest.raises(RawBranchError, match="literal predecessor"):
        g.validate(emitted(g))


def test_duplicated_or_changed_original_driver_is_rejected():
    g, _ = graph(["r1"])
    dup = "\n    ot_dp_rrelay u_r1b (.clk(clk), .d(r0), .q(r1));"
    with pytest.raises(RawBranchError):
        g.validate(emitted(g, dup))
    g, _ = graph(["r1"])
    changed = emitted(g).replace("u_r1 (.clk(clk), .d(r0), .q(r1))", "u_r1 (.clk(clk), .d(r2), .q(r1))")
    with pytest.raises(RawBranchError, match="changed or duplicated"):
        g.validate(changed)
