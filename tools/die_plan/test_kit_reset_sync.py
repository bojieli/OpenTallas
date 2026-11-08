"""DIE-HBM-90-TNAME 11-07, class (f): HBM q_hub_nw kit_rtl stopped on "different source files named
ot_reset_sync.sv" (main rtl/lib vs the hbm-bind-6/tip2 r18h5_bundle copy, an older version of the same module that the
bundle's svc leaves instantiate).  bind.kit_reset_sync keeps the bound closure's copy and adds the tool copy only when no
closure source defines the module; a parameter the kept copy lacks, or a positional override, fails closed."""
import inspect
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import bind  # noqa: E402
import kit_assembly  # noqa: E402

OLD = """`default_nettype none
module ot_reset_sync #(
    parameter integer ASYNC_STAGES = 2
) (
    input  wire clk,
    input  wire async_rst_n,
    output wire sync_rst_n
);
    (* async_reg = "true" *) reg [ASYNC_STAGES-1:0] reset_pipe;
    always @(posedge clk or negedge async_rst_n)
        if (!async_rst_n) reset_pipe <= '0;
        else reset_pipe <= {reset_pipe[ASYNC_STAGES-2:0], 1'b1};
    assign sync_rst_n = reset_pipe[ASYNC_STAGES-1];
endmodule
"""
NEW = OLD.replace("parameter integer ASYNC_STAGES = 2\n",
                  "parameter integer ASYNC_STAGES = 2,\n    parameter integer OUTPUT_COPIES = 1,\n"
                  "    parameter integer TREE = 0\n")
LEAF = """module ot_hbm_svc_async_fifo (input wire wr_clk, input wire both_reset, output wire wr_reset);
    ot_reset_sync u_wr_reset(.clk(wr_clk),.async_rst_n(both_reset),.sync_rst_n(wr_reset));
endmodule
"""
WRAP = """module hbm_arch_q_hub__q_hub_nw (input wire clk, input wire arst_n);
    wire rst_n;
    ot_reset_sync #(.ASYNC_STAGES(2)) u_rst_sync (.clk(clk), .async_rst_n(arst_n), .sync_rst_n(rst_n));
endmodule
"""


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "main/rtl/lib").mkdir(parents=True)
    (tmp_path / "bundle/rtl/lib").mkdir(parents=True)
    rs = tmp_path / "main/rtl/lib/ot_reset_sync.sv"
    rs.write_text(NEW)
    old = tmp_path / "bundle/rtl/lib/ot_reset_sync.sv"
    old.write_text(OLD)
    leaf = tmp_path / "bundle/ot_hbm_svc_async_fifo.sv"
    leaf.write_text(LEAF)
    wrap = tmp_path / "hbm_arch_q_hub__q_hub_nw.sv"
    wrap.write_text(WRAP)
    return rs, old, leaf, wrap


def test_base_list_collides(tree):
    rs, old, leaf, wrap = tree
    with pytest.raises(ValueError, match="different source files named ot_reset_sync.sv"):
        kit_assembly.dedupe_sources([wrap, rs, leaf, old], wrap.parent / "alias")


def test_closure_copy_is_kept_and_tool_copy_not_added(tree):
    rs, old, leaf, wrap = tree
    assert bind.kit_reset_sync("q_hub_nw", rs, [wrap, leaf, old]) is None
    out = kit_assembly.dedupe_sources([wrap, leaf, old], wrap.parent / "alias")
    assert [p.name for p in out].count("ot_reset_sync.sv") == 1 and old in out


def test_no_closure_copy_adds_the_tool_copy(tree):
    rs, _old, leaf, wrap = tree
    assert bind.kit_reset_sync("q_su31", rs, [wrap, leaf]) == rs.resolve()


def test_missing_parameter_fails_closed(tree):
    rs, old, leaf, wrap = tree
    wrap.write_text(WRAP.replace("#(.ASYNC_STAGES(2))", "#(.ASYNC_STAGES(2), .OUTPUT_COPIES(4))"))
    with pytest.raises(bind.BindError, match=r"lacks parameter\(s\) \['OUTPUT_COPIES'\]"):
        bind.kit_reset_sync("q_hub_nw", rs, [wrap, leaf, old])


def test_positional_override_fails_closed(tree):
    rs, old, leaf, wrap = tree
    wrap.write_text(WRAP.replace("#(.ASYNC_STAGES(2))", "#(3)"))
    with pytest.raises(bind.BindError, match="positional ot_reset_sync"):
        bind.kit_reset_sync("q_hub_nw", rs, [wrap, leaf, old])


def test_comment_mentions_are_ignored(tree):
    rs, old, leaf, wrap = tree
    leaf.write_text(LEAF + "// ot_reset_sync #(.TREE(1)) is not used here\n")
    assert bind.kit_reset_sync("q_hub_nw", rs, [wrap, leaf, old]) is None


def test_kit_rtl_routes_the_tool_copy_through_kit_reset_sync():
    src = inspect.getsource(bind.cmd_kit_rtl)
    assert "rs = kit_reset_sync(tn, rs, kit_srcs)" in src and "[rs] if rs else []" in src


def test_byte_identical_closure_copy_keeps_the_old_list(tree):
    rs, old, leaf, wrap = tree
    old.write_bytes(rs.read_bytes())
    assert bind.kit_reset_sync("q_x", rs, [wrap, leaf, old]) == rs.resolve()
